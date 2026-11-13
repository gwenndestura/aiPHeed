r"""Integration checks of the served production API (E196) against its registered artifact. Read-only: GET requests only.
Usage: python api_checks.py http://127.0.0.1:8998  C:\Users\admin\aipheed_e196\backend
Writes evidence/api_checks.json; exit 1 if any check fails. Nothing is skipped silently: a check that cannot run is recorded as FAIL."""
import hashlib
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

BASE, BACKEND = sys.argv[1].rstrip("/") + "/api/v1", Path(sys.argv[2])
EV = Path(__file__).resolve().parents[1] / "evidence"
FIVE = {"cavite", "laguna", "batangas", "rizal", "quezon"}
res = []


def get(path):
    try:
        with urllib.request.urlopen(BASE + path, timeout=60) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode("utf-8"))
        except Exception:
            body = None
        return e.code, body


def check(name, ok, detail=""):
    res.append({"check": name, "pass": bool(ok), "detail": detail if isinstance(detail, str) else json.dumps(detail, default=str)[:900]})


def run(name, fn):
    try:
        ok, detail = fn()
        check(name, ok, detail)
    except Exception as ex:                       # a check that crashes is a failure, never a skip
        check(name, False, f"CHECK ERROR {type(ex).__name__}: {ex}")


reg = json.loads((BACKEND / "data" / "registry" / "registry.json").read_text(encoding="utf-8"))["production"]
art_path = BACKEND / reg["artifact_path"]
art = json.loads(art_path.read_text(encoding="utf-8"))
run("registry: production artifact file hash matches the registry", lambda: (hashlib.sha256(art_path.read_bytes()).hexdigest() == reg["artifact_file_sha256"], reg["model_id"] + " " + reg["artifact_file_sha256"][:12]))
run("health and readiness", lambda: (get("/health")[1].get("status") == "ok" and get("/readiness")[1].get("status") == "ready", ""))

sq, Q = get("/quarters")
run("quarters: current target is the quarter after the calendar quarter (one quarter ahead)",
    lambda: (sq == 200 and Q["forecastTarget"]["calendar_quarter"] == "2026-Q4" and Q["current"] == "2027-Q1" and Q["forecastTarget"]["available"] is True, {"current": Q.get("current"), "calendar": Q["forecastTarget"]["calendar_quarter"]}))
fq = [q["id"] for q in Q["quarters"] if q["state"] == "forecast"]
run("quarters: every forecast quarter is served by an artifact lead", lambda: (len(fq) >= 1 and set(fq) <= {r["target_quarter"] for r in art["provinces"]}, {"forecast_quarters": fq}))

A = {(r["province"].lower(), r["target_quarter"]): r for r in art["provinces"]}
worst, bad_cls, missing, levels = 0.0, [], [], set()
for q in fq:
    s, P = get(f"/provinces?quarter={q}")
    ids = {r["id"] for r in P.get("data", [])} if s == 200 else set()
    if ids != FIVE:
        missing.append({q: sorted(ids)})
        continue
    for r in P["data"]:
        a = A.get((r["id"], q))
        if a is None:
            missing.append({q: r["id"]})
            continue
        worst = max(worst, abs(float(r["riskScore"]) - float(a["p_high"])))
        levels.add(r["riskLevel"])
        if (r["riskLevel"] == "high") != (float(a["p_high"]) >= 0.5) or (r["riskLevel"] == "high") != (a["risk_class"].upper() == "HIGH"):
            bad_cls.append({q: r["id"]})
run("provinces: Cavite, Laguna, Batangas, Rizal, Quezon served for every forecast quarter", lambda: (not missing, missing))
run("provinces: API probability equals the artifact (to the API's 3 decimals)", lambda: (worst <= 0.0006, {"max_abs_diff": round(worst, 5)}))
run("provinces: risk class consistent with probability and the 0.50 cut-off", lambda: (not bad_cls and levels <= {"low", "high"}, {"mismatch": bad_cls, "levels": sorted(levels)}))

so, O = get("/final/food-insecurity/outlook")
run("outlook: approved production model is the one served", lambda: (so == 200 and O.get("status") == "approved" and O.get("model") == reg["model_id"] == art["model"], {"api": O.get("model"), "registry": reg["model_id"]}))
groups = sorted({d.get("group") for d in O.get("data_used", [])})
run("outlook: trigger groups listed in data_used", lambda: (len(groups) >= 5, {"groups": groups}))
run("outlook: news-derived inputs appear inside trigger groups", lambda: (any("news" in json.dumps(d).lower() for d in O.get("data_used", [])), {"n_data_used": len(O.get("data_used", []))}))
cut_api, cut_art = Q["forecastTarget"].get("origin"), O.get("origin_date")
run("consistency: one information cut-off stated across endpoints", lambda: (cut_api == cut_art, {"quarters.origin": cut_api, "outlook.origin_date": cut_art, "config_horizon": get("/config")[1]["indicator"]["horizon"][:40]}))
run("consistency: data completeness flagged per province in the artifact", lambda: (all("data_complete" in r and "inputs_filled" in r for r in art["provinces"]), {"incomplete": sorted({r["province"] for r in art["provinces"] if not r["data_complete"]})}))

C = get("/config")[1]
hz = C["indicator"].get("horizon", "")
run("consistency: indicator horizon states the served cut-off", lambda: (hz.startswith(f"issued {cut_art};"), {"horizon": hz[:120], "outlook": cut_art}))
mm = (C.get("servingModel") or {}).get("mapModel") or {}
run("identity: /config names the approved model on the map", lambda: (mm.get("model") == reg["model_id"] and mm.get("servedLeads") == sorted(art["served_leads"]), {"mapModel": mm, "registry": reg["model_id"]}))
run("identity: /final/risk/evaluation is the approved model's", lambda: (get("/final/risk/evaluation")[1].get("model") == reg["model_id"], {}))
FRONT = ["/config", "/quarters", "/provinces", "/explainability?scope=province&id=quezon", "/news?id=quezon", "/search?q=quezon",
         "/final/overview", "/final/risk/evaluation", "/final/risk/rows", "/final/food-insecurity/outlook", "/final/archive",
         "/final/evaluation", "/forecast", "/forecast/timeseries?id=quezon", "/fi9/outlook", "/fi10/provinces",
         "/fi9/provincial-measurements", "/provinces/quezon/municipalities", "/report/data?scope=province&id=quezon"]
st = {u: get(u)[0] for u in FRONT}
run("frontend integration: every public route the dashboard calls answers without a server error", lambda: (all(v < 500 for v in st.values()), st))

lgu_bad, lgu_n = [], 0
for p in sorted(FIVE):
    s, M = get(f"/provinces/{p}/municipalities")
    rows = M.get("data", []) if s == 200 else []
    lgu_n += len(rows)
    if s != 200 or not rows:
        lgu_bad.append({p: s})
        continue
    for r in rows:
        if r.get("riskLevel") not in (None, "") and r.get("scoreType") and "priority" not in str(r.get("scoreType")).lower():
            lgu_bad.append({p: {k: r.get(k) for k in ("id", "riskLevel", "scoreType")}})
            break
s1, M1 = get("/provinces/quezon/municipalities")
sample = {k: (M1["data"][0].get(k)) for k in list(M1["data"][0].keys())[:30]} if s1 == 200 and M1.get("data") else {}
run("LGU rows: served for all five provinces", lambda: (lgu_n > 100 and not any(isinstance(list(b.values())[0], int) for b in lgu_bad), {"rows": lgu_n}))
run("LGU rows: no city or municipal food-insecurity class is presented as a measurement", lambda: (not lgu_bad, {"violations": lgu_bad[:3], "sample_row": sample}))

s404, _ = get("/provinces/not-a-province/municipalities")
sbadq, Bq = get("/provinces?quarter=1999-Q1")
run("errors: unknown province returns 404", lambda: (s404 == 404, {"status": s404}))
run("errors: a quarter with no forecast is refused or returned empty, never invented", lambda: (sbadq in (400, 404, 422) or not (Bq or {}).get("data") or all(r.get("riskScore") is None for r in Bq["data"]), {"status": sbadq, "n": len((Bq or {}).get("data", []) or [])}))
sn, N = get("/news?id=quezon")
run("news: endpoint answers with dated stories", lambda: (sn == 200 and len(N.get("data", N if isinstance(N, list) else [])) > 0, {"status": sn, "keys": list(N.keys())[:8] if isinstance(N, dict) else "list"}))
sr, Rk = get("/ranking")
run("ranking: endpoint answers", lambda: (sr == 200, {"status": sr, "keys": list(Rk.keys())[:8] if isinstance(Rk, dict) else "list"}))

out = {"base": BASE, "model": reg["model_id"], "passed": sum(r["pass"] for r in res), "failed": sum(not r["pass"] for r in res), "checks": res}
(EV / "api_checks.json").write_text(json.dumps(out, indent=1))
for r in res:
    print(("PASS " if r["pass"] else "FAIL ") + r["check"] + ("" if r["pass"] else "  -> " + r["detail"]))
print(out["passed"], "passed,", out["failed"], "failed")
sys.exit(1 if out["failed"] else 0)
