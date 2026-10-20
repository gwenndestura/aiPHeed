"""FIRI v1 walk-forward evaluation (FIRI_PROTOCOL.md section 6 + amendment 1). FIRI has no fitted parameters; its
model component A1 is the sealed walk-forward LightGBM price part (E63 leads 1-3; E68 seal for the forward origins).

Writes out/firi_*.csv, backend/data/thesis/firi_history.csv (served for back-test and earlier quarters) and
backend/data/thesis/firi_evaluation.json (served by the thesis mode).

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/FINAL_Thesis_System/runner/firi_evaluate.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import final_evaluation as FE  # noqa: E402   (metrics, paired_rule, the E66 scorer, E56 data)
import firi_anchors as FA  # noqa: E402

H, F, L, np, pd = FE.H, FE.F, FE.L, FE.np, FE.pd
E = FE.G.E
from scipy.stats import binomtest  # noqa: E402

BACKEND = FE.H.BACKEND
sys.path.insert(0, str(BACKEND))
from app.ml.inference import climate_watch as CW  # noqa: E402
from app.ml.inference import firi as FI  # noqa: E402
from app.ml.inference import thesis_system as TS  # noqa: E402
from app.news import pipeline_v3 as P3  # noqa: E402

EXP = FE.EXP
OUT = HERE.parent / "out"
E68_SEAL = EXP / "E68_Resolve_E67_Critical_Failures" / "sealed" / "prospective.csv"
HIST = BACKEND / "data" / "thesis" / "firi_history.csv"
EVAL = BACKEND / "data" / "thesis" / "firi_evaluation.json"


def check():
    FA.verify_protocol()
    a = json.loads(FI.ANCHORS.read_text())
    body = {k: v for k, v in a.items() if k != "content_sha256"}
    assert hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest() == a["content_sha256"], "anchors changed"
    assert a["amendment1Sha256"] == FA.want_amendment()
    return a


def firi_row(X, t, code, p_price, lead, anc, v_strict=False, drop_h=False):
    issue = str(L.origin(t).date())
    row = X[(X["t"] == t) & (X["province_code"] == code)]
    feat = row.iloc[0].to_dict() if len(row) else {}
    rh = TS.regional_hunger(t, lead)
    raw = FI.raw_indicators(code, feat, p_price, issue, L.qs(t), CW.hazard(issue)[0],
                            rh.get("probabilityAbove11_3"), P3.fssi_v3(code, t), v_strict=v_strict)
    if drop_h:
        raw["H1"] = {"x": None, "status": "excluded", "note": "sensitivity"}
    return FI.score(raw, anc), rh, issue


def evaluate_rows(R, col, ycol="y"):
    g = R.dropna(subset=[col])
    return FE.metrics(g[ycol], g[col]), g


def main():
    anc = check()
    d, X, B = E.load()
    Y = F.t43_labels(L.load())[["province_code", "quarter", "T43", "PS"]].rename(columns={"quarter": "target"})
    S63 = pd.read_csv(FE.E63 / "sealed" / "predictions.csv", dtype={"province_code": str})
    S57 = pd.read_csv(FE.E57, dtype={"province_code": str})
    rows = []
    for r in S63.itertuples():
        t = int(r.t)
        res, rh, issue = firi_row(X, t, r.province_code, float(r.E56_p_price), int(r.lead), anc)
        strict, _, _ = firi_row(X, t, r.province_code, float(r.E56_p_price), int(r.lead), anc, v_strict=True)
        noh, _, _ = firi_row(X, t, r.province_code, float(r.E56_p_price), int(r.lead), anc, drop_h=True)
        rows.append({"lead": int(r.lead), "t": t, "origin_quarter": L.qs(t), "issue_date": issue, "target": r.target,
                     "province_code": r.province_code, "province": r.province, "E56_p": r.E56_p, "E56_p_price": r.E56_p_price,
                     "PERSIST_p": r.PERSIST_p, "CLIM_p": r.CLIM_p, "MAJORITY_p": r.MAJORITY_p,
                     "FIRI": res["firi"], "FIRI_domains": res["domainsAvailable"],
                     **{f"dom_{k}": v for k, v in res["domains"].items()},
                     "FIRI_strictV": strict["firi"], "FIRI_noH": noh["firi"], "H1": rh.get("probabilityAbove11_3")})
    R = pd.DataFrame(rows).merge(Y, on=["province_code", "target"], how="left")
    assert R["T43"].notna().all()
    R["y"] = R["T43"].astype(int)
    # lead-2 P_price equals the sealed E57 price part (the E56 walk-forward)
    chk = R[R["lead"] == 2].merge(S57[["t", "province_code", "E56_p_price"]], on=["t", "province_code"], suffixes=("", "_57"))
    assert len(chk) == 50 and (chk["E56_p_price"] - chk["E56_p_price_57"]).abs().max() < 1e-9
    leads = []
    for lead, g in R.groupby("lead"):
        g = g.copy()
        m, _ = evaluate_rows(g, "FIRI")
        rp, rc = FE.paired_rule(g, "PERSIST_p", "FIRI"), FE.paired_rule(g, "CLIM_p", "FIRI")
        sv, gs = evaluate_rows(g, "FIRI_strictV")
        nh, _ = evaluate_rows(g, "FIRI_noH")
        leads.append({"lead": int(lead), "rows": int(len(g)), "quarters": int(g["target"].nunique()),
                      "FIRI": m, "FIRI_class_rate_HIGH": float((g["FIRI"] >= FI.THRESHOLD).mean()),
                      "LightGBM": FE.metrics(g["y"], g["E56_p"]), "persistence": FE.metrics(g["y"], g["PERSIST_p"]),
                      "majority": FE.metrics(g["y"], g["MAJORITY_p"]),
                      "vs_persistence": {k: rp[k] for k in ("mean_brier_diff", "ci95_lo", "ci95_hi", "quarter_wins", "quarter_losses", "sign_p_two_sided", "holds")},
                      "vs_climatology": {k: rc[k] for k in ("mean_brier_diff", "ci95_lo", "ci95_hi", "quarter_wins", "quarter_losses", "sign_p_two_sided", "holds")},
                      "reliable": bool(rp["holds"] and rc["holds"]),
                      "sensitivity_strictV": {"rows_computable": int(len(gs)), **{k: sv[k] for k in ("accuracy", "auc_roc", "brier")}},
                      "sensitivity_noH": {k: nh[k] for k in ("accuracy", "auc_roc", "brier", "recall_HIGH")}})
    # Objective 4: FIRI beside the LightGBM and the four baselines on the identical 45 rows
    Bs = pd.read_csv(FE.E55B, dtype={"province_code": str})
    l2 = R[R["lead"] == 2][["target", "province_code", "FIRI", "E56_p"]]
    O = Bs.merge(l2, on=["target", "province_code"], how="inner")
    assert len(O) == 45 and O["FIRI"].notna().all()
    O["y"] = O["y"].astype(int)
    O["MAJ_p"] = 0.0
    cols = {"I. Naive persistence": "B1_PERSIST_p", "II. PSA-only indicator (LR)": "B2_LR_GOV_p",
            "III. NLP-only sentiment (LR)": "B4_LR_NLP_p", "IV. Logistic regression (combined)": "B6_LR_COMB_p",
            "Majority class (always LOW)": "MAJ_p", "LightGBM E56-TUNED": "E56_p"}
    obj4 = {"FIRI": FE.metrics(O["y"], O["FIRI"]), "comparisons": {}}
    for name, c in cols.items():
        pr = H.paired(O.assign(HIGH=O["y"]), c, "FIRI", "HIGH", seed=69)
        a, b = (O["FIRI"] >= .5).astype(int) == O["y"], (O[c] >= .5).astype(int) == O["y"]
        w, l_ = int((a & ~b).sum()), int((~a & b).sum())
        obj4["comparisons"][name] = {"baseline": FE.metrics(O["y"], O[c]),
                                     "brier_diff_firi_minus_baseline": pr["mean_brier_diff"], "ci95": [pr["ci95_lo"], pr["ci95_hi"]],
                                     "quarter_wins_firi": pr["quarter_wins"], "quarter_losses_firi": pr["quarter_losses"],
                                     "quarter_sign_p": pr["sign_p"], "firi_better_by_rule": bool(pr["ci95_hi"] < 0 and pr["sign_p"] < 0.05),
                                     "mcnemar_firi_right_only": w, "mcnemar_baseline_right_only": l_,
                                     "mcnemar_p": float(binomtest(w, w + l_, 0.5).pvalue) if w + l_ else 1.0}
    # regional outcome: regional mean FIRI vs observed SWS hunger > 11.3% at t+2 (E69 origins, lead 2)
    reg = []
    p_price_l2 = {(int(r.t), r.province_code): float(r.E56_p_price) for r in S57.itertuples()}
    for t in range(L.qi("2021-Q4"), L.qi("2026-Q1") + 1):
        vals = [firi_row(X, t, p, p_price_l2.get((t, p)), 2, anc)[0]["firi"] for p in FI.PROVINCES]
        vals = [v for v in vals if v is not None]
        nh = [firi_row(X, t, p, p_price_l2.get((t, p)), 2, anc, drop_h=True)[0]["firi"] for p in FI.PROVINCES]
        nh = [v for v in nh if v is not None]
        reg.append({"origin_quarter": L.qs(t), "target": L.qs(t + 2), "FIRI_region": float(np.mean(vals)) if vals else None,
                    "FIRI_region_noH": float(np.mean(nh)) if nh else None, "provinces_computable": len(vals)})
    RG = pd.DataFrame(reg)
    allr = pd.read_csv(L.SWS_FILE)
    hq = allr.groupby("quarter")["H"].mean()
    RG["H_observed"] = RG["target"].map(hq)
    RG = RG.dropna(subset=["H_observed", "FIRI_region"])
    RG["E1"] = (RG["H_observed"] > 11.3).astype(int)
    RG["pred"] = (RG["FIRI_region"] >= FI.THRESHOLD).astype(int)
    regional = {"quarters": int(len(RG)), "accuracy": float((RG["pred"] == RG["E1"]).mean()),
                "always_elevated_accuracy": float(RG["E1"].mean()),
                "auc": H.auc(RG["E1"].to_numpy(), RG["FIRI_region"].to_numpy()),
                "note": "regional outcome shares its source with the H1 component (SWS)",
                "sensitivity_noH": _noh(RG)}
    # history table served by the thesis mode (lead 2, targets 2024-Q2..2026-Q3) + forward origins (E68 seal, A0)
    hist = []
    for r in R[R["lead"] == 2].itertuples():
        res, rh, issue = firi_row(X, int(r.t), r.province_code, float(r.E56_p_price), 2, anc)
        hist.append({"target": r.target, "origin_quarter": r.origin_quarter, "issue_date": issue, "province_code": r.province_code,
                     "kind": "backtest", "observed_T43": int(r.y), **_flat(res)})
    S68 = pd.read_csv(E68_SEAL, dtype={"province_code": str})
    for r in S68[S68["arm"] == "A0"].itertuples():
        t = L.qi(r.origin_quarter)
        res, rh, issue = firi_row(X, t, r.province_code, float(r.p_price), 2, anc)
        hist.append({"target": r.target, "origin_quarter": r.origin_quarter, "issue_date": issue, "province_code": r.province_code,
                     "kind": "forecast", "observed_T43": None, **_flat(res)})
    HT = pd.DataFrame(hist)
    H.write_csv(HT, HIST)
    H.write_csv(R, OUT / "firi_rows_all_leads.csv")
    H.write_csv(RG, OUT / "firi_regional_outcome.csv")
    body = {"schema": "aipheed.firi.evaluation/1", "protocolSha256": FA.verify_protocol(), "amendment1Sha256": FA.want_amendment(),
            "anchorsSha256": anc["content_sha256"],
            "domainsUsed": sorted({k for k in FI.DOMAINS if not (k == "N" and not anc["indicators"]["N1"]["usable"])}),
            "newsDomain": ("excluded by the frozen rule: FSSI-v3 has only "
                           f"{anc['indicators']['N1']['n_window_values']} SUFFICIENT province-quarters in the anchor window"),
            "leads": leads, "objective4": obj4, "regionalOutcome": regional,
            "evidenceStatus": ("development evidence on rows examined during development; the labels (T43) share price sources "
                               "with A1/A2 and the regional outcome shares SWS with H1, so no result validates FIRI as a "
                               "measure of food insecurity")}
    EVAL.write_bytes(json.dumps(body, indent=1, default=float).encode("utf-8"))
    pd.set_option("display.width", 250)
    for x in leads:
        m = x["FIRI"]
        print(x["lead"], x["rows"], "FIRI acc %.3f prec %s rec %.3f f1 %.3f auc %s brier %.3f HIGHrate %.2f" % (
            m["accuracy"], m["precision_HIGH"], m["recall_HIGH"] or 0, m["f1_HIGH"] or 0, m["auc_roc"], m["brier"],
            x["FIRI_class_rate_HIGH"]), m["confusion"], "reliable", x["reliable"], x["vs_persistence"], x["vs_climatology"],
              "strictV", x["sensitivity_strictV"], "noH", x["sensitivity_noH"])
    for k, v in obj4["comparisons"].items():
        print(k, round(v["brier_diff_firi_minus_baseline"], 3), [round(c, 3) for c in v["ci95"]], v["quarter_wins_firi"], v["quarter_losses_firi"], v["firi_better_by_rule"], v["mcnemar_firi_right_only"], v["mcnemar_baseline_right_only"])
    print("regional", regional)
    print(HT.groupby("target")[["FIRI"]].mean().round(3).T.to_string())


def _noh(RG):
    g = RG.dropna(subset=["FIRI_region_noH"])
    return {"quarters": int(len(g)), "accuracy": float(((g["FIRI_region_noH"] >= FI.THRESHOLD).astype(int) == g["E1"]).mean()),
            "auc": H.auc(g["E1"].to_numpy(), g["FIRI_region_noH"].to_numpy()), "always_elevated": float(g["E1"].mean())}


def _flat(res):
    ind = res["indicators"]
    return {"FIRI": res["firi"], "class": res["class"], "domainsAvailable": res["domainsAvailable"],
            **{f"dom_{k}": v for k, v in res["domains"].items()},
            "indicators_json": json.dumps({k: {"x": v["x"], "score": v["score"], "status": v["status"]} for k, v in ind.items()})}


if __name__ == "__main__":
    main()
