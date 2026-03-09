"""
scrape_merchants.py

Enriches shopify_merchants.csv by scraping each merchant's homepage.
Uses Firecrawl API if FIRECRAWL_API_KEY is set; falls back to BeautifulSoup.

For each domain, extracts:
  - Company description
  - Product/service categories
  - Price range (if visible)
  - Tools detected (chat widgets, pop-ups, review apps, marketing tools)
  - Blog topics (indicates marketing focus)
  - Social proof (review counts, testimonials)

Output: merchant_enrichment.json  →  {domain: {description, products, tools_detected, ...}}

Rate limit: 1 request per 2 seconds. Timeout: 10 seconds per domain.

Usage:
    python scrape_merchants.py
    python scrape_merchants.py --input shopify_merchants.csv --output merchant_enrichment.json
"""

import argparse
import json
import os
import re
import sys
import time

import pandas as pd
import requests
from bs4 import BeautifulSoup

TIMEOUT = 10
RATE_LIMIT_SECONDS = 2

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# Known SaaS tools identifiable by script/src patterns
TOOL_SIGNATURES = {
    # Chat & Support
    "Intercom":      r"intercom\.io|intercomcdn",
    "Zendesk":       r"zendesk\.com|zdassets\.com",
    "Gorgias":       r"gorgias\.com",
    "Tidio":         r"tidio\.com|tidiocdn",
    "Drift":         r"drift\.com|js\.driftt\.com",
    "LiveChat":      r"livechatinc\.com",
    # Email & Pop-ups
    "Klaviyo":       r"klaviyo\.com",
    "Mailchimp":     r"mailchimp\.com|chimpstatic\.com",
    "Privy":         r"privy\.com",
    "Omnisend":      r"omnisend\.com",
    "Drip":          r"drip\.com",
    # Reviews
    "Yotpo":         r"yotpo\.com",
    "Judge.me":      r"judge\.me",
    "Stamped.io":    r"stamped\.io",
    "Okendo":        r"okendo\.io",
    "Loox":          r"loox\.io",
    # Loyalty
    "Smile.io":      r"smile\.io|cdn\.sweettooth",
    "LoyaltyLion":   r"loyaltylion\.com",
    # Analytics / Ads
    "Google Analytics": r"google-analytics\.com|gtag|googletagmanager",
    "Meta Pixel":    r"connect\.facebook\.net|fbevents\.js",
    "TikTok Pixel":  r"analytics\.tiktok\.com",
    # Search & UX
    "Searchanise":   r"searchanise\.com",
    "Boost Commerce":r"boostcommerce\.net",
    "Rebuy":         r"rebuyengine\.com",
}

PRICE_PATTERN = re.compile(r"\$\s?[\d,]+(?:\.\d{2})?")
REVIEW_COUNT_PATTERN = re.compile(r"(\d[\d,]*)\s*(review|rating|testimonial)s?", re.IGNORECASE)


# ──────────────────────────────────────────────
#  Firecrawl scraper
# ──────────────────────────────────────────────

def scrape_with_firecrawl(url: str, api_key: str) -> str | None:
    """Return markdown content from Firecrawl, or None on failure."""
    endpoint = "https://api.firecrawl.dev/v1/scrape"
    payload = {"url": url, "formats": ["markdown"]}
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        resp = requests.post(endpoint, json=payload, headers=headers, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", {}).get("markdown", "")
    except Exception:
        return None


# ──────────────────────────────────────────────
#  BeautifulSoup scraper
# ──────────────────────────────────────────────

def scrape_with_bs4(url: str) -> BeautifulSoup | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except Exception:
        return None


def extract_description(soup: BeautifulSoup) -> str:
    for attr in ("description", "og:description", "twitter:description"):
        tag = soup.find("meta", attrs={"name": attr}) or soup.find("meta", attrs={"property": attr})
        if tag and tag.get("content", "").strip():
            return tag["content"].strip()
    # Fallback: first non-empty paragraph
    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        if len(text) > 40:
            return text[:300]
    return ""


def extract_products(soup: BeautifulSoup) -> list[str]:
    categories = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/collections/" in href:
            slug = href.split("/collections/")[-1].split("?")[0].strip("/")
            if slug and slug not in ("all", "frontpage"):
                categories.add(slug.replace("-", " ").replace("_", " ").title())
    return sorted(categories)[:10]


def extract_price_range(soup: BeautifulSoup) -> str:
    prices = []
    for tag in soup.find_all(string=PRICE_PATTERN):
        matches = PRICE_PATTERN.findall(tag)
        for m in matches:
            try:
                prices.append(float(m.replace("$", "").replace(",", "")))
            except ValueError:
                pass
    if not prices:
        return ""
    lo, hi = min(prices), max(prices)
    return f"${lo:,.0f}" if lo == hi else f"${lo:,.0f} – ${hi:,.0f}"


def detect_tools(soup: BeautifulSoup) -> list[str]:
    page_text = str(soup)
    detected = []
    for tool, pattern in TOOL_SIGNATURES.items():
        if re.search(pattern, page_text, re.IGNORECASE):
            detected.append(tool)
    return detected


def extract_blog_topics(soup: BeautifulSoup) -> list[str]:
    topics = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/blogs/" in href or "/blog/" in href:
            text = a.get_text(strip=True)
            if text and len(text) > 3:
                topics.add(text)
    return sorted(topics)[:8]


def extract_social_proof(soup: BeautifulSoup) -> dict:
    text = soup.get_text(" ")
    match = REVIEW_COUNT_PATTERN.search(text)
    count = match.group(1).replace(",", "") if match else ""
    has_testimonials = bool(soup.find(class_=re.compile(r"testimonial|review|rating", re.I)))
    return {
        "review_count": int(count) if count.isdigit() else None,
        "has_testimonials": has_testimonials,
    }


# ──────────────────────────────────────────────
#  Main enrichment logic
# ──────────────────────────────────────────────

def enrich_domain(domain: str, firecrawl_key: str | None) -> dict:
    url = f"https://{domain}" if not domain.startswith("http") else domain

    # Try Firecrawl first
    if firecrawl_key:
        md = scrape_with_firecrawl(url, firecrawl_key)
        if md:
            # Minimal extraction from markdown
            lines = md.splitlines()
            description = next((l.strip() for l in lines if len(l.strip()) > 40), "")[:300]
            return {
                "description": description,
                "products": [],
                "tools_detected": [],
                "price_range": "",
                "blog_topics": [],
                "social_proof": {},
                "source": "firecrawl",
            }

    # Fallback: BeautifulSoup
    soup = scrape_with_bs4(url)
    if soup is None:
        return {"error": "failed to fetch"}

    return {
        "description": extract_description(soup),
        "products": extract_products(soup),
        "tools_detected": detect_tools(soup),
        "price_range": extract_price_range(soup),
        "blog_topics": extract_blog_topics(soup),
        "social_proof": extract_social_proof(soup),
        "source": "beautifulsoup",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape and enrich Shopify merchant homepages.")
    parser.add_argument("--input", default="shopify_merchants.csv", help="Filtered merchant CSV")
    parser.add_argument("--output", default="merchant_enrichment.json", help="Output JSON file")
    args = parser.parse_args()

    df = pd.read_csv(args.input, encoding="utf-8-sig")
    domains = df["domain"].dropna().unique().tolist()
    print(f"Loaded {len(domains)} domains from '{args.input}'")

    firecrawl_key = os.getenv("FIRECRAWL_API_KEY")
    if firecrawl_key:
        print("Firecrawl API key detected — will use Firecrawl with BS4 fallback.")
    else:
        print("No FIRECRAWL_API_KEY found — using BeautifulSoup only.")

    results = {}

    for i, domain in enumerate(domains, 1):
        print(f"[{i}/{len(domains)}] Scraping: {domain} ...", end=" ", flush=True)
        try:
            data = enrich_domain(domain, firecrawl_key)
            results[domain] = data
            source = data.get("source", "")
            tools = data.get("tools_detected", [])
            print(f"done ({source}, {len(tools)} tools detected)")
        except Exception as e:
            print(f"ERROR: {e}")
            results[domain] = {"error": str(e)}

        if i < len(domains):
            time.sleep(RATE_LIMIT_SECONDS)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nExported enrichment data for {len(results)} domains to '{args.output}'")


if __name__ == "__main__":
    main()
