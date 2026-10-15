"""Regenerate the results workbook for label v2, Food Price Pressure (exploratory), in the layout of
aiPHeed_Results_All_Quarters_2026-10-15.xlsx, from the frozen E39 outputs (not from a live API). Replaces the
unrecorded "Correct?" export: every value comes from the evaluation run, the issued forecasts and the ledger.

    <backend venv python> -B runner/e39_export_workbook.py runs/eval_<stamp>
    -> docs/aiPHeed_Results_All_Quarters_v2_FoodPricePressure_2026-10-15.xlsx

No third-party spreadsheet library is available, so a minimal standard-library xlsx writer is used.
"""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

import pandas as pd

E39 = Path(__file__).resolve().parents[1]
ROOT = E39.parents[2]
sys.path.insert(0, str(ROOT / "backend"))
NAMES = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal",
         "PH040500000": "Batangas"}
ORDER = ["PH040100000", "PH040200000", "PH040500000", "PH040400000", "PH040300000"]


# ------------------------------------------------------------------------------------------- tiny xlsx writer
def _col(i: int) -> str:
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def _cell(ref: str, v) -> str:
    if v is None or (isinstance(v, float) and v != v):
        return ""
    if isinstance(v, bool):
        return f'<c r="{ref}" t="inlineStr"><is><t>{"Yes" if v else "No"}</t></is></c>'
    if isinstance(v, (int, float)):
        return f'<c r="{ref}"><v>{v}</v></c>'
    return f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">{escape(str(v))}</t></is></c>'


def write_xlsx(path: Path, sheets: list[tuple[str, list[list]]]):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml",
                   '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="xml" ContentType="application/xml"/>'
                   '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                   + "".join(f'<Override PartName="/xl/worksheets/sheet{i + 1}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                             for i in range(len(sheets))) + "</Types>")
        z.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr("xl/workbook.xml", '<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                   'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
                   + "".join(f'<sheet name="{escape(n[:31])}" sheetId="{i + 1}" r:id="rId{i + 1}"/>' for i, (n, _) in enumerate(sheets))
                   + "</sheets></workbook>")
        z.writestr("xl/_rels/workbook.xml.rels", '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   + "".join(f'<Relationship Id="rId{i + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i + 1}.xml"/>'
                             for i in range(len(sheets))) + "</Relationships>")
        for i, (_, rows) in enumerate(sheets):
            body = "".join(f'<row r="{r + 1}">' + "".join(_cell(f"{_col(c)}{r + 1}", v) for c, v in enumerate(row)) + "</row>"
                           for r, row in enumerate(rows))
            z.writestr(f"xl/worksheets/sheet{i + 1}.xml", '<?xml version="1.0" encoding="UTF-8"?><worksheet '
                       'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>' + body + "</sheetData></worksheet>")


# ------------------------------------------------------------------------------------------- content
def r4(x):
    return None if x is None or (isinstance(x, float) and x != x) else round(float(x), 4)


def main(run_dir: str):
    run = Path(run_dir)
    spec = json.loads((E39 / "label_v2_spec.json").read_text())
    res = json.loads((run / "results.json").read_text())
    P = pd.read_csv(run / "predictions.csv", dtype={"province_code": str})
    fc = json.loads((E39 / "frozen" / "E39_FORECASTS_2026Q4_2027Q1.json").read_text())
    lab = pd.read_csv(E39 / "label_v2.csv", dtype={"province_code": str})
    # issued forecasts at the latest origin, in the same long shape as the evaluation predictions
    extra = []
    for key, f in fc["forecasts"].items():
        kind, k = key.split("_lead")
        for p, v in f["provinces"].items():
            extra.append({"target": kind, "lead": int(k), "target_quarter": f["target_quarter"], "province_code": p,
                          "arm": "model", "pred": v["pred"], "raw": v.get("raw"), "status": f["status"],
                          "lo": (v.get("interval") or [None, None])[0], "hi": (v.get("interval") or [None, None])[1],
                          "rank": v.get("rank"), "tied": v.get("tied")})
    M = pd.concat([P[P.arm == "model"], pd.DataFrame(extra)], ignore_index=True)
    M = M.drop_duplicates(["target", "lead", "target_quarter", "province_code"], keep="first")
    obsF = {(r.province_code, r.quarter): r.F for r in lab.itertuples()}
    obsH = lab.dropna(subset=["H"]).groupby("quarter")["H"].first().to_dict()
    obs_rank = {(r.province_code, r.quarter): r.F_rank_in_quarter for r in lab.itertuples()}
    note = spec["framing"]
    readme = [["aiPHeed results by province and city/municipality: Food Price Pressure (exploratory), label v2"],
              ["Built from the frozen E39 outputs (aipheed-backend-aligned/experiments/E39_Label_V2), not from a live API."],
              [""], ["What it measures"], [note], [""],
              ["Rule: HIGH when the province's food CPI year-on-year rate (PSA published, quarter mean) is above 4%. "
               "4% is the BSP inflation-target ceiling (a headline target, not food-specific). Tool-adopted default; not "
               "adviser-endorsed; not validated."],
              ["Targets: A = P(HIGH) from the LightGBM classifier, calibrated chronologically (shrinkage toward the "
               "climatological rate wherever fewer than 8 earlier forecast dates exist; no isotonic; display clipping is "
               "not calibration). B = predicted food inflation (%). C = predicted regional SWS hunger (%; one value for all "
               "five provinces)."],
              ["Scored? Yes = outcome released and scored; Withheld = fewer than 8 labelled training quarters at the origin; "
               "No outcome yet = forecast; Missing round = no approved SWS round for that quarter (C only)."],
              ["Evaluation verdicts (one run, date-level scoring): " + "; ".join(
                  f"{k}: {v['verdict']}" for k, v in res["results"].items() if not k.startswith("A_vs_B"))],
              ["80% intervals: none could be issued (fewer than 8 earlier residual dates at every origin)."],
              ["Ranks: provinces are ranked within a quarter by food inflation; ties share the average rank (flagged)."],
              ["City/municipality index = P(HIGH) of the province x within-province vulnerability (PSA 2021 poverty, POPCEN "
               "2024 density): a relative position, not a municipal forecast."],
              [""], ["Limits: food price pressure is not food insecurity. No skill beyond persistence and climatology was "
                     "demonstrated. Small samples (about 5-9 independent dates per target and lead)."]]
    quarters = sorted(M[(M.target == "A") & (M.lead == 1)]["target_quarter"].unique())
    a1 = M[(M.target == "A") & (M.lead == 1)].set_index(["province_code", "target_quarter"])["pred"]
    a2 = M[(M.target == "A") & (M.lead == 2)].set_index(["province_code", "target_quarter"])["pred"]
    pbq = [["Province", "Code"] + [f"{q} (lead 1)" for q in quarters] + ["2027-Q1 (lead 2, next quarter)"]]
    for p in ORDER:
        pbq.append([NAMES[p], p] + [r4(a1.get((p, q))) for q in quarters] + [r4(a2.get((p, "2027-Q1")))])
    detail = [["Quarter", "Lead", "Quarter type", "Province", "P(HIGH) calibrated", "P(HIGH) raw", "Predicted label (P >= 0.5)",
               "Observed label", "Label error", "Predicted food inflation % (F_hat)", "80% interval", "Observed food inflation %",
               "Abs error (pp)", "Predicted rank (of 5)", "Observed rank (of 5)", "Tied", "Predicted regional hunger %",
               "Observed regional hunger %", "Scored?"]]
    status_txt = {"Scored": "Yes", "Withheld": "Withheld", "No outcome yet": "No outcome yet", "Missing round": "Missing round"}
    for k in (1, 2):
        for q in sorted(M[M.lead == k]["target_quarter"].unique()):
            for p in ORDER:
                g = {t: M[(M.lead == k) & (M.target == t) & (M.target_quarter == q) & (M.province_code == p)]
                     for t in ("A", "B", "C")}
                a = g["A"].iloc[0] if len(g["A"]) else None
                b = g["B"].iloc[0] if len(g["B"]) else None
                c = g["C"].iloc[0] if len(g["C"]) else None
                pa = None if a is None or pd.isna(a["pred"]) else float(a["pred"])
                fo = obsF.get((p, q))
                ol = None if fo is None else ("HIGH" if fo > 4 else "NOT HIGH")
                pl = None if pa is None else ("HIGH" if pa >= 0.5 else "NOT HIGH")
                fb = None if b is None or pd.isna(b["pred"]) else float(b["pred"])
                iv = None if b is None or pd.isna(b.get("lo")) else f"{b['lo']:.2f} to {b['hi']:.2f}"
                detail.append([q, k, "Backtest" if fo is not None and q <= "2026-Q3" else "Forecast", NAMES[p], r4(pa),
                               r4(None if a is None else a.get("raw")), pl, ol,
                               None if pl is None or ol is None else int(pl != ol), r4(fb), iv or ("no interval" if fb is not None else None),
                               r4(fo), None if fb is None or fo is None else r4(abs(fb - fo)),
                               None if b is None or pd.isna(b.get("rank")) else float(b["rank"]),
                               r4(obs_rank.get((p, q))), None if b is None or pd.isna(b.get("tied")) else bool(b["tied"]),
                               None if c is None or pd.isna(c["pred"]) else r4(c["pred"]), r4(obsH.get(q)),
                               status_txt.get(a["status"] if a is not None else "Withheld", a["status"] if a is not None else None)])
    ovp = [["Province", "Row"] + quarters]
    for p in ORDER:
        ovp.append([NAMES[p], "Predicted (P >= 0.5)"] + [None if pd.isna(a1.get((p, q), float("nan"))) else
                                                         ("HIGH" if a1[(p, q)] >= .5 else "NOT HIGH") for q in quarters])
        ovp.append([NAMES[p], "Observed"] + [None if obsF.get((p, q)) is None else ("HIGH" if obsF[(p, q)] > 4 else "NOT HIGH")
                                            for q in quarters])
    # city / municipality index from the existing LGU method (vulnerability used only here)
    from app.quarterly.lgu_audit import build_ranking

    vul = pd.read_csv(ROOT / "backend" / "data" / "inputs" / "lgu_vulnerability.csv", dtype={"lgu_code": str})
    ros = pd.read_csv(ROOT / "backend" / "data" / "reference" / "calabarzon_lgus.csv", dtype={"lgu_psgc": str})
    cols = [(q, a1) for q in quarters] + [("2027-Q1", a2)]
    lgu_idx, lgu_rank, long = {}, {}, [["Quarter", "Lead", "Province", "City / Municipality", "Type", "PSGC code",
                                       "Risk index", "Rank in province", "Tied", "No province estimate"]]
    for q, src in cols:
        probs = {p: src.get((p, q)) for p in ORDER}
        if any(v is None or pd.isna(v) for v in probs.values()):
            continue
        rk = build_ranking(vul, ros, {p: float(v) for p, v in probs.items()}, {"source": f"E39 P(HIGH) {q}"})
        for r in rk["rows"]:
            lgu_idx[(r["lgu_code"], q)] = r["risk_index"]
            lgu_rank[(r["lgu_code"], q)] = r["rank_in_province"]
            long.append([q, 2 if q == "2027-Q1" else 1, r["province"], r["lgu_name"], r["lgu_type"], r["lgu_code"],
                         r["risk_index"], r["rank_in_province"], bool(r["tied"]), False])
    qcols = [q for q, _ in cols if any(k[1] == q for k in lgu_idx)]
    v2 = vul.sort_values(["province", "lgu_name"])
    lgu = [["Province", "City / Municipality", "Type", "PSGC code", "Population 2024", "Poverty rate (%)"] + qcols]
    lgr = [["Province", "City / Municipality"] + qcols]
    for r in v2.itertuples():
        lgu.append([r.province, r.lgu_name, r.lgu_type, r.lgu_code, int(r.population_2024),
                    r4(r.poverty_value_used)] + [lgu_idx.get((r.lgu_code, q)) for q in qcols])
        lgr.append([r.province, r.lgu_name] + [lgu_rank.get((r.lgu_code, q)) for q in qcols])
    # scores by date and baselines
    sbd = [["Target", "Lead", "Date", "Metric", "Model"] + ["persistence", "climatology", "seasonal_naive", "AR1",
                                                          "always_LOW", "always_HIGH", "B2_LR_COMB", "B3_LR_GOV",
                                                          "B4_LR_NLP", "B5_LGBM_GOV", "B6_LGBM_NLP"]]
    s = P[(P.status == "Scored") & P.pred.notna()].copy()
    for (kind, k, q), g in s.groupby(["target", "lead", "target_quarter"]):
        loss = lambda a: (((g[g.arm == a]["pred"] - g[g.arm == a]["y"]) ** 2) if kind == "A"  # noqa: E731
                          else (g[g.arm == a]["pred"] - g[g.arm == a]["y"]).abs()).mean()
        sbd.append([kind, int(k), q, "Brier" if kind == "A" else "MAE", r4(loss("model"))] +
                   [r4(loss(a)) if (g.arm == a).any() else None for a in sbd[0][5:]])
    bl = [["Target, lead", "Comparator", "Primary?", "Model loss", "Comparator loss", "Skill", "Skill 95% CI (date bootstrap)",
           "p (sign-flip, two-sided)", "p (Holm)", "Verdict"]]
    for key, r in res["results"].items():
        if key.startswith("A_vs_B") or "comparisons" not in r:
            continue
        losses = r.get("brier") or r.get("MAE")
        for ref, t in r["comparisons"].items():
            ci = t.get("skill_ci95")
            bl.append([key, ref, "Yes" if t["primary"] else "No", r4(losses.get("model")), r4(losses.get(ref)), r4(t["skill"]),
                       None if not ci else f"{ci[0]:.3f} to {ci[1]:.3f}", r4(t["p_two_sided"]), r4(t.get("p_holm")), r["verdict"]])
    out = E39 / "docs" / "aiPHeed_Results_All_Quarters_v2_FoodPricePressure_2026-10-15.xlsx"
    write_xlsx(out, [("Read me", readme), ("Provinces by quarter", pbq), ("Province detail", detail),
                     ("Observed vs predicted", ovp), ("Cities-Municipalities", lgu), ("City-Mun rank in province", lgr),
                     ("City-Mun detail", long), ("Scores by date", sbd), ("Baselines", bl)])
    print(out, len(detail) - 1, "province rows;", len(long) - 1, "LGU rows")


if __name__ == "__main__":
    main(sys.argv[1])
