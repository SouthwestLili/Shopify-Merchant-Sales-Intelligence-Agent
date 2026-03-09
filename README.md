# Shopify Merchant Sales Intelligence Agent

## Who Can Use This System

While building it, I realized the same system could actually be useful for multiple players in the Shopify ecosystem.

## [IDEA-EN](./idea-en.md) | [项目构想-中文](./idea-cn.md)

**1️⃣ Shopify itself**
It could identify merchants who might benefit from products like Shopify Email or Shopify POS.

**2️⃣ Shopify app companies**
Tools like Klaviyo, Yotpo, and Gorgias constantly need to find merchants who need their products.
This system detects technology gaps and surfaces high-intent leads automatically.

**3️⃣ Brands or suppliers**
Manufacturers looking for Shopify stores to sell their products could also use the same system to identify potential partners.

---

## Overview

This project is a six-stage pipeline:

1. **Filter** — Scans a raw tech-stack CSV to identify Shopify merchants in target industries.
2. **Scrape** — Visits each merchant's homepage to extract live data: description, products, tools in use, pricing, blog topics, social proof.
3. **Analyze** — Feeds the enriched profiles to Claude AI for structured sales intelligence (pain points, opportunity score, personalization hooks).
4. **Email** — Generates 3 A/B/C cold email variants per merchant using the analysis.
5. **RAG** — Embeds all merchant profiles into ChromaDB for natural-language querying (e.g. "beauty merchants with no review app").
6. **Agent** — A Claude-powered Sales Intelligence Agent that orchestrates tools to find prospects, analyze fit, and produce a campaign-ready CSV.

```text
tech_stack.csv
     │
     ▼
filter_shopify_merchants.py  →  shopify_merchants.csv
                                        │
                                        ▼
                              scrape_merchants.py  →  merchant_enrichment.json
                                        │
                                        ▼
                              analyze_merchants.py  →  merchant_analysis.json
                                        │
                                        ▼
                              generate_emails.py  →  merchant_emails.json
                                        │
                                        ▼
                              build_rag.py  →  chroma_db/  (queryable vector store)
                                        │
                                        ▼
                              sales_agent.py  →  campaign.csv  (campaign-ready outreach)
```

---

## Module: `filter_shopify_merchants.py`

### What it does

1. Loads a tech-stack CSV (with fallback encoding detection)
2. Normalises column names (lowercase, strip whitespace)
3. Filters rows where the `technologies` column contains `"Shopify"`
4. Filters rows where the `title` column contains any target industry keyword (e.g., `fashion`, `beauty`)
5. Exports the matched rows to `shopify_merchants.csv`

### Input CSV expected columns

| Column | Description |
| --- | --- |
| `domain` | Merchant website domain |
| `title` | Page title (used for industry keyword matching) |
| `business_name` | Company name |
| `country` | Country or region |
| `tech_spend` | Estimated monthly technology spend |
| `technologies` | List of detected technologies (must contain `"Shopify"`) |
| `seo_score` | SEO score (not exported) |
| `crawled_at` | Crawl timestamp (not exported) |

### Output CSV columns

| Column | Description |
| --- | --- |
| `business_name` | Company name |
| `domain` | Website domain |
| `title` | Page title |
| `country` | Country or region |
| `tech_spend` | Estimated monthly technology spend |

---

## Usage

```bash
# Quickstart — run this in the project directory
cd "d:/_0_Carleton_University_Computer_Science_Student_Document/SIDE-PROJECT/Shopify-Merchant-Sales-Intelligence-Agent"
python filter_shopify_merchants.py
```

Equivalent full command:

```bash
python filter_shopify_merchants.py --input tech_stack.csv --industries fashion beauty --output shopify_merchants.csv
```

---

### More examples

```bash
# Default: filters for fashion + beauty, reads tech_stack.csv
python filter_shopify_merchants.py

# Custom input file and industries
python filter_shopify_merchants.py --input my_data.csv --industries fashion apparel clothing

# Custom column names (if your CSV uses different headers)
python filter_shopify_merchants.py --tech-col technologies --industry-col title

# Full options
python filter_shopify_merchants.py \
  --input tech_stack.csv \
  --industries fashion beauty \
  --output shopify_merchants.csv \
  --tech-col technologies \
  --industry-col title
```

### Arguments

| Argument | Default | Description |
| --- | --- | --- |
| `--input` | `tech_stack.csv` | Path to input CSV file |
| `--industries` | `fashion beauty` | One or more industry keywords |
| `--output` | `shopify_merchants.csv` | Output CSV path |
| `--tech-col` | `technologies` | Column containing tech stack data |
| `--industry-col` | `title` | Column to match industry keywords against |

---

## Data Collection Prompt

Use the following prompt to collect or request the tech-stack dataset from a data provider or scraping tool:

```text
Collect a CSV dataset of e-commerce merchants with the following fields:

- domain: the merchant's website domain
- title: the page title of their storefront
- business_name: the registered or displayed business name
- country: country or region of operation
- seo_score: an SEO quality score (0–100)
- tech_spend: estimated monthly technology spend in USD
- crawled_at: ISO 8601 timestamp of when the data was collected
- technologies: a list of detected technologies (e.g., Shopify, Klaviyo, Google Analytics)

Target: merchants using Shopify as their e-commerce platform,
operating in the fashion, beauty, or lifestyle verticals.
Minimum dataset size: 500 rows.
Output format: UTF-8 encoded CSV.
```

---

## Module: `scrape_merchants.py`

### Scraping flow

1. Loads `shopify_merchants.csv` and reads the `domain` column
2. For each domain, attempts Firecrawl API first (if `FIRECRAWL_API_KEY` is set), then falls back to BeautifulSoup
3. Extracts live data from the merchant homepage
4. Rate-limits to 1 request every 2 seconds; skips on timeout > 10s
5. Exports results to `merchant_enrichment.json`

### Data extracted

| Field | Description |
| --- | --- |
| `description` | Meta description or first paragraph |
| `products` | Collection slugs from `/collections/` links |
| `price_range` | Min–max prices visible on homepage |
| `tools_detected` | Matched tools from 20+ known SaaS signatures |
| `blog_topics` | Link text from `/blog/` or `/blogs/` URLs |
| `social_proof` | Review count and whether testimonials are present |

### Tools detected (signatures built-in)

Chat & Support, Email & Pop-ups, Reviews, Loyalty, Analytics/Ads, Search & UX:
`Intercom`, `Zendesk`, `Gorgias`, `Tidio`, `Drift`, `LiveChat`, `Klaviyo`, `Mailchimp`, `Privy`, `Omnisend`, `Yotpo`, `Judge.me`, `Stamped.io`, `Okendo`, `Loox`, `Smile.io`, `LoyaltyLion`, `Google Analytics`, `Meta Pixel`, `TikTok Pixel`, `Searchanise`, `Rebuy`

### Running the scraper

```bash
# With BeautifulSoup only (no API key needed)
python scrape_merchants.py

# With Firecrawl (set API key first)
export FIRECRAWL_API_KEY="your-key"
python scrape_merchants.py
```

### Scraper arguments

| Argument | Default | Description |
| --- | --- | --- |
| `--input` | `shopify_merchants.csv` | Filtered merchant CSV |
| `--output` | `merchant_enrichment.json` | Output JSON file |

### Scraper output format

```json
{
  "example-brand.com": {
    "description": "Premium handmade candles for every occasion.",
    "products": ["Candles", "Gift Sets", "Home Fragrance"],
    "tools_detected": ["Klaviyo", "Yotpo", "Google Analytics"],
    "price_range": "$18 – $85",
    "blog_topics": ["Candle Care Tips", "Holiday Gift Ideas"],
    "social_proof": { "review_count": 312, "has_testimonials": true },
    "source": "beautifulsoup"
  }
}
```

### Environment variable (optional)

```bash
export FIRECRAWL_API_KEY="your-firecrawl-key"   # optional — enables richer extraction
```

---

## Module: `analyze_merchants.py`

### How it works

1. Loads `shopify_merchants.csv` (output from the filter step)
2. For each merchant row, formats the profile as structured text
3. Calls Claude (`claude-opus-4-6`) with the sales intelligence prompt
4. Parses the JSON response from Claude
5. Exports all analyses to `merchant_analysis.json`

### Analysis prompt

The prompt instructs Claude to return a JSON object containing:

| Field | Description |
| --- | --- |
| `MERCHANT SNAPSHOT` | 2–3 sentence summary of what they sell and their scale |
| `PAIN POINTS DETECTED` | 3–5 tech stack gaps or operational problems |
| `OPPORTUNITY SCORE` | 1–10 fit score with one-sentence reasoning |
| `PERSONALIZATION HOOKS` | 3 specific details to reference in outreach |
| `RECOMMENDED APPROACH` | Best channel, timing, and key value prop |

### Running the analyzer

```bash
# Quickstart — runs after filter_shopify_merchants.py
python analyze_merchants.py
```

Equivalent full command:

```bash
python analyze_merchants.py \
  --input shopify_merchants.csv \
  --saas "Your SaaS product description here" \
  --output merchant_analysis.json
```

### Analyzer arguments

| Argument | Default | Description |
| --- | --- | --- |
| `--input` | `shopify_merchants.csv` | Filtered merchant CSV |
| `--saas` | Email marketing + loyalty app description | Your product/service description |
| `--output` | `merchant_analysis.json` | Output JSON file |

### Output format

```json
[
  {
    "merchant": {
      "business_name": "Example Brand",
      "domain": "example-brand.com"
    },
    "analysis": {
      "MERCHANT SNAPSHOT": "...",
      "PAIN POINTS DETECTED": ["...", "..."],
      "OPPORTUNITY SCORE": { "score": 8, "reasoning": "..." },
      "PERSONALIZATION HOOKS": ["...", "..."],
      "RECOMMENDED APPROACH": { "channel": "email", "timing": "...", "value_prop": "..." }
    }
  }
]
```

### Environment variable required

```bash
export ANTHROPIC_API_KEY="your-api-key"
```

---

## Module: `generate_emails.py`

### Email generation flow

1. Loads `merchant_analysis.json` (output from the analyze step)
2. For each merchant, serializes the full analysis as context
3. Calls Claude (`claude-opus-4-6`) to write 3 cold email versions (A/B/C)
4. Parses subject lines and bodies from each version
5. Exports all email sets to `merchant_emails.json`

### Email versions

| Version | Strategy |
| --- | --- |
| A | Problem-focused — leads with the merchant's detected pain point |
| B | Social proof — leads with a similar customer success story |
| C | Curiosity hook — leads with a provocative question |

### Running the email generator

```bash
# Quickstart — runs after analyze_merchants.py
python generate_emails.py
```

Equivalent full command:

```bash
python generate_emails.py \
  --input merchant_analysis.json \
  --output merchant_emails.json
```

### Email generator arguments

| Argument | Default | Description |
| --- | --- | --- |
| `--input` | `merchant_analysis.json` | Analysis JSON from analyze_merchants.py |
| `--output` | `merchant_emails.json` | Output JSON file |

### Email output format

```json
[
  {
    "merchant": {
      "business_name": "Example Brand",
      "domain": "example-brand.com"
    },
    "emails": {
      "version_A": {
        "subject": "Your cart recovery is leaking revenue",
        "body": "Noticed you're running Shopify without an abandoned cart flow..."
      },
      "version_B": {
        "subject": "How [Similar Brand] 3x'd repeat purchases",
        "body": "..."
      },
      "version_C": {
        "subject": "Quick question about your loyalty strategy",
        "body": "..."
      }
    }
  }
]
```

---

## Module: `build_rag.py`

### RAG flow

1. Loads `shopify_merchants.csv` and `merchant_enrichment.json`
2. Chunks each merchant into 4 focused segments (identity, tech stack, social proof, full profile)
3. Adds structured metadata per chunk: `domain`, `industry`, `company_size`, `tech_stack`, `has_reviews`, `has_loyalty`, `has_email`, `has_chat`
4. Embeds all chunks using **sentence-transformers all-MiniLM-L6-v2** (free, local) or **OpenAI text-embedding-3-small** (if `OPENAI_API_KEY` is set)
5. Stores vectors in a persistent **ChromaDB** collection named `merchant_profiles`

### Chunking strategy

| Chunk | Content |
| --- | --- |
| `::identity` | Business name, title, description, products, price range, country |
| `::techstack` | All detected tools, tech spend, tool category flags |
| `::social` | Blog topics, review count, testimonials, industry, size |
| `::full` | All three combined — best for broad queries |

### Running the RAG module

```bash
# Build the vector index
python build_rag.py build

# Query the index
python build_rag.py query "beauty merchants with no review app"

# Build and query in one command
python build_rag.py build --query "merchants using Klaviyo but no loyalty program"
```

### RAG arguments

**`build` subcommand:**

| Argument | Default | Description |
| --- | --- | --- |
| `--csv` | `shopify_merchants.csv` | Filtered merchant CSV |
| `--enrichment` | `merchant_enrichment.json` | Scraped enrichment JSON |
| `--query` | _(empty)_ | Optional query to run immediately after build |

**`query` subcommand:**

| Argument | Default | Description |
| --- | --- | --- |
| `question` | _(required)_ | Natural language question |
| `--top-k` | `10` | Number of results to return |

### Example queries

```bash
python build_rag.py query "Which merchants sell beauty products with no review app installed?"
python build_rag.py query "Fashion stores with Klaviyo but no loyalty program"
python build_rag.py query "High-spend merchants without live chat support"
python build_rag.py query "Small brands in USA with active blog content"
```

### Environment variables

```bash
export OPENAI_API_KEY="your-key"    # optional — uses text-embedding-3-small
                                    # if not set, falls back to free local model
```

---

## Full Pipeline

```bash
# Step 1 — filter merchants
python filter_shopify_merchants.py

# Step 2 — scrape merchant homepages
python scrape_merchants.py

# Step 3 — analyze with Claude
python analyze_merchants.py

# Step 4 — generate cold emails
python generate_emails.py

# Step 5 — build RAG index and query
python build_rag.py build
python build_rag.py query "your question here"

# Step 6 — run the sales intelligence agent
python sales_agent.py
python sales_agent.py --criteria "fashion merchants with no email marketing" --output campaign.csv
```

---

## Module: `sales_agent.py`

### Agent overview

A Claude-powered Sales Intelligence Agent for Lili's Company.
Runs an autonomous agentic loop using 4 Claude tools to find prospects, enrich them with live data, score their fit, and write personalized outreach — then exports a campaign-ready CSV.

### Agent workflow

1. **Search** — Queries the ChromaDB RAG index for up to 20 matching merchants
2. **Scrape** — Visits each merchant's homepage to collect fresh data
3. **Analyze** — Calls Claude to score merchant fit (1–10) and identify pain points
4. **Filter** — Proceeds to email generation only for merchants with `opportunity_score >= 7`
5. **Email** — Generates 3 cold email versions (A/B/C) per qualified merchant
6. **Export** — Writes a campaign CSV sorted by opportunity score

### Tools available to the agent

| Tool | Description |
| --- | --- |
| `search_merchants(query, top_k)` | Natural-language search over the ChromaDB merchant index |
| `scrape_website(domain)` | Live homepage scrape: description, products, tools detected, prices |
| `analyze_merchant(domain, profile)` | Claude sales analysis: score, pain points, hooks, recommended approach |
| `generate_email(domain, analysis)` | Claude writes 3 A/B/C cold email versions |

### Running the agent

```bash
# Default: searches for fashion/beauty merchants with no email marketing or loyalty program
python sales_agent.py

# Custom criteria
python sales_agent.py --criteria "beauty stores in USA with no review app"

# Custom output file
python sales_agent.py --criteria "high-spend fashion merchants" --output outreach.csv
```

### Agent arguments

| Argument | Default | Description |
| --- | --- | --- |
| `--criteria` | `"fashion and beauty Shopify merchants with no email marketing or loyalty program"` | Natural language target criteria |
| `--output` | `campaign.csv` | Output CSV file path |

### Agent output format

`campaign.csv` — one row per qualified merchant (score >= 7), sorted by score descending:

| Column | Description |
| --- | --- |
| `company` | Merchant business name |
| `contact` | Merchant domain |
| `opportunity_score` | Fit score (7–10) |
| `subject` | Version A email subject |
| `email_body` | Version A email body |
| `subject_B` | Version B subject |
| `email_body_B` | Version B body |
| `subject_C` | Version C subject |
| `email_body_C` | Version C body |

### Prerequisites

Before running the agent, the RAG index must exist:

```bash
python filter_shopify_merchants.py  # produces shopify_merchants.csv
python scrape_merchants.py          # produces merchant_enrichment.json
python build_rag.py build           # builds chroma_db/ vector store
python sales_agent.py               # runs the agent
```

### Agent environment variables

```bash
export ANTHROPIC_API_KEY="your-api-key"   # required
export FIRECRAWL_API_KEY="your-key"       # optional — enables richer scraping
```

### System prompt used

```text
You are a Sales Intelligence Agent for Lili's Company.
Lili's Product: A Shopify app that helps fashion and beauty merchants automate
email marketing, recover abandoned carts, and build customer loyalty programs.

Workflow:
1. Call search_merchants with the user's criteria (top_k=20)
2. For each domain returned, call scrape_website
3. For each domain, call analyze_merchant with the full profile
4. Call generate_email only for merchants with opportunity_score >= 7
5. Summarize: total candidates, how many scored >= 7, campaigns generated
```

---

## Module: `dashboard.py`

### Dashboard overview

A Flask web dashboard that reads all pipeline output files and displays them in a
visual interface — merchant cards with score badges, pain points, tool chips, and
an email preview panel with one-click copy.

### Running the dashboard

```bash
# Install Flask (one-time)
pip install flask

# Start the server
python dashboard.py
# Open http://localhost:5000
```

### Dashboard features

| Feature | Description |
| --- | --- |
| Stat bar | Total merchants, qualified (≥ 7), emails generated, average score |
| Search | Filter by company name or domain |
| Score filter | Show all / score ≥ 7 / ≥ 8 / ≥ 9 |
| Industry filter | All / Fashion / Beauty / Other |
| Email filter | All / Has emails / No emails yet |
| Merchant cards | Score circle, snapshot, tool chips, pain point count |
| Detail modal | Full analysis — pain points, hooks, recommended approach |
| Email preview | Switch between A/B/C versions; one-click copy |
| 3D View | Interactive 3D scatter plot of merchants by score, industry, and tool coverage |

### Data sources loaded

| File | Used for |
| --- | --- |
| `merchant_analysis.json` | Scores, snapshots, pain points, hooks |
| `merchant_emails.json` | A/B/C email versions |
| `merchant_enrichment.json` | Tools detected, price range, products |
| `shopify_merchants.csv` | Country, tech spend |

The dashboard works even if some files are missing — it shows whatever data is available.

---

## Module: `create_sample_data.py`

### Purpose

Reads `shopify_merchants.csv` (the real filtered merchants) and generates realistic sample output files for dashboard testing — without spending any API credits or running the full pipeline.

### Generated files

| File | Description |
| --- | --- |
| `merchant_analysis.json` | Opportunity scores, snapshots, pain points, hooks, recommended approach |
| `merchant_emails.json` | A/B/C cold email versions per merchant |
| `merchant_enrichment.json` | Tools detected, price range, products, social proof |

### Running it

```bash
python create_sample_data.py
python dashboard.py   # then open http://localhost:5000
```

The script uses pre-written sample data keyed by domain from `shopify_merchants.csv`. Any merchant not explicitly defined falls back to auto-generated generic data so the script never fails on new merchants.

---

## Requirements

```bash
pip install pandas anthropic requests beautifulsoup4 chromadb sentence-transformers flask
```

Python 3.10+ required (uses `list[str]` type hint syntax).
