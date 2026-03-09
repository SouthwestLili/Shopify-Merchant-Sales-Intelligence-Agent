"""
analyze_merchants.py

Loads shopify_merchants.csv, calls Claude to analyze each merchant profile,
and exports results to merchant_analysis.json.

Usage:
    python analyze_merchants.py
    python analyze_merchants.py --input shopify_merchants.csv --saas "Your product description" --output merchant_analysis.json
"""

import argparse
import json
import sys
import pandas as pd
import anthropic

MODEL = "claude-opus-4-6"

ANALYSIS_PROMPT = """You are a SaaS sales intelligence analyst specializing in Shopify merchants.

Analyze the following merchant profile and identify sales opportunities:

MERCHANT PROFILE:
{merchant_data}

YOUR PRODUCT/SERVICE:
{your_saas_description}

Analyze in this order:

1. MERCHANT SNAPSHOT (2-3 sentences)
   - What do they sell, who are their customers, what's their scale?

2. PAIN POINTS DETECTED (list 3-5)
   - Based on their tech stack gaps, what problems likely exist?
   - Look for: missing review tools, no loyalty program, no email marketing,
     slow site, no chatbot, manual inventory, etc.

3. OPPORTUNITY SCORE (1-10)
   - How well does our product fit this merchant?
   - Explain your reasoning in 1 sentence.

4. PERSONALIZATION HOOKS (list 3)
   - Specific details from their website/products to reference in outreach
   - e.g., "You sell handmade candles and currently have no subscription option"

5. RECOMMENDED APPROACH
   - Best channel: email / LinkedIn / cold call?
   - Best timing: product launch season / post-holiday?
   - Key value prop to lead with

Output as JSON for easy parsing."""


def row_to_merchant_data(row: pd.Series) -> str:
    parts = []
    for col, val in row.items():
        if pd.notna(val) and str(val).strip():
            parts.append(f"{col}: {val}")
    return "\n".join(parts)


def analyze_merchant(client: anthropic.Anthropic, merchant_data: str, saas_description: str) -> dict:
    prompt = ANALYSIS_PROMPT.format(
        merchant_data=merchant_data,
        your_saas_description=saas_description,
    )

    with client.messages.stream(
        model=MODEL,
        max_tokens=2048,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        response = stream.get_final_message()

    # Extract the text block
    text = next(
        (block.text for block in response.content if block.type == "text"),
        ""
    )

    # Parse JSON from the response
    try:
        # Strip markdown code fences if present
        clean = text.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        return json.loads(clean.strip())
    except json.JSONDecodeError:
        return {"raw_response": text}


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze Shopify merchants with Claude AI.")
    parser.add_argument("--input", default="shopify_merchants.csv", help="Input CSV from filter_shopify_merchants.py")
    parser.add_argument("--output", default="merchant_analysis.json", help="Output JSON file")
    parser.add_argument(
        "--saas",
        default="A Shopify app that helps fashion and beauty merchants automate email marketing, recover abandoned carts, and build customer loyalty programs.",
        help="Description of your SaaS product or service",
    )
    args = parser.parse_args()

    df = pd.read_csv(args.input, encoding="utf-8-sig")
    print(f"Loaded {len(df):,} merchants from '{args.input}'")

    client = anthropic.Anthropic()
    results = []

    for i, (_, row) in enumerate(df.iterrows(), 1):
        merchant_name = row.get("business_name") or row.get("domain") or f"Merchant {i}"
        print(f"[{i}/{len(df)}] Analyzing: {merchant_name} ...", end=" ", flush=True)

        merchant_data = row_to_merchant_data(row)
        try:
            analysis = analyze_merchant(client, merchant_data, args.saas)
            results.append({
                "merchant": {
                    "business_name": row.get("business_name"),
                    "domain": row.get("domain"),
                },
                "analysis": analysis,
            })
            print("done")
        except Exception as e:
            print(f"ERROR: {e}")
            results.append({
                "merchant": {"business_name": merchant_name},
                "analysis": {"error": str(e)},
            })

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nExported {len(results)} analyses to '{args.output}'")


if __name__ == "__main__":
    main()
