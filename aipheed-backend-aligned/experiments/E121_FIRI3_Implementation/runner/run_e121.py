"""E121: run FIRI3 (backend/app/ml/inference/firi3.py) on the E119 / E120 inputs, verify it against the frozen E120
design, and write the results, contribution records, snapshots and validation analyses. No model is trained.

    python run_e121.py
"""
from __future__ import annotations

import hashlib
import itertools
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
EXP = ROOT.parent
REPO = EXP.parent.parent
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(EXP / "E120_FIRI_Consolidated_Design" / "runner"))
from app.ml.inference import firi3 as F3      # noqa: E402
from app.ml.inference import firi as FI       # noqa: E402  (FIRI v2: read only, for the comparison)
import e120 as E120                           # noqa: E402  (frozen E120 design computation and its input loader)

OUT = ROOT / "out"
SNAP = ROOT / "snapshots"
OUT.mkdir(exist_ok=True)
ORIGINS = list(range(F3.START_Q, 2026 * 4 + 3))       # 2021-Q1 .. 2026-Q3
E121_START = "2026-10-31"                              # snapshots of origins issued before this are retrospective
SOURCE = {"D01": "PSA CPI by province (E40)", "D02": "PSA CPI by province (E40)", "D03": "PSA CPI Region IV-A index (E114)", "D05": "PSA wholesale rice (E107)",
          "D07": "PSA farmgate prices (E118)", "D08": "PSA retail prices (E118)", "D09": "PSA retail prices (E118)", "D10": "PSA retail prices (E118)",
          "D20": "PSA palay/corn production (E118)", "D21": "PSA palay/corn production (E118)", "D22": "PSA vegetables/root crops production (E118)",
          "D23": "PSA vegetables/root crops production (E118)", "D24": "PSA fisheries production (E118)", "D26": "PSA chicken production (E118)",
          "D27": "PSA livestock production (E118)", "D33": "IBTrACS, 100 km (corrected pipeline)", "D34": "IBTrACS, PAR (E114)", "D36": "NASA POWER (E118)",
          "D37": "NASA POWER (E118)", "D40": "PSA LFS national (E114)", "D41": "PSA provincial LFS tables (owner file, E116)", "D42": "BSP via dated reports",
          "D50": "PSA SAE 2021 (lgu_vulnerability.csv)", "D60": "aiPHeed news corpus (FSSI-v3)", "D62": "GDELT DOC (E114)"}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def sha_df(d: pd.DataFrame) -> str:
    return hashlib.sha256(d.to_csv(index=False, lineterminator="\n", float_format="%.12g").encode()).hexdigest()


def verify_protocol():
    h = sha(ROOT / "E121_FIRI3_PROTOCOL.md")
    assert h == (HERE / "PROTOCOL_SHA256.txt").read_text().strip() == F3.PROTOCOL_SHA256, "protocol hash mismatch"
    return h


def inputs():
    L, ann = E120.load()
    obs = L.assign(source=L["feature"] + " @ " + L["unit"])[["feature", "unit", "period", "value", "avail", "status", "source", "resolution"]]
    ann = ann.assign(source=ann["feature"] + " @ " + ann["unit"] + " (" + ann["ref"] + ")")
    return obs, ann


def run(obs, ann):
    return F3.compute(obs, ann, ORIGINS)


# ------------------------------------------------------------------------------------------------ analyses
def cmp(a, b, label, scope=None):
    m = a.merge(b, on=["scope", "unit", "t"], suffixes=("", "_alt")).dropna(subset=["firi3", "firi3_alt"])
    if scope:
        m = m[m["scope"] == scope]
    rk = [g["firi3"].corr(g["firi3_alt"], method="spearman") for _, g in m[m["scope"] == "provincial"].groupby("t")
          if len(g) == 5 and g["firi3"].nunique() > 1 and g["firi3_alt"].nunique() > 1]
    return {"variant": label, "scope": scope or "all", "rows": int(len(m)),
            "mean_abs_change": round(float((m["firi3"] - m["firi3_alt"]).abs().mean()), 4) if len(m) else None,
            "max_abs_change": round(float((m["firi3"] - m["firi3_alt"]).abs().max()), 4) if len(m) else None,
            "side_of_0_5_flip_pct": round(100 * float(((m["firi3"] >= .5) != (m["firi3_alt"] >= .5)).mean()), 1) if len(m) else None,
            "band_change_pct": round(100 * float((m["band"] != m["band_alt"]).mean()), 1) if len(m) else None,
            "province_rank_spearman_mean": round(float(np.mean(rk)), 3) if rk else None}


def main():
    proto = verify_protocol()
    firi_v2_sha = sha(REPO / "backend" / "app" / "ml" / "inference" / "firi.py")
    watched = [REPO / "backend" / "app" / "ml" / "inference" / "firi.py", REPO / "backend" / "data" / "thesis" / "firi2_history.csv",
               REPO / "backend" / "data" / "thesis" / "firi2_reference.json"]
    before = {str(p.relative_to(REPO)): sha(p) for p in watched}
    obs, ann = inputs()
    R1 = run(obs, ann)
    R2 = run(obs, ann)
    deterministic = all(sha_df(R1[k]) == sha_df(R2[k]) for k in ("features", "indicators", "overall"))
    FS, IND, OV = R1["features"], R1["indicators"], R1["overall"]

    # ---------------- E120 reproduction (the frozen design computation)
    e120 = pd.read_csv(EXP / "E120_FIRI_Consolidated_Design" / "out" / "level3_firi_equal.csv")
    m = OV.merge(e120, on=["scope", "unit", "t"], suffixes=("_f3", "_e120"))
    reproduces_e120 = bool(len(m) == len(OV) == len(e120)
                           and np.allclose(m["firi3"].astype(float).fillna(-1), m["firi"].fillna(-1), atol=1e-12)
                           and (m["indicators_available_f3"] == m["indicators_available_e120"]).all())
    bands_match = bool((m["band_f3"].replace({"not_computable": "not computable"}) == m["band_e120"]).all())

    # ---------------- FIRI v2 beside FIRI3 (served history, read only)
    h = pd.read_csv(REPO / "backend" / "data" / "thesis" / "firi2_history.csv")
    h["t"] = h["origin_quarter"].map(F3.qindex)
    h["unit"] = h["province_code"].map(FI.PROVINCES)
    v2 = h[["t", "unit", "target", "kind", "FIRI", "class", "domainsAvailable", "dom_A", "dom_V", "dom_C", "dom_E", "dom_N", "dom_H", "weights_json"]].rename(
        columns={"FIRI": "firi_v2", "class": "class_v2", "domainsAvailable": "v2_domains_available", "kind": "v2_kind", "target": "v2_target"})
    OVv = OV.merge(v2, on=["t", "unit"], how="left")
    OVv.loc[OVv["scope"] == "regional", ["firi_v2", "class_v2"]] = np.nan

    # ---------------- contributions per feature
    contrib = []
    base_ov = OV
    for f in F3.FEATURES:
        sc = "provincial" if f.scope == "P" else "regional"
        fr = FS[(FS["feature"] == f.code)]
        ind_f = IND[(IND["indicator"] == f.indicator) & (IND["scope"] == sc) & IND["available"]]
        alt_ind = F3.indicator_scores(FS, drop_features=(f.code,))
        alt_ov = F3.overall(alt_ind)
        c = cmp(base_ov, alt_ov, f"without {f.code}", sc)
        ai = ind_f.merge(alt_ind[(alt_ind["indicator"] == f.indicator) & (alt_ind["scope"] == sc)], on=["scope", "unit", "t", "indicator"], how="left", suffixes=("", "_alt"))
        # dominance: indicator rows where this feature is the only scored feature
        cnt = FS[(FS["indicator"] == f.indicator) & (FS["scope"] == sc) & FS["score"].notna()].groupby(["unit", "t"])["feature"].agg(list)
        only = sum(1 for v in cnt if v == [f.code])
        corr = fr.merge(ind_f[["unit", "t", "score"]], on=["unit", "t"], suffixes=("", "_ind")).dropna(subset=["score", "score_ind"])
        contrib.append({"feature": f.code, "indicator": f.indicator, "component": f.component, "scope": sc, "dataset": f.dataset, "source": SOURCE.get(f.dataset, ""),
                        "direction": "+ (higher = more risk)" if f.direction > 0 else "- (lower = more risk)", "transform": f.transform, "normalization": f.normalization,
                        "unit_origins": int(len(fr)), "scored": int(fr["score"].notna().sum()), "scored_pct": round(100 * float(fr["score"].notna().mean()), 1),
                        "statuses": "; ".join(f"{k}: {v}" for k, v in fr["status"].value_counts().items()),
                        "verified_share_of_scored": round(float((fr.loc[fr["score"].notna(), "status"] == "verified").mean()), 3) if fr["score"].notna().any() else None,
                        "mean_score": round(float(fr["score"].mean()), 3) if fr["score"].notna().any() else None,
                        "corr_with_indicator_score": round(float(corr["score"].corr(corr["score_ind"], method="spearman")), 3) if len(corr) > 5 else None,
                        "indicator_rows_sole_feature": int(only), "indicator_rows": int(len(ind_f)),
                        "indicator_unavailable_without_pct": round(100 * float(ai["score_alt"].isna().mean()), 1) if len(ai) else None,
                        "mean_abs_indicator_change_without": round(float((ai["score"] - ai["score_alt"]).abs().mean()), 4) if ai["score_alt"].notna().any() else None,
                        "mean_abs_firi3_change_without": c["mean_abs_change"], "max_abs_firi3_change_without": c["max_abs_change"],
                        "band_change_without_pct": c["band_change_pct"], "firi3_rows_compared": c["rows"]})
    CON = pd.DataFrame(contrib)

    # ---------------- coverage
    cov = []
    for (sc, i), g in IND.groupby(["scope", "indicator"]):
        n = 5 if sc == "provincial" else 1
        cov.append({"level": "indicator", "scope": sc, "name": i, "label": F3.INDICATORS[i], "possible": n * len(ORIGINS), "available": int(g["available"].sum()),
                    "available_pct": round(100 * float(g["available"].sum()) / (n * len(ORIGINS)), 1),
                    "first_available": F3.qlabel(int(g.loc[g["available"], "t"].min())) if g["available"].any() else "",
                    "mean_components_available": round(float(g.loc[g["available"], "components_available"].mean()), 2) if g["available"].any() else None,
                    "components_defined": int(g["components_defined"].max())})
    for (sc, u), g in OV.groupby(["scope", "unit"]):
        cov.append({"level": "FIRI3 by unit", "scope": sc, "name": u, "label": "", "possible": len(ORIGINS), "available": int(g["firi3"].notna().sum()),
                    "available_pct": round(100 * float(g["firi3"].notna().mean()), 1), "first_available": F3.qlabel(int(g.loc[g["firi3"].notna(), "t"].min())) if g["firi3"].notna().any() else "",
                    "mean_components_available": round(float(g.loc[g["firi3"].notna(), "indicators_available"].mean()), 2) if g["firi3"].notna().any() else None,
                    "components_defined": int(g["indicators_defined"].max())})
    for sc, g in OV.groupby("scope"):
        k = g.loc[g["firi3"].notna(), "indicators_available"].value_counts().sort_index().to_dict()
        cov.append({"level": "FIRI3", "scope": sc, "name": "overall", "label": f"indicators available: {k}", "possible": len(g), "available": int(g["firi3"].notna().sum()),
                    "available_pct": round(100 * float(g["firi3"].notna().mean()), 1), "first_available": F3.qlabel(int(g.loc[g["firi3"].notna(), "t"].min())),
                    "mean_components_available": round(float(g.loc[g["firi3"].notna(), "indicators_available"].mean()), 2), "components_defined": int(g["indicators_defined"].max())})
    COV = pd.DataFrame(cov)

    # ---------------- missingness sensitivity
    core = ["FMA", "AFP", "CEC", "EHS"]
    pv = IND.pivot_table(index=["scope", "unit", "t"], columns="indicator", values="score").reset_index()
    ok = OV[OV["firi3"].notna()].merge(pv, on=["scope", "unit", "t"])
    miss = []
    for k, g in ok[ok["scope"] == "provincial"].groupby("indicators_available"):
        core4 = g[core].mean(axis=1) if g[core].notna().all(axis=1).all() else g[core].mean(axis=1, skipna=True)
        miss.append({"k": int(k), "rows": int(len(g)), "mean_firi3": round(float(g["firi3"].mean()), 3), "sd_firi3": round(float(g["firi3"].std()), 3) if len(g) > 1 else None,
                     "chance_sd": round(F3.chance_sd(int(k)), 3), "core4_all_present_pct": round(100 * float(g[core].notna().all(axis=1).mean()), 1),
                     "mean_core4_score": round(float(core4.mean()), 3), "mean_abs_firi3_minus_core4": round(float((g["firi3"] - core4).abs().mean()), 4),
                     "max_abs_firi3_minus_core4": round(float((g["firi3"] - core4).abs().max()), 4),
                     "band_differs_from_core4_pct": round(100 * float((g["band"] != [F3.band(float(x), 4) for x in core4]).mean()), 1),
                     "sets": "; ".join(f"{s}: {n}" for s, n in g["indicators_used"].value_counts().items())})
    MISS = pd.DataFrame(miss)
    # entry effect: provincial quarters where an indicator joins (PSV from 2025-Q3; FIS)
    entry = []
    for u, g in OV[(OV["scope"] == "provincial") & OV["firi3"].notna()].sort_values("t").groupby("unit"):
        g = g.set_index("t")
        for t in g.index:
            if t - 1 in g.index:
                a, b = set(g.loc[t - 1, "indicators_used"].split()), set(g.loc[t, "indicators_used"].split())
                if a != b:
                    common = sorted(a & b)
                    s_now = pv[(pv["scope"] == "provincial") & (pv["unit"] == u) & (pv["t"] == t)][common].mean(axis=1).iloc[0]
                    s_prev = pv[(pv["scope"] == "provincial") & (pv["unit"] == u) & (pv["t"] == t - 1)][common].mean(axis=1).iloc[0]
                    d = g.loc[t, "firi3"] - g.loc[t - 1, "firi3"]
                    entry.append({"unit": u, "origin": F3.qlabel(t), "joined": " ".join(sorted(b - a)), "left": " ".join(sorted(a - b)), "change": round(float(d), 4),
                                  "change_common_indicators": round(float(s_now - s_prev), 4), "composition_effect": round(float(d - (s_now - s_prev)), 4)})
    ENTRY = pd.DataFrame(entry)

    # ---------------- weighting sensitivity (approved: equal) by scope
    prov_feat = [f for f in F3.FEATURES if f.scope == "P"]
    comp_w = {i: len(F3.components(i, "P")) for i in F3.INDICATORS}
    feat_w = {i: sum(1 for f in prov_feat if f.indicator == i) for i in F3.INDICATORS}
    pp = pv[pv["scope"] == "provincial"].set_index(["unit", "t"])[list(F3.INDICATORS)]
    rc = pp.corr(method="spearman", min_periods=8)
    red_w = {d: 1 / (1 + sum(max(0, rc.loc[d, e]) for e in rc.columns if e != d and not np.isnan(rc.loc[d, e]))) for d in rc.columns}
    cc = pp[[c for c in pp.columns if pp[c].notna().mean() >= .3]].dropna()
    ev, evec = np.linalg.eigh(cc.corr().to_numpy())
    pca_w = {**dict(zip(cc.columns, np.abs(evec[:, -1]) / np.abs(evec[:, -1]).sum())), **{c: 1 / len(cc.columns) for c in pp.columns if c not in cc.columns}}
    WS = []
    variants = {"component-count": comp_w, "feature-count": feat_w, "redundancy-adjusted": red_w, "PCA first component": pca_w,
                **{f"{i} doubled": {**{j: 1.0 for j in F3.INDICATORS}, i: 2.0} for i in F3.INDICATORS},
                **{f"{i} halved": {**{j: 1.0 for j in F3.INDICATORS}, i: 0.5} for i in F3.INDICATORS}}
    for name, w in variants.items():
        alt = F3.overall(IND, weights=w)
        WS += [cmp(OV, alt, name, "provincial"), cmp(OV, alt, name, "regional")]
    rng = np.random.default_rng(121)
    rnd_p, rnd_r = [], []
    for _ in range(300):
        alt = F3.overall(IND, weights=dict(zip(F3.INDICATORS, rng.dirichlet(np.ones(6)))))
        rnd_p.append(cmp(OV, alt, "r", "provincial")); rnd_r.append(cmp(OV, alt, "r", "regional"))
    for sc, rr in (("provincial", rnd_p), ("regional", rnd_r)):
        WS.append({"variant": "random Dirichlet(1), 300 draws: median", "scope": sc, "rows": rr[0]["rows"],
                   **{k: float(np.median([x[k] for x in rr if x[k] is not None])) for k in ("mean_abs_change", "max_abs_change", "side_of_0_5_flip_pct", "band_change_pct")},
                   "province_rank_spearman_mean": float(np.median([x["province_rank_spearman_mean"] for x in rr if x["province_rank_spearman_mean"] is not None])) if sc == "provincial" else None})
    WSD = pd.DataFrame(WS)
    LOIO = pd.DataFrame([{**cmp(OV, F3.overall(IND, drop_indicators=(i,)), f"without {i}", sc)} for i in F3.INDICATORS for sc in ("provincial", "regional")
                         if not (i == "PSV" and sc == "regional")])

    # ---------------- temporal stability
    tem = []
    for (sc, u), g in OV[OV["firi3"].notna()].sort_values("t").groupby(["scope", "unit"]):
        g = g.set_index("t")
        for t in g.index:
            if t - 1 not in g.index:
                continue
            a, b = g.loc[t - 1, "indicators_used"].split(), g.loc[t, "indicators_used"].split()
            common = sorted(set(a) & set(b))
            q = pv[(pv["scope"] == sc) & (pv["unit"] == u)].set_index("t")
            d = float(g.loc[t, "firi3"] - g.loc[t - 1, "firi3"])
            dc = float(q.loc[t, common].mean() - q.loc[t - 1, common].mean())
            # feature-level causes inside common indicators
            f_now = FS[(FS["scope"] == sc) & (FS["unit"] == u) & (FS["t"] == t) & FS["score"].notna()]
            f_prev = FS[(FS["scope"] == sc) & (FS["unit"] == u) & (FS["t"] == t - 1) & FS["score"].notna()]
            fj = sorted(set(f_now["feature"]) - set(f_prev["feature"]))
            fl = sorted(set(f_prev["feature"]) - set(f_now["feature"]))
            same_period = f_now.merge(f_prev, on="feature", suffixes=("", "_p"))
            renorm = same_period[(same_period["period"] == same_period["period_p"]) & (same_period["score"] != same_period["score_p"])]["feature"].tolist()
            tem.append({"scope": sc, "unit": u, "origin": F3.qlabel(t), "firi3": round(float(g.loc[t, "firi3"]), 4), "change": round(d, 4),
                        "indicators_prev": " ".join(a), "indicators_now": " ".join(b), "change_from_common_indicators": round(dc, 4),
                        "composition_effect": round(d - dc, 4), "features_joined": " ".join(fj), "features_left": " ".join(fl),
                        "rescored_same_observation": " ".join(renorm), "band_prev": g.loc[t - 1, "band"], "band_now": g.loc[t, "band"]})
    TEM = pd.DataFrame(tem)

    # ---------------- geographic consistency (comparable origins: all five provinces with the same indicator set)
    po = OV[(OV["scope"] == "provincial") & OV["firi3"].notna()]
    comp_t = [t for t, g in po.groupby("t") if len(g) == 5 and g["indicators_used"].nunique() == 1]
    pc = po[po["t"].isin(comp_t)].copy()
    pc["rank"] = pc.groupby("t")["firi3"].rank(ascending=False)
    GEO = pc.groupby("unit").agg(comparable_origins=("t", "size"), mean_firi3=("firi3", "mean"), mean_rank=("rank", "mean"),
                                 times_highest=("rank", lambda r: int((r == 1).sum())), times_lowest=("rank", lambda r: int((r == 5).sum()))).round(3).reset_index()
    ind_geo = IND[(IND["scope"] == "provincial") & IND["t"].isin(comp_t) & IND["available"]].pivot_table(index="unit", columns="indicator", values="score", aggfunc="mean").round(3)
    sets_by_origin = po.groupby("t")["indicators_used"].agg(lambda s: s.nunique()).value_counts().to_dict()
    kendall_w = None
    if len(comp_t) >= 2:
        R = pc.pivot_table(index="t", columns="unit", values="rank")
        n, mm = R.shape[1], R.shape[0]
        S = ((R.sum(axis=0) - R.sum(axis=0).mean()) ** 2).sum()
        kendall_w = round(float(12 * S / (mm ** 2 * (n ** 3 - n))), 3)

    # ---------------- FIRI v2 comparison
    vm = OVv[(OVv["scope"] == "provincial") & OVv["firi3"].notna() & OVv["firi_v2"].notna()].copy()
    for d in "AVCENH":
        vm[f"dom_{d}"] = pd.to_numeric(vm[f"dom_{d}"], errors="coerce")
    def v2_without(row, drop):
        w = json.loads(row["weights_json"]) if isinstance(row["weights_json"], str) else {}
        num = sum(w.get(d, 0) * row[f"dom_{d}"] for d in "AVCENH" if d not in drop and not pd.isna(row[f"dom_{d}"]) and d in w)
        den = sum(w.get(d, 0) for d in "AVCENH" if d not in drop and not pd.isna(row[f"dom_{d}"]) and d in w)
        return num / den if den else np.nan
    vm["v2_without_H"] = vm.apply(lambda r: v2_without(r, "H"), axis=1)
    vm["v2_without_H_E"] = vm.apply(lambda r: v2_without(r, "HE"), axis=1)
    vm["v2_provincial_domains_A_V"] = vm.apply(lambda r: v2_without(r, "HECN"), axis=1)
    sp = lambda a, b: round(float(vm[[a, b]].dropna()[a].corr(vm[[a, b]].dropna()[b], method="spearman")), 3) if len(vm[[a, b]].dropna()) > 5 else None  # noqa: E731
    v2c = {"rows": int(len(vm)), "origins": int(vm["t"].nunique()), "spearman_firi3_v2": sp("firi3", "firi_v2"),
           "side_of_0_5_agreement_pct": round(100 * float(((vm["firi3"] >= .5) == (vm["class_v2"] == "HIGH")).mean()), 1),
           "share_v2_high": round(float((vm["class_v2"] == "HIGH").mean()), 3), "share_firi3_ge_0_5": round(float((vm["firi3"] >= .5).mean()), 3),
           "firi3_band_counts": vm["band"].value_counts().to_dict(),
           "spearman_with_v2_domain": {d: sp("firi3", f"dom_{d}") for d in "AVCENH"},
           "spearman_v2_with_its_H_domain": sp("firi_v2", "dom_H"),
           "spearman_firi3_v2_without_H": sp("firi3", "v2_without_H"), "spearman_firi3_v2_without_H_E": sp("firi3", "v2_without_H_E"),
           "spearman_firi3_v2_A_V_only": sp("firi3", "v2_provincial_domains_A_V"),
           "mean_v2_weights": {d: round(float(np.mean([json.loads(w).get(d, 0) for w in vm["weights_json"]])), 3) for d in "AVCENH"},
           "v2_identical_across_provinces_share": round(float(vm.groupby("t")["firi_v2"].agg(lambda s: s.nunique() == 1).mean()), 3),
           "firi3_mean_quarter_change": None, "v2_mean_quarter_change": None}
    rk = [g["firi3"].corr(g["firi_v2"], method="spearman") for _, g in vm.groupby("t") if len(g) == 5 and g["firi3"].nunique() > 1 and g["firi_v2"].nunique() > 1]
    v2c["province_rank_spearman_mean"] = round(float(np.mean(rk)), 3) if rk else None
    ch3, ch2 = [], []
    for u, g in vm.sort_values("t").groupby("unit"):
        g = g.set_index("t")
        for t in g.index:
            if t - 1 in g.index:
                ch3.append(abs(g.loc[t, "firi3"] - g.loc[t - 1, "firi3"])); ch2.append(abs(g.loc[t, "firi_v2"] - g.loc[t - 1, "firi_v2"]))
    v2c["firi3_mean_quarter_change"] = round(float(np.mean(ch3)), 4) if ch3 else None
    v2c["v2_mean_quarter_change"] = round(float(np.mean(ch2)), 4) if ch2 else None
    v2c["v2_rows_with_firi3_not_computable"] = int(OVv[(OVv["scope"] == "provincial") & OVv["firi3"].isna() & OVv["firi_v2"].notna()].shape[0])
    v2c["v2_regional_score"] = "none (FIRI v2 has no regional index)"

    # ---------------- SWS: descriptive external reference for the regional FIRI3 (never an input, never used to adjust)
    sws = pd.read_csv(EXP / "E119_Preprocessing" / "out" / "indicators" / "H1" / "observations_clean.csv").groupby("period")["value"].mean()
    reg = OV[(OV["scope"] == "regional") & OV["firi3"].notna()][["t", "firi3"]].copy()
    reg["sws_same_quarter"] = reg["t"].map(sws)
    reg["sws_next_quarter"] = (reg["t"] + 1).map(sws)
    sws_desc = {"quarters": int(len(reg)),
                "spearman_same_quarter": round(float(reg[["firi3", "sws_same_quarter"]].dropna().corr(method="spearman").iloc[0, 1]), 3) if reg["sws_same_quarter"].notna().sum() > 4 else None,
                "spearman_next_quarter": round(float(reg[["firi3", "sws_next_quarter"]].dropna().corr(method="spearman").iloc[0, 1]), 3) if reg["sws_next_quarter"].notna().sum() > 4 else None,
                "n_next": int(reg["sws_next_quarter"].notna().sum()), "note": "descriptive only; computed after the design was frozen; not used for any choice"}

    # ---------------- leakage checks
    fsc = FS[FS["score"].notna()]
    dyn = fsc[fsc["normalization"] == "pct"]
    leak = {
        "protocol_hash_verified": proto == F3.PROTOCOL_SHA256,
        "no_future_observation": bool((dyn["period"].map(F3.qindex) <= dyn["t"]).all()),
        "no_future_publication": bool((fsc["avail_date"].astype(str) < fsc["issue_date"].astype(str)).all()),
        "no_stale_beyond_3_quarters": bool(((dyn["t"] - dyn["period"].map(F3.qindex)) <= F3.MAX_STALE).all()),
        "no_sws_or_index_series_in_features": not any(any(k in s.lower() for k in F3.FORBIDDEN) for s in {f.series for f in F3.FEATURES}),
        "sws_refused_if_passed": False,
        "no_pre2021_observation_scored": bool((fsc["period"].astype(str).str[:4].astype(int) >= 2021).all()),
        "pre2021_rows_rejected_count": R1["log"]["pre2021_rows_rejected"],
        "provincial_scores_from_provinces_only": bool(set(FS.loc[FS["scope"] == "provincial", "unit"]) == set(F3.PROVINCES)
                                                      and (FS.loc[FS["scope"] == "provincial", "series_unit"] == "province").all()),
        "regional_scores_from_regional_units_only": bool(set(FS.loc[FS["scope"] == "regional", "series_unit"]) <= set(F3.REGIONAL_UNITS)),
        "no_national_feature_in_provincial_score": not FS[(FS["scope"] == "provincial")]["feature"].str.endswith("_R").any(),
        "annual_not_expanded": bool(FS[FS["normalization"] == "rank5"]["period"].dropna().astype(str).str.fullmatch(r"\d{4}").all()),
        "rolling_prior_strictly_earlier_and_available": True,
        "missing_never_scored": bool(FS.loc[FS["status"].isin(["missing", "stale", "insufficient_history", "unavailable_at_issue", "incomplete_year"]), "score"].isna().all()),
        "firi_only_when_complete": bool((OV.loc[OV["firi3"].notna(), "indicators_available"] >= np.ceil(F3.MIN_SHARE * OV.loc[OV["firi3"].notna(), "indicators_defined"])).all()),
    }
    try:
        F3.validate_inputs(pd.concat([obs, pd.DataFrame([{"feature": "sws_balance_luzon_hunger", "unit": "Balance Luzon", "period": 8100, "value": 1, "avail": "2025-01-01", "status": "verified"}])]), ann)
    except ValueError:
        leak["sws_refused_if_passed"] = True
    # prior check: recompute a sample of dynamic scores from scratch with an independent filter
    samp = dyn.sample(min(200, len(dyn)), random_state=1)
    okp = True
    for r in samp.itertuples():
        f = next(x for x in F3.FEATURES if x.code == r.feature)
        units = F3.PROVINCES if f.scope == "P" else (f.unit,)
        s = obs[(obs["feature"] == f.series) & obs["unit"].isin(units) & (obs["avail"].astype(str) < r.issue_date) & (obs["period"] < F3.qindex(r.period))]
        x = f.direction * (s["value"].abs() if f.transform == "abs" else s["value"])
        if not np.isclose(F3.midrank(r.aligned_value, x.to_numpy()), r.score):
            okp = False
    leak["rolling_prior_strictly_earlier_and_available"] = okp
    after = {k: sha(REPO / k) for k in before}
    leak["firi_v2_files_unchanged"] = before == after
    assert all(v for k, v in leak.items() if isinstance(v, bool)), leak

    # ---------------- snapshots (write once)
    snap_log = []
    for t in ORIGINS:
        o = F3.qlabel(t)
        d = SNAP / o
        parts = {"features.csv": FS[FS["t"] == t], "indicators.csv": IND[IND["t"] == t].assign(component_scores=lambda x: x["component_scores"].map(json.dumps)),
                 "overall.csv": OVv[OVv["t"] == t].drop(columns=["weights_json"])}
        blobs = {k: v.to_csv(index=False, lineterminator="\n", float_format="%.12g").encode() for k, v in parts.items()}
        man = {"origin": o, "issue_date": F3.issue_date(t), "kind": "retrospective" if F3.issue_date(t) < E121_START else "prospective",
               "protocol_sha256": proto, "firi3_version": F3.VERSION, "firi_v2_module_sha256": firi_v2_sha,
               "files": {k: hashlib.sha256(b).hexdigest() for k, b in blobs.items()}}
        if (d / "manifest.json").exists():
            old = json.loads((d / "manifest.json").read_text())
            assert old["files"] == man["files"], f"snapshot {o} would change: refused (immutable)"
            snap_log.append({"origin": o, "action": "verified unchanged", "kind": old["kind"]})
            continue
        d.mkdir(parents=True)
        for k, b in blobs.items():
            (d / k).write_bytes(b)
        man["written_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        (d / "manifest.json").write_text(json.dumps(man, indent=1))
        snap_log.append({"origin": o, "action": "written", "kind": man["kind"]})

    # ---------------- write
    FS.to_csv(ROOT / "E121_FIRI3_FEATURE_RESULTS.csv", index=False, lineterminator="\n", float_format="%.10g")
    IND.assign(component_scores=IND["component_scores"].map(json.dumps)).to_csv(ROOT / "E121_FIRI3_INDICATOR_RESULTS.csv", index=False, lineterminator="\n", float_format="%.10g")
    OVv.drop(columns=["weights_json"]).to_csv(ROOT / "E121_FIRI3_OVERALL_RESULTS.csv", index=False, lineterminator="\n", float_format="%.10g")
    COV.to_csv(ROOT / "E121_FIRI3_COVERAGE_REPORT.csv", index=False, lineterminator="\n")
    CON.to_csv(ROOT / "E121_FIRI3_FEATURE_CONTRIBUTION_REPORT.csv", index=False, lineterminator="\n")
    MISS.to_csv(OUT / "missingness_by_k.csv", index=False, lineterminator="\n")
    ENTRY.to_csv(OUT / "composition_changes.csv", index=False, lineterminator="\n")
    WSD.to_csv(OUT / "weighting_sensitivity.csv", index=False, lineterminator="\n")
    LOIO.to_csv(OUT / "leave_one_indicator_out.csv", index=False, lineterminator="\n")
    TEM.to_csv(OUT / "temporal_changes.csv", index=False, lineterminator="\n")
    GEO.to_csv(OUT / "geographic_comparable.csv", index=False, lineterminator="\n")
    ind_geo.to_csv(OUT / "geographic_indicator_means.csv", lineterminator="\n")
    reg.to_csv(OUT / "regional_vs_sws_descriptive.csv", index=False, lineterminator="\n")
    pd.DataFrame(snap_log).to_csv(OUT / "snapshot_log.csv", index=False, lineterminator="\n")
    summary = {"protocol_sha256": proto, "deterministic": deterministic, "reproduces_e120": reproduces_e120, "bands_match_e120": bands_match,
               "leakage": leak, "log": R1["log"], "weights": {"component-count": comp_w, "feature-count": feat_w, "redundancy-adjusted": {k: round(v, 4) for k, v in red_w.items()},
                                                              "PCA": {k: round(float(v), 4) for k, v in pca_w.items()}, "pca_pc1_share": round(float(ev[-1] / ev.sum()), 3)},
               "geographic": {"comparable_origins": [F3.qlabel(t) for t in comp_t], "kendall_w": kendall_w, "distinct_indicator_sets_per_origin": sets_by_origin},
               "v2_comparison": v2c, "sws_descriptive": sws_desc, "watched_sha256": before,
               "temporal": {sc: {"rows": int(len(g)), "mean_abs_change": round(float(g["change"].abs().mean()), 4), "sd_change": round(float(g["change"].std()), 4),
                                 "abrupt_changes_gt_0_15": int((g["change"].abs() > .15).sum()),
                                 "mean_abs_composition_effect": round(float(g["composition_effect"].abs().mean()), 4),
                                 "rows_with_composition_change": int((g["indicators_prev"] != g["indicators_now"]).sum()),
                                 "band_changes": int((g["band_prev"] != g["band_now"]).sum())} for sc, g in TEM.groupby("scope")}}
    json.dump(summary, open(OUT / "summary.json", "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    pd.set_option("display.width", 250)
    print(json.dumps({k: summary[k] for k in ("deterministic", "reproduces_e120", "bands_match_e120", "leakage", "log", "geographic", "v2_comparison", "sws_descriptive", "temporal")},
                     indent=1, default=str))
    print(COV.to_string()); print(MISS.to_string()); print(ENTRY.to_string()); print(LOIO.to_string())
    print(WSD.to_string()); print(GEO.to_string()); print(ind_geo.to_string())
    print(CON[["feature", "scored_pct", "verified_share_of_scored", "corr_with_indicator_score", "indicator_rows_sole_feature", "indicator_rows",
               "mean_abs_firi3_change_without", "max_abs_firi3_change_without", "band_change_without_pct"]].to_string())
    print(TEM[TEM["change"].abs() > .15].to_string())


if __name__ == "__main__":
    main()
