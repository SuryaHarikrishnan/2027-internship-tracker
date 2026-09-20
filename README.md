# 2027 Internship Tracker

![demo](assets/demo.svg)

**Summer 2026 and Summer 2027 SWE, AI/ML, Quant, Hardware, and PM internship listings -- plus a built-in application tracker so you know where you applied, when, and how long ago.**

> Just here for the list? [Jump to listings](#listings)

Most internship repos stop at the list. Fork this one and you also get:

- A personal tracker that lives next to the listings
- A `days-since-applied` column so nothing goes quiet without you noticing
- Daily Top 20 picks ranked by freshness + company signal + YC batch
- Listings that refresh 5x per day automatically via GitHub Actions -- no setup needed

**[Fork to start tracking your applications →](https://github.com/SuryaHarikrishnan/2027-internship-tracker/fork)**

```bash
python scripts/track.py add "Stripe" "SWE Intern" "2026-08-11" "Applied"
python scripts/track.py update 0 "Interviewed"
python scripts/track.py render   # writes APPLICATIONS.md
```

---

## Listings

**4119 active listings** across 6 categories. Last refreshed: 2026-09-20 10:08 UTC.

Browse by category below, or go straight to **[today's Top 20 picks](TOP20.md)**.

| Category | Active listings |
|---|---|
| [Data Science, AI & Machine Learning](listings/data-science-ai-machine-learning.md) | 1427 |
| [Hardware Engineering](listings/hardware-engineering.md) | 639 |
| [Other](listings/other.md) | 308 |
| [Product Management](listings/product-management.md) | 225 |
| [Quantitative Finance](listings/quantitative-finance.md) | 224 |
| [Software Engineering](listings/software-engineering.md) | 1296 |

---
**[Domestic India roles](listings/domestic-india.md)** -- a separate, auto-refreshed list of India-based postings pulled directly from a few big tech companies' own career-site APIs, every ~3 days. List only -- not part of the auto-refresh above and not integrated with the application tracker.

---
*Sources and credits: [ATTRIBUTION.md](ATTRIBUTION.md) -- Scripts and usage: [USAGE.md](USAGE.md) -- Add a source: [CONTRIBUTING.md](CONTRIBUTING.md)*
