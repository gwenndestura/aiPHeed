"""PROTOCOL_LEAD2_FINAL: one candidate K1 (P0H4-U + food-price composition and breadth) vs B0 = P0H4-U, one unified
LightGBM over all leads, all 12 families, x pi_H (S-AB); frozen adoption rule, R1-R7, errors fixed / made, mechanism.

    python final.py             # ../out/final.json, ../out/final_rows.csv
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import lt_lib as T
from features_v4 import K_COLS

F, M, KEY = T.F, T.M, T.KEY
DIRS = {"A1_food": 1, "A1_gap": 1, "A_mom": 1, "K_core": 1, "K_diff": 1, "K_fresh_gap": -1}
CANDS = {"B0": T.U2, "K1": T.U2 + K_COLS}


class UniD(T.Uni):
    """lt_lib.Uni with signed monotone directions (the protocol fixes K_fresh_gap at -1)."""

    def fit(self, tr):
        import lightgbm as lgb
        y = tr["y"].to_numpy(int)
        if len(set(y)) < 2:
            self.const = float(y.mean()) if len(y) else 0.5
            return self
        self.m = lgb.LGBMClassifier(objective="binary", learning_rate=0.05, reg_lambda=5.0, deterministic=True,
                                    force_row_wise=True, feature_pre_filter=False, random_state=T.SEED_UNI, n_jobs=1,
                                    verbose=-1, max_depth=self.cfg["depth"], num_leaves=self.cfg["leaves"],
                                    n_estimators=self.cfg["trees"], class_weight=self.cfg["cw"],
                                    min_child_samples=self.min_child,
                                    monotone_constraints=[DIRS.get(c, 0) for c in self.cols],
                                    monotone_constraints_method="basic")
        self.m.fit(tr[self.cols].astype(float), y)
        return self


def select(tr, cols):
    origins = sorted(tr["t"].unique())[-4:]
    folds = [(tr[tr["q"] <= o - 1], tr[tr["t"] == o]) for o in origins]
    folds = [(f, h) for f, h in folds if f["q"].nunique() >= 3 and f["y"].nunique() == 2 and len(h)]
    if not folds:
        return T.GRID[0]
    ys = np.concatenate([h["y"].to_numpy(int) for _, h in folds])
    sc = {}
    for c in T.GRID:
        p = np.clip(np.concatenate([UniD(c, cols).fit(f).predict(h) for f, h in folds]), 1e-6, 1 - 1e-6)
        sc[c["id"]] = float(-np.mean(ys * np.log(p) + (1 - ys) * np.log(1 - p)))
    return min(T.GRID, key=lambda c: (round(sc[c["id"]], 9), c["id"]))


def run(S, cols, origins, models=None):
    out = []
    for t in origins:
        tr = T.train_rows(S, int(t))
        te = S[S["t"] == t]
        if not T.eligible(tr) or not len(te):
            continue
        cfg = select(tr, cols)
        mdl = UniD(cfg, cols).fit(tr)
        if models is not None:
            models[int(t)] = mdl
        o = te[KEY].assign(pi_P=mdl.predict(te), cfg=cfg["id"])
        sv = mdl.shap(te)
        if sv is not None:
            for j, c in enumerate(cols):
                o[f"shap_{c}"] = sv[:, j]
        out.append(o)
    return pd.concat(out, ignore_index=True)


def smd(x, y) -> float:
    a, b = x[y == 1].dropna(), x[y == 0].dropna()
    s = np.sqrt((a.var() + b.var()) / 2)
    return float((a.mean() - b.mean()) / s) if len(a) > 1 and len(b) > 1 and s > 0 else float("nan")


def lead_eval(E: pd.DataFrame, c: str) -> dict:
    """R1-R7 and the before/after quantities of candidate c vs B0, by lead."""
    dec = {}
    for k, g in E.groupby("lead"):
        d = F.evaluate(g, f"{c}_p", "PERS_AB")
        dv = g["q"] <= F.DEV_LAST
        d["dev"], d["conf"] = M.cls(g.loc[dv, "y"], g.loc[dv, f"{c}_p"]), M.cls(g.loc[~dv, "y"], g.loc[~dv, f"{c}_p"])
        d["vs_B0"] = M.boot_diff(g["q"], (g[f"{c}_p"] - g["y"]) ** 2, (g["B0_p"] - g["y"]) ** 2)
        d["price_term"] = M.cls(g["price"], g[f"{c}_price"])
        d["new_hits_vs_B0"] = int(((g[f"{c}_p"] >= .5) & (g["B0_p"] < .5) & (g["y"] == 1)).sum())
        d["new_false_alarms_vs_B0"] = int(((g[f"{c}_p"] >= .5) & (g["B0_p"] < .5) & (g["y"] == 0)).sum())
        d["lost_hits_vs_B0"] = int(((g[f"{c}_p"] < .5) & (g["B0_p"] >= .5) & (g["y"] == 1)).sum())
        d["removed_false_alarms_vs_B0"] = int(((g[f"{c}_p"] < .5) & (g["B0_p"] >= .5) & (g["y"] == 0)).sum())
        yr = g["q"] // 4
        d["acc_by_year"] = {int(a): float(((h[f"{c}_p"] >= .5).astype(int) == h["y"]).mean()) for a, h in g.groupby(yr)}
        dec[int(k)] = d
    return {"leads": dec, "max_reliable_lead": F.max_reliable(dec)}


def adoption_rule(b: dict, k1: dict) -> dict:
    """PROTOCOL_LEAD2_FINAL §5, candidate k1 vs B0 b (per-lead results of lead_eval)."""
    m_b, m_k = b[2]["metrics"], k1[2]["metrics"]
    return {
        "1a_L2_dev_brier_gain_ge_0.005": b[2]["dev"]["brier"] - k1[2]["dev"]["brier"] >= 0.005,
        "1b_L1_dev_brier_not_worse_by_0.005": k1[1]["dev"]["brier"] <= b[1]["dev"]["brier"] + 0.005,
        "1c_L2_dev_balanced_not_lower": k1[2]["dev"]["balanced_accuracy"] >= b[2]["dev"]["balanced_accuracy"] - 1e-12,
        **{f"2_L2_{m}_within_0.02": m_k[m] >= m_b[m] - 0.02 - 1e-12
           for m in ("accuracy", "balanced_accuracy", "precision", "recall")},
        "2_new_FA_le_new_hits": k1[2]["new_false_alarms_vs_B0"] <= k1[2]["new_hits_vs_B0"],
        "2_L2_conf_accuracy_not_lower": k1[2]["conf"]["accuracy"] >= b[2]["conf"]["accuracy"] - 1e-12,
        "3_L1_passes_R1_R7": k1[1]["reliable"],
    }


def main():
    assert T.sha256(T.LT / "PROTOCOL_LEAD2_FINAL.md") == (T.HERE / "FINAL_SHA256.txt").read_text().strip(), \
        "protocol changed after freezing"
    S = pd.read_csv(T.DATA / "stack_v4.csv", dtype={"province_code": str})
    C = pd.read_csv(T.OUT / "candidates.csv", dtype={"province_code": str})
    E = C[KEY + ["q", "y", "price", "hunger", "pi_H_AB", "PERS_AB", "CLIM_p", "ALWAYS-LOW_p", "C0_price", "C0_p"]].copy()
    origins = sorted(E["t"].unique())
    shap = {}
    for c, cols in CANDS.items():
        P = run(S, cols, origins)
        shap[c] = P
        E = E.merge(P[KEY + ["pi_P", "cfg"]].rename(columns={"pi_P": f"{c}_price", "cfg": f"{c}_cfg"}), on=KEY, how="left")
        assert E[f"{c}_price"].notna().all(), c
        E[f"{c}_p"] = E["pi_H_AB"] * E[f"{c}_price"]
        print(c, "done", flush=True)
    repro = float((E["B0_price"] - E["C0_price"]).abs().max())
    assert repro < 1e-5, f"B0 must reproduce P0H4-U ({repro})"
    res = {"protocol_sha256": T.sha256(T.LT / "PROTOCOL_LEAD2_FINAL.md"), "b0_reproduction_max_abs": repro, "cands": {}}
    for c in CANDS:
        res["cands"][c] = lead_eval(E, c)
    # ---------------------------------------------------------------- frozen adoption rule (protocol §5)
    rule = adoption_rule(res["cands"]["B0"]["leads"], res["cands"]["K1"]["leads"])
    adopt = all(rule.values())
    final = "K1" if adopt else "B0"
    res["adoption"] = {"rule": rule, "adopted": adopt, "FINAL": final,
                       "lead2_reliable": res["cands"][final]["leads"][2]["reliable"],
                       "lead2_failed": res["cands"][final]["leads"][2]["failed"]}
    # ---------------------------------------------------------------- B0 errors fixed / new errors at Lead 2
    g = E[E["lead"] == 2]
    eb, ek = (g["B0_p"] >= .5).astype(int) != g["y"], (g["K1_p"] >= .5).astype(int) != g["y"]
    nm = {v: k for k, v in {"Cavite": "PH040100000", "Laguna": "PH040200000", "Quezon": "PH040300000",
                            "Rizal": "PH040400000", "Batangas": "PH040500000"}.items()}
    lst = lambda m: [f"{nm[r.province_code]} {F.qs(int(r.q))} ({'FN' if r.y else 'FP'}; B0 {r.B0_p:.3f} -> K1 {r.K1_p:.3f})"  # noqa: E731
                     for r in g[m].itertuples()]
    res["lead2_errors"] = {"fixed_by_K1": lst(eb & ~ek), "new_errors_K1": lst(~eb & ek), "kept": lst(eb & ek)}
    # ---------------------------------------------------------------- mechanism (diagnostic only)
    last = max(origins)
    tr = T.train_rows(S, int(last))
    tr = tr.assign(proj=tr[["A1_food", "A1_gap"]].max(axis=1))
    hi = tr[tr["proj"] >= 0]
    res["mechanism"] = {
        "train_rows_final_origin": int(len(tr)),
        "smd_high_minus_low_all": {c: smd(tr[c], tr["y"]) for c in K_COLS + ["A1_food", "accel"]},
        "smd_high_minus_low_projection_above_threshold": {c: smd(hi[c], hi["y"]) for c in K_COLS + ["A1_food", "accel"]},
        "rows_projection_above_threshold": int(len(hi)), "of_which_price_condition_held": int(hi["y"].sum()),
    }
    sp = shap["K1"]
    sp = sp[sp["lead"] == 2]
    tot = sp[[f"shap_{c}" for c in CANDS["K1"]]].abs().sum(axis=1)
    res["mechanism"]["lead2_mean_abs_shap_share"] = {c: float((sp[f"shap_{c}"].abs() / tot).mean()) for c in CANDS["K1"]}
    E.to_csv(T.OUT / "final_rows.csv", index=False, lineterminator="\n", float_format="%.6g")
    T.OUT.joinpath("final.json").write_text(json.dumps(res, indent=1, default=float))
    for c, r in res["cands"].items():
        print(c, "max reliable lead", r["max_reliable_lead"])
        for k in (1, 2, 3, 4):
            d = r["leads"][k]
            m = d["metrics"]
            print(f"  L{k} acc {m['accuracy']:.3f} {d['acc_ci90']} bal {m['balanced_accuracy']:.3f} P {m['precision']:.2f} "
                  f"R {m['recall']:.2f} TP{m['tp']} FP{m['fp']} FN{m['fn']} TN{m['tn']} Br {m['brier']:.4f} "
                  f"vsB0 {d['vs_B0']['diff']:+.4f} [{d['vs_B0']['ci90'][0]:+.4f},{d['vs_B0']['ci90'][1]:+.4f}] p{d['vs_B0'].get('p_less', float('nan')):.3f} "
                  f"devBr {d['dev']['brier']:.4f} conf acc {d['conf']['accuracy']:.3f} thirds {[round(x, 3) for x in d['acc_thirds']]} "
                  f"loqo {d['loqo_min']:.3f} vsPers p{d['brier_vs_persist']['p_less']:.3f} vsClim p{d['brier_vs_clim']['p_less']:.3f} fail {d['failed']}")
    print(json.dumps(res["adoption"], indent=1))
    print(json.dumps(res["lead2_errors"], indent=1))
    print(json.dumps(res["mechanism"], indent=1, default=float))


if __name__ == "__main__":
    main()
