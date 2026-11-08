"""
scripts/build_record_fpp.py
---------------------------
The label-v2 record: Food Price Pressure (exploratory), from the frozen E39 outputs. Served only when
LABEL_VERSION=v2 (app/api/v1/fpp.py); v1 stays the default.

    python -B scripts/build_record_fpp.py        (run from backend/)

Writes data/fpp/fpp_record.json and data/fpp/aiPHeed_Food_Price_Pressure_exploratory.pdf (Subject = record hash).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
E39 = ROOT.parent / "aipheed-backend-aligned" / "experiments" / "E39_Label_V2"
OUT = ROOT / "data" / "fpp"
NAME = "Food Price Pressure (exploratory)"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def build() -> dict:
    freeze = json.loads((E39 / "frozen" / "E39_FREEZE.json").read_text())
    for f, h in freeze["sha256"].items():
        assert _sha(E39 / f) == h, f"{f} changed after freezing"
    spec = json.loads((E39 / "label_v2_spec.json").read_text())
    run = sorted((E39 / "runs").glob("eval_*"))[0]
    res = json.loads((run / "results.json").read_text())["results"]
    fc_path = E39 / "frozen" / "E39_FORECASTS_2026Q4_2027Q1.json"
    fc = json.loads(fc_path.read_text())
    diag = json.loads((E39 / "runs" / "diagnostics.json").read_text())
    lab = pd.read_csv(E39 / "label_v2.csv", dtype={"province_code": str})
    summary = {}
    for key, r in res.items():
        if key.startswith("A_vs_B"):
            continue
        s = {"verdict": r.get("verdict"), "scored_dates": r.get("n_dates"), "dates": r.get("dates"),
             "withheld": r.get("withheld"), "missing_round": r.get("missing_round"),
             "skill_vs_primary": {ref: {k: r["comparisons"][ref].get(k) for k in ("skill", "skill_ci95", "p_holm")}
                                  for ref in ("persistence", "climatology") if ref in r.get("comparisons", {})}}
        if key.startswith("A"):
            s.update(brier=r["brier"], HIGH_dates=r["HIGH_dates"], pooled_model=r["pooled"]["model"],
                     calibration=r["calibration"])
        else:
            s.update(MAE=r["MAE"], MASE=r["MASE"], interval=r["interval"], ranking=r.get("ranking"))
        summary[key] = s
    rec = {
        "schema": "fpp/1", "name": NAME, "label_version": "v2",
        "note": spec["framing"],
        "status": "EXPERIMENTAL; tool-adopted default rule (food CPI YoY > 4%, BSP target ceiling); not "
                  "adviser-endorsed; not validated; measures food price pressure, not food insecurity",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "specs_sha256": freeze["sha256"], "evaluation_run": run.name, "forecasts_sha256": _sha(fc_path),
        "label": json.loads(lab.to_json(orient="records")),
        "forecasts": fc["forecasts"], "forecast_origin": fc["origin"],
        "evaluation": summary,
        "diagnostics": {k: diag[k] for k in ("D1_prevalence", "D2_dates", "D3_mixed", "D5_sensitivity_information_only")},
        "limitations": [
            "Food price pressure is not food insecurity: high food inflation does not prove hunger and low food "
            "inflation does not prove adequate food.",
            "The 4% rule is the BSP headline-inflation target ceiling applied to provincial food inflation; it is a "
            "tool-adopted default, not adviser-endorsed and not validated.",
            "Skill is not demonstrated for any target at either lead; persistence is the stronger forecast for food "
            "inflation and regional hunger.",
            "Probabilities are shrunk toward the climatological rate (fewer than 8 prior forecast dates exist for "
            "Platt calibration), and no 80% interval could be issued (fewer than 8 prior residual dates).",
            "About 5-9 independent dates per target and lead; the five provinces share the regional hunger value.",
        ],
    }
    rec["content_sha256"] = hashlib.sha256(json.dumps(rec, sort_keys=True, default=str).encode()).hexdigest()
    return rec


def write_pdf(rec: dict, path: Path):
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Table

    st = getSampleStyleSheet()
    P = lambda t, s="Normal": Paragraph(str(t).replace("&", "&amp;").replace("<", "&lt;"), st[s])  # noqa: E731
    f3 = lambda x: "-" if x is None else f"{x:.3f}"  # noqa: E731
    els = [P(rec["name"], "Title"), P(rec["note"]), P("Status: " + rec["status"]),
           P(f"Record SHA-256 {rec['content_sha256']}; forecasts issued at origin {rec['forecast_origin']}."),
           P("Forecasts (no outcome yet)", "Heading2")]
    rows = [["Target", "Quarter", "Lead"] + [v["province"] for v in next(iter(rec["forecasts"].values()))["provinces"].values()]]
    for key, f in rec["forecasts"].items():
        rows.append([key.split("_")[0], f["target_quarter"], f["lead"]] +
                    [f3(v["pred"]) for v in f["provinces"].values()])
    els += [Table(rows), P("A = calibrated P(food inflation > 4%); B = predicted food inflation (%); C = predicted "
                           "regional hunger (%)."), P("Evaluation (one run, date-level scoring)", "Heading2")]
    ev = [["Target, lead", "Scored dates", "Verdict", "Skill vs persistence", "Skill vs climatology"]]
    for key, s in rec["evaluation"].items():
        sk = s["skill_vs_primary"]
        ev.append([key, s["scored_dates"], s["verdict"], f3(sk.get("persistence", {}).get("skill")),
                   f3(sk.get("climatology", {}).get("skill"))])
    els += [Table(ev), P("Limitations", "Heading2")] + [P("- " + t) for t in rec["limitations"]]
    SimpleDocTemplate(str(path), pagesize=landscape(A4), title=rec["name"], subject=rec["content_sha256"],
                      invariant=1, pageCompression=0).build(els)


def main():
    rec = build()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "fpp_record.json").write_bytes(json.dumps(rec, indent=1, default=str).encode())
    write_pdf(rec, OUT / "aiPHeed_Food_Price_Pressure_exploratory.pdf")
    print(rec["content_sha256"])


if __name__ == "__main__":
    main()
