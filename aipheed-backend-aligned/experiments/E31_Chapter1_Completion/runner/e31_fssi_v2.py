"""E31: score the R1-admitted articles (v2 intensity) and build FSSI-v1 (unchanged definition, E31 store) and FSSI-v2
for 2021-Q1..2026-Q4 (2026-Q4 = 1-14 October only)."""
import json, sys
from pathlib import Path
sys.dont_write_bytecode = True
EXP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXP / "runner")); sys.path.insert(0, str(EXP / "backend_dev"))
import guard31  # noqa: E402
guard31.install()
from app.news.store import NewsStore  # noqa: E402
from app.news.fssi_v2 import admitted_articles, build_fssi_v2, score_admitted  # noqa: E402
from app.news.fssi import build_fssi  # noqa: E402
from app.news.timeutil import quarters_between  # noqa: E402
store = NewsStore(EXP / "backend_dev" / "data" / "news_e31")
kept, funnel = admitted_articles(store)
print("funnel", funnel, "admitted", len(kept))
print(score_admitted(store, [a["article_key"] for a in kept]))
qs = quarters_between("2021-Q1", "2026-Q4")
v1 = build_fssi(store, qs)
v2 = build_fssi_v2(store, qs)
print("v1", v1["summary"]["evidence_status_counts"], "v2", v2["manifest"]["evidence_status_counts"], v2["manifest"]["n_admitted_total"])
