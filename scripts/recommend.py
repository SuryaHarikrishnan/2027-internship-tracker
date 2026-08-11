#!/usr/bin/env python3
"""Generates TOP20.md — a daily shortlist of 20 recommended companies to apply to.

Scoring:
  - Freshness: listings posted in the last 3 days score highest
  - Company tier: well-known / high-signal companies get a bonus
  - YC startups: recent YC batches (W24–S26) get a startup signal boost
  - Category preference: SWE and AI/ML roles weighted higher than others
  - Dedup: one entry per company (best role wins)
"""
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# YC batches to pull — recent enough to still be in hiring/growth mode
YC_BATCHES = ["W24", "S24", "W25", "S25", "W26", "S26"]
# Higher score for more recent batches
YC_BATCH_SCORE = {"W24": 0.8, "S24": 0.8, "W25": 1.0, "S25": 1.2, "W26": 1.4, "S26": 1.4}
YC_CACHE_PATH = ROOT / "data" / "yc_companies.json"
YC_HEADERS = {"User-Agent": "internship-tracker/1.0 (personal aggregator)"}


def fetch_yc_companies() -> dict[str, float]:
    """Returns {company_name_lower: score} for recent YC companies.
    Caches to data/yc_companies.json, refreshes once per day."""
    if YC_CACHE_PATH.exists():
        age_hours = (time.time() - YC_CACHE_PATH.stat().st_mtime) / 3600
        if age_hours < 23:
            return json.loads(YC_CACHE_PATH.read_text(encoding="utf-8"))

    companies: dict[str, float] = {}
    for batch in YC_BATCHES:
        page = 1
        while True:
            url = f"https://api.ycombinator.com/v0.1/companies?batch={batch}&per_page=100&page={page}"
            try:
                req = urllib.request.Request(url, headers=YC_HEADERS)
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
            except Exception as e:
                print(f"[warn] YC API fetch failed for {batch} page {page}: {e}")
                break
            batch_companies = data.get("companies", [])
            if not batch_companies:
                break
            score = YC_BATCH_SCORE.get(batch, 0.8)
            for c in batch_companies:
                name = c.get("name", "").lower().strip()
                if name:
                    # keep the higher score if company appears in multiple batches
                    companies[name] = max(companies.get(name, 0), score)
            page += 1

    YC_CACHE_PATH.write_text(json.dumps(companies), encoding="utf-8")
    print(f"Fetched {len(companies)} YC companies across {YC_BATCHES}.")
    return companies

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

    yc_companies = fetch_yc_companies()

    listings = json.loads(data_path.read_text(encoding="utf-8"))
    active = [l for l in listings if l.get("active", True) and l.get("is_visible", True)]
    today = datetime.now(timezone.utc).date()

    # score each listing
    scored = []
    for l in active:
        cat = l.get("category") or "Other"
        company_key = l.get("company_name", "").lower().strip()
        yc_score = yc_companies.get(company_key, 0.0)
        score = (
            freshness_score(l.get("date_posted"), today)
            + tier_score(l.get("company_name", ""))
            + yc_score
            + CATEGORY_WEIGHT.get(cat, 0.5)
        )
        scored.append((score, l))

    scored.sort(key=lambda x: x[0], reverse=True)

    # top 15 from unified scoring (one per company)
    seen_companies: set = set()
    main_picks = []
    for score, l in scored:
        company = l.get("company_name", "").strip()
        key = company.lower()
        if key in seen_companies:
            continue
        seen_companies.add(key)
        main_picks.append((score, l))
        if len(main_picks) == 15:
            break

    # top 5 YC startups not already in main picks
    # sort by: yc batch score desc, then freshness desc
    yc_candidates = [
        (yc_companies.get(l.get("company_name","").lower().strip(), 0),
         freshness_score(l.get("date_posted"), today), l)
        for l in active
        if l.get("company_name","").lower().strip() in yc_companies
        and l.get("company_name","").lower().strip() not in seen_companies
    ]
    yc_candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    startup_picks = []
    startup_seen: set = set()
    for yc_score, fresh, l in yc_candidates:
        key = l.get("company_name","").lower().strip()
        if key in startup_seen:
            continue
        startup_seen.add(key)
        startup_picks.append(l)
        if len(startup_picks) == 5:
            break

    write_top20(main_picks, startup_picks, today)
    print(f"Top 20 written for {today}.")


def listing_row(i, l, today):
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
    return f"| {i} | **{company}** | {title} | {loc} | {terms} | {date_str} | {link} |"


def write_top20(main_picks, startup_picks, today):
    table_header = (
        "| # | Company | Role | Location | Terms | Date Posted | Apply |\n"
        "|---|---|---|---|---|---|---|"
    )
    lines = [
        f"# Today's Top 20 — {today}\n",
        "Updated with every refresh. Apply today — freshness matters.\n",
        "## 🏢 Top 15 — High-signal picks\n",
        "Ranked by freshness + company tier + role category.\n",
        table_header,
    ]
    for i, (score, l) in enumerate(main_picks, 1):
        lines.append(listing_row(i, l, today))

    lines.append("\n## 🚀 Top 5 Startups — YC-backed, actively hiring\n")
    lines.append("Recent YC companies (W24–S26) with open roles right now.\n")
    lines.append(table_header)
    if startup_picks:
        for i, l in enumerate(startup_picks, 1):
            lines.append(listing_row(i, l, today))
    else:
        lines.append("*No YC startup listings found in today's active feed.*")

    lines.append(
        f"\n---\n*Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} — "
        "rankings update with each refresh. See [README](README.md) for all listings.*"
    )
    (ROOT / "TOP20.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
