# Domestic India Roles

[← back to index](../README.md)

**A standalone list, not part of the rest of this repo.** It is not fed by the auto-refresh pipeline used for the categories above and does not integrate with the application tracker (`scripts/track.py`). The companies below are checked directly against their own public career-site APIs every ~3 days -- no AI judgment, no aggregators, just a plain scraper like the one used for the rest of this repo.

Last automated check: 2026-09-19 12:48 UTC

## Confirmed open postings (auto-checked every 3 days)

### Amazon

| Role | Location | Link |
|---|---|---|
| Financial Analyst Intern | Bengaluru | [Apply](https://www.amazon.jobs/en/jobs/10498382/financial-analyst-intern) |

### Adobe

| Role | Location | Link |
|---|---|---|
| Intern - Returnship - RMO | Bangalore | [Apply](https://adobe.wd5.myworkdayjobs.com/en-US/external_experienced/job/Bangalore/Intern---Returnship---RMO_R171621) |
| Internal Product Manager 3 - Sales Performance Management | Bangalore | [Apply](https://adobe.wd5.myworkdayjobs.com/en-US/external_experienced/job/Bangalore/Product-Manager-3_R169439) |

### Razorpay

*No open internship listings found in this pass.*

## Other big tech in India (no public API found -- browse manually)

These companies don't expose a scrapable public job feed as far as we could find, so they aren't auto-checked. Browse directly:

- [Google](https://careers.google.com/students/internships)
- [Microsoft](https://careers.microsoft.com)
- [Atlassian](https://www.atlassian.com/company/careers)
- [Flipkart](https://www.flipkartcareers.com)
- [Zoho](https://careers.zohocorp.com)

## How this section updates

A GitHub Actions workflow runs this script (`scripts/scrape_india.py`) every 3 days. It queries each confirmed company's own public API directly (Amazon's job search API, Adobe's Workday API, Razorpay's Workable API) and rewrites the table above -- fully automated, no manual review, free (no external API keys or paid services involved). Companies in the "no public API found" list are not touched by automation; add a fetcher function in the script if a working endpoint turns up for one of them.
