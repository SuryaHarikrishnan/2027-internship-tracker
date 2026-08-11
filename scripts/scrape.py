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
        "# Internship Tracker — Summer 2026 & Summer 2027 Internships + New Grad Jobs\n",
        "A daily-updated, deduplicated list of **software engineering, AI/ML, data science, "
        "hardware, quant, and product internships and new grad roles**, aggregated from "
        "multiple community-maintained sources into one place, browsable by category.\n",
        "If you're searching for a **Summer 2027 internships GitHub repo**, a "
        "**Summer 2026 internships tracker**, or a **new grad software engineering jobs list**, "
        "this aggregates several of those trackers so you don't have to check each one.\n",
        "⭐ **Star this repo** to stay current — listings refresh 5× a day. "
        "**Fork it** to get your own personal application tracker alongside the listings.\n",
        "📋 **[Today's Top 20 picks →](TOP20.md)** — highest-signal companies with fresh openings, updated every refresh.\n",
        "## Track your own applications, not just browse listings\n",
        "Most listing repos stop at the list. This one also gives you a personal application "
        "tracker that lives next to the data:\n",
        "```bash\n"
        "git clone https://github.com/YOUR_USERNAME/internship-tracker  # fork first\n"
        "cd internship-tracker\n"
        "python scripts/track.py add \"Stripe\" \"SWE Intern\" \"2026-06-29\" \"Applied\"\n"
        "python scripts/track.py render  # regenerates APPLICATIONS.md\n"
        "```\n",
        "[APPLICATIONS.md](APPLICATIONS.md) gets a *days-since-applied* column automatically "
        "so you can see what's gone quiet. The daily listings refresh runs via GitHub Actions "
        "on any fork — no local machine needed. See [USAGE.md](USAGE.md) for full details.\n",
        "## How this works\n",
        "A script runs 5× per day, pulls the latest active listings from the source repos, "
        "merges and deduplicates them by company + role + location, and updates: "
        "this index, the per-category files in [`listings/`](listings/), and a daily "
        "diff in [`digests/`](digests/) showing what's new and what closed. "
        "See [ATTRIBUTION.md](ATTRIBUTION.md) for source credits and "
        "[CONTRIBUTING.md](CONTRIBUTING.md) to add new sources.\n",
    ]
    index.append(
        f"Last refreshed: **{refreshed_at}**. "
        f"Sources: {', '.join(fetched_sources) or 'none (cached)'}.\n"
    )
    index.append(
        f"**Active listings: {len(active)}** (of {len(listings)} total seen across all sources)\n"
    )
    index.append("See [APPLICATIONS.md](APPLICATIONS.md) for personal application tracking.\n")
    index.append("\n## Browse by category\n")
    index.append("| Category | Active listings |")
    index.append("|---|---|")
    for cat, slug, count in category_links:
        index.append(f"| [{cat}](listings/{slug}.md) | {count} |")
    index.append(f"\n---\n*Listings data sourced from community trackers — see [ATTRIBUTION.md](ATTRIBUTION.md)*")

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
