"""E62 r6: does every number and sentence the dashboard receives match the served record? (in-process FastAPI client,
AIPHEED_LEAD2_MODEL=e58, the real clock of the run day)

Checks (each recorded as pass/fail with the observed values):
  C1  /quarters: the current target quarter equals the record's target (dynamic, not hard-coded).
  C2  /provinces: the five P(HIGH) equal the record's forecast probabilities.
  C3  /forecast region: the regional score equals a documented aggregation of the five provinces.
  C4  /forecast/timeseries province and region: every point equals the record's back-test / earlier / issued value.
  C5  /provinces/{id}/municipalities: 142 LGUs in total, unique codes, ranks consistent, every LGU labelled as relative
      prioritization (no municipal probability), riskIndex finite.
  C6  /explainability province: trigger signed contributions equal the record's grouped TreeSHAP; the summary
      components equal the record's two parts; the sentence quotes the record's probabilities, observations and
      directions (unemployment direction checked against the record's sign and the observed change).
  C7  /news: every item has a source, URL and date; excerpt (lead) is non-empty or explicitly absent; items dated after
      the forecast issue date are counted (context vs evidence).
  C8  The cached record is not mutated by serving: deep hash before and after two full passes.
  C9  Data-sufficiency label agrees with the record's input coverage.

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E62_Final_System_Audit/runner/r6_api_consistency.py
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path

os.environ["AIPHEED_LEAD2_MODEL"] = os.environ.get("AIPHEED_LEAD2_MODEL", "e58")
sys.dont_write_bytecode = True
E62 = Path(__file__).resolve().parents[1]
BACKEND = E62.parents[2] / "backend"
os.chdir(BACKEND)
sys.path.insert(0, str(BACKEND))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.ml.inference import e41_lead2 as L2  # noqa: E402

SLUGS = {"PH040100000": "cavite", "PH040200000": "laguna", "PH040300000": "quezon", "PH040400000": "rizal",
         "PH040500000": "batangas"}
results: list[dict] = []
timings: list[dict] = []


def check(cid, ok, **obs):
    results.append({"check": cid, "pass": bool(ok), **obs})
    print(("PASS " if ok else "FAIL ") + cid, json.dumps(obs, default=str)[:300])


def get(c, path, **params):
    t0 = time.perf_counter()
    r = c.get(path, params=params)
    timings.append({"path": path, "params": params, "ms": round((time.perf_counter() - t0) * 1000, 1),
                    "status": r.status_code, "bytes": len(r.content)})
    assert r.status_code == 200, (path, params, r.status_code, r.text[:300])
    return r.json()


def deep_hash(o) -> str:
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()


def full_pass(c, rec):
    tq = rec["targetQuarter"]
    out = {"quarters": get(c, "/api/v1/quarters", horizon="nowcast"), "provinces": get(c, "/api/v1/provinces", quarter=tq),
           "region": get(c, "/api/v1/forecast", scope="region", id="calabarzon", quarter=tq),
           "region_ts": get(c, "/api/v1/forecast/timeseries", scope="region", id="calabarzon"),
           "region_expl": get(c, "/api/v1/explainability", scope="region", id="calabarzon", quarter=tq),
           "region_news": get(c, "/api/v1/news", scope="region", id="calabarzon", quarter=tq, page=1, pageSize=20)}
    for code, slug in SLUGS.items():
        out[f"{slug}_ts"] = get(c, "/api/v1/forecast/timeseries", scope="province", id=slug)
        out[f"{slug}_expl"] = get(c, "/api/v1/explainability", scope="province", id=slug, quarter=tq)
        out[f"{slug}_muni"] = get(c, f"/api/v1/provinces/{slug}/municipalities", quarter=tq)
        out[f"{slug}_news"] = get(c, "/api/v1/news", scope="province", id=slug, quarter=tq, page=1, pageSize=20)
        out[f"{slug}_fc"] = get(c, "/api/v1/forecast", scope="province", id=slug, quarter=tq)
    return out


def main():
    rec = L2.record()
    snap = deep_hash(rec)
    tq = rec["targetQuarter"]
    with TestClient(app) as c:
        A = full_pass(c, rec)
        B = full_pass(c, rec)
    check("C8 record not mutated by serving", deep_hash(L2.record()) == snap and deep_hash(rec) == snap)
    check("C8b two passes identical", deep_hash(A) == deep_hash(B))
    q = A["quarters"]
    cur = q.get("current") or q.get("currentQuarter") or next((x.get("quarter") for x in q.get("data", []) if x.get("isCurrent")), None)
    check("C1 current target quarter dynamic", cur == tq, current=cur, record_target=tq)
    provs = {p["provinceCode"]: p for p in A["provinces"]["data"]}
    d2 = {code: abs(provs[code]["riskScore"] - v["forecast"]["probability"]) for code, v in rec["provinces"].items()}
    check("C2 province scores equal record", max(d2.values()) < 5e-4, max_abs_diff=max(d2.values()))
    ps = [v["forecast"]["probability"] for v in rec["provinces"].values()]
    reg = A["region"]["riskScore"]
    agg = {"mean": sum(ps) / 5, "max": max(ps), "median": sorted(ps)[2]}
    match = [k for k, v in agg.items() if abs(v - reg) < 5e-4]
    check("C3 region score is a documented aggregation", bool(match), region=reg, candidates=agg, matches=match)
    # C4 timeseries
    bad = []
    for code, v in rec["provinces"].items():
        want = {x["targetQuarter"]: x["probability"] for x in v["pastForecasts"]}
        want.update({x["targetQuarter"]: x["probability"] for x in v["earlierForecasts"]})
        want[tq] = v["forecast"]["probability"]
        got = {p["quarter"]: p["riskScore"] for p in A[f"{SLUGS[code]}_ts"]["series"]}
        for qq, w in want.items():
            if qq not in got or abs(got[qq] - w) > 5e-3:
                bad.append({"province": v["name"], "quarter": qq, "record": w, "served": got.get(qq)})
        extra = sorted(set(got) - set(want))
        if extra:
            bad.append({"province": v["name"], "points_not_in_record": extra,
                        "values": {e: got[e] for e in extra}})
    check("C4 province timeseries equal record", not bad, mismatches=bad[:12])
    rs = {p["quarter"]: p["riskScore"] for p in A["region_ts"]["series"]}
    reg_bad = []
    for qq in rs:
        vals = []
        for v in rec["provinces"].values():
            allv = {x["targetQuarter"]: x["probability"] for x in v["pastForecasts"] + v["earlierForecasts"]}
            allv[tq] = v["forecast"]["probability"]
            if qq in allv:
                vals.append(allv[qq])
        if len(vals) == 5 and abs(sum(vals) / 5 - rs[qq]) > 5e-3:
            reg_bad.append({"quarter": qq, "served": rs[qq], "mean_of_record": sum(vals) / 5})
        if len(vals) != 5:
            reg_bad.append({"quarter": qq, "served": rs[qq], "record_values": len(vals)})
    check("C4b region timeseries = mean of five provinces' record values", not reg_bad, mismatches=reg_bad[:12],
          quarters=sorted(rs))
    # C5 municipalities
    lgus = [m for s in SLUGS.values() for m in A[f"{s}_muni"]["data"]]
    codes = [m["lguCode"] for m in lgus]
    labels = {m["disaggregationLabel"] for m in lgus}
    finite = all(m["riskIndex"] is not None and math.isfinite(m["riskIndex"]) for m in lgus)
    ranks_ok = sorted(m["rankRegion"] for m in lgus) == list(range(1, len(lgus) + 1))
    inprov_ok = all(sorted(m["rankInProvince"] for m in A[f"{s}_muni"]["data"]) ==
                    list(range(1, len(A[f"{s}_muni"]["data"]) + 1)) for s in SLUGS.values())
    order_ok = all(
        [m["rankInProvince"] for m in sorted(A[f"{s}_muni"]["data"], key=lambda m: -m["riskIndex"])] ==
        sorted(m["rankInProvince"] for m in A[f"{s}_muni"]["data"]) for s in SLUGS.values())
    check("C5 LGU outputs", len(lgus) == 142 and len(set(codes)) == 142 and finite and ranks_ok and inprov_ok and order_ok,
          n=len(lgus), unique=len(set(codes)), finite=finite, region_ranks=ranks_ok, province_ranks=inprov_ok,
          rank_follows_index=order_ok, labels=sorted(labels)[:3], risk_levels=sorted({m["riskLevel"] for m in lgus}),
          indicator=A["laguna_muni"]["indicator"].get("name"))
    # C6 explainability vs record
    exp_bad = []
    for code, v in rec["provinces"].items():
        ex = A[f"{SLUGS[code]}_expl"]
        rd = {d["driver_group"]: d["group_shap"] for d in v["drivers"]["drivers"]}
        for t in ex["triggers"]:
            if abs(t["signedContribution"] - rd.get(t["key"], 0.0)) > 1e-6:
                exp_bad.append({"province": v["name"], "group": t["key"], "served": t["signedContribution"],
                                "record": rd.get(t["key"])})
        s = ex.get("summary") or {}
        comp = s.get("components") or {}
        rc = v["forecast"]["components"]
        if abs(comp.get("probabilityHungerElevated", -1) - rc["probabilityHungerElevated"]) > 1e-6 or \
           abs(comp.get("probabilityPricePressure", -1) - rc["probabilityPricePressure"]) > 1e-6:
            exp_bad.append({"province": v["name"], "components_served": comp, "record": rc})
        sent = s.get("sentence", "")
        pct = f"{round(v['forecast']['probability'] * 100)}%"
        if pct not in sent:
            exp_bad.append({"province": v["name"], "missing_score_in_sentence": pct})
        emp = v["fiveTriggerContributions"]["employment"]["logOddsEffect"]
        ur = v["observed"]["employment"]["unemploymentChangeYoY"]
        if emp < 0 and ur > 0 and "statistical pattern" not in sent:
            exp_bad.append({"province": v["name"], "unemployment_note_missing": True})
        if emp < 0 and "Employment raised it" in sent:
            exp_bad.append({"province": v["name"], "employment_direction_wrong": True})
        if "tested probability" in sent and "not a tested probability" not in sent:
            exp_bad.append({"province": v["name"], "score_called_probability": True})
        fy = v["observed"]["foodInflationLatestMonths"]["value"]
        if f"{fy}%" not in sent:
            exp_bad.append({"province": v["name"], "food_yoy_not_quoted": fy})
    check("C6 explanations equal record", not exp_bad, mismatches=exp_bad[:10])
    # C7 news
    issue = rec["origin"]
    news_stats = {}
    for key in ["region_news"] + [f"{s}_news" for s in SLUGS.values()]:
        items = A[key]["data"]
        news_stats[key] = {"items": len(items), "total": A[key]["total"],
                           "no_source": sum(1 for a in items if not a.get("source")),
                           "no_url": sum(1 for a in items if not a.get("url")),
                           "no_date": sum(1 for a in items if not a.get("date")),
                           "empty_excerpt": sum(1 for a in items if not (a.get("excerpt") or "").strip()),
                           "excerpt_equals_title": sum(1 for a in items if (a.get("excerpt") or "").strip() == a["title"].strip()),
                           "dated_on_or_after_issue": sum(1 for a in items if (a.get("date") or "") >= issue),
                           "quarters": sorted({a.get("quarter") for a in items if a.get("quarter")}),
                           "evidenceQuarter": A[key].get("evidenceQuarter"), "evidenceMode": A[key].get("evidenceMode"),
                           "evidenceNote": (A[key].get("evidenceNote") or "")[:240]}
    ok7 = all(s["no_source"] == 0 and s["no_url"] == 0 and s["no_date"] == 0 for s in news_stats.values())
    check("C7 news items have source/url/date", ok7, stats={k: {kk: v[kk] for kk in ("items", "empty_excerpt",
          "excerpt_equals_title", "dated_on_or_after_issue")} for k, v in news_stats.items()})
    # C9 data sufficiency
    suff = {}
    for code, v in rec["provinces"].items():
        s = (A[f"{SLUGS[code]}_expl"].get("summary") or {})
        partial = [g for g, b in v["triggerStatus"].items() if b.get("inputsPresent", 1) < 1]
        suff[v["name"]] = {"dataStatus": s.get("dataStatus"), "partial_groups_record": partial}
    ok9 = all((x["dataStatus"] == "limited") == bool(x["partial_groups_record"]) for x in suff.values())
    check("C9 sufficiency label matches record coverage", ok9, detail=suff)
    out = {"mode": L2.mode(), "record_target": tq, "record_origin": issue, "checks": results, "news": news_stats,
           "timings_in_process_ms": timings}
    (E62 / "out" / f"r6_api_consistency_{L2.mode()}.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    sample = {k: A[k] for k in ("region", "laguna_expl", "laguna_news")}
    (E62 / "out" / f"r6_sample_responses_{L2.mode()}.json").write_text(json.dumps(sample, indent=1, default=str), encoding="utf-8")
    print("failed:", [r["check"] for r in results if not r["pass"]])


if __name__ == "__main__":
    main()
