"""E31: the date-level authorized limit (authorized_through) inside the last authorized quarter."""
from datetime import date, datetime, timezone

import _paths  # noqa: F401
from app.news.collector import Collector
from app.news.store import NewsStore


class _Src:
    name = "fake"

    def __init__(self):
        self.calls = []

    def search(self, query, a, b):
        from app.news import sources as S
        self.calls.append((a, b))
        items = [{"title": "Fish kill hits Taal Lake", "link": f"https://x/{a}", "source_item_id": str(a),
                  "source_domain": "newsinfo.inquirer.net", "published_raw": f"{a.isoformat()}T02:00:00Z"},
                 {"title": "Rice prices up in Batangas", "link": "https://x/late", "source_item_id": "late",
                  "source_domain": "newsinfo.inquirer.net", "published_raw": "2026-10-15T02:00:00Z"}]
        return S.FetchResult(source=self.name, status=S.OK, items=items, n_raw=len(items), http_status=200, attempts=1)


def test_nothing_after_authorized_through_is_admitted_or_queried(tmp_path):
    src = _Src()
    col = Collector(NewsStore(tmp_path / "s"), [src], authorized_until="2026-Q4", authorized_through="2026-10-14",
                    now=datetime(2026, 12, 20, tzinfo=timezone.utc), credible=lambda d: True, geocode=lambda t: None)
    col.run("backfill", ["2026-Q4"], provinces=["Batangas"])
    assert all(a < date(2026, 11, 1) for a, _ in src.calls)          # November/December windows are not queried
    keys = [a["published_ph"] for a in col.store.articles.values()]
    assert keys and all(k < "2026-10-15" for k in keys)
    rej = [r["reason"] for r in col.store.read("rejected")]
    assert "AFTER_AUTHORIZED_LIMIT" in rej
