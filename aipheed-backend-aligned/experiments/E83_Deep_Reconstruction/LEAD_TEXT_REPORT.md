# E83 lead-text extraction report

Generated from `backend/data/news_e83/leads.jsonl`: 9667 unique articles, every attempt logged per article.

**Why most articles are headline-only.**

- The corpus links are Google News redirects. Google's robots.txt disallows them, and they do not reveal the
  publisher URL.
- The publisher URL can be recovered only through the publisher's own sitemap or search API.
- Pages are fetched only when robots.txt allows this crawler and the AI-crawler tokens (ClaudeBot, anthropic-ai),
  with at least 2.5 s between requests per host.
- Bot challenges are never bypassed.
- Full bodies are not stored (E31 authorization). Only the publisher's description and up to 3 opening paragraphs
  (at most 1,200 characters) are kept.

## Status of all articles

| Status | Articles | Share | Meaning |
|---|---|---|---|
| no_method | 3687 | 38.1% | no permitted way to find the publisher URL (no article sitemap or search API; Google News links are robots-disallowed) |
| blocked | 2982 | 30.8% | publisher answers with a bot challenge or HTTP 403 (never bypassed) |
| robots_disallowed | 1812 | 18.7% | publisher robots.txt disallows the article path for this crawler or for AI crawlers |
| lead_ok | 730 | 7.6% | opening paragraphs extracted from the publisher page |
| unresolved | 456 | 4.7% | no publisher URL matched the headline in the publisher's sitemap/search (extraction failed) |

## Relevant (admitted) articles only: 695

| Status | Articles | Share |
|---|---|---|
| no_method | 268 | 38.6% |
| blocked | 164 | 23.6% |
| robots_disallowed | 149 | 21.4% |
| lead_ok | 87 | 12.5% |
| unresolved | 27 | 3.9% |

## By publisher (top 25 by volume)

| Publisher | Articles | lead_ok | meta_only | blocked | robots_disallowed | unresolved | no_method |
|---|---|---|---|---|---|---|---|
| newsinfo.inquirer.net | 2039 | 0 | 0 | 2039 | 0 | 0 | 0 |
| gmanetwork.com | 1567 | 0 | 0 | 0 | 1567 | 0 | 0 |
| mb.com.ph | 1524 | 0 | 0 | 0 | 0 | 0 | 1524 |
| philstar.com | 895 | 0 | 0 | 0 | 0 | 0 | 895 |
| da.gov.ph | 663 | 476 | 0 | 0 | 0 | 187 | 0 |
| business.inquirer.net | 470 | 0 | 0 | 470 | 0 | 0 | 0 |
| abs-cbn.com | 396 | 0 | 0 | 0 | 0 | 0 | 396 |
| pia.gov.ph | 277 | 0 | 0 | 0 | 0 | 0 | 277 |
| rappler.com | 245 | 0 | 0 | 0 | 245 | 0 | 0 |
| pna.gov.ph | 242 | 0 | 0 | 0 | 0 | 0 | 242 |
| bworldonline.com | 166 | 151 | 0 | 0 | 0 | 15 | 0 |
| businessmirror.com.ph | 140 | 0 | 0 | 0 | 0 | 140 | 0 |
| interaksyon.philstar.com | 131 | 0 | 0 | 0 | 0 | 0 | 131 |
| sunstar.com.ph | 110 | 0 | 0 | 0 | 0 | 110 | 0 |
| fo4a.dswd.gov.ph | 107 | 103 | 0 | 0 | 0 | 4 | 0 |
| manilatimes.net | 100 | 0 | 0 | 0 | 0 | 0 | 100 |
| globalnation.inquirer.net | 100 | 0 | 0 | 100 | 0 | 0 | 0 |
| opinion.inquirer.net | 94 | 0 | 0 | 94 | 0 | 0 | 0 |
| entertainment.inquirer.net | 71 | 0 | 0 | 71 | 0 | 0 | 0 |
| onenews.ph | 70 | 0 | 0 | 0 | 0 | 0 | 70 |
| cebudailynews.inquirer.net | 57 | 0 | 0 | 57 | 0 | 0 | 0 |
| inquirer.net | 43 | 0 | 0 | 43 | 0 | 0 | 0 |
| lifestyle.inquirer.net | 42 | 0 | 0 | 42 | 0 | 0 | 0 |
| uplb.edu.ph | 40 | 0 | 0 | 40 | 0 | 0 | 0 |
| dswd.gov.ph | 21 | 0 | 0 | 0 | 0 | 0 | 21 |

Lead text available for 730 articles (mean lead length 758 characters).
Most come from government and WordPress publishers (DA, DSWD FO4A, BusinessWorld, SunStar), so lead-text features describe press releases more than independent reporting.
