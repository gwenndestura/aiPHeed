"""PROTOCOL_LEAD2_IMPROVE: candidates B0-B4 (one unified LightGBM, all 12 families) x pi_H (S-AB), frozen DEV
selection, CONF report, R1-R7, the earlier misses, error patterns and the early-warning check.

    python improve.py           # ../out/improve.json, ../out/improve_rows.csv, ../out/error_patterns.csv
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import lt_lib as T

F, M, KEY = T.F, T.M, T.KEY
ANC = ["A1_food_anc", "A1_gap_anc"]
DYN = ["dC3", "dC4", "dE1", "dE2", "C2_2q", "C1_run"]
CANDS = {"B0": (T.U2, T.MONO_UP, (None,)), "B1": (T.U2 + ANC, T.MONO_UP + ANC, (None,)),
         "B2": (T.U2, T.MONO_UP, (None, 8, 4)), "B3": (T.U2 + ANC, T.MONO_UP + ANC, (None, 8, 4)),
         "B4": (T.U2 + DYN, T.MONO_UP, (None,))}


class UniW(T.Uni):
    def __init__(self, cfg, cols, mono_cols, hl=None):
        super().__init__(cfg, cols)
        self.mono_cols, self.hl = mono_cols, hl

    def fit(self, tr, origin=None):
        import lightgbm as lgb
        y = tr["y"].to_numpy(int)
        if len(set(y)) < 2:
            self.const = float(y.mean()) if len(y) else 0.5
            return self
        w = None
        if self.hl:
            w = np.power(0.5, (origin - tr["q"].to_numpy(float)) / self.hl)
        self.m = lgb.LGBMClassifier(objective="binary", learning_rate=0.05, reg_lambda=5.0, deterministic=True,
                                    force_row_wise=True, feature_pre_filter=False, random_state=T.SEED_UNI, n_jobs=1,
                                    verbose=-1, max_depth=self.cfg["depth"], num_leaves=self.cfg["leaves"],
                                    n_estimators=self.cfg["trees"], class_weight=self.cfg["cw"], min_child_samples=15,
                                    monotone_constraints=[1 if c in self.mono_cols else 0 for c in self.cols],
                                    monotone_constraints_method="basic")
        self.m.fit(tr[self.cols].astype(float), y, sample_weight=w)
        return self


def select(tr, cols, mono, hls):
    origins = sorted(tr["t"].unique())[-4:]
    folds = [(tr[tr["q"] <= o - 1], tr[tr["t"] == o], o) for o in origins]
    folds = [(f, h, o) for f, h, o in folds if f["q"].nunique() >= 3 and f["y"].nunique() == 2 and len(h)]
    opts = [(c, hl) for hl in hls for c in T.GRID]
    if not folds:
        return opts[0]
    sc = {}
    ys = np.concatenate([h["y"].to_numpy(int) for _, h, _ in folds])
    for c, hl in opts:
        ps = np.concatenate([UniW(c, cols, mono, hl).fit(f, o).predict(h) for f, h, o in folds])
        p = np.clip(ps, 1e-6, 1 - 1e-6)
        sc[(c["id"], hl or 0)] = float(-np.mean(ys * np.log(p) + (1 - ys) * np.log(1 - p)))
    return min(opts, key=lambda o: (round(sc[(o[0]["id"], o[1] or 0)], 9), o[1] or 0, o[0]["id"]))


def run(S, cols, mono, hls, origins, models=None):
    out = []
    for t in origins:
        tr = T.train_rows(S, int(t))
        te = S[S["t"] == t]
        if not T.eligible(tr) or not len(te):
            continue
        cfg, hl = select(tr, cols, mono, hls)
        mdl = UniW(cfg, cols, mono, hl).fit(tr, int(t))
        if models is not None:
            models[int(t)] = mdl
        out.append(te[KEY].assign(pi_P=mdl.predict(te), cfg=f"{cfg['id']}|hl{hl or 0}"))
    return pd.concat(out, ignore_index=True)


def main():
    assert T.sha256(T.LT / "PROTOCOL_LEAD2_IMPROVE.md") == (T.HERE / "IMPROVE_SHA256.txt").read_text().strip()
    S = pd.read_csv(T.DATA / "stack_v2.csv", dtype={"province_code": str})
    C = pd.read_csv(T.OUT / "candidates.csv", dtype={"province_code": str})
    E = C[KEY + ["q", "y", "price", "hunger", "pi_H_AB", "PERS_AB", "CLIM_p", "ALWAYS-LOW_p", "C0_price", "C0_p"]].copy()
    origins = sorted(E["t"].unique())
    for c, (cols, mono, hls) in CANDS.items():
        P = run(S, cols, mono, hls, origins)
        E = E.merge(P[KEY + ["pi_P", "cfg"]].rename(columns={"pi_P": f"{c}_price", "cfg": f"{c}_cfg"}), on=KEY, how="left")
        assert E[f"{c}_price"].notna().all(), c
        E[f"{c}_p"] = E["pi_H_AB"] * E[f"{c}_price"]
        print(c, "done", flush=True)
    assert float((E["B0_price"] - E["C0_price"]).abs().max()) < 1e-5, "B0 must reproduce P0H4-U"
    res = {"protocol_sha256": T.sha256(T.LT / "PROTOCOL_LEAD2_IMPROVE.md"), "cands": {}}
    miss7 = E[(E["lead"] == 2) & (E["y"] == 1) & (E["C0_p"] < .5)][KEY]
    for c in CANDS:
        dec = {}
        for k, g in E.groupby("lead"):
            d = F.evaluate(g, f"{c}_p", "PERS_AB")
            dv = g["q"] <= F.DEV_LAST
            d["dev"], d["conf"] = M.cls(g.loc[dv, "y"], g.loc[dv, f"{c}_p"]), M.cls(g.loc[~dv, "y"], g.loc[~dv, f"{c}_p"])
            d["vs_B0"] = M.boot_diff(g["q"], (g[f"{c}_p"] - g["y"]) ** 2, (g["B0_p"] - g["y"]) ** 2)
            d["price_term"] = M.cls(g["price"], g[f"{c}_price"])
            d["new_false_alarms_vs_B0"] = int(((g[f"{c}_p"] >= .5) & (g["B0_p"] < .5) & (g["y"] == 0)).sum())
            d["new_hits_vs_B0"] = int(((g[f"{c}_p"] >= .5) & (g["B0_p"] < .5) & (g["y"] == 1)).sum())
            dec[int(k)] = d
        m7 = miss7.merge(E[KEY + [f"{c}_p"]], on=KEY)
        res["cands"][c] = {"leads": dec, "max_reliable_lead": F.max_reliable(dec), "dev_L1": dec[1]["dev"]["brier"],
                           "dev_L2": dec[2]["dev"]["brier"], "dev_L2_bal": dec[2]["dev"]["balanced_accuracy"],
                           "earlier_misses_caught": int((m7[f"{c}_p"] >= .5).sum()),
                           "hl_used": E.loc[E["lead"] == 2, f"{c}_cfg"].str.split("|").str[1].value_counts().to_dict()}
    b0 = res["cands"]["B0"]
    ok = [c for c in CANDS if c != "B0" and res["cands"][c]["dev_L1"] <= b0["dev_L1"] + 0.005]
    best = min(ok, key=lambda c: (round(res["cands"][c]["dev_L2"], 9), list(CANDS).index(c))) if ok else None
    adopt = bool(best and b0["dev_L2"] - res["cands"][best]["dev_L2"] >= 0.005
                 and res["cands"][best]["dev_L2_bal"] >= b0["dev_L2_bal"] - 1e-12)
    res["selection"] = {"eligible": ok, "best": best, "FINAL": best if adopt else "B0", "adopted": adopt,
                        "dev_L2": {c: res["cands"][c]["dev_L2"] for c in CANDS}, "dev_L1": {c: res["cands"][c]["dev_L1"] for c in CANDS}}
    final = res["selection"]["FINAL"]
    # ------------------------------------------------------------ error patterns (B0 and FINAL)
    lab = pd.read_csv(T.EXP / "FORECAST_RESEARCH_II" / "out" / "labels_rebuilt.csv", dtype={"province_code": str})
    E = E.merge(lab[["province_code", "q", "m_food", "m_gap"]], on=["province_code", "q"], how="left")
    E = E.merge(S[KEY + ["A1_food", "A1_gap"]], on=KEY, how="left")
    E["proj"], E["real"] = E[["A1_food", "A1_gap"]].max(axis=1), E[["m_food", "m_gap"]].max(axis=1)
    pats = []
    for c in dict.fromkeys(["B0", final]):
        g = E[E["lead"] == 2]
        err = g[((g[f"{c}_p"] >= .5).astype(int) != g["y"])]
        for _, r in err.iterrows():
            kind = ("hunger part <= 0.5" if r["pi_H_AB"] <= .5 + 1e-9 else
                    "price rose after issue" if (r["proj"] < 0 <= r["real"]) else
                    "price fell after issue" if (r["proj"] >= 0 > r["real"]) else "model behaviour")
            pats.append({"model": c, "province": r["province_code"], "target": F.qs(int(r["q"])), "type": "FN" if r["y"] == 1 else "FP",
                         "pattern": kind, "borderline": bool(abs(r["real"]) < .5), "pi_H": r["pi_H_AB"], "pi_P": r[f"{c}_price"],
                         "projected": r["proj"], "realised": r["real"]})
    P = pd.DataFrame(pats)
    P.to_csv(T.OUT / "error_patterns.csv", index=False, lineterminator="\n", float_format="%.4g")
    res["error_patterns"] = {c: P[P["model"] == c].groupby(["type", "pattern"]).size().to_dict() for c in P["model"].unique()}
    res["error_patterns"] = {c: {f"{a}|{b}": int(v) for (a, b), v in d.items()} for c, d in res["error_patterns"].items()}
    res["borderline_errors"] = {c: int(P[(P["model"] == c) & P["borderline"]].shape[0]) for c in P["model"].unique()}
    # ------------------------------------------------------------ early-warning check for the 7 misses
    ew = []
    for _, r in miss7.merge(E, on=KEY).iterrows():
        tr = T.train_rows(S, int(r["t"]))
        s = S[(S["t"] == r["t"]) & (S["lead"] == 2) & (S["province_code"] == r["province_code"])].iloc[0]
        flags = []
        for col in [c for c in T.U2 + ANC + DYN if c != "lead"]:
            x = tr[col].dropna()
            if x.nunique() < 3 or pd.isna(s[col]):
                continue
            hi, lo = tr.loc[tr["y"] == 1, col].mean(), tr.loc[tr["y"] == 0, col].mean()
            up = hi > lo
            pct = float((x < s[col]).mean()) if up else float((x > s[col]).mean())
            if pct >= .75:
                flags.append(f"{col} ({pct:.0%})")
        ew.append({"province": r["province_code"], "target": F.qs(int(r["q"])), "warning_indicators": flags})
    res["early_warning_check"] = ew
    E.to_csv(T.OUT / "improve_rows.csv", index=False, lineterminator="\n", float_format="%.6g")
    T.OUT.joinpath("improve.json").write_text(json.dumps(res, indent=1, default=float))
    for c, r in res["cands"].items():
        print(f"{c} maxrel {r['max_reliable_lead']} devL1 {r['dev_L1']:.4f} devL2 {r['dev_L2']:.4f} misses caught {r['earlier_misses_caught']} hl {r['hl_used']}")
        for k in (1, 2, 3):
            d = r["leads"][k]
            m = d["metrics"]
            print(f"   L{k} acc {m['accuracy']:.3f} bal {m['balanced_accuracy']:.3f} P {m['precision']:.2f} R {m['recall']:.2f} "
                  f"TP{m['tp']} FP{m['fp']} FN{m['fn']} TN{m['tn']} Br {m['brier']:.3f} vsB0 {d['vs_B0']['diff']:+.4f}"
                  f"[{d['vs_B0']['ci90'][0]:+.3f},{d['vs_B0']['ci90'][1]:+.3f}] +hits {d['new_hits_vs_B0']} +FA {d['new_false_alarms_vs_B0']} "
                  f"conf acc {d['conf']['accuracy']:.3f} fail {d['failed']}")
    print("selection", res["selection"])
    print("patterns", res["error_patterns"], "borderline", res["borderline_errors"])
    for e in ew:
        print(e)


if __name__ == "__main__":
    main()
