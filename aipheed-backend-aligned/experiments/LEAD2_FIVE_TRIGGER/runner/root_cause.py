"""PROTOCOL_LEAD2_ROOT_CAUSE: three corrections of CR, each justified by the row-level error analysis, scored once with
the unchanged R1-R7 and final.adoption_rule vs B0 = P0H4-U:

- CR-ANC: CR + B1 anchored food / gap projections computed at each row's own CPI cut-off (m0r for Lead >= 2);
- CR-T: CR's probabilities with the ADDENDUM 2 decision cut chosen per origin and lead from CR's own earlier
  forecasts whose outcomes were published before the origin;
- CR-WCAL: CR's probability recalibrated per origin and lead by a Platt map fitted on the same earlier forecasts.

    python root_cause.py        # ../out/root_cause.json, ../out/root_cause_rows.csv
"""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

import final as FN
import lt_lib as T
import threshold as TH
from cr_resolve import GROUPS5, SEPARATE, boot, cr_stack, fixed_cfg, holm, logit
from features_v2 import II

F, M, KEY = T.F, T.M, T.KEY
G_ANCHOR = math.log(1.03) / 12
ANC = ["A1_food_anc", "A1_gap_anc"]
COLS_ANC = T.U2 + ANC
NAMES = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal",
         "PH040500000": "Batangas"}


def anchored_at(S: pd.DataFrame, g: float) -> tuple[np.ndarray, np.ndarray]:
    """features_v2.anchored with each row's own cut-off month: m0r (CR refresh) for Lead >= 2, else m0."""
    W = II.index_wide()
    lf, la = np.log(W["food"]), np.log(W["all"])
    out_f, out_g = [], []
    for t, k, p, mr in zip(S["t"], S["lead"], S["province_code"], S["m0r"]):
        m0 = int(mr) if int(k) >= 2 and pd.notna(mr) else II.m0_of(int(t))
        q = int(t) + int(k)
        months = [q // 4 * 12 + (q % 4) * 3 + j for j in range(3)]

        def L(series, m):
            if m <= m0:
                return series[p].get(m, np.nan)
            return series[p].get(m0, np.nan) + g * (m - m0)
        try:
            yf = [100 * (math.exp(L(lf, m) - L(lf, m - 12)) - 1) for m in months]
            ya = [100 * (math.exp(L(la, m) - L(la, m - 12)) - 1) for m in months]
            if any(np.isnan(yf + ya)) or min(m - 12 for m in months) < II.FIRST_YM:
                raise ValueError
            fq, aq = float(np.mean(yf)), float(np.mean(ya))
            out_f.append(fq - F.TH_F[p])
            out_g.append(fq - aq - F.TH_G[p])
        except (ValueError, KeyError):
            out_f.append(np.nan)
            out_g.append(np.nan)
    return np.array(out_f), np.array(out_g)


def earlier(E, known, t, k):
    v = E[(E["lead"] == k) & (E["t"] < t)]
    ks = known.get(int(t), set())
    return v.loc[np.array([(p, q) in ks for p, q in zip(v["province_code"], v["q"])], dtype=bool)]


def walk_forward(E, known):
    """CR-T thresholds and CR-WCAL Platt maps per origin and lead, from earlier CR forecasts with published outcomes."""
    thr, cal, info = {}, {}, []
    for t in sorted(E["t"].unique()):
        for k in sorted(E["lead"].unique()):
            v = earlier(E.rename(columns={"CR_p": "p"}), known, t, k)
            thr[(t, k)] = TH.choose(v)
            ok = v["q"].nunique() >= 4 and v["y"].sum() >= 3 and (1 - v["y"]).sum() >= 3
            if ok:
                lr = LogisticRegression(C=1e6).fit(logit(v["p"]).reshape(-1, 1), v["y"].astype(int))
                cal[(t, k)] = (float(lr.intercept_[0]), float(lr.coef_[0, 0]))
            else:
                cal[(t, k)] = None
            if k <= 2:
                info.append({"origin": F.qs(int(t)), "lead": int(k), "earlier_rows": int(len(v)), "earlier_high": int(v["y"].sum()),
                             "threshold": thr[(t, k)], "platt_a_b": cal[(t, k)]})
    return thr, cal, info


def lead_eval_calls(E, cc, pc):
    """final.lead_eval for a candidate whose calls (cc) are not p >= 0.50 (CR-T); Brier on pc."""
    dec = {}
    for k, g in E.groupby("lead"):
        d = TH.evaluate(g, cc, pc, "PERS_AB")
        dv = g["q"] <= F.DEV_LAST
        d["dev"] = TH.cls_metrics(g.loc[dv, "y"], g.loc[dv, cc], g.loc[dv, pc])
        d["conf"] = TH.cls_metrics(g.loc[~dv, "y"], g.loc[~dv, cc], g.loc[~dv, pc])
        b = g["B0_p"] >= .5
        c = g[cc] == 1
        d["new_hits_vs_B0"] = int((c & ~b & (g["y"] == 1)).sum())
        d["new_false_alarms_vs_B0"] = int((c & ~b & (g["y"] == 0)).sum())
        d["vs_B0"] = M.boot_diff(g["q"], (g[pc] - g["y"]) ** 2, (g["B0_p"] - g["y"]) ** 2)
        dec[int(k)] = d
    return {"leads": dec, "max_reliable_lead": F.max_reliable(dec)}


def summary(d):
    m = d["metrics"]
    f1 = 2 * m["precision"] * m["recall"] / (m["precision"] + m["recall"]) if (m["precision"] or 0) + (m["recall"] or 0) else 0.0
    return {"accuracy": m["accuracy"], "balanced_accuracy": m["balanced_accuracy"], "precision": m["precision"], "recall": m["recall"],
            "f1": f1, "tp_fp_fn_tn": [int(m[x]) for x in ("tp", "fp", "fn", "tn")], "brier": m["brier"], "acc_ci90": d["acc_ci90"],
            "dev_accuracy": d["dev"]["accuracy"], "dev_brier": d["dev"]["brier"], "later_accuracy": d["conf"]["accuracy"],
            "acc_thirds": d["acc_thirds"], "loqo_min": d["loqo_min"], "vs_B0": d.get("vs_B0"),
            "new_hits_vs_B0": d.get("new_hits_vs_B0"), "new_false_alarms_vs_B0": d.get("new_false_alarms_vs_B0"),
            "failed": d["failed"], "reliable": d["reliable"]}


def calib(y, p):
    y, p = np.asarray(y, int), np.asarray(p, float)
    return {"slope": float(LogisticRegression(C=1e6).fit(logit(p).reshape(-1, 1), y).coef_[0, 0]),
            "in_the_large": float(p.mean() - y.mean())}


def main():
    proto = T.LT / "PROTOCOL_LEAD2_ROOT_CAUSE.md"
    assert T.sha256(proto) == (T.HERE / "ROOT_CAUSE_SHA256.txt").read_text().strip(), "protocol changed after freezing"
    T.MONO_UP = T.MONO_UP + ANC                                   # anchored projections monotone +1, like A1
    E = pd.read_csv(T.OUT / "cr_resolve_rows.csv", dtype={"province_code": str})
    origins = sorted(E["t"].unique())
    S2 = cr_stack()
    res = {"protocol_sha256": T.sha256(proto), "seed": T.SEED_UNI, "columns_CR_ANC": COLS_ANC}

    # CR-ANC features: check against features_v2 at the quarter-start cut-off (Lead 1 rows)
    S2["A1_food_anc"], S2["A1_gap_anc"] = anchored_at(S2, G_ANCHOR)
    V2 = pd.read_csv(T.DATA / "stack_v2.csv", dtype={"province_code": str})[KEY + ANC]
    ck = S2[S2["lead"] == 1][KEY + ANC].merge(V2, on=KEY, suffixes=("", "_v2"))
    res["anc_reproduces_features_v2_lead1_max_abs"] = float(max((ck[c] - ck[f"{c}_v2"]).abs().max() for c in ANC))
    assert res["anc_reproduces_features_v2_lead1_max_abs"] < 1e-6
    res["anc_coverage_lead2"] = float(S2.loc[S2["lead"] == 2, "A1_food_anc"].notna().mean())

    # 1. CR-ANC
    P = T.run(COLS_ANC, origins, S=S2)
    E = E.merge(P[KEY + ["pi_P"]].rename(columns={"pi_P": "CRANC_price"}), on=KEY)
    E["CRANC_p"] = E["pi_H_AB"] * E["CRANC_price"]

    # 2-3. CR-T and CR-WCAL from earlier CR forecasts with published outcomes
    kn = pd.read_csv(F.DATA / "known_by_origin.csv", dtype={"province_code": str})
    kn = kn[kn["y"].notna()][["t", "province_code", "q"]]
    known = {t: set(zip(g["province_code"], g["q"])) for t, g in kn.groupby("t")}
    thr, cal, info = walk_forward(E, known)
    E["CRT_thr"] = [thr[(t, k)] for t, k in zip(E["t"], E["lead"])]
    E["CRT_cls"] = (E["CR_p"] >= E["CRT_thr"]).astype(int)
    E["CRT_p"] = E["CR_p"]
    ab = [cal[(t, k)] for t, k in zip(E["t"], E["lead"])]
    E["CRWCAL_p"] = [p if c is None else 1 / (1 + math.exp(-(c[0] + c[1] * float(logit([p])[0])))) for p, c in zip(E["CR_p"], ab)]
    E["CRWCAL_price"] = E["CR_price"]
    res["walk_forward_maps"] = info

    # evaluation, unchanged rules
    ev = {c: FN.lead_eval(E, c) for c in ("P0H4", "B0", "CR", "CRCAL", "CRANC", "CRWCAL")}
    ev["CRT"] = lead_eval_calls(E, "CRT_cls", "CRT_p")
    res["results"] = {c: {int(k): summary(v) for k, v in ev[c]["leads"].items() if int(k) <= 4} | {"max_reliable_lead": ev[c]["max_reliable_lead"]}
                      for c in ev}
    g2 = E[E["lead"] == 2]
    res["calibration_lead2"] = {c: calib(g2["y"], g2[f"{c}_p"]) for c in ("P0H4", "B0", "CR", "CRCAL", "CRANC", "CRWCAL")}
    res["baselines_lead2"] = {"always_low_accuracy": float((g2["y"] == 0).mean()),
                              "persistence_accuracy": float(((g2["PERS_AB"] >= .5).astype(int) == g2["y"]).mean())}
    res["adoption"] = {}
    for c in ("CRANC", "CRT", "CRWCAL"):
        rule = FN.adoption_rule(ev["B0"]["leads"], ev[c]["leads"])
        res["adoption"][c] = {"rule": rule, "failed_rule": [k for k, v in rule.items() if not v],
                              "lead1_R": ev[c]["leads"][1]["failed"], "lead2_R": ev[c]["leads"][2]["failed"],
                              "eligible": all(rule.values()) and ev[c]["leads"][1]["reliable"] and ev[c]["leads"][2]["reliable"]}
    elig = [c for c, a in res["adoption"].items() if a["eligible"]]
    res["decision"] = {"eligible": elig,
                       "research_candidate": min(elig, key=lambda c: ev[c]["leads"][2]["dev"]["brier"]) if elig else "CR (unchanged)",
                       "served": "P0H4 (unchanged; any change needs the researchers' approval)"}

    # errors by quarter / province and the changed calls vs CR
    calls = {c: (g2[f"{c}_p"] >= .5).astype(int) for c in ("CR", "CRANC", "CRWCAL")} | {"CRT": g2["CRT_cls"]}
    res["errors_lead2"] = {c: {"by_province": {NAMES[p]: {"fn": int(((k == 0) & (h["y"] == 1)).sum()), "fp": int(((k == 1) & (h["y"] == 0)).sum())}
                                               for p, h in g2.assign(k=k).groupby("province_code") for k in [h["k"]]},
                               "by_quarter": {F.qs(int(q)): {"fn": int(((h["k"] == 0) & (h["y"] == 1)).sum()), "fp": int(((h["k"] == 1) & (h["y"] == 0)).sum())}
                                              for q, h in g2.assign(k=k).groupby("q") if ((h["k"] != h["y"]).any())},
                               "changed_vs_CR": [f"{NAMES[r.province_code]} {F.qs(int(r.q))} y={int(r.y)} CR {r.CR_p:.3f} -> {c} call {int(kk)}"
                                                 for r, kk in zip(g2.itertuples(), k) if kk != int(r.CR_p >= .5)]}
                           for c, k in calls.items()}

    # CR-ANC diagnostics: settings, ablation, train/validation/test
    sens = {}
    for cfg in T.GRID:
        Q = fixed_cfg(S2, origins, cfg, cols=COLS_ANC)
        X = E[KEY + ["q", "y", "pi_H_AB", "PERS_AB", "CLIM_p", "ALWAYS-LOW_p"]].merge(Q, on=KEY)
        X["x_p"] = X["pi_H_AB"] * X["pi_P"]
        d = F.evaluate(X[X["lead"] == 2], "x_p", "PERS_AB")
        sens[cfg["id"]] = {"accuracy": d["metrics"]["accuracy"], "recall": d["metrics"]["recall"], "brier": d["metrics"]["brier"], "failed": d["failed"]}
    res["CRANC_settings_sensitivity_lead2"] = sens
    abl = {}
    for name, cols in {**GROUPS5, **SEPARATE}.items():
        drop = cols + (ANC if name == "market_prices" else [])
        Q = T.run([c for c in COLS_ANC if c not in drop], origins, S=S2)
        X = E[KEY + ["q", "y", "pi_H_AB", "CRANC_p"]].merge(Q, on=KEY)
        X["x_p"] = X["pi_H_AB"] * X["pi_P"]
        abl[name] = {}
        for k in (1, 2):
            g = X[X["lead"] == k]
            abl[name][k] = boot(g["q"], (g["x_p"] - g["y"]) ** 2, (g["CRANC_p"] - g["y"]) ** 2) | {
                "calls_changed": int(((g["x_p"] >= .5) != (g["CRANC_p"] >= .5)).sum())}
    for k in (1, 2):
        hp = holm({n: abl[n][k]["p_hurts"] for n in GROUPS5})
        for n in GROUPS5:
            abl[n][k]["holm_p_hurts"] = hp[n]
    res["CRANC_ablation"] = abl
    gap = []
    for t in origins:
        tr = T.train_rows(S2, int(t))
        if not T.eligible(tr):
            continue
        cfg, sc = T.select(tr, COLS_ANC)
        mdl = T.Uni(cfg, COLS_ANC).fit(tr)
        te = S2[S2["t"] == t].merge(E[E["t"] == t][KEY + ["price"]], on=KEY)
        gap.append({"origin": F.qs(int(t)), "train_brier": float(np.mean((mdl.predict(tr) - tr["y"]) ** 2)),
                    "validation_logloss": sc.get(cfg["id"]), "test_brier": float(np.mean((mdl.predict(te) - te["price"]) ** 2))})
    res["CRANC_train_validation_test"] = gap

    # diagnostics: target sensitivity (reported, not used), missingness, news timing
    lab_known = pd.read_csv(T.DATA / "known_price_l2.csv", dtype={"province_code": str})
    last_price = {(t, p): int(h.sort_values("q")["y"].iloc[-1]) for (t, p), h in lab_known.groupby(["t", "province_code"])}
    g2 = g2.assign(price_pers=[last_price.get((int(t), p), 0) for t, p in zip(g2["t"], g2["province_code"])],
                   hunger_pers=(g2["PERS_AB"] >= .5).astype(int) if "PERS_AB" in g2 else 0)
    hp_ = g2["pi_H_AB"]
    res["target_sensitivity_lead2"] = {
        "regional_hunger_condition": {"what": "Balance Luzon SWS hunger > 11.3 (regional, observed food insecurity)",
                                      "model_accuracy": float(((hp_ >= .5).astype(int) == g2["hunger"]).mean()),
                                      "brier": float(((hp_ - g2["hunger"]) ** 2).mean()),
                                      "latest_reading_persistence_accuracy": float(((hp_ > .5).astype(int) == g2["hunger"]).mean()),
                                      "note": "pi_H is itself the latest-reading rule, so it equals persistence except at the 11.3 tie"},
        "provincial_price_condition": {"what": "province food or food-minus-headline inflation above its 2021-22 P60 (proxy)",
                                       "CR_price_accuracy": float(((g2["CR_price"] >= .5).astype(int) == g2["price"]).mean()),
                                       "CR_price_brier": float(((g2["CR_price"] - g2["price"]) ** 2).mean()),
                                       "last_known_price_condition_accuracy": float((g2["price_pers"] == g2["price"]).mean())}}
    errs = pd.read_csv(T.OUT / "rootcause_errors.csv")
    S2l2 = S2[S2["lead"] == 2].merge(g2[KEY], on=KEY)
    res["missingness"] = {"N1_missing_all_lead2_rows": float(S2l2["N1"].isna().mean()),
                          "N1_missing_CR_error_rows": float(errs.loc[errs["candidate"] == "CR", "N1_missing"].mean()),
                          "A3_missing_all_lead2_rows": float(S2l2["A3"].isna().mean()),
                          "A3_missing_CR_error_rows": float(errs.loc[errs["candidate"] == "CR", "A3_missing"].mean())}
    nw = pd.to_datetime(S2["news_latest_published"], errors="coerce")
    res["news_timing"] = {"rows_with_news_date": int(nw.notna().sum()),
                          "all_before_quarter_start_issue": bool((nw.dropna() < pd.to_datetime(S2.loc[nw.notna(), "issue_date"])).all())}
    E.to_csv(T.OUT / "root_cause_rows.csv", index=False, lineterminator="\n", float_format="%.6g")
    (T.OUT / "root_cause.json").write_text(json.dumps(res, indent=1, default=float))
    for c in ("P0H4", "B0", "CR", "CRCAL", "CRANC", "CRT", "CRWCAL"):
        for k in (1, 2):
            r = res["results"][c][k]
            print(c, k, round(r["accuracy"], 3), round(r["balanced_accuracy"], 3), round(r["precision"], 3), round(r["recall"], 3),
                  r["tp_fp_fn_tn"], round(r["brier"], 4), r["failed"])
    print(json.dumps({c: {k: v for k, v in a.items() if k != "rule"} for c, a in res["adoption"].items()}, indent=1))
    print(res["decision"])


if __name__ == "__main__":
    main()
