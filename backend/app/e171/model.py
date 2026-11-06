"""
E171 (INFORMED design): level-change LightGBM + E170 calibrated provincial deviation, exactly as docs/e171/PROTOCOL.md
(locked 2026-11-06, commit f26a7279, blob 5d70b029).

    mu = L0(r, origin) + dL_hat(r, T) + Delta_hat(p, T)           (logit HFIAS moderate+severe)

L0: app.e170.model.level_at (unchanged). dL_hat: LGBRes on L_target - L0_row (L0 at the training row's own origin),
E168 FS/HPO/signs/pruning/weights, nested region-CV SSE, no calibration. Delta_hat: E170 Part A (relative persistence +
LightGBM change, raw/linear by inner Brier). sigma^2 = s_Delta(gap)^2 + s_dL(gap)^2 + s_L^2.

    python -m app.e171.model run | eval | seal
"""
from __future__ import annotations

import hashlib
import json
import sys
import warnings
from datetime import datetime, timezone
from itertools import product

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import norm
from sklearn.model_selection import GroupKFold

from app.e147 import evaluate as E7
from app.e147 import features as Fe
from app.e148 import model as M8
from app.e150 import evaluate as Ev
from app.e150 import model as M
from app.e151 import prov as Pv
from app.e152.panel import OUT as O152
from app.e154 import model as E154
from app.e155.test import panel as sun_panel
from app.e156 import leads as LD
from app.e163 import model as C
from app.e164 import auto as A4
from app.e166 import nested_source as N
from app.e166.enns2022 import ORIGIN as O22, T22
from app.e168.lgbm_only import FS, HPO, TRIG, G5, LGBRes
from app.e170.model import Level, add_parts, level_at, pct
from app.fi5.target import qindex
from app.paths import BACKEND_DIR

warnings.filterwarnings("ignore")
D = BACKEND_DIR / "data"
OUT = D / "e171" / "out"


def drop_group(cols, g):
    return [c for c in cols if C.gmap(c) != g and not (g == "employment" and c == "income_growth") and not (g == "poverty" and c == "income_rel")]


def l0_rows(base, fr):
    """Protocol 2: L0 at each row's own origin (rounds released at that origin; FIES rule via level_at)."""
    cache, out, sd = {}, np.zeros(len(fr)), np.zeros(len(fr))
    for idx, (i_, r) in enumerate(zip(fr["i"].astype(int), fr["region"])):
        if i_ not in cache:
            cache[i_] = Level(base, M.released(i_, Pv.ROUNDS))
        L, s, _ = level_at(cache[i_], i_, [r])
        out[idx], sd[idx] = L[0], s[0]
    return out, sd


def select(tr, target, w, folds, base_tr=None):
    """Nested selection over FS x prune x HPO by inner weighted SSE; returns cfg and OOF prediction of `target`."""
    b = np.zeros(len(tr)) if base_tr is None else base_tr
    best = None
    for f, pr, h in product(FS, (False, True), HPO):
        oof = np.zeros(len(tr))
        for i_tr, i_te in folds:
            oof[i_te] = b[i_te] + LGBRes(FS[f], *h, pr).fit(tr.iloc[i_tr].assign(e=target[i_tr] - b[i_tr])).predict(tr.iloc[i_te])
        sse = float(np.sum(w * (target - oof) ** 2))
        if best is None or sse < best[0]:
            best = (sse, (f, pr, h), oof)
    return best[1], best[2]


def run_proc(tr, te, L0_te, sdL_te, ablate=False):
    tr, te = tr.reset_index(drop=True), te.reset_index(drop=True)
    y, q = tr["y_true"].values, tr["q_true"].values
    w = (1.0 / (tr["se_true"] ** 2 + 0.05)).values
    gap = tr["gap_q"].values.astype(float)
    folds = list(GroupKFold(min(5, tr["region"].nunique())).split(tr, groups=tr["region"]))
    Lt, L0_tr = tr["L_target"].values, tr["L0_row"].values
    # ---- level change
    eL = Lt - L0_tr
    (fL, prL, hL), dL_oof = select(tr, eL, w, folds)
    mL = LGBRes(FS[fL], *hL, prL).fit(tr.assign(e=eL))
    dL_te = mL.predict(te)
    sd_dL, _ = A4.scale(eL - dL_oof, gap, te["gap_q"].values)
    # ---- deviation (E170 Part A)
    base_tr, base_te = tr["dev_base"].values, te["dev_base"].values
    dev_true = y - Lt
    (f, pr, h), oof = select(tr, dev_true, w, folds, base_tr)
    mdl = LGBRes(FS[f], *h, pr).fit(tr.assign(e=dev_true - base_tr))
    dev_te = base_te + mdl.predict(te)
    lin = np.zeros(len(tr))
    for i_tr, i_te in folds:
        Z = np.column_stack([np.ones(len(i_tr)), oof[i_tr]]) * np.sqrt(w[i_tr])[:, None]
        ab = np.linalg.lstsq(Z, dev_true[i_tr] * np.sqrt(w[i_tr]), rcond=None)[0]
        lin[i_te] = ab[0] + ab[1] * oof[i_te]
    sd_r, _ = A4.scale(y - (Lt + oof), gap, gap)
    sd_l, _ = A4.scale(y - (Lt + lin), gap, gap)
    inner = {"raw": float(np.mean((norm.cdf((Lt + oof) / sd_r) - q) ** 2)), "linear": float(np.mean((norm.cdf((Lt + lin) / sd_l) - q) ** 2))}
    chosen = min(inner, key=inner.get)
    if chosen == "linear":
        Z = np.column_stack([np.ones(len(tr)), oof]) * np.sqrt(w)[:, None]
        ab = np.linalg.lstsq(Z, dev_true * np.sqrt(w), rcond=None)[0]
        cal, res_in = (lambda d: ab[0] + ab[1] * d), y - (Lt + lin)
    else:
        cal, res_in = (lambda d: d), y - (Lt + oof)
    sd_d, half_d = A4.scale(res_in, gap, te["gap_q"].values)
    sd = np.sqrt(sd_d ** 2 + sd_dL ** 2 + sdL_te ** 2)
    half = half_d * sd / sd_d
    level = L0_te + dL_te
    mu = level + cal(dev_te)
    abl = {}
    if ablate:
        for g in G5:
            dLg = LGBRes(drop_group(FS[fL], g), *hL, prL).fit(tr.assign(e=eL)).predict(te)
            devg = base_te + LGBRes(drop_group(FS[f], g), *h, pr).fit(tr.assign(e=dev_true - base_tr)).predict(te)
            abl[g] = norm.cdf((L0_te + dLg + cal(devg)) / sd)
    tag = f"LEVEL[{fL}|prune={prL}|{hL}] DEV[{f}|prune={pr}|{h}|cal={chosen}]"
    return mu, norm.cdf(mu / sd), half, sd, level, dL_te, tag, abl, inner


def _prep(S, i, rel, tg, origin, lead, H, L, S_P, add_income=False):
    P_ = M.Pipeline(S, i, Pv.ROUNDS, origin)
    if P_.tr.empty:
        return None
    te = Pv.add_inputs(S, M.rows_for(S, tg, [lead], origin))
    tr = Pv.add_inputs(S, P_.tr)
    if add_income:
        te, tr = E154.add_income(te, H), E154.add_income(tr, H)
    te = N.add_sources(te, L, H, S_P).reset_index(drop=True)
    tr = N.add_sources(tr, L, H, S_P).reset_index(drop=True)
    Lv = Level(S.s8.base, rel)
    tr, te = add_parts(tr, Lv, True), add_parts(te, Lv, False)
    tr["L0_row"], _ = l0_rows(S.s8.base, tr)
    L0_te, sdL, src = level_at(Lv, i, te["region"].tolist())
    return tr, te, L0_te, sdL, src


def task(survey, lead, H, L, S_P, mode):
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    S = Pv.Store2(None)
    i = M8.RQ[survey] - lead
    rel = M.released(i, Pv.ROUNDS)
    if mode == "corrupt":
        b = S.s8.base
        z = ~b["survey"].isin(rel)
        b.loc[z, "y"] = np.random.default_rng(7).normal(0, 2, int(z.sum()))
    if not rel:
        return None
    tg = Ev.targets_2021(S) if survey == "ENNS2021" else M8.targets(S.s8, [survey])
    pr = _prep(S, i, rel, tg, Pv.ORIGIN[survey], lead, H, L, S_P)
    if pr is None:
        return None
    tr, te, L0_te, sdL, src = pr
    if mode.startswith("shuf"):
        s_ = int(mode[4:])
        tr, te = C.shuffle_cols(tr, TRIG, s_), C.shuffle_cols(te, TRIG, s_)
    mu, p, half, sd, level, dL, tag, abl, inner = run_proc(tr, te, L0_te, sdL, ablate=(mode == "main" and lead == 1))
    o = te[["key", "survey", "lead", "region", "anchor_round", "dev_base"]].copy()
    o["mode"], o["cfg"], o["L0"], o["dL"], o["level"], o["level_source"] = mode, tag, L0_te, dL, level, src
    o["mu"], o["p"], o["half"], o["sd"] = mu, p, half, sd
    for g, v in abl.items():
        o[f"abl_{g}"] = v
    for k, v in inner.items():
        o[f"inner_brier_{k}"] = v
    o["released"] = "|".join(rel)
    return o


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / "all_rows.csv").exists():
        raise SystemExit("retrospective already run once (protocol 5); not re-running")
    H, L, S_P = E154.income(), pd.read_parquet(O152 / "local_panel.parquet"), sun_panel()
    jobs = [(s, h, "main") for s in ("ENNS2018", "ENNS2019", "ENNS2021") for h in range(1, 9)] + [(s, 1, m) for s in ("ENNS2018", "ENNS2019", "ENNS2021") for m in ("shuf1", "shuf2", "shuf3", "corrupt")]
    R = Parallel(n_jobs=12)(delayed(task)(s, h, H, L, S_P, m) for s, h, m in jobs)
    Al = pd.concat([x for x in R if x is not None], ignore_index=True)
    Al.to_csv(OUT / "all_rows.csv", index=False, lineterminator="\n")
    print("rows", Al.groupby(["mode", "lead"]).size().to_dict())


def new_rows():
    p = D / "e171" / "prospective" / "scored_rows.csv"
    return pd.read_csv(p) if p.exists() else None


def evaluate():
    Al = pd.read_csv(OUT / "all_rows.csv")
    G = pd.read_csv(D / "e158" / "out" / "oof.csv")
    k = ["key", "survey", "lead"]
    NR = new_rows()
    rng = np.random.default_rng(171)
    res = {"protocol": "docs/e171/PROTOCOL.md (blob 5d70b029)", "design": "INFORMED - retrospective is not acceptance evidence", "prospective_rows": 0 if NR is None else int(len(NR)), "leads": {}}
    xs = {}
    for Ld in range(1, 9):
        m = Al[(Al["lead"] == Ld) & (Al["mode"] == "main")]
        x = G[G["lead"] == Ld].merge(m.drop(columns=["region"]), on=k).rename(columns={"mu": "mu_E171", "p": "E171", "half": "half_E171"})
        x["src"] = "R"
        if NR is not None:
            x = pd.concat([x, NR[NR["lead"] == Ld].assign(src="N")], ignore_index=True)
        if len(x) < 10:
            res["leads"][Ld] = {"rows": int(len(x)), "criteria_E156_original": None, "reliable": False}
            continue
        xs[Ld] = x
        ev = LD.evaluate(x, "E171", "E171")["leads"][0]
        crit = dict(ev["criteria"])
        xn = x[x["src"] == "N"]
        c4_new = None
        if len(xn) >= 40:
            sc = Pv.scale_test(xn.reset_index(drop=True), "E171", rng, n=2000)
            c4_new = bool(sc["slope_ci95"][0] <= 1 <= sc["slope_ci95"][1])
        crit_new_rule = {**crit, "C4": c4_new}
        d = E7.diff_ci(x, "E171", "E158", "q_true", rng, n=2000)
        g = x.assign(c=x["mu_E171"] - x.groupby("survey")["mu_E171"].transform("mean"), t=x["y_true"] - x.groupby("survey")["y_true"].transform("mean"))
        per = {s: {"rows": int(len(q_)), "accuracy": round(float(((q_["E171"] >= .5) == (q_["y_high"] == 1)).mean()), 3), "bias_pts": round(float(np.mean(pct(q_["mu_E171"]) - pct(q_["y_true"]))), 2),
                   "level_pct": round(float(pct(q_["level"]).mean()), 1), "observed_pct": round(float(pct(q_["y_true"]).mean()), 1)} for s, q_ in x.groupby("survey")}
        res["leads"][Ld] = {"rows": int(len(x)), "correct": int(((x["E171"] >= .5) == (x["y_high"] == 1)).sum()),
                            **{kk: ev[kk] for kk in ("accuracy", "accuracy_95_low_effective_n", "majority_rule", "precision", "high_recall", "low_recall", "f1", "auc", "brier_soft", "calibration_slope_ci95", "brier_minus_persistence_ci95")},
                            "criteria_E156_original": crit, "reliable_original": bool(all(crit.values())),
                            "criteria_new_rule": crit_new_rule, "reliable_new_rule": bool(all(v is True for v in crit_new_rule.values())),
                            "brier_minus_E158": round(d["diff"], 4), "brier_minus_E158_ci95": [round(z, 4) for z in d["ci95"]],
                            "within_round_slope_supplementary": round(float(np.polyfit(g["c"], g["t"], 1)[0]), 3), "per_round": per, "selected": x.groupby("survey")["cfg"].first().to_dict()}
    for rule in ("original", "new_rule"):
        ml = 0
        for Ld in range(1, 9):
            if res["leads"][Ld].get(f"reliable_{rule}") and Ld == ml + 1:
                ml = Ld
            else:
                break
        res[f"maximum_reliable_lead_{rule}"] = ml
    x = xs[1][xs[1]["src"] == "R"]
    for mo in ("shuf1", "shuf2", "shuf3", "corrupt"):
        x = x.merge(Al[(Al["lead"] == 1) & (Al["mode"] == mo)][k + ["mu", "p"]].rename(columns={"mu": f"mu_{mo}", "p": mo}), on=k)
    x["SHUF"] = x[["shuf1", "shuf2", "shuf3"]].mean(axis=1)
    v = E7.diff_ci(x, "E171", "SHUF", "q_true", rng, n=2000)
    res["shuffle"] = {"brier_shuffled": round(float(np.mean((x["SHUF"] - x["q_true"]) ** 2)), 4), "E171_minus_shuffled": round(v["diff"], 4), "ci95": [round(z, 4) for z in v["ci95"]]}
    res["leakage_max_abs_change"] = float(np.max(np.abs(x["mu_E171"] - x["mu_corrupt"])))
    res["ablation"] = {}
    for g_ in G5:
        dd = E7.diff_ci(x, "E171", f"abl_{g_}", "q_true", rng, n=2000)
        res["ablation"][g_] = {"E171_minus_without": round(dd["diff"], 4), "ci95": [round(z, 4) for z in dd["ci95"]], "accuracy_without": round(float(((x[f"abl_{g_}"] >= .5) == (x["y_high"] == 1)).mean()), 3)}
    ctrl = {"leakage": res["leakage_max_abs_change"] < 1e-9, "real_not_worse_than_shuffled": res["shuffle"]["ci95"][1] <= 0.005}
    res["controls"] = ctrl
    res["decision"] = ("ACCEPTED" if res["prospective_rows"] > 0 and res["leads"][1]["reliable_original"] and all(ctrl.values()) else "NOT ACCEPTED")
    res["note"] = "no prospective rows yet: the INFORMED retrospective cannot be acceptance evidence (protocol header); original E156 rule governs until adviser confirms the new rule"
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str), newline="\n")
    print(json.dumps({kk: res[kk] for kk in ("decision", "controls", "maximum_reliable_lead_original", "maximum_reliable_lead_new_rule", "shuffle", "leakage_max_abs_change", "ablation")}, indent=1, default=str))
    for Ld in range(1, 9):
        r = res["leads"][Ld]
        if r.get("criteria_E156_original"):
            print(Ld, r["rows"], r["correct"], r["accuracy"], r["accuracy_95_low_effective_n"], r["majority_rule"], "brier", r["brier_soft"], "dE158", r["brier_minus_E158"], r["brier_minus_E158_ci95"], "C4", r["calibration_slope_ci95"], "within", r["within_round_slope_supplementary"],
                  {c: int(b) for c, b in r["criteria_E156_original"].items()}, {s: (v_["accuracy"], v_["bias_pts"], v_["level_pct"], v_["observed_pct"]) for s, v_ in r["per_round"].items()})


def _seal_task(kind, lead, H, L, S_P):
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    if kind == "ENNS2022":
        S, T, origin = Pv.Store2(None), T22, O22
    else:
        S, T, origin = Pv.Store2(Pv.target_rows(with_2021=True)), qindex("2027-Q1"), "F"
    i = T - lead
    rel = M.released(i, Pv.ROUNDS)
    tg = S.base.drop_duplicates("key")[["key", "province", "region", "island", "sws_area"]].assign(survey=kind, T=T)
    tr, te, L0_te, sdL, src = _prep(S, i, rel, tg, origin, lead, H, L, S_P, add_income=True)
    mu, p, half, sd, level, dL, tag, _, _ = run_proc(tr, te, L0_te, sdL)
    o = te[["key", "province", "region", "lead", "gap_q", "anchor_round"]].copy()
    o["score"], o["p_high"], o["low90"], o["high90"] = pct(mu).round(2), np.round(p, 4), pct(mu - half).round(2), pct(mu + half).round(2)
    o["class"] = np.where(p >= .5, "HIGH", "LOW")
    o["mu"], o["sd"], o["L0_pct"], o["level_pct"], o["level_source"], o["config"], o["released"] = mu, sd, pct(L0_te).round(2), pct(level).round(2), src, tag, "|".join(rel)
    return o


def seal():
    H, L, S_P = E154.income(), pd.read_parquet(O152 / "local_panel.parquet"), sun_panel()
    for kind, leads, name in (("ENNS2022", (1, 2), "sealed_enns2022.json"), ("LIVE", (1,), "sealed_2027-Q1.json")):
        sp = OUT / name
        if sp.exists():
            print("already sealed", name, hashlib.sha256(sp.read_bytes()).hexdigest())
            continue
        R = pd.concat([_seal_task(kind, h, H, L, S_P) for h in leads], ignore_index=True)
        doc = {"sealed_utc": datetime.now(timezone.utc).isoformat(), "model": "E171 level-change + calibrated deviation LightGBM (protocol blob 5d70b029), INFORMED design",
               "target": "ENNS 2022 provincial HFIAS moderate+severe, ref 2022-Q3" if kind == "ENNS2022" else "provincial HFIAS moderate+severe, 2027-Q1 (issue 2026-Q4)",
               "rule": "HIGH = p_high >= 0.5; scored only on provincial HFIAS moderate_or_severe outcomes", "forecasts": R.round(6).to_dict("records")}
        sp.write_text(json.dumps(doc, indent=1, default=str), newline="\n")
        print("sealed", name, len(R), "rows sha256", hashlib.sha256(sp.read_bytes()).hexdigest())


if __name__ == "__main__":
    {"run": run, "eval": evaluate, "seal": seal}[sys.argv[1]]()
