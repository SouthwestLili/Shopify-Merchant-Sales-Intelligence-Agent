"""
build_rag.py

Builds a ChromaDB vector store from scraped merchant data, then exposes a
natural-language query function to retrieve matching merchant profiles.

Embedding priority:
  1. OpenAI text-embedding-3-small  (if OPENAI_API_KEY is set)
  2. sentence-transformers all-MiniLM-L6-v2  (free, local — no API key needed)

Usage:
    # Build the collection
    python build_rag.py build

    # Query the collection
    python build_rag.py query "Which merchants sell beauty products with no review app?"

    # Build + immediately query
    python build_rag.py build --query "merchants with Klaviyo but no loyalty program"
"""

import argparse
import json
import os
import sys
from pathlib import Path

import chromadb
import pandas as pd

COLLECTION_NAME = "merchant_profiles"
ENRICHMENT_FILE = "merchant_enrichment.json"
MERCHANTS_CSV   = "shopify_merchants.csv"
DB_DIR          = "./chroma_db"
TOP_K           = 10

REVIEW_APPS  = {"yotpo", "judge.me", "stamped.io", "okendo", "loox"}
LOYALTY_APPS = {"smile.io", "loyaltylion"}
EMAIL_APPS   = {"klaviyo", "mailchimp", "omnisend", "privy", "drip"}
CHAT_APPS    = {"intercom", "zendesk", "gorgias", "tidio", "drift", "livechat"}


# ──────────────────────────────────────────────
#  Embedding backend
# ──────────────────────────────────────────────

def get_embedding_function():
    """Return a ChromaDB-compatible embedding function."""
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
            print("Using OpenAI text-embedding-3-small")
            return OpenAIEmbeddingFunction(
                api_key=api_key,
                model_name="text-embedding-3-small",
            )
        except Exception as e:
            print(f"OpenAI embedding init failed ({e}), falling back to sentence-transformers")

    try:
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
        print("Using sentence-transformers all-MiniLM-L6-v2 (local, free)")
        return SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    except ImportError:
        print("Error: install sentence-transformers:  pip install sentence-transformers", file=sys.stderr)
        sys.exit(1)


# ──────────────────────────────────────────────
#  Data loading + enrichment merging
# ──────────────────────────────────────────────

def load_merchants(csv_path: str, enrichment_path: str) -> list[dict]:
    """Merge filtered CSV data with scraped enrichment JSON into one list."""
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    df.columns = df.columns.str.strip().str.lower()

    enrichment: dict = {}
    if Path(enrichment_path).exists():
        with open(enrichment_path, encoding="utf-8") as f:
            enrichment = json.load(f)
    else:
        print(f"Warning: '{enrichment_path}' not found — building index from CSV only.")

    merchants = []
    for _, row in df.iterrows():
        domain = str(row.get("domain", "")).strip()
        enc = enrichment.get(domain, {})
        merchants.append({
            "domain":        domain,
            "business_name": str(row.get("business_name", "") or ""),
            "title":         str(row.get("title", "") or ""),
            "country":       str(row.get("country", "") or ""),
            "tech_spend":    row.get("tech_spend"),
            # enrichment fields
            "description":   enc.get("description", ""),
            "products":      enc.get("products", []),
            "tools_detected":enc.get("tools_detected", []),
            "price_range":   enc.get("price_range", ""),
            "blog_topics":   enc.get("blog_topics", []),
            "social_proof":  enc.get("social_proof", {}),
        })
    return merchants


# ──────────────────────────────────────────────
#  Chunking
# ──────────────────────────────────────────────

def infer_industry(merchant: dict) -> str:
    text = (merchant["title"] + " " + merchant["description"]).lower()
    for kw in ("beauty", "skincare", "cosmetics", "makeup"):
        if kw in text:
            return "beauty"
    for kw in ("fashion", "apparel", "clothing", "dress", "wear"):
        if kw in text:
            return "fashion"
    return "other"


def infer_company_size(tech_spend) -> str:
    try:
        spend = float(tech_spend)
        if spend < 5_000:  return "micro"
        if spend < 20_000: return "small"
        if spend < 60_000: return "medium"
        return "large"
    except (TypeError, ValueError):
        return "unknown"


def tools_lower(merchant: dict) -> set[str]:
    return {t.lower() for t in merchant["tools_detected"]}


def chunk_merchant(merchant: dict) -> list[dict]:
    """
    Split one merchant into 4 focused text chunks.
    Each chunk carries the full metadata dict for filtering.
    Returns list of {id, text, metadata}.
    """
    domain   = merchant["domain"]
    tools    = tools_lower(merchant)
    industry = infer_industry(merchant)
    size     = infer_company_size(merchant["tech_spend"])

    metadata = {
        "domain":        domain,
        "business_name": merchant["business_name"],
        "industry":      industry,
        "company_size":  size,
        "tech_spend":    str(merchant["tech_spend"] or ""),
        "country":       merchant["country"],
        "tech_stack":    ", ".join(merchant["tools_detected"]),
        "has_reviews":   str(bool(tools & REVIEW_APPS)),
        "has_loyalty":   str(bool(tools & LOYALTY_APPS)),
        "has_email":     str(bool(tools & EMAIL_APPS)),
        "has_chat":      str(bool(tools & CHAT_APPS)),
        "price_range":   merchant["price_range"],
    }

    chunks = []

    # Chunk 1 — Identity + what they sell
    products_text = ", ".join(merchant["products"]) if merchant["products"] else "not detected"
    c1 = (
        f"Store: {merchant['business_name'] or domain}\n"
        f"Domain: {domain}\n"
        f"Title: {merchant['title']}\n"
        f"Description: {merchant['description'] or 'not available'}\n"
        f"Products/Categories: {products_text}\n"
        f"Price Range: {merchant['price_range'] or 'not visible'}\n"
        f"Country: {merchant['country'] or 'unknown'}"
    )
    chunks.append({"id": f"{domain}::identity", "text": c1, "metadata": metadata})

    # Chunk 2 — Tech stack and tools in use
    tools_list = merchant["tools_detected"] or ["none detected"]
    has_review  = "YES" if tools & REVIEW_APPS  else "NO"
    has_loyalty = "YES" if tools & LOYALTY_APPS else "NO"
    has_email   = "YES" if tools & EMAIL_APPS   else "NO"
    has_chat    = "YES" if tools & CHAT_APPS    else "NO"
    c2 = (
        f"Store: {domain}\n"
        f"Tech stack: {', '.join(tools_list)}\n"
        f"Monthly tech spend estimate: ${merchant['tech_spend'] or 'unknown'}\n"
        f"Has review app: {has_review}\n"
        f"Has loyalty program: {has_loyalty}\n"
        f"Has email marketing: {has_email}\n"
        f"Has live chat/support: {has_chat}"
    )
    chunks.append({"id": f"{domain}::techstack", "text": c2, "metadata": metadata})

    # Chunk 3 — Content and social proof
    blog_text  = ", ".join(merchant["blog_topics"]) if merchant["blog_topics"] else "no blog detected"
    proof      = merchant["social_proof"]
    review_cnt = proof.get("review_count") if isinstance(proof, dict) else None
    has_test   = proof.get("has_testimonials", False) if isinstance(proof, dict) else False
    c3 = (
        f"Store: {domain}\n"
        f"Blog/content topics: {blog_text}\n"
        f"Review count: {review_cnt if review_cnt is not None else 'unknown'}\n"
        f"Has testimonials on site: {'yes' if has_test else 'no'}\n"
        f"Industry: {industry}\n"
        f"Company size estimate: {size}"
    )
    chunks.append({"id": f"{domain}::social", "text": c3, "metadata": metadata})

    # Chunk 4 — Full profile summary (dense, good for broad queries)
    c4 = f"{c1}\n\n{c2}\n\n{c3}"
    chunks.append({"id": f"{domain}::full", "text": c4, "metadata": metadata})

    return chunks


# ──────────────────────────────────────────────
#  Build collection
# ──────────────────────────────────────────────

def build_collection(csv_path: str, enrichment_path: str) -> chromadb.Collection:
    merchants = load_merchants(csv_path, enrichment_path)
    print(f"Loaded {len(merchants)} merchants")

    ef = get_embedding_function()
    client = chromadb.PersistentClient(path=DB_DIR)

    # Drop existing collection to rebuild fresh
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"Dropped existing '{COLLECTION_NAME}' collection")
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )

    all_chunks = []
    for m in merchants:
        all_chunks.extend(chunk_merchant(m))

    print(f"Embedding {len(all_chunks)} chunks ({len(merchants)} merchants × 4 chunks)...")

    # Upsert in batches of 50
    BATCH = 50
    for i in range(0, len(all_chunks), BATCH):
        batch = all_chunks[i:i + BATCH]
        collection.upsert(
            ids       = [c["id"]       for c in batch],
            documents = [c["text"]     for c in batch],
            metadatas = [c["metadata"] for c in batch],
        )
        print(f"  Upserted chunks {i + 1}–{min(i + BATCH, len(all_chunks))}")

    print(f"\nCollection '{COLLECTION_NAME}' built with {collection.count()} vectors in '{DB_DIR}'")
    return collection


# ──────────────────────────────────────────────
#  Query
# ──────────────────────────────────────────────

def query_merchants(question: str, top_k: int = TOP_K) -> list[dict]:
    ef = get_embedding_function()
    client = chromadb.PersistentClient(path=DB_DIR)

    try:
        collection = client.get_collection(name=COLLECTION_NAME, embedding_function=ef)
    except Exception:
        print(f"Error: collection '{COLLECTION_NAME}' not found. Run:  python build_rag.py build", file=sys.stderr)
        sys.exit(1)

    # Query more candidates than needed, then deduplicate by domain
    results = collection.query(
        query_texts=[question],
        n_results=min(top_k * 4, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    seen_domains: dict[str, dict] = {}
    docs      = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    for doc, meta, dist in zip(docs, metadatas, distances):
        domain = meta["domain"]
        if domain not in seen_domains:
            seen_domains[domain] = {
                "domain":        domain,
                "business_name": meta.get("business_name", ""),
                "industry":      meta.get("industry", ""),
                "company_size":  meta.get("company_size", ""),
                "country":       meta.get("country", ""),
                "price_range":   meta.get("price_range", ""),
                "tech_stack":    meta.get("tech_stack", ""),
                "has_reviews":   meta.get("has_reviews", ""),
                "has_loyalty":   meta.get("has_loyalty", ""),
                "has_email":     meta.get("has_email", ""),
                "has_chat":      meta.get("has_chat", ""),
                "similarity":    round(1 - dist, 4),
                "matched_chunk": doc[:200] + "..." if len(doc) > 200 else doc,
            }
        if len(seen_domains) >= top_k:
            break

    return list(seen_domains.values())


def print_results(question: str, results: list[dict]) -> None:
    print(f"\nQuery: \"{question}\"")
    print(f"Top {len(results)} matches:\n")
    print("-" * 70)
    for i, r in enumerate(results, 1):
        name = r["business_name"] or r["domain"]
        print(f"{i:2}. {name}  ({r['domain']})")
        print(f"    Industry: {r['industry']} | Size: {r['company_size']} | Country: {r['country']}")
        print(f"    Price: {r['price_range'] or 'n/a'} | Similarity: {r['similarity']}")
        print(f"    Tools: {r['tech_stack'] or 'none'}")
        print(f"    Reviews: {r['has_reviews']} | Loyalty: {r['has_loyalty']} | Email: {r['has_email']}")
        print()


# ──────────────────────────────────────────────
#  CLI
# ──────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Build and query a RAG index of merchant profiles.")
    sub = parser.add_subparsers(dest="command", required=True)

    # build
    p_build = sub.add_parser("build", help="Embed and store merchant profiles in ChromaDB")
    p_build.add_argument("--csv",        default=MERCHANTS_CSV,   help="Filtered merchant CSV")
    p_build.add_argument("--enrichment", default=ENRICHMENT_FILE, help="Scraped enrichment JSON")
    p_build.add_argument("--query",      default="",              help="Optional query to run immediately after build")

    # query
    p_query = sub.add_parser("query", help="Query the merchant profile index")
    p_query.add_argument("question", help="Natural language question")
    p_query.add_argument("--top-k", type=int, default=TOP_K, help="Number of results (default: 10)")

    args = parser.parse_args()

    if args.command == "build":
        build_collection(args.csv, args.enrichment)
        if args.query:
            results = query_merchants(args.query)
            print_results(args.query, results)

    elif args.command == "query":
        results = query_merchants(args.question, top_k=args.top_k)
        print_results(args.question, results)


if __name__ == "__main__":
    main()
