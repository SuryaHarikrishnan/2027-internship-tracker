#!/usr/bin/env python3
"""Generates TOP20.md — a daily shortlist of 20 recommended companies to apply to.

Scoring:
  - Freshness: listings posted in the last 3 days score highest
  - Company tier: well-known / high-signal companies get a bonus
  - Category preference: SWE and AI/ML roles weighted higher than others
  - Dedup: one entry per company (best role wins)
"""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Tier 1 = household names / highest signal for resume
# Tier 2 = strong mid-size / fast-growing companies
TIER1 = {
    "google","meta","apple","amazon","microsoft","openai","anthropic","netflix",
    "stripe","spacex","tesla","nvidia","deepmind","jane street","citadel",
    "citadel securities","two sigma","de shaw","hudson river trading","jump trading",
    "susquehanna international group","sig","palantir","databricks","figma",
    "notion","linear","scale ai","anduril","waymo","boston dynamics",
    "salesforce","adobe","airbnb","lyft","uber","doordash","coinbase","robinhood",
    "ramp","brex","plaid","chime","rippling","retool","airtable","asana",
    "snowflake","datadog","cloudflare","vercel","hashicorp","confluent",
    "elastic","mongodb","cockroachdb","pinecone","weaviate","hugging face",
}

TIER2 = {
    "bloomberg","goldman sachs","jpmorgan","morgan stanley","blackrock","optiver",
    "imc trading","akuna capital","five rings","tower research","virtu financial",
    "yahoo","linkedin","twitter","x","bytedance","tiktok","pinterest","snap",
    "shopify","square","block","intuit","qualcomm","intel","amd","arm","broadcom",
    "samsung","sony","siemens","ge","lockheed martin","boeing","northrop grumman",
    "raytheon","l3harris","oracle","ibm","sap","vmware","cisco","juniper",
    "palo alto networks","crowdstrike","okta","zscaler","sentinelone",
    "servicenow","workday","veeva","epic","cerner","medidata","tempus",
    "moderna","pfizer","genentech","bristol myers squibb","abbvie",
    "ford","gm","rivian","lucid","zoox","cruise","aurora","mobileye",
    "deloitte","mckinsey","bain","bcg","accenture","pwc","kpmg","ey",
    "a16z","sequoia","greylock","bessemer","general catalyst",
}

CATEGORY_WEIGHT = {
    "Software Engineering": 1.0,
    "Data Science, AI & Machine Learning": 1.0,
    "Quantitative Finance": 0.9,
    "Hardware Engineering": 0.7,
    "Product Management": 0.6,
    "Other": 0.5,
}


def tier_score(company_name: str) -> float:
    name = company_name.lower().strip()
    if name in TIER1:
        return 3.0
    if name in TIER2:
        return 1.5
    return 0.0


def freshness_score(date_posted_ts, today) -> float:
    if not date_posted_ts:
        return 0.0
    posted = datetime.fromtimestamp(date_posted_ts, tz=timezone.utc).date()
    days_old = (today - posted).days
    if days_old == 0:
        return 3.0
    if days_old <= 1:
        return 2.5
    if days_old <= 3:
        return 2.0
    if days_old <= 7:
        return 1.0
    if days_old <= 14:
        return 0.5
    return 0.0


def main():
    data_path = ROOT / "data" / "listings.json"
    if not data_path.exists():
        print("No listings.json found — run scrape.py first.")
        return

    listings = json.loads(data_path.read_text(encoding="utf-8"))
    active = [l for l in listings if l.get("active", True) and l.get("is_visible", True)]
    today = datetime.now(timezone.utc).date()

    # score each listing
    scored = []
    for l in active:
        cat = l.get("category") or "Other"
        score = (
            freshness_score(l.get("date_posted"), today)
            + tier_score(l.get("company_name", ""))
            + CATEGORY_WEIGHT.get(cat, 0.5)
        )
        scored.append((score, l))

    scored.sort(key=lambda x: x[0], reverse=True)

    # one pick per company (highest-scoring role wins)
    seen_companies: set = set()
    picks = []
    for score, l in scored:
        company = l.get("company_name", "").strip()
        key = company.lower()
        if key in seen_companies:
            continue
        seen_companies.add(key)
        picks.append((score, l))
        if len(picks) == 20:
            break

    write_top20(picks, today)
    print(f"Top 20 written for {today}.")


def write_top20(picks, today):
    lines = [
        f"# Today's Top 20 — {today}\n",
        "Ranked by freshness + company signal + role category. "
        "Apply to these today — all are actively hiring right now.\n",
        "| # | Company | Role | Location | Terms | Date Posted | Apply |\n"
        "|---|---|---|---|---|---|---|",
    ]

    for i, (score, l) in enumerate(picks, 1):
        company = l.get("company_name", "")
        title = l.get("title", "")
        url = l.get("url", "")
        loc = ", ".join(l.get("locations", []) or [])
        terms = ", ".join(l.get("terms", []) or [])
        date_ts = l.get("date_posted")
        if date_ts:
            posted = datetime.fromtimestamp(date_ts, tz=timezone.utc).date()
            days_old = (today - posted).days
            date_str = f"{posted} ({days_old}d ago)"
        else:
            date_str = "Unknown"
        link = f"[Apply]({url})" if url else "—"
        lines.append(f"| {i} | **{company}** | {title} | {loc} | {terms} | {date_str} | {link} |")

    lines.append(f"\n---\n*Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} — "
                 "rankings update with each refresh. See [README](README.md) for full listings.*")

    (ROOT / "TOP20.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
