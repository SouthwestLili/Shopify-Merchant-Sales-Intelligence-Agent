"""
generate_emails.py

Loads merchant_analysis.json, calls Claude to generate 3 cold email versions
per merchant, and exports results to merchant_emails.json.

Usage:
    python generate_emails.py
    python generate_emails.py --input merchant_analysis.json --output merchant_emails.json
"""

import argparse
import json
import re
import sys
import anthropic

MODEL = "claude-opus-4-6"

EMAIL_PROMPT = """You are an expert B2B copywriter specializing in SaaS cold outreach.

Using this merchant analysis:
{agent_analysis_output}

Write 3 versions of a cold email:

VERSION A - Problem-focused (lead with pain point)
VERSION B - Social proof focused (lead with similar customer success)
VERSION C - Curiosity/question hook (lead with provocative question)

Rules for ALL versions:
- Subject line: under 8 words, no emojis, not salesy
- Opening: reference something SPECIFIC about their store (use personalization hooks)
- Body: max 4 sentences, no fluff
- CTA: one single ask, low friction (e.g., "Worth a 15-min chat?" not "Book a demo")
- Tone: peer-to-peer, not vendor-to-customer
- NEVER start with "I hope this email finds you well"
- NEVER say "I wanted to reach out"

Format output as:
SUBJECT: ...
BODY: ..."""


def parse_email_versions(text: str) -> dict:
    """Parse VERSION A/B/C blocks from Claude's response into a dict."""
    versions = {}
    pattern = re.compile(
        r"VERSION\s+([ABC])\s*[-–—]?\s*[^\n]*\n(.*?)(?=VERSION\s+[ABC]|$)",
        re.DOTALL | re.IGNORECASE,
    )
    for match in pattern.finditer(text):
        label = match.group(1).upper()
        block = match.group(2).strip()

        subject_match = re.search(r"SUBJECT:\s*(.+)", block)
        body_match = re.search(r"BODY:\s*([\s\S]+)", block)

        versions[f"version_{label}"] = {
            "subject": subject_match.group(1).strip() if subject_match else "",
            "body": body_match.group(1).strip() if body_match else block,
        }

    if not versions:
        versions["raw_response"] = text

    return versions


def generate_emails(client: anthropic.Anthropic, analysis: dict) -> dict:
    analysis_text = json.dumps(analysis, indent=2, ensure_ascii=False)
    prompt = EMAIL_PROMPT.format(agent_analysis_output=analysis_text)

    with client.messages.stream(
        model=MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        response = stream.get_final_message()

    text = next(
        (block.text for block in response.content if block.type == "text"),
        ""
    )
    return parse_email_versions(text)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate cold emails from merchant analyses.")
    parser.add_argument("--input", default="merchant_analysis.json", help="Input JSON from analyze_merchants.py")
    parser.add_argument("--output", default="merchant_emails.json", help="Output JSON file")
    args = parser.parse_args()

    try:
        with open(args.input, encoding="utf-8") as f:
            merchants = json.load(f)
    except FileNotFoundError:
        print(f"Error: '{args.input}' not found. Run analyze_merchants.py first.", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {len(merchants):,} merchant analyses from '{args.input}'")

    client = anthropic.Anthropic()
    results = []

    for i, entry in enumerate(merchants, 1):
        merchant = entry.get("merchant", {})
        name = merchant.get("business_name") or merchant.get("domain") or f"Merchant {i}"
        analysis = entry.get("analysis", {})

        print(f"[{i}/{len(merchants)}] Writing emails for: {name} ...", end=" ", flush=True)

        try:
            emails = generate_emails(client, analysis)
            results.append({
                "merchant": merchant,
                "emails": emails,
            })
            print("done")
        except Exception as e:
            print(f"ERROR: {e}")
            results.append({
                "merchant": merchant,
                "emails": {"error": str(e)},
            })

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nExported {len(results)} email sets to '{args.output}'")


if __name__ == "__main__":
    main()
