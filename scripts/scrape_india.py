#!/usr/bin/env python3
"""Fetches India-based internship/entry-level listings directly from the
small set of employers whose career sites expose a public, unauthenticated
JSON API (verified by hand -- see README history). Unlike scrape.py, there
is no single aggregated feed for domestic India roles, so each company is
queried individually.

Companies with no discoverable public API (Google, Microsoft, Atlassian,
Flipkart, Zoho, ...) are listed as static browse links in
NO_API_COMPANIES below and are never touched by this script -- add a
fetch_<company>() function and register it in FETCHERS once a working
endpoint is found for one of them.
"""
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LISTINGS_PATH = ROOT / "listings" / "domestic-india.md"

HEADERS = {"User-Agent": "internship-tracker/1.0 (personal aggregator)"}

INDIA_HINTS = [
    "india", "bangalore", "bengaluru", "hyderabad", "noida", "pune",
    "mumbai", "delhi", "gurugram", "gurgaon", "chennai", "kolkata",
]

NO_API_COMPANIES = [
    ("Google", "https://careers.google.com/students/internships"),
    ("Microsoft", "https://careers.microsoft.com"),
    ("Atlassian", "https://www.atlassian.com/company/careers"),
    ("Flipkart", "https://www.flipkartcareers.com"),
    ("Zoho", "https://careers.zohocorp.com"),
]


def fetch_json(url: str, data: dict | None = None) -> dict:
    headers = dict(HEADERS, **({"Content-Type": "application/json"} if data is not None else {}))
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method="POST" if data is not None else "GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def looks_intern(title: str) -> bool:
    return "intern" in (title or "").lower()


def looks_india(text: str) -> bool:
    t = (text or "").lower()
    return any(h in t for h in INDIA_HINTS)


def fetch_amazon() -> list:
    # business_category=studentprograms is amazon.jobs's own category for
    # intern/student roles (confirmed via its facet listing) -- more
    # reliable than the "is_intern" field, which is inconsistently set.
    results = []
    try:
        data = fetch_json(
            "https://www.amazon.jobs/en/search.json?"
            "normalized_country_code%5B%5D=IND&business_category%5B%5D=studentprograms"
            "&offset=0&result_limit=100&sort=recent"
        )
    except Exception as exc:
        print(f"[warn] amazon fetch failed: {exc}")
        return results
    for j in data.get("jobs", []):
        results.append({
            "title": j.get("title", ""),
            "location": j.get("city") or j.get("location") or "India",
            "url": "https://www.amazon.jobs" + j.get("job_path", ""),
            "posted": (j.get("posted_date") or "")[:10],
        })
    return results


def fetch_adobe() -> list:
    # Workday's CXS API rejects limit > 20, so page through it manually.
    results = []
    offset = 0
    page_size = 20
    max_pages = 5
    for _ in range(max_pages):
        try:
            data = fetch_json(
                "https://adobe.wd5.myworkdayjobs.com/wday/cxs/adobe/external_experienced/jobs",
                data={"appliedFacets": {}, "limit": page_size, "offset": offset, "searchText": "intern"},
            )
        except Exception as exc:
            print(f"[warn] adobe fetch failed at offset {offset}: {exc}")
            break
        postings = data.get("jobPostings", [])
        if not postings:
            break
        for j in postings:
            title = j.get("title", "")
            loc = j.get("locationsText", "")
            if not looks_intern(title) or not looks_india(loc):
                continue
            results.append({
                "title": title,
                "location": loc,
                "url": "https://adobe.wd5.myworkdayjobs.com/en-US/external_experienced" + j.get("externalPath", ""),
                "posted": "",
            })
        offset += page_size
        if offset >= data.get("total", 0):
            break
    return results


def fetch_razorpay() -> list:
    results = []
    try:
        data = fetch_json(
            "https://apply.workable.com/api/v3/accounts/razorpay/jobs",
            data={"query": "", "location": []},
        )
    except Exception as exc:
        print(f"[warn] razorpay fetch failed: {exc}")
        return results
    for j in data.get("results", []):
        title = j.get("title", "")
        if not looks_intern(title):
            continue
        loc = j.get("location")
        loc_str = loc.get("city", "India") if isinstance(loc, dict) else "India"
        results.append({
            "title": title,
            "location": loc_str,
            "url": j.get("url", "https://apply.workable.com/razorpay/"),
            "posted": "",
        })
    return results


FETCHERS = {
    "Amazon": fetch_amazon,
    "Adobe": fetch_adobe,
    "Razorpay": fetch_razorpay,
}


def company_section(company: str, roles: list) -> str:
    lines = [f"### {company}\n"]
    if not roles:
        lines.append("*No open internship listings found in this pass.*\n")
        return "\n".join(lines)
    lines.append("| Role | Location | Link |")
    lines.append("|---|---|---|")
    for r in roles:
        lines.append(f"| {r['title']} | {r['location']} | [Apply]({r['url']}) |")
    return "\n".join(lines) + "\n"


def write_file(all_results: dict):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Domestic India Roles\n",
        "[← back to index](../README.md)\n",
        "**A standalone list, not part of the rest of this repo.** It is not "
        "fed by the auto-refresh pipeline used for the categories above and "
        "does not integrate with the application tracker (`scripts/track.py`). "
        "The companies below are checked directly against their own public "
        "career-site APIs every ~3 days -- no AI judgment, no aggregators, "
        "just a plain scraper like the one used for the rest of this repo.\n",
        f"Last automated check: {now}\n",
        "## Confirmed open postings (auto-checked every 3 days)\n",
    ]
    for company in FETCHERS:
        lines.append(company_section(company, all_results.get(company, [])))
    lines.append(
        "## Other big tech in India (no public API found -- browse manually)\n"
    )
    lines.append(
        "These companies don't expose a scrapable public job feed as far as "
        "we could find, so they aren't auto-checked. Browse directly:\n"
    )
    for name, url in NO_API_COMPANIES:
        lines.append(f"- [{name}]({url})")
    lines.append("")
    lines.append("## How this section updates\n")
    lines.append(
        "A GitHub Actions workflow runs this script "
        "(`scripts/scrape_india.py`) every 3 days. It queries each "
        "confirmed company's own public API directly (Amazon's job search "
        "API, Adobe's Workday API, Razorpay's Workable API) and rewrites "
        "the table above -- fully automated, no manual review, free (no "
        "external API keys or paid services involved). Companies in the "
        "\"no public API found\" list are not touched by automation; add a "
        "fetcher function in the script if a working endpoint turns up for "
        "one of them.\n"
    )
    LISTINGS_PATH.write_text("\n".join(lines), encoding="utf-8")


def main():
    all_results = {}
    total = 0
    for company, fetcher in FETCHERS.items():
        roles = fetcher()
        all_results[company] = roles
        total += len(roles)
    write_file(all_results)
    counts = ", ".join(f"{c}: {len(r)}" for c, r in all_results.items())
    print(f"Domestic India refresh -- {total} matching listing(s) ({counts}).")


if __name__ == "__main__":
    main()
