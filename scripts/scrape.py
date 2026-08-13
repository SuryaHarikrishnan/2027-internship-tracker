#!/usr/bin/env python3
"""Aggregates internship/new-grad listings from several open-source tracker
repos into one deduplicated README table, and writes a daily digest of
new/closed listings compared to the previous snapshot.

Sources (each maintains a machine-readable listings.json fed by their own
scrapers/bots):
  - SimplifyJobs/Summer2026-Internships (MIT)
  - vanshb03/Summer2026-Internships (MIT)
  - vanshb03/Summer2027-Internships (MIT)
"""
import json
import re
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
LISTINGS_DIR = ROOT / "listings"
DIGESTS_DIR = ROOT / "digests"
DATA_DIR.mkdir(exist_ok=True)
LISTINGS_DIR.mkdir(exist_ok=True)
DIGESTS_DIR.mkdir(exist_ok=True)

SOURCES = {
    "simplify-2026": "https://raw.githubusercontent.com/SimplifyJobs/Summer2026-Internships/dev/.github/scripts/listings.json",
    "vanshb03-2026": "https://raw.githubusercontent.com/vanshb03/Summer2026-Internships/dev/.github/scripts/listings.json",
    "vanshb03-2027": "https://raw.githubusercontent.com/vanshb03/Summer2027-Internships/dev/.github/scripts/listings.json",
}

HEADERS = {"User-Agent": "internship-tracker/1.0 (personal aggregator)"}


def fetch_json(url: str):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def slugify(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s or "other"


CATEGORY_ALIASES = {
    "software": "Software Engineering",
    "software engineering": "Software Engineering",
    "ai/ml/data": "Data Science, AI & Machine Learning",
    "data science, ai & machine learning": "Data Science, AI & Machine Learning",
    "hardware": "Hardware Engineering",
    "hardware engineering": "Hardware Engineering",
    "quant": "Quantitative Finance",
    "quantitative finance": "Quantitative Finance",
    "product": "Product Management",
    "product management": "Product Management",
}


def normalize_category(cat: str) -> str:
    return CATEGORY_ALIASES.get(norm(cat), cat or "Other")


def dedup_key(item: dict) -> str:
    locs = item.get("locations") or []
    first_loc = locs[0] if locs else ""
    return f"{norm(item.get('company_name'))}|{norm(item.get('title'))}|{norm(first_loc)}"


def active_key_set(listings: list) -> set:
    return {
        dedup_key(l)
        for l in listings
        if l.get("active", True) and l.get("is_visible", True)
    }


def main():
    # load previous snapshot for diffing
    snapshot_path = DATA_DIR / "listings.json"
    prev_keys: set = set()
    if snapshot_path.exists():
        try:
            prev = json.loads(snapshot_path.read_text(encoding="utf-8"))
            prev_keys = active_key_set(prev)
        except Exception:
            pass

    merged: dict = {}
    fetched_sources: list = []
    for name, url in SOURCES.items():
        try:
            items = fetch_json(url)
        except Exception as exc:
            print(f"[warn] failed to fetch {name}: {exc}")
            continue
        fetched_sources.append(name)
        for item in items:
            key = dedup_key(item)
            if key not in merged:
                item["_sources"] = [name]
                merged[key] = item
            else:
                if name not in merged[key]["_sources"]:
                    merged[key]["_sources"].append(name)

    listings = list(merged.values())
    listings.sort(key=lambda x: x.get("date_updated", 0), reverse=True)

    snapshot_path.write_text(json.dumps(listings, indent=2), encoding="utf-8")

    curr_keys = active_key_set(listings)
    new_keys = curr_keys - prev_keys
    closed_keys = prev_keys - curr_keys

    new_listings = [l for l in listings if dedup_key(l) in new_keys]
    closed_listings = [l for l in (json.loads(snapshot_path.read_text(encoding="utf-8")) if prev_keys else [])
                       if dedup_key(l) in closed_keys]

    write_listings(listings, fetched_sources)
    write_digest(listings, new_listings, closed_listings, fetched_sources)

    print(
        f"Merged {len(listings)} unique listings from {fetched_sources}. "
        f"New: {len(new_listings)}, closed: {len(closed_listings)}."
    )


def category_table(rows, today):
    lines = [
        "| Company | Role | Location | Terms | Date Posted | Days Old | Sources |",
        "|---|---|---|---|---|---|---|",
    ]
    for l in rows:
        company = l.get("company_name", "")
        title = l.get("title", "")
        url = l.get("url", "")
        loc = ", ".join(l.get("locations", []) or [])
        terms = ", ".join(l.get("terms", []) or [])
        srcs = ", ".join(l.get("_sources", []))
        company_cell = f"[{company}]({url})" if url else company

        date_posted_ts = l.get("date_posted")
        if date_posted_ts:
            posted_date = datetime.fromtimestamp(date_posted_ts, tz=timezone.utc).date()
            date_str = posted_date.strftime("%Y-%m-%d")
            days_old = (today - posted_date).days
        else:
            date_str = "Unknown"
            days_old = "?"

        lines.append(
            f"| {company_cell} | {title} | {loc} | {terms} | {date_str} | {days_old} | {srcs} |"
        )
    return lines


def write_listings(listings, fetched_sources):
    active = [l for l in listings if l.get("active", True) and l.get("is_visible", True)]
    by_category: dict = defaultdict(list)
    for l in active:
        cat = normalize_category(l.get("category"))
        by_category[cat].append(l)
    for cat in by_category:
        by_category[cat].sort(key=lambda x: x.get("date_posted", 0), reverse=True)

    today = datetime.now(timezone.utc).date()
    refreshed_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    existing_files = set(LISTINGS_DIR.glob("*.md"))
    written_files = set()
    category_links = []
    for cat in sorted(by_category):
        rows = by_category[cat]
        slug = slugify(cat)
        path = LISTINGS_DIR / f"{slug}.md"
        written_files.add(path)
        category_links.append((cat, slug, len(rows)))

        lines = [f"# {cat} ({len(rows)})\n", "[← back to index](../README.md)\n"]
        lines += category_table(rows, today)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    for stale in existing_files - written_files:
        stale.unlink()

    index = [
        "# 2027 Internship Tracker\n",
        "![demo](assets/demo.svg)\n",
        "**Summer 2026 and Summer 2027 SWE, AI/ML, Quant, Hardware, and PM internship listings "
        "-- plus a built-in application tracker so you know where you applied, "
        "when, and how long ago.**\n",
        "> Just here for the list? [Jump to listings](#listings)\n",
        "Most internship repos stop at the list. Fork this one and you also get:\n",
        "- A personal tracker that lives next to the listings\n"
        "- A `days-since-applied` column so nothing goes quiet without you noticing\n"
        "- Daily Top 20 picks ranked by freshness + company signal + YC batch\n"
        "- Listings that refresh 5x per day automatically via GitHub Actions -- no setup needed\n",
        "**[Fork to start tracking your applications →]"
        "(https://github.com/SuryaHarikrishnan/2027-internship-tracker/fork)**\n",
        "```bash\n"
        "python scripts/track.py add \"Stripe\" \"SWE Intern\" \"2026-08-11\" \"Applied\"\n"
        "python scripts/track.py update 0 \"Interviewed\"\n"
        "python scripts/track.py render   # writes APPLICATIONS.md\n"
        "```\n",
        "---\n",
        "## Listings\n",
        f"**{len(active)} active listings** across {len(by_category)} categories. "
        f"Last refreshed: {refreshed_at}.\n",
        "Browse by category below, or go straight to "
        "**[today's Top 20 picks](TOP20.md)**.\n",
        "| Category | Active listings |",
        "|---|---|",
    ]
    for cat, slug, count in category_links:
        index.append(f"| [{cat}](listings/{slug}.md) | {count} |")
    index.append(
        "\n---\n"
        "*Sources and credits: [ATTRIBUTION.md](ATTRIBUTION.md) -- "
        "Scripts and usage: [USAGE.md](USAGE.md) -- "
        "Add a source: [CONTRIBUTING.md](CONTRIBUTING.md)*"
    )

    (ROOT / "README.md").write_text("\n".join(index) + "\n", encoding="utf-8")


def write_digest(listings: list, new_listings: list, closed_listings: list, fetched_sources: list):
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    time_str = datetime.now(timezone.utc).strftime("%H:%M UTC")
    digest_path = DIGESTS_DIR / f"{today_str}.md"

    active = [l for l in listings if l.get("active", True) and l.get("is_visible", True)]

    # load existing digest to append, so multiple runs accumulate entries for the day
    existing = digest_path.read_text(encoding="utf-8") if digest_path.exists() else ""
    header = f"# Digest — {today_str}\n\n[← back to index](../README.md)\n"

    section = f"\n## Snapshot at {time_str}\n\n"
    section += f"**Total active:** {len(active)}\n\n"

    if new_listings:
        section += f"### {len(new_listings)} new listing(s)\n\n"
        section += "| Company | Role | Location | Terms |\n|---|---|---|---|\n"
        for l in new_listings:
            company = l.get("company_name", "")
            url = l.get("url", "")
            title = l.get("title", "")
            loc = ", ".join(l.get("locations", []) or [])
            terms = ", ".join(l.get("terms", []) or [])
            company_cell = f"[{company}]({url})" if url else company
            section += f"| {company_cell} | {title} | {loc} | {terms} |\n"
    else:
        section += "*No new listings since last snapshot.*\n"

    if closed_listings:
        section += f"\n### {len(closed_listings)} listing(s) closed/removed\n\n"
        for l in closed_listings:
            section += f"- {l.get('company_name', '')} — {l.get('title', '')}\n"

    if existing:
        digest_path.write_text(existing + section, encoding="utf-8")
    else:
        digest_path.write_text(header + section, encoding="utf-8")


if __name__ == "__main__":
    main()
