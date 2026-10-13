"""E18 runner (E18_PROTOCOL.md, frozen; hash checked first).
Classification (implemented label) and continuous targets at h = 1..5 (h = 3 primary = 2027-Q1 horizon),
E17v3 frozen-candidate holdout on 2026-Q1/Q2, diagnostics, 2027-Q1 forecast, dashboard JSON.
Usage: python -B runner/run_e18.py [--deliverables]"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "21")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard  # noqa: E402

guard.install()
import hashlib  # noqa: E402
import io  # noqa: E402
import json  # noqa: E402
from datetime import datetime, timezone  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import e17v3_frozen_lib as V  # noqa: E402
import e18_lib as L  # noqa: E402

EXP = guard.EXP
HS = [1, 2, 3, 4, 5]
PRIMARY = 3
TARGET = "2027-Q1"
LAST_ELIG, LAST_AUTH = "2025-Q4", "2026-Q2"
qk, qs = V.qk, V.qs


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def jd(o):
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return None if np.isnan(o) else float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(type(o))


def check_frozen():
    for ln in (EXP / "runner" / "PROTOCOL_SHA256.txt").read_text(encoding="utf-8").splitlines():
        p = ln.split()
        if len(p) == 2 and len(p[0]) == 64 and sha(EXP / p[1]) != p[0]:
            raise SystemExit(f"E18: {p[1]} differs from its frozen hash; stop.")


def load(log):
    comp = pd.read_csv(io.StringIO(guard.read_allowed_text(guard.E12_RUN / "realized_components_2021_2025.csv")),
                       dtype={"province_code": str})
    det = json.loads(guard.read_allowed_text(guard.E12_RUN / "details.json"))
    rounds = pd.DataFrame(det["two_layer"]["regional_layer_rounds"])
    gov = json.loads(guard.read_allowed_text(guard.AL / "config" / "governing_model.json"))
    feats = gov["feature_set"]["candidates_section_3_3_2_6"] + ["cpi_dev"]
    ff = guard.read_allowed_parquet(guard.PROC / "features_fused.parquet", ["province_code", "quarter"] + feats)
    cpi26 = pd.read_csv(io.StringIO(guard.read_allowed_text(guard.COLL / "provincial_food_cpi_yoy_2026H1_raw.csv")),
                        dtype={"province_code": str})
    sws26 = guard.read_allowed_parquet(guard.PROD_SWS, ["quarter", "pct_total_hunger", "stratum"])
    checks = [("components", comp["quarter"], LAST_ELIG), ("rounds", rounds["quarter"], LAST_ELIG),
              ("features_fused", ff["quarter"], LAST_ELIG), ("sws_2026", sws26["quarter"], LAST_AUTH)]
    for name, col, mx in checks:
        bad = int((col.map(qk) > qk(mx)).sum())
        log.append({"assert": f"{name} <= {mx}", "rows": int(len(col)), "violations": bad})
        if bad:
            raise guard.AccessDenied(f"E18: {name} beyond {mx}")
    months = sorted(cpi26["reference_month"].unique())
    ok = months == [f"2026-0{m}" for m in range(1, 7)] and len(cpi26) == 30
    log.append({"assert": "CPI 2026 = 2026-01..2026-06, 30 rows", "ok": bool(ok), "months": months})
    if not ok:
        raise guard.AccessDenied("E18: CPI 2026 file outside the authorized Jan-Jun range")
    log.append({"assert": "SWS 2026 stratum is balance_luzon", "ok": bool((sws26["stratum"] == "balance_luzon").all())})
    gov_cols = [c for c in feats if c not in L.NLP and c != "poverty_incidence"]
    return comp, rounds, ff, cpi26, sws26, gov_cols


# =============================================================== classification
def run_classification(X, Lab, comp_x, gov_cols):
    rows, meta = [], {}
    for h in HS:
        for T in sorted(Lab["q"].unique()):
            r = L.fold(X, Lab, comp_x, T, h, gov_cols)
            if r is None:
                continue
            test, s, m = r
            meta[f"h{h}_{qs(T)}"] = m
            for arm, v in s.items():
                for i, pc in enumerate(test["province_code"]):
                    rows.append({"h": h, "target_quarter": qs(T), "province_code": pc, "arm": arm,
                                 "score": float(v[i]), "pred": int(v[i] >= 0.5)})
    return pd.DataFrame(rows), meta


def evaluate_classification(P, Lab):
    d = P.merge(Lab[["province_code", "quarter", "y"]].rename(columns={"quarter": "target_quarter"}),
                on=["province_code", "target_quarter"], how="left")
    d["correct"] = (d["pred"] == d["y"]).astype(int)
    out = {}
    for h, dh in d.groupby("h"):
        for setname in ("A", "B"):
            if setname == "A":
                ds = dh[dh["target_quarter"].map(qk) <= qk(LAST_ELIG)]
                arms_needed = L.ARMS
            else:
                ds = dh[dh["arm"].isin(L.NO_NEWS)]
                arms_needed = L.NO_NEWS
            qsets = [set(ds.loc[ds["arm"] == a, "target_quarter"]) for a in arms_needed]
            common = sorted(set.intersection(*qsets), key=qk) if all(qsets) else []
            ds = ds[ds["target_quarter"].isin(common)]
            if not common:
                continue
            res = {"quarters": common, "n_quarters": len(common), "arms": {}}
            perq = ds.groupby(["target_quarter", "arm"])["correct"].mean().unstack()
            for a, g in ds.groupby("arm"):
                hard = a in ("P_persistence", "MAJ_majority", "N1_structural_rule", "N2_structural_shrink")
                m = L.cls_metrics(g["y"], g["pred"], None if hard else g["score"])
                sd = g.groupby("target_quarter")["score"].std(ddof=0).mean()
                distinct = g.groupby("target_quarter")["pred"].nunique().mean()
                m.update({"mean_within_quarter_sd_score": float(sd), "mean_distinct_labels_per_quarter": float(distinct),
                          "share_pred_HIGH": float(g["pred"].mean()),
                          "agreement_with_persistence": None,
                          "per_quarter_accuracy": perq[a].to_dict()})
                res["arms"][a] = m
            pp = ds[ds["arm"] == "P_persistence"].set_index(["target_quarter", "province_code"])["pred"]
            for a in res["arms"]:
                ga = ds[ds["arm"] == a].set_index(["target_quarter", "province_code"])["pred"]
                res["arms"][a]["agreement_with_persistence"] = float((ga == pp.reindex(ga.index)).mean())
            if setname == "A":
                ok_n = len(common) >= 5
                sel = {}
                for c in L.NEW:
                    if c in res["arms"]:
                        sel[c] = L.select(perq, res["arms"], c) if ok_n else {"passes": False, "note": "insufficient (<5 quarters)"}
                winners = [c for c, x in sel.items() if x["passes"]]
                chosen = (max(winners, key=lambda c: (res["arms"][c]["balanced_accuracy"] or 0, res["arms"][c]["accuracy"]))
                          if winners else "P_persistence")
                yv = ds[ds["arm"] == "P_persistence"]["y"]
                supported = bool(winners) and len(common) >= 8 and int(yv.sum()) >= 5 and int((1 - yv).sum()) >= 5
                res["selection"] = {"checks": sel, "selected": chosen, "insufficient": not ok_n,
                                    "reliability_working_criterion_met": supported,
                                    "test_HIGH": int(yv.sum()), "test_LOW": int((1 - yv).sum())}
            out[f"h{h}|{setname}"] = res
    return d, out


# =============================================================== continuous
def continuous(hs_all, f5, U, comp_x):
    rows = []
    for h in HS:
        for T in hs_all.index:
            c, meta = V.h_candidates(hs_all, f5, U, T, h)
            if not c:
                continue
            c["C8_recent4_mean"] = L.c8_recent_mean(hs_all, T, h)
            c["C9_ewma"] = L.c9_ewma(hs_all, T, h)
            for k, v in c.items():
                rows.append({"target": "H", "h": h, "origin_target": qs(T), "unit": "REGION", "candidate": k, "forecast": v})
        for var in ("F", "D"):
            for T in range(qk("2021-Q2"), qk(LAST_AUTH) + 1):
                df, _ = V.fd_candidates(comp_x, var, T, h)
                for r in df.itertuples(index=False):
                    for k in [x for x in df.columns if x != "province_code"]:
                        v = getattr(r, k)
                        if v == v:
                            rows.append({"target": var, "h": h, "origin_target": qs(T), "unit": r.province_code,
                                         "candidate": k, "forecast": float(v)})
    return pd.DataFrame(rows)


def eval_continuous(preds, actual, exclude_2026=False):
    d = preds.merge(actual, on=["target", "origin_target", "unit"], how="left")
    d = d[d["y"].notna()].copy()
    if exclude_2026:
        d = d[d["origin_target"].map(qk) <= qk(LAST_ELIG)]
    d["ae"], d["e"] = (d["forecast"] - d["y"]).abs(), d["forecast"] - d["y"]
    sets = {"H": (["C1_carry_forward"], V.H_SELECTABLE + ["C8_recent4_mean", "C9_ewma"], V.H_DIAG),
            "F": (V.F_BASE, V.F_FIT, []), "D": (V.D_BASE, V.D_FIT, [])}
    out = {}
    for (tg, h), g in d.groupby(["target", "h"]):
        base, sel, diag = sets[tg]
        need = [c for c in base + sel]
        qsets = [set(g.loc[g["candidate"] == c, "origin_target"]) for c in need]
        common = sorted(set.intersection(*qsets), key=qk) if all(qsets) else []
        gg = g[g["origin_target"].isin(common)]
        po = gg.groupby(["candidate", "origin_target"])["ae"].mean().unstack(0)
        po.index = [qk(q) for q in po.index]
        po = po.sort_index()
        r = {"common_origins": common, "n_origins": len(common),
             "evidence": "exploratory only (<8 origins)" if len(common) < 8 else ">=8 origins", "candidates": {}}
        for c in [x for x in base + sel + diag if x in po.columns]:
            gc = gg[gg["candidate"] == c]
            r["candidates"][c] = {"MAE": float(gc["ae"].mean()), "RMSE": float(np.sqrt((gc["e"] ** 2).mean())),
                                  "bias": float(gc["e"].mean()),
                                  "per_origin": {qs(i): float(v) for i, v in po[c].items()}}
        if len(common):
            chk = {c: {b: V.rule_check(po[c], po[b]) for b in base} for c in sel if c in po.columns}
            win = [c for c, x in chk.items() if all(v["passes"] for v in x.values())]
            r["selection"] = {"qualifying": win,
                              "selected": min(win, key=lambda c: r["candidates"][c]["MAE"]) if win else base[0],
                              "checks": {c: {b: {k: v[k] for k in ("cond1", "cond2", "cond3", "cond4", "wins", "passes")}
                                             for b, v in x.items()} for c, x in chk.items()}}
        out[f"{tg}|h{h}"] = r
    return out


# =============================================================== main
def main(deliverables):
    check_frozen()
    started = datetime.now(timezone.utc)
    out = EXP / "runs" / started.strftime("%Y%m%dT%H%M%SZ")
    out.mkdir(parents=True)
    log = [{"check": "allowlist (start)", "result": guard.verify_allowlist()}]
    comp, rounds, ff, cpi26, sws26, gov_cols = load(log)
    comp_x = L.extend_components(comp, cpi26, sws26)
    log.append({"assert": "extended components quarters <= 2026-Q2",
                "violations": int((comp_x["quarter"].map(qk) > qk(LAST_AUTH)).sum())})
    hprod = L.h_series(rounds, sws26, production_only=True)
    hall = L.h_series(rounds, sws26, production_only=False)
    X = L.feature_frame(ff, comp_x, hprod, gov_cols)
    Lab = L.labels(comp_x)

    # ---------------- predictions (sealed before scoring)
    Pc, cmeta = run_classification(X, Lab, comp_x, gov_cols)
    f5 = comp_x.drop_duplicates("quarter").set_index("quarter")["mean5"]
    f5 = pd.Series(f5.values, index=[qk(q) for q in f5.index])
    U = ff.drop_duplicates("quarter").set_index("quarter")["unemployment_rate"]
    U = pd.Series(U.values, index=[qk(q) for q in U.index])
    Pn = continuous(hall, f5, U, comp_x)
    Pc.to_csv(out / "classification_predictions.csv", index=False, lineterminator="\n", float_format="%.8g")
    Pn.to_csv(out / "continuous_predictions.csv", index=False, lineterminator="\n", float_format="%.8g")
    seal = {f: sha(out / f) for f in ("classification_predictions.csv", "continuous_predictions.csv")}
    seal["sealed_utc"] = datetime.now(timezone.utc).isoformat()
    (out / "SEAL.json").write_text(json.dumps(seal, indent=1), encoding="utf-8", newline="\n")

    # ---------------- scoring
    dcls, rcls = evaluate_classification(Pc, Lab)
    act = [{"target": "H", "origin_target": qs(k), "unit": "REGION", "y": float(v)} for k, v in hall.items()]
    for var in ("F", "D"):
        act += [{"target": var, "origin_target": r.quarter, "unit": r.province_code, "y": float(getattr(r, var))}
                for r in comp_x.itertuples() if getattr(r, var) == getattr(r, var)]
    act = pd.DataFrame(act)
    rcon = eval_continuous(Pn, act)
    rcon_no26 = eval_continuous(Pn, act, exclude_2026=True)

    # ---------------- E17v3 frozen-candidate holdout (2026-Q1/Q2 at h=5)
    hold = []
    for T in (qk("2026-Q1"), qk("2026-Q2")):
        c, _ = V.h_candidates(hall, f5, U, T, 5)
        for k, v in c.items():
            hold.append({"target": "H", "quarter": qs(T), "unit": "REGION", "candidate": k, "forecast": v, "y": float(hall[T])})
        for var in ("F", "D"):
            df, _ = V.fd_candidates(comp_x, var, T, 5)
            y = comp_x[comp_x["quarter"] == qs(T)].set_index("province_code")[var]
            for r in df.itertuples(index=False):
                for k in [x for x in df.columns if x != "province_code"]:
                    hold.append({"target": var, "quarter": qs(T), "unit": r.province_code, "candidate": k,
                                 "forecast": float(getattr(r, k)), "y": float(y[r.province_code])})
    hold = pd.DataFrame(hold)
    hold["abs_err"] = (hold["forecast"] - hold["y"]).abs()
    hold_summary = hold.groupby(["target", "candidate"])["abs_err"].mean().unstack(0).round(4)

    # ---------------- 2027-Q1 forecast (h = 3; information <= 2026-Q2)
    T = qk(TARGET)
    fc = {"target_quarter": TARGET, "horizon": PRIMARY, "information_cutoff": LAST_AUTH}
    cH, _ = V.h_candidates(hall, f5, U, T, PRIMARY)
    cH["C8_recent4_mean"], cH["C9_ewma"] = L.c8_recent_mean(hall, T, PRIMARY), L.c9_ewma(hall, T, PRIMARY)
    selH = rcon[f"H|h{PRIMARY}"]["selection"]["selected"]
    fc["H"] = {"label": "Research forecast of regional hunger (SWS Balance Luzon, % of families); not a forecast of "
                        "provincial food insecurity.", "selected": selH, "forecast": cH.get(selH),
               "all_candidates": cH, "latest_observed": "2026-Q2"}
    for var, lab in (("F", "Research forecast of provincial food inflation (YoY %); not food insecurity."),
                     ("D", "Research forecast of relative provincial food-price pressure (points vs the unweighted "
                           "five-province mean); not food insecurity.")):
        df, art = V.fd_candidates(comp_x, var, T, PRIMARY)
        sel = rcon[f"{var}|h{PRIMARY}"]["selection"]["selected"]
        fc[var] = {"label": lab, "selected": sel, "forecast": df.set_index("province_code")[sel].to_dict(),
                   "all_candidates": df.set_index("province_code").to_dict("index")}
    selC = rcls.get(f"h{PRIMARY}|A", {}).get("selection", {}).get("selected", "P_persistence")
    Xf = X[X["c"] == qk(LAST_AUTH)].sort_values("province_code")
    pers = Lab[Lab["quarter"] == LAST_AUTH].set_index("province_code")["y"]
    s1rule = (Xf.set_index("province_code")["H_last"] + 2 * Xf.set_index("province_code")["D_c"])
    lab_out = {"label": "Research forecast of the constructed composite label (HIGH if regional hunger + 2 x relative "
                        "price pressure > 14.6); NOT a measurement or forecast of provincial food insecurity.",
               "selected_by_rule": selC,
               "news_models_available": False,
               "persistence_2026Q2_label": {p: ("HIGH" if v else "LOW") for p, v in pers.items()},
               "N1_structural_rule_S1_hat": s1rule.round(3).to_dict(),
               "N1_structural_rule_label": {p: ("HIGH" if v > L.THR else "LOW") for p, v in s1rule.items()}}
    if selC in L.NO_NEWS and selC not in ("P_persistence", "MAJ_majority", "N1_structural_rule"):
        lab_out["note"] = f"{selC} selected; its 2027-Q1 output is computed in classification_2027Q1 below."
    if selC not in L.NO_NEWS:
        lab_out["note"] = f"{selC} needs news inputs not available for 2026; persistence is reported instead."
    fc["constructed_label"] = lab_out
    fc["generated_utc"] = datetime.now(timezone.utc).isoformat()

    metrics = {"classification": rcls, "continuous": rcon, "continuous_excluding_2026": rcon_no26,
               "classification_fold_meta": cmeta, "holdout_e17v3_frozen_h5": hold_summary.to_dict()}
    (out / "metrics.json").write_text(json.dumps(metrics, indent=1, default=jd), encoding="utf-8", newline="\n")
    (out / "forecast_2027Q1.json").write_text(json.dumps(fc, indent=1, default=jd), encoding="utf-8", newline="\n")
    hold.to_csv(out / "holdout_e17v3_frozen_h5.csv", index=False, lineterminator="\n", float_format="%.6g")
    dcls.to_csv(out / "classification_scored.csv", index=False, lineterminator="\n", float_format="%.6g")
    comp_x.to_csv(out / "components_2021Q1_2026Q2.csv", index=False, lineterminator="\n", float_format="%.8g")
    log.append({"check": "allowlist (end)", "result": guard.verify_allowlist()})
    (out / "integrity_log.json").write_text(json.dumps({"log": log, "access_log": guard.ACCESS_LOG}, indent=1, default=jd),
                                            encoding="utf-8", newline="\n")
    man = {"started_utc": started.isoformat(), "finished_utc": datetime.now(timezone.utc).isoformat(),
           "protocol": (EXP / "runner" / "PROTOCOL_SHA256.txt").read_text(encoding="utf-8"),
           "code_sha256": {p.name: sha(p) for p in sorted((EXP / "runner").glob("*.py"))},
           "outputs_sha256": {p.name: sha(p) for p in sorted(out.glob("*")) if p.name != "manifest.json"}}
    (out / "manifest.json").write_text(json.dumps(man, indent=1), encoding="utf-8", newline="\n")
    print(out)


if __name__ == "__main__":
    main("--deliverables" in sys.argv)
