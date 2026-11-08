"""
E170 two-part LightGBM system, implemented exactly as docs/e170/PROTOCOL.md (locked 2026-11-06, commit 9526e8bc).

    mu(p, r, T) = L(r, T) + Delta(p, T)          (logit of HFIAS moderate+severe)

Part B, level L: the newer of (i) the newest released provincial HFIAS round (region mean logit if >= 2 provinces measured,
else that round's national mean logit; level SD 0), or (ii) the newest published regional FIES bridged with
logit H = 0.25 + 0.955 logit F (level SD^2 = 0.13^2 + se_F^2).
Part A, deviation: relative-persistence baseline (province's last measured deviation from its round level) + constrained
LightGBM change (E168 grid, signs, weights, pruning, region-grouped nested selection); raw/linear layer by inner Brier.

    python -m app.e170.model run        retrospective + controls (once) -> data/e170/out/all_rows.csv
    python -m app.e170.model eval       gates on the pooled set           -> data/e170/out/results.json
    python -m app.e170.model seal       ENNS 2022 + 2027-Q1 seals          -> data/e170/out/sealed_*.json
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
from app.e168.lgbm_only import FS, HPO, TRIG, G5, LGBRes
from app.fi5.target import qindex
from app.paths import BACKEND_DIR

warnings.filterwarnings("ignore")
D = BACKEND_DIR / "data"
OUT = D / "e170" / "out"
BRIDGE_A, BRIDGE_B, DRIFT_SD, SE_F_DEFAULT = 0.25, 0.955, 0.13, 0.10
FIES_REGION = {"Region IV-A": "CALABARZON", "Region I": "Ilocos", "Region II": "Cagayan Valley", "Region III": "Central Luzon", "MIMAROPA Region": "MIMAROPA",
               "Region V": "Bicol", "Region VI": "Western Visayas", "Region VII": "Central Visayas", "Region VIII": "Eastern Visayas", "Region IX": "Zamboanga Peninsula",
               "Region X": "Northern Mindanao", "Region XI": "Davao", "Region XII": "SOCCSKSARGEN", "Region XIII": "Caraga",
               "Cordillera Administrative Region (CAR)": "CAR", "Bangsamoro Autonomous Region in Muslim Mindanao (BARMM)": "ARMM"}
RQINV = {v: k for k, v in M8.RQ.items()}
FIELD_YEAR = {s: int(s[-4:]) for s in M8.RQ}
lg = lambda p: np.log(np.asarray(p, float) / (1 - np.asarray(p, float)))
pct = lambda y: 100 / (1 + np.exp(-np.asarray(y, float)))


# ---------------------------------------------------------------- Part B: level
class Level:
    """Round levels from provincial HFIAS rows of the given (released) rounds."""

    def __init__(self, base, rounds):
        b = base[base["survey"].isin(rounds)]
        self.rounds = list(rounds)
        self.nat = b.groupby("survey")["y"].mean().to_dict()
        g = b.groupby(["survey", "region"])["y"].agg(["mean", "size"])
        self.reg = {k: float(v["mean"]) for k, v in g.iterrows() if v["size"] >= 2}

    def round_level(self, survey, region):
        return self.reg.get((survey, region), self.nat[survey])

    def newest(self):
        return max(self.rounds, key=lambda s: M8.RQ[s])


def fies_regional(t_index):
    """Newest regional FIES published at or before quarter index t: {region: (fieldwork_year, logit H bridged, sd_L)}."""
    f = pd.read_csv(D / "fi_labels" / "clean" / "published_fies_psa_sdg212.csv")
    f = f[(f["level"] == "region") & (f["category"] == "moderate_or_severe_food_insecurity")]
    out = {}
    for _, r in f.iterrows():
        usable = qindex(f"{int(r['year']) + 2}-Q1")            # publication date undocumented in repo -> Q1 of second year after fieldwork
        reg = FIES_REGION.get(r["geography"])
        if reg is None or usable > t_index:
            continue
        p = r["percent"] / 100
        se = (lg(r["ci95_high"] / 100) - lg(r["ci95_low"] / 100)) / (2 * 1.96) if pd.notna(r.get("ci95_low")) and pd.notna(r.get("ci95_high")) else SE_F_DEFAULT
        if reg not in out or r["year"] > out[reg][0]:
            out[reg] = (int(r["year"]), float(BRIDGE_A + BRIDGE_B * lg(p)), float(np.sqrt(DRIFT_SD ** 2 + se ** 2)))
    return out


def level_at(Lv, t_index, regions):
    """Protocol 2, Part B: level and level SD at origin for each region; returns (L, sd_L, source)."""
    s = Lv.newest()
    fy = FIELD_YEAR[s]
    fies = fies_regional(t_index)
    L, sd, src = [], [], []
    for r in regions:
        if r in fies and fies[r][0] > fy:
            L.append(fies[r][1]); sd.append(fies[r][2]); src.append(f"FIES{fies[r][0]}_bridged")
        else:
            L.append(Lv.round_level(s, r)); sd.append(0.0); src.append(f"HFIAS_{s}")
    return np.array(L), np.array(sd), src


# ---------------------------------------------------------------- Part A: deviation
def add_parts(fr, Lv, level_target=True):
    """Adds anchor-round level and baseline deviation; for training rows also the realised target-round level."""
    fr = fr.copy()
    ar = fr["rq_anchor"].map(RQINV)
    assert ar.notna().all(), "anchor round not in RQ"
    fr["anchor_round"] = ar
    fr["L_anchor"] = [Lv.round_level(s, r) for s, r in zip(ar, fr["region"])]
    fr["dev_base"] = fr["y_anchor"] - fr["L_anchor"]
    if level_target:
        fr["L_target"] = [Lv.round_level(s, r) for s, r in zip(fr["survey"], fr["region"])]
    return fr


def run_proc(tr, te, L_te, sdL_te, ablate=False):
    tr = tr.reset_index(drop=True)
    y, q = tr["y_true"].values, tr["q_true"].values
    w = (1.0 / (tr["se_true"] ** 2 + 0.05)).values
    gap = tr["gap_q"].values.astype(float)
    Lt, base_tr, base_te = tr["L_target"].values, tr["dev_base"].values, te["dev_base"].values
    dev_true = y - Lt
    folds = list(GroupKFold(min(5, tr["region"].nunique())).split(tr, groups=tr["region"]))
    best = None
    for f, pr, h in product(FS, (False, True), HPO):
        oof = np.zeros(len(tr))
        for i_tr, i_te in folds:
            oof[i_te] = base_tr[i_te] + LGBRes(FS[f], *h, pr).fit(tr.iloc[i_tr].assign(e=dev_true[i_tr] - base_tr[i_tr])).predict(tr.iloc[i_te])
        sse = float(np.sum(w * (dev_true - oof) ** 2))
        if best is None or sse < best["sse"]:
            best = {"sse": sse, "cfg": (f, pr, h), "oof": oof}
    f, pr, h = best["cfg"]
    oof = best["oof"]
    mdl = LGBRes(FS[f], *h, pr).fit(tr.assign(e=dev_true - base_tr))
    dev_te = base_te + mdl.predict(te)
    # calibration layer on the deviation: raw vs linear (cross-fitted), chosen by inner Brier
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
        cal = lambda d: ab[0] + ab[1] * d
        res_in = y - (Lt + lin)
    else:
        cal = lambda d: d
        res_in = y - (Lt + oof)
    sd_d, half_d = A4.scale(res_in, gap, te["gap_q"].values)
    sd = np.sqrt(sd_d ** 2 + sdL_te ** 2)
    half = half_d * sd / sd_d
    mu = L_te + cal(dev_te)
    abl = {}
    if ablate:
        for g in G5:
            cols = [c for c in FS[f] if C.gmap(c) != g and not (g == "employment" and c == "income_growth") and not (g == "poverty" and c == "income_rel")]
            m2 = LGBRes(cols, *h, pr).fit(tr.assign(e=dev_true - base_tr))
            abl[g] = norm.cdf((L_te + cal(base_te + m2.predict(te))) / sd)
    tag = f"{f}|prune={pr}|leaves={h[0]},minchild={h[1]},lambda={h[2]},trees={h[3]}|cal={chosen}"
    return mu, norm.cdf(mu / sd), half, sd, tag, abl, inner, len(mdl.use_)


# ---------------------------------------------------------------- retrospective task
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
    P_ = M.Pipeline(S, i, Pv.ROUNDS, Pv.ORIGIN[survey])
    if P_.tr.empty:
        return None
    tg = Ev.targets_2021(S) if survey == "ENNS2021" else M8.targets(S.s8, [survey])
    te = N.add_sources(Pv.add_inputs(S, M.rows_for(S, tg, [lead], Pv.ORIGIN[survey])), L, H, S_P)
    tr = N.add_sources(Pv.add_inputs(S, P_.tr), L, H, S_P)
    Lv = Level(S.s8.base, rel)
    tr, te = add_parts(tr, Lv, True), add_parts(te, Lv, False)
    if mode.startswith("shuf"):
        s_ = int(mode[4:])
        tr, te = C.shuffle_cols(tr, TRIG, s_), C.shuffle_cols(te, TRIG, s_)
    L_te, sdL, src = level_at(Lv, i, te["region"].tolist())
    mu, p, half, sd, tag, abl, inner, nf = run_proc(tr, te, L_te, sdL, ablate=(mode == "main" and lead == 1))
    o = te[["key", "survey", "lead", "region", "anchor_round", "dev_base"]].copy()
    o["mode"], o["cfg"], o["n_features"], o["level"], o["level_sd"], o["level_source"] = mode, tag, nf, L_te, sdL, src
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
        raise SystemExit("retrospective already run once (protocol 3.1); not re-running")
    H, L, S_P = E154.income(), pd.read_parquet(O152 / "local_panel.parquet"), sun_panel()
    jobs = [(s, h, "main") for s in ("ENNS2018", "ENNS2019", "ENNS2021") for h in range(1, 9)] + [(s, 1, m) for s in ("ENNS2018", "ENNS2019", "ENNS2021") for m in ("shuf1", "shuf2", "shuf3", "corrupt")]
    R = Parallel(n_jobs=12)(delayed(task)(s, h, H, L, S_P, m) for s, h, m in jobs)
    Al = pd.concat([x for x in R if x is not None], ignore_index=True)
    Al.to_csv(OUT / "all_rows.csv", index=False, lineterminator="\n")
    print("rows", Al.groupby(["mode", "lead"]).size().to_dict())


# ---------------------------------------------------------------- evaluation (pooled set)
def new_rows():
    """Qualifying prospective rows (protocol 3.2): none until FNRI publishes provincial HFIAS after the seal date."""
    p = D / "e170" / "prospective" / "scored_rows.csv"
    return pd.read_csv(p) if p.exists() else None


def evaluate():
    Al = pd.read_csv(OUT / "all_rows.csv")
    G = pd.read_csv(D / "e158" / "out" / "oof.csv")
    k = ["key", "survey", "lead"]
    NR = new_rows()
    rng = np.random.default_rng(170)
    res = {"protocol": "docs/e170/PROTOCOL.md (blob ef63fe67)", "prospective_rows": 0 if NR is None else int(len(NR)), "leads": {}}
    xs = {}
    for Ld in range(1, 9):
        m = Al[(Al["lead"] == Ld) & (Al["mode"] == "main")]
        x = G[G["lead"] == Ld].merge(m.drop(columns=["region"]), on=k).rename(columns={"mu": "mu_E170", "p": "E170", "half": "half_E170"})
        if NR is not None:
            x = pd.concat([x, NR[NR["lead"] == Ld]], ignore_index=True)
        if len(x) < 10:
            res["leads"][Ld] = {"rows": int(len(x)), "criteria": None, "reliable": False}
            continue
        xs[Ld] = x
        ev = LD.evaluate(x, "E170", "E170")["leads"][0]
        b170, b158 = float(np.mean((x["E170"] - x["q_true"]) ** 2)), float(np.mean((x["E158"] - x["q_true"]) ** 2))
        d = E7.diff_ci(x, "E170", "E158", "q_true", rng, n=2000)
        g = x.assign(c=x["mu_E170"] - x.groupby("survey")["mu_E170"].transform("mean"), t=x["y_true"] - x.groupby("survey")["y_true"].transform("mean"))
        per = {s: {"rows": int(len(q_)), "accuracy": round(float(((q_["E170"] >= .5) == (q_["y_high"] == 1)).mean()), 3), "bias_pts": round(float(np.mean(pct(q_["mu_E170"]) - pct(q_["y_true"]))), 2),
                   "level_source": q_["level_source"].iloc[0] if "level_source" in q_ else None} for s, q_ in x.groupby("survey")}
        res["leads"][Ld] = {"rows": int(len(x)), "correct": int(((x["E170"] >= .5) == (x["y_high"] == 1)).sum()), **{kk: ev[kk] for kk in ("accuracy", "accuracy_95_low_effective_n", "majority_rule", "precision", "high_recall", "low_recall", "f1", "auc", "brier_soft", "calibration_slope_ci95", "brier_minus_persistence_ci95")},
                            "criteria": ev["criteria"], "reliable": ev["reliable"], "brier_E158": round(b158, 4), "brier_minus_E158": round(d["diff"], 4), "brier_minus_E158_ci95": [round(z, 4) for z in d["ci95"]],
                            "within_round_slope_supplementary": round(float(np.polyfit(g["c"], g["t"], 1)[0]), 3), "per_round": per, "selected": x.groupby("survey")["cfg"].first().to_dict()}
    ml = 0
    for Ld in range(1, 9):
        if res["leads"][Ld].get("reliable") and Ld == ml + 1:
            ml = Ld
        else:
            break
    res["maximum_reliable_lead"] = ml
    # controls at Lead 1 (retrospective rows)
    x = xs[1]
    for mo in ("shuf1", "shuf2", "shuf3", "corrupt"):
        x = x.merge(Al[(Al["lead"] == 1) & (Al["mode"] == mo)][k + ["mu", "p"]].rename(columns={"mu": f"mu_{mo}", "p": mo}), on=k)
    x["SHUF"] = x[["shuf1", "shuf2", "shuf3"]].mean(axis=1)
    v = E7.diff_ci(x, "E170", "SHUF", "q_true", rng, n=2000)
    res["shuffle"] = {"brier_shuffled": round(float(np.mean((x["SHUF"] - x["q_true"]) ** 2)), 4), "E170_minus_shuffled": round(v["diff"], 4), "ci95": [round(z, 4) for z in v["ci95"]]}
    res["leakage_max_abs_change"] = float(np.max(np.abs(x["mu_E170"] - x["mu_corrupt"])))
    res["ablation"] = {}
    for g_ in G5:
        dd = E7.diff_ci(x, "E170", f"abl_{g_}", "q_true", rng, n=2000)
        res["ablation"][g_] = {"E170_minus_without": round(dd["diff"], 4), "ci95": [round(z, 4) for z in dd["ci95"]], "accuracy_without": round(float(((x[f"abl_{g_}"] >= .5) == (x["y_high"] == 1)).mean()), 3)}
    acc = {"C1_C6_lead1_pooled": bool(res["leads"][1]["reliable"]), "leakage": res["leakage_max_abs_change"] < 1e-9, "real_not_worse_than_shuffled": res["shuffle"]["ci95"][1] <= 0.005}
    res["acceptance"] = acc
    res["decision"] = "ACCEPTED" if all(acc.values()) else "NOT ACCEPTED"
    res["note"] = "pooled set = retrospective rows only until qualifying provincial HFIAS outcomes are released (protocol 3.2)" if res["prospective_rows"] == 0 else "pooled retrospective + prospective"
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str), newline="\n")
    print(json.dumps({kk: res[kk] for kk in ("decision", "acceptance", "maximum_reliable_lead", "shuffle", "leakage_max_abs_change", "ablation", "note")}, indent=1, default=str))
    for Ld in range(1, 9):
        r = res["leads"][Ld]
        if r.get("criteria"):
            print(Ld, r["rows"], r["correct"], r["accuracy"], r["accuracy_95_low_effective_n"], r["majority_rule"], "brier", r["brier_soft"], "E158", r["brier_E158"], r["brier_minus_E158_ci95"], "C4", r["calibration_slope_ci95"], "within", r["within_round_slope_supplementary"], {c: int(b) for c, b in r["criteria"].items()}, {s: (v_["accuracy"], v_["bias_pts"]) for s, v_ in r["per_round"].items()})


# ---------------------------------------------------------------- seals
def _seal_task(kind, lead, H, L, S_P):
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    if kind == "ENNS2022":
        S = Pv.Store2(None)
        T = qindex("2022-Q3")
        origin = "O3"
    else:
        S = Pv.Store2(Pv.target_rows(with_2021=True))
        T = qindex("2027-Q1")
        origin = "F"
    i = T - lead
    rel = M.released(i, Pv.ROUNDS)
    P_ = M.Pipeline(S, i, Pv.ROUNDS, origin)
    b = S.base.drop_duplicates("key")[["key", "province", "region", "island", "sws_area"]]
    tg = b.assign(survey=kind, T=T)
    te = N.add_sources(E154.add_income(Pv.add_inputs(S, M.rows_for(S, tg, [lead], origin)), H), L, H, S_P).reset_index(drop=True)
    tr = N.add_sources(E154.add_income(Pv.add_inputs(S, P_.tr), H), L, H, S_P).reset_index(drop=True)
    Lv = Level(S.s8.base, rel)
    tr, te = add_parts(tr, Lv, True), add_parts(te, Lv, False)
    L_te, sdL, src = level_at(Lv, i, te["region"].tolist())
    mu, p, half, sd, tag, _, _, _ = run_proc(tr, te, L_te, sdL)
    o = te[["key", "province", "region", "lead", "gap_q", "anchor_round"]].copy()
    o["score"], o["p_high"], o["low90"], o["high90"] = pct(mu).round(2), np.round(p, 4), pct(mu - half).round(2), pct(mu + half).round(2)
    o["class"] = np.where(p >= .5, "HIGH", "LOW")
    o["mu"], o["sd"], o["level_pct"], o["level_sd"], o["level_source"], o["config"], o["released"] = mu, sd, pct(L_te).round(2), sdL, src, tag, "|".join(rel)
    return o


def seal():
    H, L, S_P = E154.income(), pd.read_parquet(O152 / "local_panel.parquet"), sun_panel()
    for kind, leads, name in (("ENNS2022", (1, 2), "sealed_enns2022.json"), ("LIVE", (1,), "sealed_2027-Q1.json")):
        sp = OUT / name
        if sp.exists():
            print("already sealed", name, hashlib.sha256(sp.read_bytes()).hexdigest())
            continue
        R = pd.concat([_seal_task(kind, h, H, L, S_P) for h in leads], ignore_index=True)
        doc = {"sealed_utc": datetime.now(timezone.utc).isoformat(), "model": "E170 two-part LightGBM (protocol blob ef63fe67)",
               "target": "ENNS 2022 provincial HFIAS moderate+severe, ref 2022-Q3" if kind == "ENNS2022" else "provincial HFIAS moderate+severe, 2027-Q1 (issue 2026-Q4)",
               "rule": "HIGH = p_high >= 0.5; scored only on provincial HFIAS moderate_or_severe outcomes", "forecasts": R.round(6).to_dict("records")}
        sp.write_text(json.dumps(doc, indent=1, default=str), newline="\n")
        print("sealed", name, len(R), "rows sha256", hashlib.sha256(sp.read_bytes()).hexdigest())


if __name__ == "__main__":
    {"run": run, "eval": evaluate, "seal": seal}[sys.argv[1]]()
