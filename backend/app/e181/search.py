"""
E181 (docs/e181/PROTOCOL.md): EXPLORATORY search. Every E179 augmentation setting (and "none" = E168) is fitted on each
outer job at seeds 17901-17905 and averaged over seeds; the variants are ranked on the 72 real outer rows by a balanced
rule (HIGH recall >= E168's at both leads; mean balanced accuracy; then Brier). A chronological select-then-test check
(2018 -> 2019, 2018+2019 -> 2021) gives the honest estimate of what such a search is worth.

    python -m app.e181.search run      -> data/e181/out/
    python -m app.e181.search report   re-score data/e181/out/variant_rows.csv
"""
from __future__ import annotations

import sys
import time
import warnings
from itertools import product

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.model_selection import GroupKFold

from app.e168 import lgbm_only as E
from app.e178 import common as K
from app.e178 import retrain as RT
from app.e179 import tuned as T

warnings.filterwarnings("ignore")
OUT = K.D / "e181" / "out"
PROTOCOL = K.BACKEND_DIR.parent / "docs" / "e181" / "PROTOCOL.md"
KEYS = RT.KEYS


def _frames(survey, lead, H, L, S_P):
    tr, te, AN = RT.build(survey, lead, H, L, S_P, "main")
    tr = tr.reset_index(drop=True)
    folds = list(GroupKFold(min(5, tr["region"].nunique())).split(tr, groups=tr["region"]))
    return tr, te.reset_index(drop=True), AN, folds


def stage_a(survey, lead, H, L, S_P):
    """E168's selection on real rows (lgbm_only.run_proc's loop, as E179 Stage A)."""
    tr, te, AN, folds = _frames(survey, lead, H, L, S_P)
    y, w = tr["y_true"].values, (1.0 / (tr["se_true"] ** 2 + 0.05)).values
    best = None
    for a, f, pr, h in product(E.ANCH, E.FS, (False, True), E.HPO):
        atr = AN[a][0]
        oof = np.zeros(len(tr))
        for i_tr, i_te in folds:
            oof[i_te] = atr[i_te] + E.LGBRes(E.FS[f], *h, pr).fit(tr.iloc[i_tr].assign(e=y[i_tr] - atr[i_tr])).predict(tr.iloc[i_te])
        sse = float(np.sum(w * (y - oof) ** 2))
        if best is None or sse < best["sse"]:
            best = {"sse": sse, "cfg": (a, f, pr, h), "oof": oof}
    return {"survey": survey, "lead": lead, "cfg": best["cfg"], "oof": best["oof"]}


def variants(survey, lead, H, L, S_P, cfg, base_oof, seed):
    """Every setting's outer forecast for one job and seed (calibration chosen on real inner OOF, as E168)."""
    tr, te, AN, folds = _frames(survey, lead, H, L, S_P)
    job = RT.job_id(survey, lead, "main")
    y, q, w = tr["y_true"].values, tr["q_true"].values, (1.0 / (tr["se_true"] ** 2 + 0.05)).values
    gap = tr["gap_q"].values.astype(float)
    a, f, pr, h = cfg
    atr, ate = AN[a]
    an_all = {x: np.asarray(AN[x][0], float) for x in E.ANCH}
    out, cache = [], {}
    for s in T.SETTINGS:
        if s is None:
            if seed != T.SEEDS[0]:
                continue
            oof = base_oof
            mdl = E.LGBRes(E.FS[f], *h, pr).fit(tr.assign(e=y - atr))
        else:
            oof = np.zeros(len(tr))
            for fi, (i_tr, i_te) in enumerate(folds):
                k = (fi, s[0], s[1], s[3], s[4])
                if k not in cache:
                    real = tr.iloc[i_tr].reset_index(drop=True)
                    cache[k] = T._augment(real, {x: v[i_tr] for x, v in an_all.items()}, s, seed, job, fi)[:2]
                syn, sa = cache[k]
                m = RT.LGBResAug(E.FS[f], *h, pr)
                m.syn_weight = s[2]
                m.fit(tr.iloc[i_tr].assign(e=y[i_tr] - atr[i_tr]), syn.assign(e=syn["y_true"].values - sa[a]))
                oof[i_te] = atr[i_te] + m.predict(tr.iloc[i_te])
            kf = ("final", s[0], s[1], s[3], s[4])
            if kf not in cache:
                cache[kf] = T._augment(tr, an_all, s, seed, job, "final")[:2]
            syn, sa = cache[kf]
            mdl = RT.LGBResAug(E.FS[f], *h, pr)
            mdl.syn_weight = s[2]
            mdl.fit(tr.assign(e=y - atr), syn.assign(e=syn["y_true"].values - sa[a]))
        mu = ate + mdl.predict(te)
        P, chosen, _ = RT._calibrate(tr, te, folds, oof, mu, y, q, w, gap)
        o = te[KEYS].copy()
        o["seed"], o["variant"], o["cal"] = seed, T.setting_name(s), chosen
        o["mu"], o["p"], o["half"] = P[chosen]
        out.append(o)
    return pd.concat(out, ignore_index=True)


# ---------------------------------------------------------------------------------------------------------- scoring
def _truth():
    G = pd.read_csv(K.D / "e158" / "out" / "oof.csv")
    cols = KEYS + [c for c in ("y_high", "q_true", "y_true", "region", "island", "province") if c in G.columns]
    return G[G["lead"].isin([1, 2])][cols]


def score(rows: pd.DataFrame, surveys=None) -> pd.DataFrame:
    """Accuracy, balanced accuracy, HIGH/LOW recall and Brier per variant and lead (real rows only)."""
    x = rows.merge(_truth(), on=KEYS)
    if surveys is not None:
        x = x[x["survey"].isin(surveys)]
    hi, pr = x["y_high"] == 1, x["p"] >= .5
    x = x.assign(ok=(pr == hi), tp=(pr & hi), tn=(~pr & ~hi), pos=hi, neg=~hi, sq=(x["p"] - x["q_true"]) ** 2)
    g = x.groupby(["variant", "lead"]).agg(n=("ok", "size"), acc=("ok", "mean"), tp=("tp", "sum"), pos=("pos", "sum"),
                                           tn=("tn", "sum"), neg=("neg", "sum"), brier=("sq", "mean")).reset_index()
    g["high_recall"], g["low_recall"] = g["tp"] / g["pos"].clip(lower=1), g["tn"] / g["neg"].clip(lower=1)
    g["bal_acc"] = (g["high_recall"] + g["low_recall"]) / 2
    return g


def select(sc: pd.DataFrame, recall_floor: dict[int, float]) -> tuple[str, pd.DataFrame]:
    """The balanced rule: HIGH recall >= E168's at both leads; max mean balanced accuracy; then min mean Brier; then grid order."""
    w = sc.pivot_table(index="variant", columns="lead", values=["high_recall", "bal_acc", "brier", "acc"])
    w.columns = [f"{a}_L{b}" for a, b in w.columns]
    w["eligible"] = (w["high_recall_L1"] >= recall_floor[1] - 1e-12) & (w["high_recall_L2"] >= recall_floor[2] - 1e-12)
    w["bal_acc_mean"] = (w["bal_acc_L1"] + w["bal_acc_L2"]) / 2
    w["brier_mean"] = (w["brier_L1"] + w["brier_L2"]) / 2
    order = {T.setting_name(s): i for i, s in enumerate(T.SETTINGS)}
    w["grid"] = [order[v] for v in w.index]
    w = w.sort_values(["eligible", "bal_acc_mean", "brier_mean", "grid"], ascending=[False, False, True, True])
    return w.index[0], w


def evaluate(log=None) -> dict:
    log = log or K.RunLog(OUT / "run_log.jsonl", fresh=False)
    V = pd.read_csv(OUT / "variant_rows.csv", float_precision="round_trip")
    ens = V.groupby(KEYS + ["variant"])[["mu", "p", "half"]].mean().reset_index()
    nseed = V.groupby(KEYS + ["variant"]).size().reset_index(name="n")
    assert ((nseed["variant"] == "none") | (nseed["n"] == len(T.SEEDS))).all()
    sc = score(ens)
    base = sc[sc["variant"] == "none"].set_index("lead")
    floor = {1: float(base.at[1, "high_recall"]), 2: float(base.at[2, "high_recall"])}
    best, table = select(sc, floor)
    table.round(4).to_csv(OUT / "variant_scores.csv", lineterminator="\n")
    # full metrics of the winner vs E168, with the shared code
    Al = ens[ens["variant"].isin([best, "none"])].assign(mode="main", seed=0, arm=lambda d: np.where(d["variant"] == best, "E181", "E168_rerun"),
                                                         cfg=lambda d: d["variant"])
    res = {"label": "EXPLORATORY: the winner was chosen on the same 72 outer rows it is scored on; optimistic by construction",
           "n_variants": int(ens["variant"].nunique()), "n_eligible": int(table["eligible"].sum()), "winner": best,
           "e168_recall_floor": floor, "top10": table.head(10).round(4).reset_index().to_dict("records")}
    full = {}
    for Ld in (1, 2):
        x = RT._frame(Al.assign(lead=Al["lead"]), Ld, 0, ["E181"])
        rng = np.random.default_rng(181)
        full[Ld] = {"E181": RT._metrics(x, "E181", rng), "E168": RT._metrics(x, "E168", rng),
                    "brier_E181_minus_E168": E.E7.diff_ci(x, "E181", "E168", "q_true", np.random.default_rng(181), n=2000),
                    "mcnemar": RT._mcnemar(x, "E181", "E168")}
    res["winner_metrics"] = {Ld: {"E181": {k: v[k] for k in ("accuracy", "balanced_accuracy", "high_recall", "high_precision", "low_recall", "f1", "auc", "brier", "confusion")},
                                  "E168": {k: v[k] for k in ("accuracy", "balanced_accuracy", "high_recall", "high_precision", "low_recall", "f1", "auc", "brier", "confusion")},
                                  "brier_diff": {"diff": round(full[Ld]["brier_E181_minus_E168"]["diff"], 4), "ci95": [round(z, 4) for z in full[Ld]["brier_E181_minus_E168"]["ci95"]]},
                                  "mcnemar": full[Ld]["mcnemar"]} for Ld in (1, 2)}
    # chronological select-then-test (the honest estimate)
    chrono = []
    for train_s, test_s in ((["ENNS2018"], "ENNS2019"), (["ENNS2018", "ENNS2019"], "ENNS2021")):
        s_tr = score(ens, train_s)
        b_tr = s_tr[s_tr["variant"] == "none"].set_index("lead")
        pick, _ = select(s_tr, {1: float(b_tr.at[1, "high_recall"]), 2: float(b_tr.at[2, "high_recall"])})
        chrono.append({"select_on": train_s, "test_on": test_s, "picked": pick})
    test_rows = pd.concat([ens[(ens["survey"] == c["test_on"]) & (ens["variant"] == c["picked"])].assign(variant="SELECT_THEN_TEST") for c in chrono]
                          + [ens[ens["survey"].isin([c["test_on"] for c in chrono]) & (ens["variant"] == "none")]])
    ct = score(test_rows)
    res["chronological_check"] = {"picks": chrono, "scores_on_2019_and_2021": ct.round(4).to_dict("records")}
    K.dump_json(res, OUT / "results.json")
    log("evaluated", winner=best, n_eligible=res["n_eligible"], chrono=chrono)
    K.write_hashes([OUT / n for n in ("variant_rows.csv", "variant_scores.csv", "results.json")] + [OUT / "run_log.jsonl"], OUT / "hashes.json")
    print("variants:", res["n_variants"], "eligible:", res["n_eligible"], "winner:", best)
    print(table.head(10)[["eligible", "acc_L1", "acc_L2", "bal_acc_L1", "bal_acc_L2", "high_recall_L1", "high_recall_L2", "brier_L1", "brier_L2"]].round(4).to_string())
    print("E168 (none):", table.loc["none", ["acc_L1", "acc_L2", "bal_acc_L1", "bal_acc_L2", "high_recall_L1", "high_recall_L2", "brier_L1", "brier_L2"]].round(4).to_dict())
    for Ld in (1, 2):
        print("Lead", Ld, res["winner_metrics"][Ld])
    print("chronological picks:", chrono)
    print(ct.round(4).to_string())
    return res


def run() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    log = K.RunLog(OUT / "run_log.jsonl")
    RT._check_inputs(log)
    log("start", protocol_sha256=K.sha256(PROTOCOL), n_settings=len(T.SETTINGS), seeds=T.SEEDS)
    H, L, S_P = K.pipeline_inputs()
    t0 = time.time()
    A_ = Parallel(n_jobs=6)(delayed(stage_a)(s, l, H, L, S_P) for s, l in RT.MAIN)
    log("stage_a", seconds=round(time.time() - t0, 1), configs={f"{a['survey']}|L{a['lead']}": str(a["cfg"]) for a in A_})
    jobs = [(a, sd) for a in A_ for sd in T.SEEDS]
    R = Parallel(n_jobs=RT.N_JOBS, verbose=5)(delayed(variants)(a["survey"], a["lead"], H, L, S_P, a["cfg"], a["oof"], sd) for a, sd in jobs)
    pd.concat(R, ignore_index=True).to_csv(OUT / "variant_rows.csv", index=False, lineterminator="\n")
    log("fitted", seconds=round(time.time() - t0, 1))
    evaluate(log)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"run": run, "report": evaluate}.get(cmd, lambda: sys.exit("usage: python -m app.e181.search run | report"))()
