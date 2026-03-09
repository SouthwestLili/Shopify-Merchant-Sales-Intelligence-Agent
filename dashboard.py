"""
dashboard.py

Web dashboard for viewing Sales Intelligence Agent results.
Reads all pipeline output files and serves a visual interface.

Usage:
    pip install flask
    python dashboard.py
    # Open http://localhost:5000 in your browser
"""

import json
from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, render_template

app = Flask(__name__)

# ── Data file paths ───────────────────────────────────────────────────────────
_DIR = Path(__file__).resolve().parent

ANALYSIS_JSON   = _DIR / "merchant_analysis.json"
EMAILS_JSON     = _DIR / "merchant_emails.json"
ENRICHMENT_JSON = _DIR / "merchant_enrichment.json"
MERCHANTS_CSV   = _DIR / "shopify_merchants.csv"


# ── Data loading ──────────────────────────────────────────────────────────────

def _load_json(path: Path, default=None):
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default if default is not None else []


def load_merchants() -> list[dict]:
    """Merge all pipeline output files into a single list of merchant dicts."""
    merchants: dict[str, dict] = {}

    # 1. Analysis (primary source — every analyzed merchant is here)
    for entry in _load_json(ANALYSIS_JSON):
        m      = entry.get("merchant", {})
        domain = str(m.get("domain", "")).strip()
        if not domain:
            continue
        merchants[domain] = {
            "domain":        domain,
            "business_name": m.get("business_name") or domain,
            "analysis":      entry.get("analysis", {}),
            "emails":        {},
            "enrichment":    {},
            "country":       "",
            "tech_spend":    "",
        }

    # 2. Emails
    for entry in _load_json(EMAILS_JSON):
        domain = str(entry.get("merchant", {}).get("domain", "")).strip()
        if domain in merchants:
            merchants[domain]["emails"] = entry.get("emails", {})

    # 3. Scraped enrichment
    enrichment_map = _load_json(ENRICHMENT_JSON, default={})
    for domain, data in enrichment_map.items():
        if domain in merchants:
            merchants[domain]["enrichment"] = data

    # 4. CSV for country / tech_spend
    if MERCHANTS_CSV.exists():
        df = pd.read_csv(MERCHANTS_CSV, encoding="utf-8-sig")
        df.columns = df.columns.str.strip().str.lower()
        for _, row in df.iterrows():
            domain = str(row.get("domain", "")).strip()
            if domain in merchants:
                merchants[domain]["country"]    = str(row.get("country", "") or "")
                merchants[domain]["tech_spend"] = row.get("tech_spend", "")

    # 5. Flatten into a list
    result = []
    for domain, m in merchants.items():
        analysis   = m["analysis"]
        enrichment = m["enrichment"]

        opp   = analysis.get("OPPORTUNITY SCORE", {})
        score = opp.get("score", 0) if isinstance(opp, dict) else (opp or 0)
        try:
            score = int(score)
        except (ValueError, TypeError):
            score = 0

        approach = analysis.get("RECOMMENDED APPROACH", {})

        # Infer industry from title / description
        text = (m["business_name"] + " " + enrichment.get("description", "")).lower()
        if any(kw in text for kw in ("beauty", "skincare", "cosmetics", "makeup")):
            industry = "beauty"
        elif any(kw in text for kw in ("fashion", "apparel", "clothing", "dress", "wear")):
            industry = "fashion"
        else:
            industry = "other"

        result.append({
            "domain":          domain,
            "business_name":   m["business_name"],
            "country":         m["country"],
            "tech_spend":      str(m["tech_spend"] or ""),
            "industry":        industry,
            "opportunity_score": score,
            "score_reasoning": opp.get("reasoning", "") if isinstance(opp, dict) else "",
            "snapshot":        analysis.get("MERCHANT SNAPSHOT", ""),
            "pain_points":     analysis.get("PAIN POINTS DETECTED", []),
            "hooks":           analysis.get("PERSONALIZATION HOOKS", []),
            "approach_channel": approach.get("channel", "") if isinstance(approach, dict) else "",
            "approach_timing":  approach.get("timing", "") if isinstance(approach, dict) else "",
            "approach_value":   approach.get("value_prop", "") if isinstance(approach, dict) else "",
            "tools_detected":  enrichment.get("tools_detected", []),
            "price_range":     enrichment.get("price_range", ""),
            "description":     enrichment.get("description", ""),
            "products":        enrichment.get("products", []),
            "emails":          m["emails"],
        })

    result.sort(key=lambda x: x["opportunity_score"], reverse=True)
    return result


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("dashboard.html")


@app.route("/api/merchants")
def api_merchants():
    return jsonify(load_merchants())


@app.route("/api/stats")
def api_stats():
    merchants = load_merchants()
    qualified = [m for m in merchants if m["opportunity_score"] >= 7]
    emailed   = [m for m in qualified if m["emails"]]
    return jsonify({
        "total":     len(merchants),
        "qualified": len(qualified),
        "emailed":   len(emailed),
        "files": {
            "analysis":   ANALYSIS_JSON.exists(),
            "emails":     EMAILS_JSON.exists(),
            "enrichment": ENRICHMENT_JSON.exists(),
            "csv":        MERCHANTS_CSV.exists(),
        },
    })


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n  Sales Intelligence Dashboard — Lili's Company")
    print("  Open http://localhost:5000 in your browser\n")
    app.run(debug=True, port=5000)
