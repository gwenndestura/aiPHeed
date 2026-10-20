"""E74: trace the employment driver (FIRI v2 indicator E1 = national LFS unemployment-rate change) from the raw file to
the dashboard, recompute every displayed driver independently, and compare employment with every other driver.
Run with cwd = backend and AIPHEED_LEAD2_MODEL=thesis. Writes ../aipheed-backend-aligned/experiments/E74_.../out/.

Independent recomputations (no FIRI code used for these numbers):
  * E1 raw value from lfs_rates_national.csv: mean unemployment rate of the months of quarter t-1 minus that of t-5;
  * E1 score = mid-rank percentile among the earlier E1 values (prior list served by thesis_system.prior_for);
  * every indicator push = normalised domain weight x (score - 0.5) / indicators observed in its domain;
  * the five bar percentages = |group push| / sum of |group push| over the five groups (largest remainder);
  * the full-role ranking (dimensions.py) including observed regional hunger, vulnerability and news.
"""
import csv
import json
import math
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, ".")
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.ml.inference import dimensions as D  # noqa: E402
from app.ml.inference import e41_lead2 as LEAD2  # noqa: E402
from app.ml.inference import thesis_system as T  # noqa: E402

E74 = Path("../aipheed-backend-aligned/experiments/E74_Employment_Driver_Audit")
LFS = Path("../aipheed-backend-aligned/experiments/E41_Lead2_Audit/data_acquired/lfs_rates_national.csv")
MONTHS = {m: i for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August",
                                      "September", "October", "November", "December"])}
SLUG = {"PH040100000": "cavite", "PH040200000": "laguna", "PH040300000": "quezon", "PH040400000": "rizal",
        "PH040500000": "batangas"}
c = TestClient(app)


def qi(q):
    return int(q[:4]) * 4 + int(q[-1]) - 1


def qs(i):
    return f"{i // 4}-Q{i % 4 + 1}"


def lfs_ur():
    ur = {}
    for r in csv.DictReader(LFS.open(encoding="utf-8")):
        if r["Rates"] == "Unemployment Rate" and r["Month"] in MONTHS and r["value"]:
            ur[int(r["Year"]) * 12 + MONTHS[r["Month"]]] = float(r["value"])
    return ur


def e1_independent(ur, origin_q):
    """ur_yoy at origin t: mean of quarter t-1's available months minus quarter t-5's (e41_lib.features)."""
    t = qi(origin_q)

    def qm(q):
        v = [ur[q // 4 * 12 + (q % 4) * 3 + j] for j in range(3) if (q // 4 * 12 + (q % 4) * 3 + j) in ur]
        return (sum(v) / len(v), len(v)) if v else (None, 0)
    a, na = qm(t - 1)
    b, nb = qm(t - 5)
    return (None if a is None or b is None else a - b), {"quarter_t_minus_1": qs(t - 1), "months_t_minus_1": na,
                                                         "quarter_t_minus_5": qs(t - 5), "months_t_minus_5": nb}


def pct_mid(x, prior):
    return (sum(v < x for v in prior) + 0.5 * sum(v == x for v in prior)) / len(prior)


def integer_shares(vals):
    tot = sum(vals)
    if tot <= 0:
        return [0] * len(vals)
    ex = [v / tot * 100 for v in vals]
    fl = [int(x) for x in ex]
    for i in sorted(range(len(ex)), key=lambda i: ex[i] - fl[i], reverse=True)[:100 - sum(fl)]:
        fl[i] += 1
    return fl


def main():
    # set here, not at import, so that importing the helpers (the E74 tests do) never changes the process mode
    os.environ.setdefault("AIPHEED_LEAD2_MODEL", "thesis")
    os.environ.setdefault("AIPHEED_NOW", "2026-10-20T09:00:00")
    rec = LEAD2.record()
    ur = lfs_ur()
    hist = list(csv.DictReader(open(T.FIRI_HISTORY, encoding="utf-8")))
    keys = sorted({(r["target"], r["province_code"]) for r in hist if r["FIRI"]} | {(rec["targetQuarter"], p) for p in rec["provinces"]})
    rows, issues = [], []
    for q, code in keys:
        f = T.firi_for(rec, q, code)
        if not f or f["firi"] is None:
            continue
        origin = qs(qi(q) - 2)
        w = T._norm_weights(f)
        ind = f["indicators"]
        per_dom = defaultdict(list)
        for k, v in ind.items():
            if v["score"] is not None and v["domain"] in w:
                per_dom[v["domain"]].append(k)
        push = {k: w[d] * (ind[k]["score"] - 0.5) / len(ks) for d, ks in per_dom.items() for k in ks}
        # independent E1
        e1x, e1meta = e1_independent(ur, origin)
        e1 = ind["E1"]
        e1_served_x = None if e1.get("x") is None else float(e1["x"])
        if e1x is not None and e1_served_x is not None and abs(e1x - e1_served_x) > 1e-6:
            issues.append({"target": q, "province": code, "issue": "E1 raw value differs", "independent": e1x, "served": e1_served_x})
        prior = (T.prior_for(origin) or {}).get("E1") or []
        e1_score_ind = pct_mid(e1_served_x, prior) if (e1_served_x is not None and len(prior) >= 8) else None
        if e1_score_ind is not None and e1["score"] is not None and abs(e1_score_ind - float(e1["score"])) > 1e-9:
            issues.append({"target": q, "province": code, "issue": "E1 score differs", "independent": e1_score_ind, "served": e1["score"]})
        groups = {g: sum(push.get(k, 0.0) for k in ks) for g, ks in T.FIVE_GROUPS.items()}
        pcts = dict(zip(groups, integer_shares([abs(v) for v in groups.values()])))
        roles = {d["key"]: d["push"] for d in D.breakdown(f) if d["push"] is not None}
        recon = sum(push.values()) - (f["firi"] - 0.5)
        five_rank = sorted(groups, key=lambda g: -abs(groups[g]))
        role_rank = sorted(roles, key=lambda r: -abs(roles[r]))
        rows.append({"target": q, "origin": origin, "province_code": code, "province": SLUG[code], "firi": f["firi"],
                     "class": f["class"], "kind": "forecast" if q == rec["targetQuarter"] else "history",
                     "E1_x": e1_served_x, "E1_x_independent": e1x, **{f"lfs_{k}": v for k, v in e1meta.items()},
                     "E1_score": e1["score"], "E1_score_independent": e1_score_ind, "E1_prior_n": len(prior),
                     "E1_status": e1["status"], "E2_status": ind["E2"]["status"], "E_indicators_observed": len(per_dom.get("E", [])),
                     "w_E": w.get("E"), "w": w, "E1_push": push.get("E1"), "group_push": groups, "pct_five": pcts,
                     "role_push": roles, "five_rank": five_rank, "role_rank": role_rank,
                     "indicator_push": push, "indicator_status": {k: v["status"] for k, v in ind.items()},
                     "indicator_score": {k: v["score"] for k, v in ind.items()},
                     "indicator_x": {k: (None if v.get("x") is None else float(v["x"])) for k, v in ind.items()},
                     "employment_top_of_five": five_rank[0] == "employment",
                     "employment_top_overall": role_rank[0] == "ACCESS" and abs(push.get("E1", 0)) == max(abs(v) for v in push.values()),
                     "E1_largest_single_indicator": max(push, key=lambda k: abs(push[k])) == "E1",
                     "largest_single_indicator": max(push, key=lambda k: abs(push[k])), "reconstruction_error": recon})
    # API comparison for the served target and three back-test quarters
    api = []
    for q in (rec["targetQuarter"], "2026-Q3", "2025-Q2", "2024-Q2"):
        for code, slug in SLUG.items():
            r = c.get("/api/v1/explainability", params={"scope": "province", "id": slug, "quarter": q})
            if r.status_code != 200:
                continue
            tr = {t["key"]: t for t in r.json()["triggers"]}
            mine = next((x for x in rows if x["target"] == q and x["province_code"] == code), None)
            if mine is None:
                continue
            for g in T.FIVE_GROUPS:
                ok_pct = tr[g]["pct"] == mine["pct_five"][g]
                ok_sign = math.isclose(tr[g]["signedContribution"], round(mine["group_push"][g], 6), abs_tol=2e-6)
                api.append({"target": q, "province": slug, "group": g, "api_pct": tr[g]["pct"], "recomputed_pct": mine["pct_five"][g],
                            "api_signed": tr[g]["signedContribution"], "recomputed_signed": mine["group_push"][g],
                            "match": ok_pct and ok_sign, "api_direction": tr[g]["direction"]})
                if not (ok_pct and ok_sign):
                    issues.append({"target": q, "province": slug, "issue": f"API {g} differs", "api": tr[g], "recomputed": mine["group_push"][g]})
    # summaries
    by_q = defaultdict(list)
    for r in rows:
        by_q[r["target"]].append(r)
    national = {q: len({round(x["E1_x"], 9) for x in v if x["E1_x"] is not None}) for q, v in by_q.items()}
    summ = {"rows": len(rows), "quarters": len(by_q), "max_reconstruction_error": max(abs(r["reconstruction_error"]) for r in rows),
            "api_checks": len(api), "api_mismatches": sum(not a["match"] for a in api), "issues": issues,
            "E1_distinct_values_per_quarter": national,
            "E1_identical_across_provinces_every_quarter": all(v <= 1 for v in national.values()),
            "E1_missing_rows": sum(r["E1_score"] is None for r in rows),
            "E1_negative_push_rows": sum((r["E1_push"] or 0) < 0 for r in rows),
            "E2_missing_rows": sum(r["E2_status"] != "observed" for r in rows),
            "employment_top_of_five_rows": sum(r["employment_top_of_five"] for r in rows),
            "E1_largest_single_indicator_rows": sum(r["E1_largest_single_indicator"] for r in rows),
            "largest_single_indicator_counts": dict(Counter(r["largest_single_indicator"] for r in rows)),
            "top_of_five_counts": dict(Counter(r["five_rank"][0] for r in rows)),
            "top_role_counts": dict(Counter(r["role_rank"][0] for r in rows))}
    fc = [r for r in rows if r["kind"] == "forecast"]
    summ["forecast_2027Q1"] = [{"province": r["province"], "firi": round(r["firi"], 4), "E1_x": r["E1_x"], "E1_score": r["E1_score"],
                                "w_E": r["w_E"], "E_indicators_observed": r["E_indicators_observed"], "E1_push": r["E1_push"],
                                "pct_five": r["pct_five"], "five_rank": r["five_rank"], "role_push": r["role_push"],
                                "role_rank": r["role_rank"], "largest_single_indicator": r["largest_single_indicator"]} for r in fc]
    (E74 / "out").mkdir(parents=True, exist_ok=True)
    (E74 / "out" / "trace_rows.json").write_text(json.dumps(rows, indent=1, default=str))
    (E74 / "out" / "api_comparison.json").write_text(json.dumps(api, indent=1, default=str))
    (E74 / "out" / "trace_summary.json").write_text(json.dumps(summ, indent=1, default=str))
    print(json.dumps({k: v for k, v in summ.items() if k not in ("forecast_2027Q1", "E1_distinct_values_per_quarter")}, indent=1, default=str))
    for r in summ["forecast_2027Q1"]:
        print(r["province"], r["firi"], "E1", r["E1_x"], r["E1_score"], "wE", round(r["w_E"], 3), "nE", r["E_indicators_observed"],
              "pushE1", round(r["E1_push"], 4), r["pct_five"], "roles", {k: round(v, 3) for k, v in r["role_push"].items()},
              "largest", r["largest_single_indicator"])


if __name__ == "__main__":
    main()
