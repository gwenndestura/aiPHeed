"""Objective 1 measurements from the served news pipeline (app.news.pipeline_v3), run with cwd = backend."""
import collections
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, ".")
from app.news import pipeline_v3 as P  # noqa: E402

OUT = Path(sys.argv[1])
C = P.corpus()
rel = [a for a in C if a["relevant"] == 1]
adm = P.admitted()
_, dropped = P.dedupe(rel)
FIL = set("ang mga sa ng na nang para presyo bigas gutom kagutuman tulong magsasaka mangingisda ayuda tumaas bumaba".split())


def lang(t):
    w = set(re.findall(r"[a-z]+", t.lower()))
    return "fil" if len(w & FIL) >= 2 else "eng_or_mixed"


res = {"corpus_in_window": len(C), "relevant": len(rel), "admitted_after_dedupe": len(adm),
       "syndication_dropped": len(dropped),
       "admitted_province_attributed": sum(1 for a in adm if a["province_code"]),
       "admitted_national": sum(1 for a in adm if not a["province_code"]),
       "admitted_by_province": dict(collections.Counter(P.PROVINCE_CODES.index(a["province_code"]) and a["province_code"] or a["province_code"]
                                                        for a in adm if a["province_code"])),
       "language_heuristic_admitted": dict(collections.Counter(lang(a["title"]) for a in adm)),
       "top_outlets_share_admitted": None, "retrospective": None}
oc = collections.Counter(a["outlet"] for a in adm)
res["top_outlets_share_admitted"] = [(o, n, round(n / len(adm), 3)) for o, n in oc.most_common(8)]
res["n_outlets_admitted"] = len(oc)
fs = [a for a in adm if a.get("first_seen_at")]
late = 0
for a in fs:
    try:
        s = datetime.fromisoformat(a["first_seen_at"].replace("Z", "+00:00")).replace(tzinfo=None)
        late += s > P.origin(P.qi(a["quarter"]))
    except Exception:  # noqa: BLE001
        pass
res["retrospective"] = {"admitted_with_first_seen": len(fs), "first_seen_after_issue_date_of_their_quarter": late}
# sufficiency per province-quarter at each origin 2021-Q1..2026-Q3 (as-of)
cells = []
for t in range(P.qi("2021-Q1"), P.qi("2026-Q3") + 1):
    arts = P.asof(t)
    for p in P.PROVINCE_CODES:
        f = P.fssi_v3(p, t, arts)
        cells.append({"t": P.qs(t), "p": p, "n": f["n"], "status": f["status"], "fssi": f["fssi"], "bw": f["bias_weight"]})
st = collections.Counter(c["status"] for c in cells)
res["province_quarters"] = len(cells)
res["status_counts"] = dict(st)
res["sufficient_by_province"] = dict(collections.Counter(c["p"] for c in cells if c["status"] == "SUFFICIENT"))
res["zero_article_by_province"] = dict(collections.Counter(c["p"] for c in cells if c["n"] == 0))
bws = [c["bw"] for c in cells if c["bw"] is not None]
res["bias_weight_range"] = [min(bws), max(bws)]
res["median_n_by_province"] = {p: sorted(c["n"] for c in cells if c["p"] == p)[len([c for c in cells if c["p"] == p]) // 2] for p in P.PROVINCE_CODES}
OUT.write_text(json.dumps(res, indent=1, default=str))
print(json.dumps(res, indent=1, default=str))
