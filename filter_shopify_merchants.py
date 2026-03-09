"""
filter_shopify_merchants.py

Loads a tech-stack CSV dataset, filters for Shopify merchants in specified industries,
and exports results to shopify_merchants.csv.

Usage:
    python filter_shopify_merchants.py --input tech_stack.csv --industries fashion beauty
"""

import argparse
import sys
import pandas as pd


OUTPUT_COLUMNS = ["business_name", "domain", "title", "country", "tech_spend"]


def load_csv(path: str) -> pd.DataFrame:
    """Load CSV with fallback encodings to handle encoding errors."""
    for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            df = pd.read_csv(path, encoding=encoding, low_memory=False)
            print(f"Loaded '{path}' with encoding={encoding} ({len(df):,} rows)")
            return df
        except UnicodeDecodeError:
            continue
        except FileNotFoundError:
            print(f"Error: file not found — '{path}'", file=sys.stderr)
            sys.exit(1)

    print("Error: could not decode file with any supported encoding.", file=sys.stderr)
    sys.exit(1)


def normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Lowercase and strip column names so minor naming variations don't break matching."""
    df.columns = df.columns.str.strip().str.lower().str.replace(r"\s+", "_", regex=True)
    return df


def filter_shopify(df: pd.DataFrame, tech_col: str = "technologies") -> pd.DataFrame:
    """Keep rows where tech_stack contains 'Shopify' (case-insensitive)."""
    if tech_col not in df.columns:
        available = ", ".join(df.columns.tolist())
        print(
            f"Error: column '{tech_col}' not found. Available columns: {available}",
            file=sys.stderr,
        )
        sys.exit(1)

    mask = df[tech_col].fillna("").str.contains(r"\bShopify\b", case=False, regex=True)
    result = df[mask].copy()
    print(f"After Shopify filter: {len(result):,} rows")
    return result


def filter_industries(df: pd.DataFrame, industries: list[str], industry_col: str = "title") -> pd.DataFrame:
    """Keep rows whose industry matches any of the requested industries (case-insensitive)."""
    if industry_col not in df.columns:
        available = ", ".join(df.columns.tolist())
        print(
            f"Error: column '{industry_col}' not found. Available columns: {available}",
            file=sys.stderr,
        )
        sys.exit(1)

    pattern = "|".join(map(re_escape, industries))
    mask = df[industry_col].fillna("").str.contains(pattern, case=False, regex=True)
    result = df[mask].copy()
    print(f"After industry filter {industries}: {len(result):,} rows")
    return result


def re_escape(s: str) -> str:
    import re
    return re.escape(s.strip())


def select_output_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Select only the desired output columns; add missing ones as NaN."""
    for col in OUTPUT_COLUMNS:
        if col not in df.columns:
            print(f"Warning: column '{col}' not found in dataset — will be empty in output.")
            df[col] = pd.NA
    return df[OUTPUT_COLUMNS]


def export(df: pd.DataFrame, path: str = "shopify_merchants.csv") -> None:
    df.to_csv(path, index=False, encoding="utf-8-sig")  # utf-8-sig for Excel compatibility
    print(f"Exported {len(df):,} rows to '{path}'")


def main() -> None:
    parser = argparse.ArgumentParser(description="Filter Shopify merchants by industry from a tech-stack CSV.")
    parser.add_argument("--input", default="tech_stack.csv", help="Path to the input CSV file (default: tech_stack.csv)")
    parser.add_argument(
        "--industries",
        nargs="+",
        default=["fashion", "beauty"],
        help="One or more industry keywords to filter on (default: fashion beauty)",
    )
    parser.add_argument("--output", default="shopify_merchants.csv", help="Output CSV path")
    parser.add_argument(
        "--tech-col", default="technologies", help="Column name containing tech stack data"
    )
    parser.add_argument(
        "--industry-col", default="title", help="Column name to filter industry keywords against (default: title)"
    )
    args = parser.parse_args()

    df = load_csv(args.input)
    df = normalise_columns(df)

    df = filter_shopify(df, tech_col=args.tech_col)
    if df.empty:
        print("No Shopify rows found. Check that the tech_stack column contains 'Shopify'.")
        sys.exit(0)

    df = filter_industries(df, args.industries, industry_col=args.industry_col)
    if df.empty:
        print(f"No rows matched industries: {args.industries}")
        sys.exit(0)

    df = select_output_columns(df)
    export(df, args.output)


if __name__ == "__main__":
    main()
