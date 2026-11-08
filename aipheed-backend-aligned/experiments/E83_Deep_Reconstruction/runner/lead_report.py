"""E83 LEAD_TEXT_REPORT.md from backend/data/news_e83/leads.jsonl (run from backend/)."""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, ".")
from app.news import pipeline_v3 as P  # noqa: E402

LEADS = Path("data/news_e83/leads.jsonl")
OUT = Path("../aipheed-backend-aligned/experiments/E83_Deep_Reconstruction/LEAD_TEXT_REPORT.md")
REASON = {
    "lead_ok": "opening paragraphs extracted from the publisher page",
    "meta_only": "only the publisher's own description/excerpt available",
    "robots_disallowed": "publisher robots.txt disallows the article path for this crawler or for AI crawlers",
    "blocked": "publisher answers with a bot challenge or HTTP 403 (never bypassed)",
    "unresolved": "no publisher URL matched the headline in the publisher's sitemap/search (extraction failed)",
    "fetch_error": "network or parse failure after 3 tries",
    "no_method": "no permitted way to find the publisher URL (no article sitemap or search API; Google News links are robots-disallowed)",
}

R = [json.loads(l) for l in LEADS.read_text(encoding="utf-8").splitlines()]
last = {}
for r in R:                                   # a later retry supersedes an earlier record of the same article
    last[r["article_key"]] = r
R = list(last.values())
st = Counter(r["extraction_status"] for r in R)
dom = defaultdict(Counter)
for r in R:
    dom[r["source_domain"]][r["extraction_status"]] += 1
rel = {a["article_key"] for a in P.admitted()}
rs = Counter(r["extraction_status"] for r in R if r["article_key"] in rel)
withlead = [r for r in R if r["extraction_status"] in ("lead_ok", "meta_only")]
lines = [
    "# E83 lead-text extraction report",
    "",
    f"Generated from `backend/data/news_e83/leads.jsonl`: {len(R)} unique articles, every attempt logged per article.",
    "",
    "**Why most articles are headline-only.**",
    "",
    "- The corpus links are Google News redirects. Google's robots.txt disallows them, and they do not reveal the",
    "  publisher URL.",
    "- The publisher URL can be recovered only through the publisher's own sitemap or search API.",
    "- Pages are fetched only when robots.txt allows this crawler and the AI-crawler tokens (ClaudeBot, anthropic-ai),",
    "  with at least 2.5 s between requests per host.",
    "- Bot challenges are never bypassed.",
    "- Full bodies are not stored (E31 authorization). Only the publisher's description and up to 3 opening paragraphs",
    "  (at most 1,200 characters) are kept.",
    "",
    "## Status of all articles",
    "",
    "| Status | Articles | Share | Meaning |",
    "|---|---|---|---|",
] + [f"| {k} | {v} | {v / len(R):.1%} | {REASON.get(k, k)} |" for k, v in st.most_common()] + [
    "",
    f"## Relevant (admitted) articles only: {len(rel)}",
    "",
    "| Status | Articles | Share |",
    "|---|---|---|",
] + [f"| {k} | {v} | {v / max(sum(rs.values()), 1):.1%} |" for k, v in rs.most_common()] + [
    "",
    "## By publisher (top 25 by volume)",
    "",
    "| Publisher | Articles | lead_ok | meta_only | blocked | robots_disallowed | unresolved | no_method |",
    "|---|---|---|---|---|---|---|---|",
] + [f"| {d} | {sum(c.values())} | {c['lead_ok']} | {c['meta_only']} | {c['blocked']} | {c['robots_disallowed']} | "
     f"{c['unresolved']} | {c['no_method']} |" for d, c in sorted(dom.items(), key=lambda kv: -sum(kv[1].values()))[:25]] + [
    "",
    f"Lead text available for {len(withlead)} articles "
    f"(mean lead length {sum(len(r['lead'] or r['meta_description']) for r in withlead) / max(len(withlead), 1):.0f} characters).",
    "Most come from government and WordPress publishers (DA, DSWD FO4A, BusinessWorld, SunStar), so lead-text features describe press releases more than independent reporting.",
]
OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines[:40]))
