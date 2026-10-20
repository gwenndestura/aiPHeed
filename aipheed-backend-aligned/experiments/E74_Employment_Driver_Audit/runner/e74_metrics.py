"""E74: reproduce the headline Lead-1/2/3 metrics from the committed artifacts, independently of each experiment's
scorer, and compare with the recorded figures. Four result families are kept apart:
  (1) food-price-pressure prediction: E56 (E70 R0) on T43, labels rebuilt here from E71 out/labels.csv (PSA CPI YoY) and
      the SWS rounds file with the E40 thresholds;
  (2) regional hunger outcome (SWS): FIRI v2 regional class (E72 input rows);
  (3) the dimensional proxy FIR71 (E71 sealed predictions vs E71 labels);
  (4) the independent outcome (OCTA, E73 rows).
Run from the repository root: python -B aipheed-backend-aligned/experiments/E74_Employment_Driver_Audit/runner/e74_metrics.py
"""
import csv
import json
import math
from pathlib import Path

EXP = Path(__file__).resolve().parents[2]
ROOT = EXP.parents[1]
E74 = EXP / "E74_Employment_Driver_Audit"


def cm(y, p, thr=0.5):
    tp = sum(1 for a, b in zip(y, p) if a == 1 and b >= thr)
    fp = sum(1 for a, b in zip(y, p) if a == 0 and b >= thr)
    fn = sum(1 for a, b in zip(y, p) if a == 1 and b < thr)
    tn = sum(1 for a, b in zip(y, p) if a == 0 and b < thr)
    n = tp + fp + fn + tn
    rec_h = tp / (tp + fn) if tp + fn else None
    rec_l = tn / (tn + fp) if tn + fp else None
    z = 1.959964
    acc = (tp + tn) / n
    d = 1 + z * z / n
    c = (acc + z * z / (2 * n)) / d
    h = z * math.sqrt(acc * (1 - acc) / n + z * z / (4 * n * n)) / d
    return {"n": n, "TP": tp, "FP": fp, "FN": fn, "TN": tn, "accuracy": acc, "wilson95": [c - h, c + h],
            "precision_HIGH": tp / (tp + fp) if tp + fp else None, "recall_HIGH": rec_h,
            "balanced_accuracy": None if rec_h is None or rec_l is None else (rec_h + rec_l) / 2,
            "brier": sum((b - a) ** 2 for a, b in zip(y, p)) / n}


def qi(q):
    return int(q[:4]) * 4 + int(q[-1]) - 1


def main():
    out, checks = {}, []
    spec = json.loads((EXP / "E40_SWS_CPI_Tiers" / "label_spec.json").read_text())["thresholds"]
    lab = {(r["province_code"], r["quarter"]): r for r in csv.DictReader((EXP / "E71_Food_Insecurity_Dimensions" / "out" / "labels.csv").open(encoding="utf-8"))}
    sws = {}
    for r in csv.DictReader((ROOT / "backend" / "data" / "inputs" / "sws_rounds.csv").open(encoding="utf-8")):
        sws.setdefault(r["quarter"], []).append(float(r["H"]))
    H = {q: sum(v) / len(v) for q, v in sws.items()}
    # (1) price-pressure label T43 for the E70 R0 rows
    P = list(csv.DictReader((EXP / "E70_Objectives_Completion" / "sealed" / "predictions.csv").open(encoding="utf-8")))
    s70 = json.loads((EXP / "E70_Objectives_Completion" / "out" / "score.json").read_text(encoding="utf-8"))
    for lead in ("1", "2", "3"):
        y, p = [], []
        for r in P:
            if r["lead"] != lead:
                continue
            L = lab[(r["province_code"], r["target"])]
            f, g = float(L["a1"]), float(L["gap"])
            ps = int(f > spec["food"][r["province_code"]] or g > spec["gap"][r["province_code"]])
            y.append(int(H[r["target"]] > spec["H"] and ps))
            p.append(float(r["R0_p"]))
        m = cm(y, p)
        out[f"T43_price_pressure_lead{lead}"] = m
        rec = s70["leads"][lead]["metrics"]["R0"]
        checks.append({"what": f"E56 on T43, lead {lead}", "reproduced": (m["TP"], m["FP"], m["FN"], m["TN"]),
                       "recorded": (rec["TP"], rec["FP"], rec["FN"], rec["TN"]),
                       "match": (m["TP"], m["FP"], m["FN"], m["TN"]) == (rec["TP"], rec["FP"], rec["FN"], rec["TN"])
                                and abs(m["brier"] - rec["brier"]) < 1e-9})
    # (2) regional SWS outcome, FIRI v2
    R = list(csv.DictReader((EXP / "E72_Final_Thesis_System" / "inputs" / "firi2_regional.csv").open(encoding="utf-8")))
    s72 = json.loads((EXP / "E72_Final_Thesis_System" / "out" / "regional_outcome.json").read_text())
    for lead in ("1", "2", "3"):
        g = [r for r in R if r["lead"] == lead and r["C3"] and r["y"]]
        m = cm([int(float(r["y"])) for r in g], [float(r["C3"]) for r in g])
        out[f"SWS_regional_FIRI_lead{lead}"] = m
        rec = s72[lead]["metrics"]["C3"]
        checks.append({"what": f"FIRI v2 vs SWS, lead {lead}", "reproduced": (m["TP"], m["FP"], m["FN"], m["TN"]),
                       "recorded": (rec["TP"], rec["FP"], rec["FN"], rec["TN"]),
                       "match": (m["TP"], m["FP"], m["FN"], m["TN"]) == (rec["TP"], rec["FP"], rec["FN"], rec["TN"])})
    # (3) FIR71 dimensional proxy
    s71 = json.loads((EXP / "E71_Food_Insecurity_Dimensions" / "out" / "score.json").read_text(encoding="utf-8"))
    P71 = list(csv.DictReader((EXP / "E71_Food_Insecurity_Dimensions" / "sealed" / "predictions.csv").open(encoding="utf-8")))
    for lead in ("1", "2", "3"):
        for arm in ("DIMFUSE", "LGBM"):
            y = [int(float(lab[(r["province_code"], r["target"])]["HIGH"])) for r in P71 if r["lead"] == lead]
            p = [float(r[f"{arm}_p"]) for r in P71 if r["lead"] == lead]
            m = cm(y, p)
            out[f"FIR71_{arm}_lead{lead}"] = m
            rec = s71["leads"][lead]["metrics"][arm]
            checks.append({"what": f"FIR71 {arm}, lead {lead}", "reproduced": (m["TP"], m["FP"], m["FN"], m["TN"]),
                           "recorded": (rec["TP"], rec["FP"], rec["FN"], rec["TN"]),
                           "match": (m["TP"], m["FP"], m["FN"], m["TN"]) == (rec["TP"], rec["FP"], rec["FN"], rec["TN"])})
    # (4) independent OCTA outcome
    o = json.loads((EXP / "E73_Objective_Remediation" / "out" / "octa_validation.json").read_text())
    rows = o["rows"]
    m = cm([r["y"] for r in rows], [r["FIRI_p"] for r in rows])
    out["OCTA_independent_FIRI_lead2"] = m
    rec = o["classification"]["FIRI"]
    checks.append({"what": "FIRI v2 vs OCTA, lead 2", "reproduced": (m["TP"], m["FP"], m["FN"], m["TN"]),
                   "recorded": (rec["TP"], rec["FP"], rec["FN"], rec["TN"]),
                   "match": (m["TP"], m["FP"], m["FN"], m["TN"]) == (rec["TP"], rec["FP"], rec["FN"], rec["TN"])})
    # sensitivity: OCTA values known only as a later article's "from X percent" (2024-Q2, 2026-Q1) removed; same threshold
    direct = [r for r in rows if r["target"] not in ("2024-Q2", "2026-Q1")]
    out["OCTA_independent_FIRI_lead2_direct_reports_only"] = cm([r["y"] for r in direct], [r["FIRI_p"] for r in direct])
    prov = list(csv.DictReader((EXP / "E73_Objective_Remediation" / "inputs" / "provenance.csv").open(encoding="utf-8")))
    octa_cutoff_ok = all(r["published"] <= "2026-10-14" for r in prov)
    res_prov = {"rounds_logged": len(prov), "all_published_by_2026_10_14": octa_cutoff_ok,
                "source_type": "press reports quoting OCTA (primary OCTA release pages not accessible: bot-check)",
                "secondary_from_later_article": [r["fieldwork"] for r in prov if "previous round" in r["fieldwork"]]}
    res = {"metrics": out, "checks": checks, "all_match": all(c["match"] for c in checks), "octa_provenance": res_prov,
           "goal80": {"price_label_lead2": out["T43_price_pressure_lead2"]["accuracy"],
                      "independent_outcome_lead2": out["OCTA_independent_FIRI_lead2"]["accuracy"],
                      "demonstrated": False}}
    (E74 / "out").mkdir(exist_ok=True)
    (E74 / "out" / "metrics_reproduction.json").write_text(json.dumps(res, indent=1))
    for c in checks:
        print(("OK   " if c["match"] else "DIFF ") + c["what"], c["reproduced"], c["recorded"])
    for k, v in out.items():
        print(f"{k:34s} n={v['n']:3d} acc={v['accuracy']:.3f} [{v['wilson95'][0]:.3f},{v['wilson95'][1]:.3f}] "
              f"TP/FP/FN/TN={v['TP']}/{v['FP']}/{v['FN']}/{v['TN']} recH={v['recall_HIGH']} bal={v['balanced_accuracy']} brier={v['brier']:.3f}")
    print("all match:", res["all_match"])


if __name__ == "__main__":
    main()
