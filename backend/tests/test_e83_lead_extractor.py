"""E83 lead-text extractor: robots compliance, challenge detection, parsing, statuses, idempotence (no network)."""
import json

from app.news import lead_extractor as LX


class Resp:
    def __init__(self, text, status=200, ctype="text/html; charset=utf-8"):
        self.text, self.status_code, self.headers, self.encoding = text, status, {"content-type": ctype}, "utf-8"


ROBOTS_OK = "User-agent: *\nDisallow: /wp-admin/\n"
ROBOTS_NO_CLAUDE = "User-agent: ClaudeBot\nDisallow: /\n\nUser-agent: *\nDisallow:\n"
PAGE = """<html><head><meta property="og:description" content="Prices of rice rose in Laguna markets."></head>
<body><article><p>Prices of well-milled rice rose by two pesos per kilo in Laguna public markets this week, traders said.</p>
<p>Subscribe to our newsletter for more updates and exclusive stories every week.</p>
<p>The Department of Agriculture said supply remains adequate despite the recent typhoon damage in the province.</p>
</article><script>var x = "<p>not text</p>";</script></body></html>"""
SITEMAP_INDEX = "<sitemapindex><sitemap><loc>https://www.da.gov.ph/post-sitemap.xml</loc><lastmod>2026-10-20</lastmod></sitemap></sitemapindex>"
SITEMAP = ("<urlset><url><loc>https://www.da.gov.ph/rice-prices-rise-in-laguna-markets/</loc><lastmod>2026-09-02</lastmod></url>"
           "<url><loc>https://www.da.gov.ph/unrelated-story/</loc><lastmod>2026-09-02</lastmod></url></urlset>")


def fetcher(routes):
    calls = []

    def get(url):
        calls.append(url)
        r = routes.get(url)
        return r if r is not None else Resp("not found", 404)
    f = LX.Fetcher(get=get, sleep=lambda s: None)
    f.calls = calls
    return f


def test_parse_page_extracts_meta_and_opening_paragraphs_without_boilerplate():
    p = LX.parse_page(PAGE)
    assert p["meta_description"] == "Prices of rice rose in Laguna markets."
    assert p["lead"].startswith("Prices of well-milled rice") and "newsletter" not in p["lead"]
    assert "not text" not in p["lead"] and p["body_paragraphs"] == 2


def test_robots_disallow_for_ai_crawler_tokens_is_respected():
    f = fetcher({"https://x.example/robots.txt": Resp(ROBOTS_NO_CLAUDE)})
    assert not f.allowed("https://x.example/story")
    f2 = fetcher({"https://y.example/robots.txt": Resp(ROBOTS_OK)})
    assert f2.allowed("https://y.example/story") and not f2.allowed("https://y.example/wp-admin/a")


def test_unknown_robots_policy_means_no_fetch():
    f = fetcher({"https://z.example/robots.txt": Resp("err", 503)})
    assert not f.allowed("https://z.example/story")


def test_challenge_page_is_blocked_not_parsed():
    f = fetcher({"https://w.example/a": Resp("<title>Just a moment...</title>", 403)})
    r, out = f.fetch("https://w.example/a")
    assert out == "blocked"


def test_extract_resolves_via_sitemap_and_is_idempotent(tmp_path):
    routes = {"https://www.da.gov.ph/robots.txt": Resp(ROBOTS_OK),
              "https://www.da.gov.ph/sitemap_index.xml": Resp(SITEMAP_INDEX, ctype="application/xml"),
              "https://www.da.gov.ph/post-sitemap.xml": Resp(SITEMAP, ctype="application/xml"),
              "https://www.da.gov.ph/rice-prices-rise-in-laguna-markets/": Resp(PAGE)}
    arts = [{"article_key": "a1", "title": "Rice prices rise in Laguna markets", "source_domain": "da.gov.ph",
             "ph_date": "2026-09-01"},
            {"article_key": "a2", "title": "Totally different headline", "source_domain": "gmanetwork.com",
             "ph_date": "2026-09-01"},
            {"article_key": "a3", "title": "Something", "source_domain": "unknown.example", "ph_date": "2026-09-01"}]
    out = tmp_path / "leads.jsonl"
    c = LX.extract(arts, out, f=fetcher(routes))
    recs = {r["article_key"]: r for r in map(json.loads, out.read_text(encoding="utf-8").splitlines())}
    assert recs["a1"]["extraction_status"] == "lead_ok"
    assert recs["a1"]["publisher_url"].endswith("rice-prices-rise-in-laguna-markets/")
    assert recs["a2"]["extraction_status"] == "robots_disallowed"
    assert recs["a3"]["extraction_status"] == "no_method"
    assert all(r["attempts"] is not None for r in recs.values())
    assert "_body_text" not in out.read_text(encoding="utf-8")          # no full text is stored
    again = LX.extract(arts, out, f=fetcher(routes))
    assert again == {} and len(out.read_text(encoding="utf-8").splitlines()) == 3
