"""
sales_agent.py

Sales Intelligence Agent for Lili's Company.
Orchestrates the full merchant intelligence pipeline via Claude tool use:
  1. Search the merchant RAG database for prospects
  2. Scrape fresh data from each merchant's website
  3. Analyze merchant fit and pain points (opportunity score 1-10)
  4. Generate personalized cold emails for high-fit merchants (score >= 7)
  5. Export a campaign-ready CSV: company, contact, subject, email_body

Usage:
    python sales_agent.py
    python sales_agent.py --criteria "fashion merchants with no email marketing"
    python sales_agent.py --criteria "beauty stores in USA" --output campaign.csv
"""

import argparse
import csv
import json
import os
import sys
from pathlib import Path

import anthropic

# Allow sibling module imports when running from any directory
_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT))

from build_rag import query_merchants
from scrape_merchants import enrich_domain
from analyze_merchants import analyze_merchant as _claude_analyze
from generate_emails import generate_emails as _claude_generate_emails

# ── Configuration ─────────────────────────────────────────────────────────────

MODEL       = "claude-opus-4-6"
TOP_K       = 20
MIN_SCORE   = 7

SAAS_DESCRIPTION = (
    "A Shopify app that helps fashion and beauty merchants automate email marketing, "
    "recover abandoned carts, and build customer loyalty programs."
)

SYSTEM_PROMPT = f"""You are a Sales Intelligence Agent for Lili's Company.

Lili's Product: {SAAS_DESCRIPTION}

Your goal: Find Shopify merchants who would benefit from Lili's product, analyze their \
needs, and generate personalized outreach emails.

You have access to four tools:
  - search_merchants(query, top_k)  — Search the merchant RAG database
  - scrape_website(domain)           — Get live data from a merchant's homepage
  - analyze_merchant(domain, profile) — Score merchant fit 1-10 and identify pain points
  - generate_email(domain, analysis)  — Write 3 cold email versions (A/B/C)

Workflow you MUST follow step-by-step:
1. Call search_merchants with the user's criteria, requesting top_k={TOP_K}.
2. For EACH domain returned, call scrape_website to get fresh live data.
3. For EACH domain, build a profile string combining the search result data and the
   scraped data, then call analyze_merchant.
4. Read the OPPORTUNITY SCORE from each analysis. Call generate_email ONLY for
   merchants whose score is >= {MIN_SCORE}.
5. After processing every candidate, provide a brief summary:
     • Total candidates found
     • How many scored >= {MIN_SCORE}
     • How many campaigns generated

Be methodical — process EVERY merchant returned by search_merchants before finishing."""


# ── Shared campaign state ──────────────────────────────────────────────────────
# Each tool writes results into this dict; main() reads it after the loop ends.
_campaign: dict[str, dict] = {}


# ── Tool implementations ───────────────────────────────────────────────────────

def _tool_search_merchants(query: str, top_k: int = TOP_K) -> str:
    """Query the ChromaDB RAG index and seed _campaign with basic info."""
    try:
        results = query_merchants(query, top_k=int(top_k))
    except Exception as exc:
        return json.dumps({"error": f"RAG query failed: {exc}. Run: python build_rag.py build"})

    if not results:
        return json.dumps({
            "merchants": [],
            "count": 0,
            "note": "No results found. Run: python build_rag.py build",
        })

    for r in results:
        domain = r["domain"]
        _campaign.setdefault(domain, {}).update({
            "domain":        domain,
            "business_name": r.get("business_name") or domain,
            "industry":      r.get("industry", ""),
            "country":       r.get("country", ""),
            "tech_stack":    r.get("tech_stack", ""),
            "has_reviews":   r.get("has_reviews", ""),
            "has_loyalty":   r.get("has_loyalty", ""),
            "has_email":     r.get("has_email", ""),
            "similarity":    r.get("similarity", 0),
        })

    payload = [
        {
            "domain":        r["domain"],
            "business_name": r.get("business_name", r["domain"]),
            "industry":      r.get("industry", ""),
            "country":       r.get("country", ""),
            "tech_stack":    r.get("tech_stack", ""),
            "has_reviews":   r.get("has_reviews", ""),
            "has_loyalty":   r.get("has_loyalty", ""),
            "has_email":     r.get("has_email", ""),
            "similarity":    r.get("similarity", 0),
        }
        for r in results
    ]
    return json.dumps({"merchants": payload, "count": len(payload)})


def _tool_scrape_website(domain: str) -> str:
    """Scrape fresh homepage data and store it in _campaign."""
    firecrawl_key = os.getenv("FIRECRAWL_API_KEY")
    try:
        data = enrich_domain(domain, firecrawl_key)
    except Exception as exc:
        data = {"error": str(exc)}

    _campaign.setdefault(domain, {})["enrichment"] = data
    return json.dumps(data)


def _tool_analyze_merchant(domain: str, profile: str) -> str:
    """
    Analyze a merchant's fit for Lili's product.
    Augments the caller-supplied profile with any enrichment data stored in
    _campaign so the AI has the richest context possible.
    """
    enrichment = _campaign.get(domain, {}).get("enrichment", {})
    if enrichment and "error" not in enrichment:
        enrich_parts = [
            f"description: {enrichment.get('description', '')}",
            f"products: {', '.join(enrichment.get('products', []))}",
            f"tools_detected: {', '.join(enrichment.get('tools_detected', []))}",
            f"price_range: {enrichment.get('price_range', '')}",
            f"blog_topics: {', '.join(enrichment.get('blog_topics', []))}",
        ]
        proof = enrichment.get("social_proof", {})
        if isinstance(proof, dict):
            enrich_parts += [
                f"review_count: {proof.get('review_count', 'unknown')}",
                f"has_testimonials: {proof.get('has_testimonials', False)}",
            ]
        full_profile = profile + "\n\nLIVE SCRAPED DATA:\n" + "\n".join(enrich_parts)
    else:
        full_profile = profile

    client = anthropic.Anthropic()
    try:
        result = _claude_analyze(client, full_profile, SAAS_DESCRIPTION)
    except Exception as exc:
        return json.dumps({"error": str(exc)})

    _campaign.setdefault(domain, {})["analysis"] = result
    return json.dumps(result)


def _tool_generate_email(domain: str, analysis: str) -> str:
    """
    Generate A/B/C cold email versions for a merchant.
    Prefers the stored analysis over the serialized string Claude passes in,
    so the full structured data reaches the email generator.
    """
    analysis_dict = _campaign.get(domain, {}).get("analysis")
    if not analysis_dict:
        try:
            analysis_dict = json.loads(analysis)
        except (json.JSONDecodeError, ValueError):
            analysis_dict = {"raw_response": analysis}

    client = anthropic.Anthropic()
    try:
        emails = _claude_generate_emails(client, analysis_dict)
    except Exception as exc:
        return json.dumps({"error": str(exc)})

    _campaign.setdefault(domain, {})["emails"] = emails
    versions = [k for k in emails if k.startswith("version_")]
    return json.dumps({"status": "emails generated", "versions": versions})


# ── Tool schema (JSON Schema for the Messages API) ─────────────────────────────

TOOLS: list[dict] = [
    {
        "name": "search_merchants",
        "description": (
            "Search the merchant RAG database for Shopify prospects matching the given criteria. "
            "Returns up to top_k candidates with domain, industry, country, tech stack, "
            "and similarity score."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Natural language search query describing target merchants, "
                        "e.g. 'fashion merchants with no email marketing'"
                    ),
                },
                "top_k": {
                    "type": "integer",
                    "description": f"Maximum results to return (default {TOP_K})",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "scrape_website",
        "description": (
            "Scrape fresh live data from a merchant's homepage: description, product "
            "categories, detected SaaS tools, price range, blog topics, and review count."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Merchant website domain, e.g. 'example-brand.com'",
                }
            },
            "required": ["domain"],
        },
    },
    {
        "name": "analyze_merchant",
        "description": (
            "Deep analysis of a merchant's fit for Lili's product. "
            "Returns OPPORTUNITY SCORE (1-10), PAIN POINTS DETECTED, "
            "PERSONALIZATION HOOKS, and RECOMMENDED APPROACH. "
            "Only call generate_email if score >= 7."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Merchant website domain",
                },
                "profile": {
                    "type": "string",
                    "description": (
                        "Formatted merchant profile text including business name, domain, "
                        "country, tech stack, industry, and any other known details."
                    ),
                },
            },
            "required": ["domain", "profile"],
        },
    },
    {
        "name": "generate_email",
        "description": (
            "Generate 3 personalized cold email versions for a merchant: "
            "A (problem-focused), B (social proof), C (curiosity hook). "
            "Call this ONLY for merchants with opportunity_score >= 7."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Merchant website domain",
                },
                "analysis": {
                    "type": "string",
                    "description": "JSON string returned by analyze_merchant",
                },
            },
            "required": ["domain", "analysis"],
        },
    },
]

TOOL_DISPATCH: dict[str, any] = {
    "search_merchants": lambda inp: _tool_search_merchants(**inp),
    "scrape_website":   lambda inp: _tool_scrape_website(**inp),
    "analyze_merchant": lambda inp: _tool_analyze_merchant(**inp),
    "generate_email":   lambda inp: _tool_generate_email(**inp),
}


# ── Agentic loop ───────────────────────────────────────────────────────────────

def run_agent(criteria: str) -> None:
    """
    Run the sales intelligence agent with a manual agentic loop.
    Streams each API call to avoid timeouts; loops until stop_reason == 'end_turn'.
    """
    client = anthropic.Anthropic()
    messages: list[dict] = [{
        "role": "user",
        "content": (
            f"Find Shopify merchants for outreach using these target criteria:\n\n"
            f"{criteria}\n\n"
            "Follow the full workflow: search → scrape every domain → analyze every domain "
            "→ generate emails for merchants scoring >= 7."
        ),
    }]

    print(f"\n{'=' * 60}")
    print("Sales Intelligence Agent — Lili's Company")
    print(f"{'=' * 60}")
    print(f"Criteria : {criteria}")
    print(f"Model    : {MODEL}")
    print(f"Min score: {MIN_SCORE}/10")
    print(f"{'=' * 60}\n")

    while True:
        # Stream the response to avoid HTTP timeout on large outputs
        with client.messages.stream(
            model=MODEL,
            max_tokens=4096,
            thinking={"type": "adaptive"},
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        ) as stream:
            response = stream.get_final_message()

        # Print any narrative text Claude produced this turn
        for block in response.content:
            if block.type == "text" and block.text.strip():
                print(f"\n[Agent] {block.text.strip()}")

        # Check termination
        if response.stop_reason == "end_turn":
            print("\n[Agent] Workflow complete.")
            break

        if response.stop_reason != "tool_use":
            print(f"\n[Agent] Stopped unexpectedly: {response.stop_reason}")
            break

        # Append the full assistant message (including tool_use blocks) to history
        messages.append({"role": "assistant", "content": response.content})

        # Dispatch all tool calls produced in this turn
        tool_results: list[dict] = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            name = block.name
            inp  = block.input

            # Pretty-print the call
            args_preview = ", ".join(
                f"{k}={str(v)[:60]!r}" for k, v in inp.items()
            )
            print(f"\n  ▶ {name}({args_preview})")

            fn  = TOOL_DISPATCH.get(name)
            raw = fn(inp) if fn else json.dumps({"error": f"Unknown tool: {name}"})

            # Brief progress hint
            try:
                parsed = json.loads(raw)
                if "count" in parsed:
                    print(f"    ✓ {parsed['count']} merchants returned")
                elif "error" in parsed:
                    print(f"    ✗ {parsed['error']}")
                elif "status" in parsed:
                    print(f"    ✓ {parsed['status']}")
                elif "OPPORTUNITY SCORE" in parsed:
                    opp   = parsed["OPPORTUNITY SCORE"]
                    score = opp.get("score", "?") if isinstance(opp, dict) else opp
                    print(f"    ✓ opportunity score: {score}/10")
                elif "description" in parsed or "tools_detected" in parsed:
                    tools_found = len(parsed.get("tools_detected", []))
                    print(f"    ✓ scraped ({tools_found} tools detected)")
            except (json.JSONDecodeError, TypeError, AttributeError):
                pass

            tool_results.append({
                "type":        "tool_result",
                "tool_use_id": block.id,
                "content":     raw,
            })

        # Return all tool results as a single user message
        messages.append({"role": "user", "content": tool_results})


# ── CSV export ─────────────────────────────────────────────────────────────────

def export_csv(output_path: str) -> int:
    """
    Write campaign results to CSV, sorted by score descending.
    Only includes merchants with opportunity_score >= MIN_SCORE.
    Columns: company, contact, opportunity_score,
             subject, email_body,
             subject_B, email_body_B,
             subject_C, email_body_C
    """
    rows: list[dict] = []

    for domain, data in _campaign.items():
        analysis = data.get("analysis", {})
        emails   = data.get("emails", {})

        # Parse opportunity score (may be int or nested dict)
        opp = analysis.get("OPPORTUNITY SCORE", {})
        if isinstance(opp, dict):
            score = opp.get("score", 0)
        else:
            score = opp
        try:
            score = int(score)
        except (ValueError, TypeError):
            score = 0

        if score < MIN_SCORE:
            continue

        ver_a = emails.get("version_A", {})
        ver_b = emails.get("version_B", {})
        ver_c = emails.get("version_C", {})

        rows.append({
            "company":      data.get("business_name", domain),
            "contact":      domain,
            "opportunity_score": score,
            "subject":      ver_a.get("subject", ""),
            "email_body":   ver_a.get("body", ""),
            "subject_B":    ver_b.get("subject", ""),
            "email_body_B": ver_b.get("body", ""),
            "subject_C":    ver_c.get("subject", ""),
            "email_body_C": ver_c.get("body", ""),
        })

    rows.sort(key=lambda r: r["opportunity_score"], reverse=True)

    if rows:
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

    return len(rows)


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sales Intelligence Agent — Lili's Company.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python sales_agent.py\n"
            '  python sales_agent.py --criteria "beauty stores with no loyalty program"\n'
            '  python sales_agent.py --criteria "high-spend fashion merchants" --output outreach.csv'
        ),
    )
    parser.add_argument(
        "--criteria",
        default=(
            "fashion and beauty Shopify merchants with no email marketing "
            "or loyalty program"
        ),
        help="Target criteria for prospect search (natural language)",
    )
    parser.add_argument(
        "--output",
        default="campaign.csv",
        help="Output CSV file path (default: campaign.csv)",
    )
    args = parser.parse_args()

    run_agent(args.criteria)

    count = export_csv(args.output)

    print(f"\n{'=' * 60}")
    if count:
        print(f"Campaign CSV → '{args.output}'")
        print(f"{count} merchant(s) with opportunity score >= {MIN_SCORE}")
    else:
        print("No merchants met the minimum score threshold.")
        print(f"MIN_SCORE={MIN_SCORE}  |  candidates processed={len(_campaign)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
