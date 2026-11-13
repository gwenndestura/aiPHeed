"""Full-system audit trace (2026-11-14): frozen FINAL model -> issue files -> ledger -> APIs -> map values.
Run from backend/:  python ../research_notes/audit_20261114/trace_end_to_end.py [api_base]
Writes trace_results.json next to this script. Every check recomputes the value from the layer below; nothing is copied."""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

import pandas as pd

OUT = Path(__file__).with_name("trace_results.json")
API = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8975/api/v1"
R: list[dict] = []


def check(layer, name, ok, detail):
    R.append({"layer": layer, "check": name, "pass": bool(ok), "detail": detail})
    print(("PASS " if ok else "FAIL ") + f"[{layer}] {name}: {detail}")


def get(path):
    with urllib.request.urlopen(API + path, timeout=60) as r:
        return json.loads(r.read())


from app.final import frozen as FZ
from app.final import history as HI
from app.final import issue as IS
from app.final import period as PD
from app.final import serving as FS
from app.services import reference as ref

issue_dir = FS.served_issue_dir()
check("serving", "served issue exists", issue_dir is not None, str(issue_dir))
rows = pd.read_csv(issue_dir / "dashboard_rows.csv")
man = json.loads((issue_dir / "manifest.json").read_text(encoding="utf-8"))
quarters = sorted(rows.quarter.unique())

# ---- 1. model artifact -> issue: re-predict with the frozen model and compare with the stored issue
models = FZ.load(IS.MODEL)
check("model", "frozen artifact sha = manifest model_sha256", IS.sha256(IS.MODEL) == man["model_sha256"], IS.sha256(IS.MODEL)[:16])
fits = sorted((m.seed, m.lead) for m in models)
want_fits = sorted((s, L) for s in PD.serving()["seeds"] for L in range(1, PD.max_lead() + 1))
check("model", "one fit per seed x served lead", fits == want_fits, f"{len(models)} fits")
try:
    again = pd.DataFrame(IS.assemble(man["issue_quarter"], IS.predict_issue(man["issue_quarter"], models), man["generated_utc"])["rows"])
    m = rows.merge(again, on=["province", "quarter"], suffixes=("", "_re"))
    d_share = float((m["score_pct"] - m["score_pct_re"]).abs().max())
    d_p = float((m["probability"] - m["probability_re"]).abs().max())
    check("model", "re-prediction reproduces the stored shares and P(HIGH)", len(m) == len(rows) and d_share < 0.05 and d_p < 5e-4,
          f"{len(m)} rows, max |d share| {d_share:.4f} pts, max |d P(HIGH)| {d_p:.6f}")
except IS.RetrainingRequired as ex:
    check("model", "re-prediction reproduces the stored shares and P(HIGH)", False, f"RetrainingRequired: {ex}")

# ---- 2. issue internal rules
check("issue", "only served leads", set(rows["lead"]) <= set(range(1, PD.max_lead() + 1)), sorted(set(int(x) for x in rows["lead"])))
names = sorted(v["name"] for v in ref.PROVINCES.values())
check("issue", "exactly the five CALABARZON provinces per quarter", all(sorted(g.province) == names for _, g in rows.groupby("quarter")), names)
check("issue", "targets = issue quarter + 1..max_lead", quarters == [t["quarter"] for t in PD.targets(man["issue_quarter"])], quarters)
check("issue", "class = HIGH iff share >= 50%", all((r["class"] == "HIGH") == (r["score_pct"] >= 50) for r in rows.to_dict("records")),
      "all rows")
check("issue", "cut-off = issue rule date (1st of 2nd month, PHT)", man["information_cutoff"] == PD.issue_datetime(man["issue_quarter"]).date().isoformat(),
      man["information_cutoff"])

# ---- 3. ledger
v = HI.verify(); ok, msg = v["ok"], v
check("history", "ledger hash chain intact", ok, msg)
led = [r for r in HI.read() if r.get("issue_quarter") == man["issue_quarter"] and "share_pct" in r]
lk = {(r["province"], r["target_quarter"]): r for r in led}
mism = [(r["province"], r["quarter"]) for r in rows.to_dict("records")
        if abs(lk.get((r["province"], r["quarter"]), {}).get("share_pct", -1) - r["score_pct"]) > 1e-9]
check("history", "ledger records = issue rows", not mism and len(lk) == len(rows), f"{len(lk)} ledger rows; mismatches {mism}")

# ---- 4. APIs (each against the issue file, not against another API)
out = get("/final/food-insecurity/outlook")
ok = all(abs(p["score_pct"] - rows[(rows.province == p["province"]) & (rows.quarter == p["target_quarter"])]["score_pct"].iloc[0]) < 1e-9
         for p in out["provinces"])
check("api", "/final/food-insecurity/outlook = issue rows", ok and len(out["provinces"]) == len(rows), f"{len(out['provinces'])} rows")
hist = get("/final/forecast-history")
check("api", "/final/forecast-history contains the served issue", man["issue_quarter"] in json.dumps(hist), list(hist)[:6])
for q in quarters:
    pv = get(f"/provinces?quarter={q}")
    data = pv.get("data", pv.get("provinces", []))
    bad, badcls = [], []
    for p in data:
        r = rows[(rows.province == p["name"]) & (rows.quarter == q)].iloc[0]
        if abs(p["riskScore"] - r["score_pct"] / 100) > 6e-4:
            bad.append((p["name"], p["riskScore"], r["score_pct"]))
        lvl = str(p.get("riskLevel") or "").lower()
        if lvl and lvl != r["class"].lower():
            badcls.append((p["name"], lvl, r["class"]))
    check("api", f"/provinces {q}: riskScore = issue share (map colour source)", not bad and len(data) == 5, f"{len(data)} provinces; bad {bad}")
    check("api", f"/provinces {q}: riskLevel = issue class", not badcls, f"bad {badcls}")
    reg = get(f"/forecast?scope=region&id=calabarzon&quarter={q}&horizon=nowcast")
    mean = rows[rows.quarter == q]["score_pct"].mean() / 100
    check("api", f"/forecast region {q} = mean of the five shares", abs(reg["riskScore"] - mean) < 6e-4, f"api {reg['riskScore']} vs {mean:.4f}")
    ts = get(f"/forecast/timeseries?scope=province&id=quezon&from={q}&to={q}&horizon=nowcast")
    pts = ts.get("data", ts.get("points", ts.get("series", [])))
    v = [x for x in pts if x.get("quarter") == q]
    want = rows[(rows.province == "Quezon") & (rows.quarter == q)]["score_pct"].iloc[0] / 100
    check("api", f"/forecast/timeseries Quezon {q} = issue share", bool(v) and abs(v[0]["riskScore"] - want) < 6e-4, f"{v[:1]} vs {want}")
per = get("/forecast-period")
check("api", "/forecast-period names the served issue", man["issue_quarter"] in json.dumps(per), {k: per.get(k) for k in list(per)[:6]})

# ---- 5. towns and cities
mun = get(f"/provinces/quezon/municipalities?quarter={quarters[0]}")["data"]
ranks = sorted(m.get("rankInProvince") or 0 for m in mun)
check("lgu", "Quezon towns ranked from 1", ranks[0] == 1 and ranks[-1] <= len(mun), f"{len(mun)} towns, ranks {ranks[0]}..{ranks[-1]}")
bad = [(a["name"], b["name"]) for a in mun for b in mun                       # 4-dp display ties may sit in either order
       if a["riskIndex"] > b["riskIndex"] and (a["rankInProvince"] or 0) > (b["rankInProvince"] or 0)]
check("lgu", "a higher priority never ranks below a lower one", not bad, bad[:3])
for q in quarters:
    allm = [m for s in ref.PROVINCES for m in get(f"/provinces/{s}/municipalities?quarter={q}")["data"]]
    check("lgu", f"{q}: 142 cities and municipalities, 5 provinces", len(allm) == 142 and len({m["provinceId"] for m in allm}) == 5, len(allm))
    M = pd.DataFrame(allm)
    share = {r.province.lower(): r.score_pct / 100 for r in rows[rows.quarter == q].itertuples()}
    check("lgu", f"{q}: provinceEstimate = own province's issue share", all(abs(m["provinceEstimate"] - share[m["provinceId"]]) < 6e-4 for m in allm),
          "every town carries its own province's value")
    pv = M["povertyValueUsed"].rank(pct=True, method="average")             # recomputed from the DISPLAYED inputs
    dn = M["densityPerKm2"].rank(pct=True, method="average")
    vul = 0.6 * pv + 0.4 * dn
    d_vul = float((vul - M["vulnerabilityIndex"]).abs().max())
    d_idx = float((M["provinceEstimate"] * M["vulnerabilityIndex"] - M["riskIndex"]).abs().max())
    check("lgu", f"{q}: vulnerability = 0.6 poverty pct + 0.4 density pct (recomputed over 142)", d_vul < 0.02, f"max |d| {d_vul:.4f}")
    check("lgu", f"{q}: priority = province share x vulnerability", d_idx < 6e-5, f"max |d| {d_idx:.6f}")
    check("lgu", f"{q}: town colour class = province class", all(m["riskLevel"] == ("high" if share[m["provinceId"]] >= 0.5 else "low") for m in allm), "all")

json.dump(R, OUT.open("w", encoding="utf-8"), indent=1, default=str)
print(f"\n{sum(r['pass'] for r in R)} / {len(R)} checks passed -> {OUT}")
