"""PROTOCOL_LEAD2_CR_RESOLVE: reproduction of P0H4 / P0H4-U (B0) / CR; one candidate CR-CAL (training-only Platt
recalibration of CR's price part) scored with the unchanged R1-R7 and final.adoption_rule vs B0; diagnostics (settings
sensitivity, SHAP stability, train / validation / test gap, five-group ablation of CR, errors, timing).

    python cr_resolve.py        # ../out/cr_resolve.json, ../out/cr_resolve_rows.csv
"""
from __future__ import annotations

import json
from datetime import date

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

import final as FN
import lt_lib as T
import cpi_refresh_features as CF  # noqa: I001  (after final: it puts the E107 runner first on sys.path)

F, M, KEY = T.F, T.M, T.KEY
CPI = ["A1_food", "A1_gap", "A_mom"]
NAMES = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal",
         "PH040500000": "Batangas"}
WORLD = ["W_rice_yoy", "W_rice_mom", "W_cereal_yoy", "W_crude_yoy"]
GROUPS5 = {"market_prices": ["A1_food", "A1_gap", "A_mom", "A2", "A3"] + WORLD,
           "climate_stress": ["C1", "C2", "C3", "W_urea_yoy"],
           "employment_remittances": ["E1", "E2"],
           "poverty_vulnerability": ["V1"],
           "news_nlp": ["N1", "G_pri_yoy", "NG_gap_price"]}
SEPARATE = {"fish_production": ["C4"], "hunger_outlook": ["H1"]}
FAMILY = {"A1": ["A1_food", "A1_gap", "A_mom"], "A2": ["A2"], "A3": ["A3"], "world": WORLD + ["W_urea_yoy"], "V1": ["V1"],
          "C1": ["C1"], "C2": ["C2"], "C3": ["C3"], "C4": ["C4"], "E1": ["E1"], "E2": ["E2"],
          "N1": ["N1", "G_pri_yoy", "NG_gap_price"], "H1": ["H1"], "lead": ["lead"]}


def cr_stack() -> pd.DataFrame:
    S = T.stack()
    R = pd.read_csv(T.DATA / "cpi_refresh.csv", dtype={"province_code": str})
    S2 = S.merge(R[KEY + ["m0r"] + [f"{c}_r" for c in CPI]], on=KEY, how="left")
    hit = S2["m0r"].notna()
    for c in CPI:
        S2.loc[hit, c] = S2.loc[hit, f"{c}_r"]
    return S2


def folds(tr):
    """The inner chronological folds of lt_lib.select (training rows only)."""
    out = []
    for o in sorted(tr["t"].unique())[-4:]:
        f, h = tr[tr["q"] <= o - 1], tr[tr["t"] == o]
        if f["q"].nunique() >= 3 and f["y"].nunique() == 2 and len(h):
            out.append((f, h))
    return out


def logit(p):
    p = np.clip(np.asarray(p, float), 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def run_cal(S, origins):
    """CR and CR-CAL price parts, with training, validation (inner-fold) and test Brier of the price part."""
    out, gap, shap = [], [], []
    for t in origins:
        tr = T.train_rows(S, int(t))
        te = S[S["t"] == t]
        if not T.eligible(tr) or not len(te):
            continue
        cfg, _ = T.select(tr, T.U2)
        mdl = T.Uni(cfg, T.U2).fit(tr)
        p = mdl.predict(te)
        oof = [(T.Uni(cfg, T.U2).fit(f).predict(h), h["y"].to_numpy(int)) for f, h in folds(tr)]
        pv = np.concatenate([a for a, _ in oof]) if oof else np.array([])
        yv = np.concatenate([b for _, b in oof]) if oof else np.array([])
        if len(yv) >= 30 and len(set(yv)) == 2:
            lr = LogisticRegression(C=1e6).fit(logit(pv).reshape(-1, 1), yv)
            pc, ab = lr.predict_proba(logit(p).reshape(-1, 1))[:, 1], [float(lr.intercept_[0]), float(lr.coef_[0, 0])]
        else:
            pc, ab = p, None
        out.append(te[KEY].assign(CR_price_re=p, CRCAL_price=pc, cfg=cfg["id"]))
        gap.append({"origin": F.qs(int(t)), "cfg": cfg["id"], "platt_a_b": ab, "train_rows": int(len(tr)),
                    "train_brier": float(np.mean((mdl.predict(tr) - tr["y"]) ** 2)),
                    "validation_rows": int(len(yv)), "validation_brier": float(np.mean((pv - yv) ** 2)) if len(yv) else None})
        sv = mdl.shap(te)
        if sv is not None:
            s = pd.DataFrame(np.abs(sv[:, :-1]), columns=T.U2).assign(lead=te["lead"].to_numpy(), t=int(t))
            shap.append(s)
    return pd.concat(out, ignore_index=True), gap, pd.concat(shap, ignore_index=True)


def fixed_cfg(S, origins, cfg, cols=T.U2):
    out = []
    for t in origins:
        tr = T.train_rows(S, int(t))
        te = S[S["t"] == t]
        if not T.eligible(tr) or not len(te):
            continue
        out.append(te[KEY].assign(pi_P=T.Uni(cfg, cols).fit(tr).predict(te)))
    return pd.concat(out, ignore_index=True)


def boot(q, a, b, draws=4000, seed=2031):
    q, d = np.asarray(q), np.asarray(a, float) - np.asarray(b, float)
    uq = np.unique(q)
    by = [d[q == u] for u in uq]
    rng = np.random.default_rng(seed)
    bs = np.array([np.concatenate([by[i] for i in rng.integers(0, len(uq), len(uq))]).mean() for _ in range(draws)])
    return {"diff": float(d.mean()), "ci90": [float(np.quantile(bs, .05)), float(np.quantile(bs, .95))],
            "p_hurts": float((bs <= 0).mean())}


def holm(ps):
    items = sorted(ps.items(), key=lambda kv: kv[1])
    out, run = {}, 0.0
    for i, (k, p) in enumerate(items):
        run = max(run, min(1.0, (len(items) - i) * p))
        out[k] = run
    return out


def summary(d):
    m = d["metrics"]
    return {"accuracy": m["accuracy"], "balanced_accuracy": m["balanced_accuracy"], "precision": m["precision"],
            "recall": m["recall"], "f1": 2 * m["precision"] * m["recall"] / (m["precision"] + m["recall"]) if m["precision"] + m["recall"] else 0.0,
            "tp_fp_fn_tn": [int(m[x]) for x in ("tp", "fp", "fn", "tn")], "brier": m["brier"], "acc_ci90": d["acc_ci90"],
            "dev_brier": d["dev"]["brier"], "dev_accuracy": d["dev"]["accuracy"], "later_accuracy": d["conf"]["accuracy"],
            "later_brier": d["conf"]["brier"], "acc_thirds": d["acc_thirds"], "loqo_min": d["loqo_min"],
            "brier_vs_persist_p": d["brier_vs_persist"]["p_less"], "brier_vs_clim_p": d["brier_vs_clim"]["p_less"],
            "vs_B0": d["vs_B0"], "new_hits_vs_B0": d["new_hits_vs_B0"], "new_false_alarms_vs_B0": d["new_false_alarms_vs_B0"],
            "failed": d["failed"], "reliable": d["reliable"]}


def calib(y, p):
    y, p = np.asarray(y, int), np.asarray(p, float)
    s = float(LogisticRegression(C=1e6).fit(logit(p).reshape(-1, 1), y).coef_[0, 0])
    return {"calibration_in_the_large": float(p.mean() - y.mean()), "calibration_slope": s}


def main():
    proto = T.LT / "PROTOCOL_LEAD2_CR_RESOLVE.md"
    assert T.sha256(proto) == (T.HERE / "CR_RESOLVE_SHA256.txt").read_text().strip(), "protocol changed after freezing"
    E = pd.read_csv(T.OUT / "cpi_refresh_rows.csv", dtype={"province_code": str})
    origins = sorted(E["t"].unique())
    S, S2 = T.stack(), cr_stack()
    res = {"protocol_sha256": T.sha256(proto), "seed": T.SEED_UNI, "grid": T.GRID, "columns": T.U2,
           "evaluation_window": [F.qs(int(E["q"].min())), F.qs(int(E["q"].max()))], "origins": [F.qs(int(t)) for t in origins],
           "data_versions": {p: T.sha256(T.DATA / p) for p in ("stack_l2.csv", "known_price_l2.csv", "cpi_refresh.csv")}}

    # 1. reproduction
    B = T.run(T.U2, origins, S=S)
    C, gap, shap = run_cal(S2, origins)
    chk = E[KEY + ["B0_price", "CR_price"]].merge(B[KEY + ["pi_P"]], on=KEY).merge(C[KEY + ["CR_price_re", "CRCAL_price"]], on=KEY)
    rep = {"B0_max_abs": float((chk["B0_price"] - chk["pi_P"]).abs().max()),
           "CR_max_abs": float((chk["CR_price"] - chk["CR_price_re"]).abs().max()), "rows": int(len(chk))}
    assert rep["B0_max_abs"] < 1e-5 and rep["CR_max_abs"] < 1e-5 and rep["rows"] == len(E), rep
    res["reproduction"] = rep

    # 2. candidate CR-CAL with the unchanged rules
    E = E.merge(C[KEY + ["CRCAL_price"]], on=KEY)
    E["CRCAL_p"] = E["pi_H_AB"] * E["CRCAL_price"]
    ev = {c: FN.lead_eval(E, c) for c in ("P0H4", "B0", "CR", "CRCAL")}
    res["results"] = {c: {int(k): summary(v) for k, v in ev[c]["leads"].items() if int(k) <= 4} | {"max_reliable_lead": ev[c]["max_reliable_lead"]}
                      for c in ev}
    g2 = E[E["lead"] == 2]
    res["calibration_lead2"] = {c: calib(g2["y"], g2[f"{c}_p"]) for c in ("P0H4", "B0", "CR", "CRCAL")}
    res["baselines_lead2"] = {"always_low_accuracy": float((g2["y"] == 0).mean()),
                              "persistence_accuracy": float(((g2["PERS_AB"] >= .5).astype(int) == g2["y"]).mean()),
                              "persistence_brier": float(((g2["PERS_AB"] - g2["y"]) ** 2).mean())}
    res["adoption"] = {c: FN.adoption_rule(ev["B0"]["leads"], ev[c]["leads"]) for c in ("CR", "CRCAL")}
    res["adoption_decision"] = {c: {"adopted": all(r.values()) and ev[c]["leads"][1]["reliable"] and ev[c]["leads"][2]["reliable"],
                                    "failed_rule": [k for k, v in r.items() if not v]} for c, r in res["adoption"].items()}
    res["platt_and_gap_by_origin"] = gap

    # 3. diagnostics: settings sensitivity
    sens = {}
    for cfg in T.GRID:
        P = fixed_cfg(S2, origins, cfg)
        X = E[KEY + ["q", "y", "pi_H_AB", "PERS_AB", "CLIM_p", "ALWAYS-LOW_p"]].merge(P, on=KEY)
        X["x_p"] = X["pi_H_AB"] * X["pi_P"]
        d = F.evaluate(X[X["lead"] == 2], "x_p", "PERS_AB")
        m = d["metrics"]
        sens[cfg["id"]] = {"cfg": cfg, "accuracy": m["accuracy"], "recall": m["recall"], "precision": m["precision"],
                           "brier": m["brier"], "failed": d["failed"]}
    res["settings_sensitivity_lead2"] = sens

    # SHAP stability (CR, Lead 2)
    s2 = shap[shap["lead"] == 2]
    share = pd.DataFrame({f: s2[cs].sum(axis=1) for f, cs in FAMILY.items() if f != "lead"}).assign(t=s2["t"].to_numpy())
    by_o = share.groupby("t").mean()
    by_o = by_o.div(by_o.sum(axis=1), axis=0)
    rk = by_o.rank(axis=1, ascending=False)
    res["shap_stability_lead2"] = {"mean_share": by_o.mean().round(4).to_dict(), "min_share": by_o.min().round(4).to_dict(),
                                   "max_share": by_o.max().round(4).to_dict(), "top_family_by_origin": by_o.idxmax(axis=1).map(str).to_dict(),
                                   "rank_corr_consecutive_origins": [float(rk.iloc[i].corr(rk.iloc[i + 1], method="spearman")) for i in range(len(rk) - 1)]}
    res["shap_stability_lead2"]["top_family_by_origin"] = {F.qs(int(k)): v for k, v in res["shap_stability_lead2"]["top_family_by_origin"].items()}

    # five-group ablation of CR (research only; the final model keeps all 12 families)
    abl = {}
    for name, cols in {**GROUPS5, **SEPARATE}.items():
        P = T.run([c for c in T.U2 if c not in cols], origins, S=S2)
        X = E[KEY + ["q", "y", "pi_H_AB", "CR_p"]].merge(P, on=KEY)
        X["x_p"] = X["pi_H_AB"] * X["pi_P"]
        abl[name] = {}
        for k in (1, 2):
            g = X[X["lead"] == k]
            abl[name][k] = boot(g["q"], (g["x_p"] - g["y"]) ** 2, (g["CR_p"] - g["y"]) ** 2) | {
                "calls_changed": int(((g["x_p"] >= .5) != (g["CR_p"] >= .5)).sum()),
                "accuracy_without": float(((g["x_p"] >= .5).astype(int) == g["y"]).mean())}
    for k in (1, 2):
        hp = holm({n: abl[n][k]["p_hurts"] for n in GROUPS5})
        for n in GROUPS5:
            abl[n][k]["holm_p_hurts"] = hp[n]
    res["ablation_CR"] = abl

    # errors and leave-one-quarter-out
    g2 = E[E["lead"] == 2].assign(province=lambda x: x["province_code"].map(NAMES))
    err = {}
    for c in ("P0H4", "B0", "CR", "CRCAL"):
        k = (g2[f"{c}_p"] >= .5).astype(int)
        err[c] = {"by_province": {p: {"fn": int(((k == 0) & (h["y"] == 1)).sum()), "fp": int(((k == 1) & (h["y"] == 0)).sum()),
                                      "high": int(h["y"].sum()), "n": int(len(h))} for p, h in g2.assign(k=k).groupby("province")
                                  for k in [h["k"]]},
                  "by_quarter": {F.qs(int(q)): {"fn": int(((h["k"] == 0) & (h["y"] == 1)).sum()), "fp": int(((h["k"] == 1) & (h["y"] == 0)).sum()),
                                                "high": int(h["y"].sum())} for q, h in g2.assign(k=k).groupby("q")},
                  "loqo_all_R_pass": int(sum(F.evaluate(g2[g2["q"] != q], f"{c}_p", "PERS_AB")["reliable"] for q in g2["q"].unique()))}
    res["errors_lead2"] = err

    # timing
    R = pd.read_csv(T.DATA / "cpi_refresh.csv", dtype={"province_code": str})
    ok_rule = all(CF.newest_month(F.issue(int(t), "B"), int(m0)) == int(m)
                  for t, m0, m in zip(R["t"], R["m0"], R["m0r"]))
    rel_before = all(date((int(m) + 1) // 12, (int(m) + 1) % 12 + 1, CF.RELEASE_DAY) < date.fromisoformat(F.issue(int(t), "B"))
                     for t, m in zip(R["t"], R["m0r"]))
    ia = json.loads((T.OUT / "input_audit.json").read_text())["time_alignment"]
    res["timing"] = {"target_quarter_equals_origin_plus_lead": bool((S["target_q"] == S["t"] + S["lead"]).all()),
                     "cpi_newest_month_matches_day10_rule": bool(ok_rule), "cpi_month_released_before_issue_under_rule": bool(rel_before),
                     "input_audit": ia, "release_day_sensitivity": json.loads((T.OUT / "cr_release_sensitivity.json").read_text()),
                     "actual_psa_provincial_release_dates": "not recorded in the repository (unresolved dependency)"}
    E.to_csv(T.OUT / "cr_resolve_rows.csv", index=False, lineterminator="\n", float_format="%.6g")
    (T.OUT / "cr_resolve.json").write_text(json.dumps(res, indent=1, default=float))
    for c in ("P0H4", "B0", "CR", "CRCAL"):
        for k in (1, 2):
            r = res["results"][c][k]
            print(c, k, round(r["accuracy"], 3), round(r["balanced_accuracy"], 3), round(r["precision"], 3), round(r["recall"], 3),
                  r["tp_fp_fn_tn"], round(r["brier"], 4), r["failed"])
    print(json.dumps(res["adoption_decision"], indent=1))


if __name__ == "__main__":
    main()
