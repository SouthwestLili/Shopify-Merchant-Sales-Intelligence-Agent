# Shopify Merchant Sales Intelligence System — Project Overview

> Author: Lili's Company
> Language: Python 3.12
> Core Technologies: Claude AI · ChromaDB · BeautifulSoup · Flask

---

## 1. Background and Core Problem

### What Problem Are We Solving?

Suppose you have a Shopify SaaS product (e.g., an app that helps merchants run email marketing and loyalty programs) and you want to identify the best potential customers to pitch.

**Pain points of the traditional approach:**
- Manually browsing hundreds of merchant websites is extremely inefficient
- Generic cold emails yield terrible conversion rates
- No way to tell which merchants genuinely have pain points and are willing to pay
- No systematic screening mechanism — massive waste of sales time

**Our solution:**

```
Raw data (hundreds of merchants)
        ↓  Filter by target industry
Targeted merchant list (dozens)
        ↓  Scrape live website data
Rich merchant profiles
        ↓  Claude AI analyzes buying intent
Opportunity score + pain point analysis
        ↓  Claude AI generates personalized emails
Three cold email variants (A/B/C testing)
        ↓  Vector database stores everything, supports natural-language queries
Reusable knowledge base
        ↓  AI Agent auto-orchestrates the entire pipeline
campaign.csv (ready-to-send outreach list)
```

---

## 2. Overall Architecture: Six-Stage Pipeline

```
tech_stack.csv
      │
      ▼ [Stage 1] Filter
filter_shopify_merchants.py  ──→  shopify_merchants.csv
      │
      ▼ [Stage 2] Scrape
scrape_merchants.py  ──→  merchant_enrichment.json
      │
      ▼ [Stage 3] Analyze
analyze_merchants.py  ──→  merchant_analysis.json
      │
      ▼ [Stage 4] Generate Emails
generate_emails.py  ──→  merchant_emails.json
      │
      ▼ [Stage 5] Vectorize
build_rag.py  ──→  chroma_db/ (vector database)
      │
      ▼ [Stage 6] AI Agent Orchestration
sales_agent.py  ──→  campaign.csv (final outreach list)
      │
      ▼ [Visualization]
dashboard.py  ──→  http://localhost:5000 (web UI)
```

---

## 3. Stage-by-Stage Breakdown

---

### Stage 1: Filter Merchants — `filter_shopify_merchants.py`

#### Problem to Solve
The raw dataset (`tech_stack.csv`) contains hundreds or thousands of merchant records.
We only care about:
1. Merchants **running on the Shopify platform** (tech stack match)
2. Merchants in **target industries** (fashion / beauty / etc.)

#### Data Source
`tech_stack.csv` — a commercial dataset recording the technology stacks used by websites.
Can be obtained from:
- [BuiltWith](https://builtwith.com/) (paid)
- [Datanyze](https://www.datanyze.com/) (paid)
- [Hunter.io](https://hunter.io/)
- Self-scraped (SimilarWeb / Wappalyzer)
- Custom order from data vendors using the built-in data acquisition prompt

#### Implementation
```python
# Core logic: two-step filtering
df[df["technologies"].str.contains("Shopify")]               # filter by tech stack
df[df["title"].str.contains("fashion|beauty", case=False)]   # filter by industry keywords
```

**Key design decisions:**
- Use `title` (page title) rather than a dedicated industry column to infer industry, because real datasets rarely have clean industry classifications
- Use a customizable keyword list, flexibly adaptable to different products' target markets
- Output retains only 5 columns: `business_name, domain, title, country, tech_spend`

#### Output
`shopify_merchants.csv` — a targeted merchant list (reduced from hundreds to dozens of rows)

---

### Stage 2: Scrape Merchant Websites — `scrape_merchants.py`

#### Problem to Solve
CSV data is static and potentially outdated.
We need to **capture merchants' real-time status**:
- What marketing tools are they currently using?
- Do they have a review system? A loyalty program?
- What products do they sell? What's the price range? Do they have a blog?

#### Implementation: Dual-Engine Scraping

**Engine 1: Firecrawl API (preferred, requires paid API key)**
- Pros: handles JavaScript-rendered pages, returns clean Markdown
- Use case: when a merchant's site uses React/Next.js or similar frontend frameworks

**Engine 2: BeautifulSoup (free, automatic fallback)**
- Parses HTML, extracts meta tags, links, and text
- No API key required; suitable for most Shopify stores (server-side rendered)

```python
# Fallback logic
if FIRECRAWL_API_KEY:
    data = scrape_with_firecrawl(url)  # prefer Firecrawl
if not data:
    data = scrape_with_bs4(url)         # fall back to BeautifulSoup
```

#### Data Fields Extracted

| Field | Extraction Method | Purpose |
| --- | --- | --- |
| `description` | meta description tag | AI analysis of merchant positioning |
| `products` | `/collections/` link paths | Understand product categories |
| `tools_detected` | script src regex matching | Discover technology gaps |
| `price_range` | page price regex extraction | Gauge merchant scale |
| `blog_topics` | `/blog/` link text | Understand content marketing direction |
| `social_proof` | review count regex | Assess brand trust level |

#### SaaS Tool Detection (22 Tools)

We detect which tools a merchant is using by scanning for known script domains in the page HTML:

```python
TOOL_SIGNATURES = {
    "Klaviyo":  r"klaviyo\.com",           # email marketing
    "Yotpo":    r"yotpo\.com",             # review system
    "Smile.io": r"smile\.io|cdn\.sweettooth",  # loyalty
    "Gorgias":  r"gorgias\.com",           # customer support
    # ... 22 tools total
}
```

**Core insight:** If a merchant lacks Klaviyo → email marketing tool opportunity. No Yotpo/Judge.me → review tool opportunity. These "gaps" are our sales entry points.

#### Rate Limiting
- 2-second delay between requests (to avoid IP bans)
- 10-second timeout per request before skipping (to avoid hanging on unresponsive sites)

#### Output
`merchant_enrichment.json` — an enrichment data dictionary keyed by domain

---

### Stage 3: AI Opportunity Analysis — `analyze_merchants.py`

#### Problem to Solve
With raw merchant data in hand, we need to determine:
- Is this merchant **worth pursuing**? (Opportunity score 1–10)
- What are their **pain points**? (What tools are missing? What operational issues do they have?)
- **How to personalize outreach?** (What topic makes the best opening?)

#### Why AI Instead of a Rules Engine?
A rules engine (e.g., "add one point if they have no Klaviyo") can only make simple judgments.
Claude comprehensively understands: the merchant's brand positioning, product price range, target market, and technology stack combination, producing **business-insight-driven** analysis rather than mechanical scoring.

#### Implementation

**Model:** `claude-opus-4-6` (strongest analytical capability)
**Thinking mode:** `thinking: {type: "adaptive"}` (adaptive deep reasoning)
**Output format:** Claude is instructed to return JSON (for easy programmatic processing)

**Prompt structure:**
```
You are a SaaS sales intelligence analyst.

Merchant information: {merchant_data}
Our product: {saas_description}

Analyze and return JSON:
1. MERCHANT SNAPSHOT — 2-3 sentences describing the merchant
2. PAIN POINTS DETECTED — 3-5 technology/operational pain points
3. OPPORTUNITY SCORE — 1-10 score + one-sentence rationale
4. PERSONALIZATION HOOKS — 3 specific details that can be referenced in outreach
5. RECOMMENDED APPROACH — best contact channel / timing / value proposition
```

#### Technical Details
- Uses **streaming output** to avoid HTTP timeouts
- Automatically strips Markdown code fences (```json ... ```) from Claude's response
- On parse failure, saves raw text without interrupting the overall pipeline

#### Output
`merchant_analysis.json` — one structured analysis record per merchant

---

### Stage 4: Generate Cold Emails — `generate_emails.py`

#### Problem to Solve
Pain points have been identified — now we need to **turn them into sendable emails**.
Generic template emails have open rates below 5%; personalized emails can reach 20–35%.

#### A/B/C Three-Version Testing Strategy

| Version | Strategy | Best For |
| --- | --- | --- |
| A — Problem-driven | Directly address the pain point upfront | Rational decision-makers, technical leads |
| B — Social proof | Reference success stories of similar customers | Risk-averse decision-makers |
| C — Curiosity hook | Open with a provocative question | Founders, brand owners |

Generating three versions enables A/B/C testing to find which opening style works best for different merchant types.

#### Email Rules (Written into the Prompt)
- Subject line: no more than 8 words, no emoji, no salesy feel
- Opening: must reference the merchant's specific information (not a generic template)
- Body: maximum 4 sentences, no filler
- CTA: only one call to action, low barrier ("Quick 15-minute chat?" not "Book a demo")
- Tone: peer-to-peer conversation, not a vendor pitch

#### Output
`merchant_emails.json` — three complete email versions per merchant (subject + body)

---

### Stage 5: Vector Database — `build_rag.py`

#### Problem to Solve
The first four stages transform merchant data into structured analysis,
but if we want to query it anytime using natural language (e.g., "find beauty merchants without a review app"), we need a **semantic search** system.

#### Why RAG (Retrieval-Augmented Generation)?
- SQL queries require exact field names — not suited for fuzzy semantic queries
- Keyword search misses synonyms ("reviews" vs. "testimonials")
- RAG converts text into vectors and retrieves based on semantic similarity

#### Implementation: ChromaDB + Local Embedding Model

**Vector database:** ChromaDB (local persistence, no cloud service needed)
**Embedding model (two options):**
- Preferred: OpenAI `text-embedding-3-small` (better quality, requires API key)
- Fallback: `sentence-transformers all-MiniLM-L6-v2` (completely free, runs locally)

#### Chunking Strategy (4 Chunks per Merchant)

| Chunk | Content | Best Query Type |
| --- | --- | --- |
| `::identity` | Merchant name, description, products, price range, country | "Merchants selling skincare" |
| `::techstack` | Tool list, tech spend, tool presence flags | "Merchants without a loyalty program" |
| `::social` | Blog, review count, testimonials presence | "Merchants with an active blog" |
| `::full` | All three chunks combined | Broad, general queries |

**Why chunk at all?**
A single vector for the entire merchant profile degrades query accuracy.
With chunking, different query types hit the most relevant chunk.

#### Metadata Filtering
Each chunk carries structured metadata that enables precise filtering:
```python
metadata = {
    "has_reviews": "True/False",
    "has_loyalty": "True/False",
    "has_email":   "True/False",
    "industry":    "fashion/beauty/other",
    "company_size": "micro/small/medium/large",
}
```

#### Output
`chroma_db/` — local vector database directory supporting natural-language queries

---

### Stage 6: AI Sales Agent — `sales_agent.py`

#### Problem to Solve
The first five stages are a manually run, step-by-step pipeline.
Can we have an Agent that decides its own execution order and ties everything together?

#### Design: Tool Use (Agentic Loop)

Claude is equipped with 4 tools and orchestrates them autonomously:

```
User input: "Find fashion merchants without email marketing"
        ↓
Claude decides:
  1. Call search_merchants("fashion no email marketing")
  2. For each result, call scrape_website(domain)
  3. For each result, call analyze_merchant(domain, profile)
  4. Only for those scoring >= 7, call generate_email(domain, analysis)
  5. Report results
```

**The Agent doesn't follow a hardcoded script.** Claude decides what to do next based on the results each tool returns.

#### Tool Design

| Tool | Internal Call | Data Flow |
| --- | --- | --- |
| `search_merchants(query, top_k)` | `build_rag.py → query_merchants()` | RAG returns candidate list |
| `scrape_website(domain)` | `scrape_merchants.py → enrich_domain()` | Writes to `_campaign[domain]["enrichment"]` |
| `analyze_merchant(domain, profile)` | `analyze_merchants.py → analyze_merchant()` | Writes to `_campaign[domain]["analysis"]` |
| `generate_email(domain, analysis)` | `generate_emails.py → generate_emails()` | Writes to `_campaign[domain]["emails"]` |

#### Shared State Design
All tools share a single Python dictionary `_campaign`.
Tools write into it during execution; after the Agent finishes, the data is exported to CSV.
This avoids passing large payloads between tools — Claude only needs to pass `domain` as the key.

#### Manual Agentic Loop (Not Auto Tool Runner)
```python
while True:
    response = stream → get_final_message()
    if stop_reason == "end_turn": break        # Claude is done
    if stop_reason == "tool_use":              # Claude wants to call a tool
        execute all tool calls
        return results to Claude
        continue loop
```
**Advantage of a manual loop:** real-time progress printing, custom logic injection, and pre/post-tool processing hooks.

#### Output
`campaign.csv` — sorted by score, containing only merchants scoring ≥ 7, with all three email versions

---

### Visualization Layer — `dashboard.py` + `templates/dashboard.html`

#### Problem to Solve
JSON and CSV files are unfriendly to non-technical users.
A UI is needed so the sales team can browse, filter, and copy emails directly.

#### Technology Choices

**Backend: Flask** (Python lightweight web framework)
- 3 routes: main page, merchant data API, stats API
- Automatically merges all output files and returns unified JSON

**Frontend: Plain HTML + Bootstrap 5 + Vanilla JS**
- No npm / webpack / React — zero build steps
- All styles loaded from CDN
- Native `fetch()` calls Flask APIs to dynamically render content

#### UI Features

| Feature | Implementation |
| --- | --- |
| Stats bar | `/api/stats` returns totals / qualified / emailed counts |
| Merchant card grid | `/api/merchants` feeds JS to dynamically generate HTML |
| Search & filter | Pure client-side filtering (no re-fetching API, real-time response) |
| Score color coding | CSS: green (≥9), blue (≥7), gray (<7) |
| Detail modal | Bootstrap Modal + JS populates content |
| A/B/C email switcher | JS tab switching; copy button uses `navigator.clipboard` |

---

## 4. Full Data Flow Diagram

```
[Raw Data]
tech_stack.csv (from third-party data vendors, or self-scraped)
      │
      ▼
[Filter] — keyword matching Shopify + industry
shopify_merchants.csv (target merchants)
      │
      ├──────────────────────────────────────────┐
      ▼                                          ▼
[Scrape] Visit each merchant's website    [Vectorize] Embed merchant
merchant_enrichment.json                  profiles into ChromaDB
(tools, prices, products, reviews)        (for semantic search)
      │
      ▼
[AI Analysis] Claude scores + identifies pain points
merchant_analysis.json
(score, snapshot, hooks, recommendations)
      │
      ▼
[Generate Emails] Claude writes three cold email variants
merchant_emails.json
(A/B/C each with subject + body)
      │
      ▼
[Agent Orchestration] Fully auto-orchestrates all steps above
campaign.csv (high-scoring merchants only, ready to send)
      │
      ▼
[Dashboard] Visual review + one-click email copy
http://localhost:5000
```

---

## 5. Key Technical Decisions and Rationale

### Why Claude Instead of GPT?

| Dimension | Claude's Advantage |
| --- | --- |
| Instruction following | Stricter JSON format compliance, fewer parsing errors |
| Long context | 200K token window — ideal for large merchant profiles |
| Analytical depth | Adaptive Thinking yields more insightful analysis |
| Tool Use | Official SDK has mature Tool Use support, stable agent orchestration |

### Why ChromaDB Instead of Pinecone / Weaviate?

- **Runs locally** — no cloud account registration, no fees, no data privacy concerns
- File-based persistence (`chroma_db/` directory) — survives restarts without data loss
- Native Python integration — seamlessly fits the rest of the project
- For a scale of dozens to hundreds of merchants, performance is more than sufficient

### Why 4 Chunks per Merchant?

A single vector cannot simultaneously optimize for all query types:
- Searching for "merchants selling skincare" → `::identity` chunk has higher recall
- Searching for "merchants without a loyalty program" → `::techstack` chunk has higher recall
- Broad queries → `::full` chunk as a catch-all

The 4-chunk strategy strikes a balance between storage cost (4×) and query precision.

### Why Generate Three Email Versions (A/B/C)?

The cold email opening style has a huge impact on conversion rates, but the best approach varies by audience:
- Technical / operations leads → more responsive to "problem-driven" (Version A)
- Conservative decision-makers → more responsive to "social proof" (Version B)
- Founders / brand owners → more responsive to "curiosity hook" (Version C)

Generating all three upfront allows sales reps to pick based on the recipient's role — or test all three simultaneously.

---

## 6. How to Run

### Full Pipeline (One-Time Run)

```bash
# Install dependencies
pip install pandas anthropic requests beautifulsoup4 chromadb sentence-transformers flask

# Set API key
export ANTHROPIC_API_KEY="your-key"

# Step 1: Filter target merchants
python filter_shopify_merchants.py

# Step 2: Scrape website data
python scrape_merchants.py

# Step 3: AI opportunity analysis
python analyze_merchants.py

# Step 4: Generate cold emails
python generate_emails.py

# Step 5: Build vector database
python build_rag.py build

# Step 6: Run AI Agent (fully auto-orchestrated)
python sales_agent.py --criteria "fashion merchants no email marketing"

# View results
python dashboard.py   # open http://localhost:5000
```

### Test the Dashboard Without Spending API Credits

```bash
python create_sample_data.py   # generates sample data for real merchants in shopify_merchants.csv
python dashboard.py             # open http://localhost:5000
```

---

## 7. Extension Directions

| Direction | How to Implement |
| --- | --- |
| Integrate real email sending | Connect `campaign.csv` output to SendGrid / Mailchimp API |
| Scheduled auto-runs | Use a cron job to periodically execute `filter → scrape → analyze` |
| Support more industries | Modify `--industries` argument to expand to baby products, pets, sports, etc. |
| Merchant score history tracking | Add SQLite to record each analysis run and track score changes over time |
| Multi-language emails | Add a language parameter to the email prompt for French, German, etc. |
| Slack notifications | Push a high-score merchant summary to a Slack channel when Agent finishes |
| Larger datasets | Swap `tech_stack.csv` for a larger data source — the system scales linearly |

---

*This document describes a complete automated path from raw commercial data to ready-to-send personalized outreach emails.*
*Each stage can be run independently, or fully auto-orchestrated via `sales_agent.py`.*
