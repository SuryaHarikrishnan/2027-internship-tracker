# Internship Tracker — Summer 2026 & Summer 2027 Internships + New Grad Jobs

A daily-updated, deduplicated list of **software engineering, AI/ML, data science, hardware, quant, and product internships and new grad roles**, aggregated from multiple community-maintained sources into one place, browsable by category.

If you're searching for a **Summer 2027 internships GitHub repo**, a **Summer 2026 internships tracker**, or a **new grad software engineering jobs list**, this aggregates several of those trackers so you don't have to check each one.

⭐ **Star this repo** to stay current — listings refresh 5× a day. **Fork it** to get your own personal application tracker alongside the listings.

## Track your own applications, not just browse listings

Most listing repos stop at the list. This one also gives you a personal application tracker that lives next to the data:

```bash
git clone https://github.com/YOUR_USERNAME/internship-tracker  # fork first
cd internship-tracker
python scripts/track.py add "Stripe" "SWE Intern" "2026-06-29" "Applied"
python scripts/track.py render  # regenerates APPLICATIONS.md
```

[APPLICATIONS.md](APPLICATIONS.md) gets a *days-since-applied* column automatically so you can see what's gone quiet. The daily listings refresh runs via GitHub Actions on any fork — no local machine needed. See [USAGE.md](USAGE.md) for full details.

## How this works

A script runs 5× per day, pulls the latest active listings from the source repos, merges and deduplicates them by company + role + location, and updates: this index, the per-category files in [`listings/`](listings/), and a daily diff in [`digests/`](digests/) showing what's new and what closed. See [ATTRIBUTION.md](ATTRIBUTION.md) for source credits and [CONTRIBUTING.md](CONTRIBUTING.md) to add new sources.

Last refreshed: **2026-07-19 14:20 UTC**. Sources: simplify-2026, vanshb03-2026, vanshb03-2027.

**Active listings: 1219** (of 13104 total seen across all sources)

See [APPLICATIONS.md](APPLICATIONS.md) for personal application tracking.


## Browse by category

| Category | Active listings |
|---|---|
| [Data Science, AI & Machine Learning](listings/data-science-ai-machine-learning.md) | 418 |
| [Hardware Engineering](listings/hardware-engineering.md) | 152 |
| [Other](listings/other.md) | 125 |
| [Product Management](listings/product-management.md) | 32 |
| [Quantitative Finance](listings/quantitative-finance.md) | 97 |
| [Software Engineering](listings/software-engineering.md) | 395 |

---
*Listings data sourced from community trackers — see [ATTRIBUTION.md](ATTRIBUTION.md)*
