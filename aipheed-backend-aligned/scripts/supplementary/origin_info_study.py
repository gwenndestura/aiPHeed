"""
scripts/supplementary/origin_info_study.py

Stage A of the origin-information study (experiments/2026-10-09_origin_info/
PREREGISTRATION_v4.json + PREREGISTRATION_v4_AMENDMENT_L.json, hashes checked).
2021-2026 window, K1-K4, strict timing, threshold 14.345, and the new
label-availability rule L: a labelled quarter trains a forecast for quarter T
only if its SWS round was released before T starts.

Primary candidate N2: a quarter-level ridge nowcast of next-quarter SWS hunger
from origin-known information, combined with Eq. 3's province term. In-memory
only; no production file, data file or earlier evidence is written.

    python -m scripts.supplementary.origin_info_study
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

import scripts.supplementary.generalization_study as G
import scripts.supplementary.reliability_diagnostics as R
import scripts.supplementary.timing_audit as T
import scripts.supplementary.window2021_study as W

warnings.filterwarnings("ignore")
EXP = Path("experiments/2026-10-09_origin_info")
PREREG_SHA = "4ac66c03280ce87d3336067e9bd212053c2213c2a309d0b8466bcba23b9c896d"
AMEND_SHA = "c1c5c2ae6b6155d484a670e92fd8732e745dfbf17c7920c2057d862f355d53c8"
THR, CUT, OUTER_MIN, INNER_MIN = W.THR_PRIMARY, 0.5, 8, 5
KEY = ["target_quarter", "province_code"]
QFEATS = ["sws_hunger", "sws_change", "sws_age", "reg_food_cpi_yoy", "reg_rice_accel", "news_ph_count"]
REL = T.sws_release_dates()


def qi(q):
    return R.qi(q)


# ---------------------------------------------------------------- splits
def released_before(s, T_):
    return s in REL and REL[s] < T.qstart(T_)


def splits(d, start, rule_l):
    """Outer/inner chronological splits; with rule L, training labels must be released before T."""
    tq = sorted(d["target_quarter"].unique(), key=qi)
    for i in range(start, len(tq)):
        Tq = tq[i]
        tr = d[d["target_quarter"].map(qi) < qi(Tq)]
        if rule_l:
            tr = tr[tr["target_quarter"].map(lambda s: released_before(s, Tq))]
        yield Tq, tr, d[d["target_quarter"] == Tq]


# --------------------------------------------------------- quarter level
def quarter_table(d, labels):
    q = d.groupby("target_quarter").agg(sws_hunger=("sws_hunger", "first"), sws_change=("sws_change", "first"),
                                        sws_age=("sws_age", "first"), reg_food_cpi_yoy=("food_cpi_yoy", "mean"),
                                        reg_rice_accel=("rice_price_regular_accel", "mean"),
                                        news_ph_count=("news_ph_count", "first"))
    sws = labels.groupby("quarter")["sws_hunger_pct"].first()
    q["sws_target"] = q.index.map(sws)
    return q


class Nowcast:
    """N2 (ridge) or N1 (shrinkage) SWS nowcast + Eq. 3 province term."""
    def __init__(self, kind):
        self.kind = kind

    def _fit_sws(self, qt):
        X = qt[QFEATS].copy()
        self.med = X.median()
        X = X.fillna(self.med)
        y = qt["sws_target"].values
        if self.kind == "N2":
            self.sc = StandardScaler().fit(X)
            self.m = Ridge(alpha=1.0).fit(self.sc.transform(X), y)
        else:
            k = qt["sws_hunger"].fillna(self.med["sws_hunger"]).values
            self.mu = float(np.mean(y))
            v = np.var(k)
            self.phi = float(np.cov(k, y, bias=True)[0, 1] / v) if v > 0 else 0.0

    def _pred_sws(self, qt):
        X = qt[QFEATS].fillna(self.med)
        if self.kind == "N2":
            return self.m.predict(self.sc.transform(X))
        return self.mu + self.phi * (X["sws_hunger"].values - self.mu)

    def fit(self, tr, qt_tr):
        self._fit_sws(qt_tr)
        # walk-forward residual SD inside the training quarters (no look-ahead)
        res = []
        qs = list(qt_tr.index)
        for j in range(4, len(qs)):
            sub = Nowcast(self.kind)
            sub._fit_sws(qt_tr.loc[qs[:j]])
            res.append(qt_tr.loc[qs[j], "sws_target"] - sub._pred_sws(qt_tr.loc[[qs[j]]])[0])
        s_sws = float(np.std(res, ddof=1)) if len(res) >= 3 else float(qt_tr["sws_target"].std())
        e = (tr["cpi_rel_target"] - tr["cpi_rel"]).dropna()
        s_rel = float(e.std()) if len(e) > 2 else 1.0
        self.sigma = float(np.sqrt(s_sws ** 2 + 4 * s_rel ** 2))
        return self

    def predict(self, te, qt_te):
        sh = pd.Series(self._pred_sws(qt_te), index=qt_te.index)
        stress = te["target_quarter"].map(sh).values + 2 * te["cpi_rel"].fillna(0).values
        return norm.cdf((stress - THR) / self.sigma), te["target_quarter"].map(sh).values


def run_nowcast(d, qt, kind, rule_l):
    rows = []
    for Tq, tr, te in splits(d, OUTER_MIN, rule_l):
        qtr = qt.loc[sorted(tr["target_quarter"].unique(), key=qi)]
        m = Nowcast(kind).fit(tr, qtr)
        p, sh = m.predict(te, qt.loc[[Tq]])
        rows.append(pd.DataFrame({"target_quarter": Tq, "province_code": te["province_code"].values, "y": te["y"].values,
                                  "p": p, "sws_hat": sh, "sws_target": qt.loc[Tq, "sws_target"],
                                  "n_train_quarters": len(qtr)}))
    r = pd.concat(rows, ignore_index=True)
    r["pred"] = (r["p"] >= CUT).astype(int)
    return r


# ------------------------------------------------ pool models (W) with rule L
def walk_cfg(d, cfg, start, rule_l):
    rows = []
    for Tq, tr, te in splits(d, start, rule_l):
        if tr["y"].nunique() < 2:
            continue
        rows.append(pd.DataFrame({"target_quarter": Tq, "province_code": te["province_code"].values,
                                  "y": te["y"].values, "p": W.fit_predict(cfg, tr, te)}))
    r = pd.concat(rows, ignore_index=True)
    r["pred"] = (r["p"] >= CUT).astype(int)
    return r


def nested_L(d, members):
    rows, choices = [], []
    for Tq, tr, te in splits(d, OUTER_MIN, True):
        scores = {}
        for c in members:
            try:
                scores[c["id"]] = G.qacc(walk_cfg(tr, c, INNER_MIN, True))
            except ValueError:
                scores[c["id"]] = -1.0
        top = max(scores.values())
        ch = next(c for c in members if abs(scores[c["id"]] - top) < 1e-12)
        rows.append(pd.DataFrame({"target_quarter": Tq, "province_code": te["province_code"].values,
                                  "y": te["y"].values, "p": W.fit_predict(ch, tr, te)}))
        choices.append({"outer_quarter": Tq, "chosen": ch["id"], "inner": round(top, 4),
                        "n_tied": sum(abs(v - top) < 1e-12 for v in scores.values()), "train_quarters": tr["target_quarter"].nunique()})
    r = pd.concat(rows, ignore_index=True)
    r["pred"] = (r["p"] >= CUT).astype(int)
    return r, choices


# ------------------------------------------------------------ news stage
def news_regeocode():
    from app.ml.corpus.location_geocoder import geocode_location
    g = pd.read_parquet("data/processed/corpus_geocoded.parquet")
    g["q"] = g["quarter"].astype(str)
    w = g[g["q"].between("2021-Q1", "2026-Q4") & (pd.to_numeric(g["food_insecurity_score"], errors="coerce") >= 0.30)
          & g["province_code"].isna()]
    out = []
    for _, r in w.iterrows():
        loc = geocode_location(f"{r['title'] or ''}. {r['summary'] or ''}") or {}
        out.append({"quarter": r["q"], "title": r["title"], "summary": str(r["summary"])[:300],
                    "assigned_province": loc.get("province_name"), "assigned_lgu": loc.get("lgu_name"),
                    "match_level": loc.get("match_level")})
    return pd.DataFrame(out)


# ------------------------------------------------------------------ main
def main():
    EXP.mkdir(parents=True, exist_ok=True)
    assert hashlib.sha256((EXP / "PREREGISTRATION_v4.json").read_bytes()).hexdigest() == PREREG_SHA
    assert hashlib.sha256((EXP / "PREREGISTRATION_v4_AMENDMENT_L.json").read_bytes()).hexdigest() == AMEND_SHA
    f, inputs, gov, log = W.window_frame(extend=True)
    labels = W.window_labels(THR)
    d = R.pairs(f[f["quarter"] <= "2025-Q4"], labels, 1)
    lab = labels.assign(cpi_rel_target=labels["food_cpi_yoy"] - labels["regional_food_cpi_yoy"])
    d = d.merge(lab[["province_code", "quarter", "cpi_rel_target"]].rename(columns={"quarter": "target_quarter"}), on=KEY)
    qt = quarter_table(d, labels)
    fs = W.feature_sets(inputs)
    res = {"provenance": {"git_head": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd="..").stdout.strip(),
                          "preregistration_sha256": PREREG_SHA, "amendment_sha256": AMEND_SHA,
                          "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                          "window_script_sha256": hashlib.sha256(Path(W.__file__).read_bytes()).hexdigest(),
                          "quarter_features": QFEATS, "threshold": THR}}

    # label-timing audit
    audit = []
    for Tq, tr0, _ in splits(d, OUTER_MIN, False):
        trL = tr0[tr0["target_quarter"].map(lambda s: released_before(s, Tq))]
        audit.append({"outer_quarter": Tq, "train_quarters_without_L": tr0["target_quarter"].nunique(),
                      "train_quarters_with_L": trL["target_quarter"].nunique(),
                      "unreleased_labels_used_without_L": sorted(set(tr0["target_quarter"]) - set(trL["target_quarter"]), key=qi)})
    res["label_timing_audit"] = audit

    # references
    pers = d[KEY + ["y"]].copy()
    pers["pred"] = W.persistence(d, labels)
    pers = pers[pers["target_quarter"].map(qi) >= qi("2023-Q3")].copy()
    pers["pred"] = pers["pred"].fillna(0).astype(int)
    dc = d.assign(time_index=d["t"])
    clock_cfg = {"id": "clock", "family": "lgbm", "w": "spw", "cols": ["time_index"]}
    b2_cfg = {"id": "b2", "family": "lgbm", "w": "spw", "cols": fs["gov_c"]}
    logit_cfg = {"id": "gov_c|logistic|C=0.1|w=balanced", "family": "logistic", "C": 0.1, "w": "balanced", "cols": fs["gov_c"]}
    rule_cfg = {"id": "struct_rule", "family": "rule", "thr": THR, "cols": ["sws_hunger", "cpi_rel"]}

    runs = {}
    for L in (True, False):
        tag = "with_L" if L else "without_L"
        runs[f"N2 nowcast + Eq.3 ({tag})"] = run_nowcast(d, qt, "N2", L)
        runs[f"N1 shrinkage + Eq.3 ({tag})"] = run_nowcast(d, qt, "N1", L)
        runs[f"MODEL-B2 config ({tag})"] = walk_cfg(d, b2_cfg, OUTER_MIN, L)
        runs[f"gov_c logistic hypothesis ({tag})"] = walk_cfg(d, logit_cfg, OUTER_MIN, L)
        runs[f"clock-only ({tag})"] = walk_cfg(dc, clock_cfg, OUTER_MIN, L)
    runs["Eq.3 rule (no training)"] = walk_cfg(d, rule_cfg, OUTER_MIN, False)
    runs["persistence (timing-valid)"] = pers.assign(p=np.nan)
    members = W.pool(fs, THR)
    P4L, choices = nested_L(d, members)
    runs["P4 nested (with_L)"] = P4L

    refs = {"persistence_timing_valid": pers, "clock_only": runs["clock-only (with_L)"]}
    res["results"] = {k: {"metrics": G.metrics(v), "detail": W.detail(v)} for k, v in runs.items()}
    res["primary_N2_with_L_acceptance"] = G.acceptance(runs["N2 nowcast + Eq.3 (with_L)"], refs)
    res["acceptance_descriptive"] = {k: G.acceptance(v, refs)["verdict"] for k, v in runs.items()
                                     if k not in ("persistence (timing-valid)",)}
    res["P4_with_L_choices"] = choices
    n2 = runs["N2 nowcast + Eq.3 (with_L)"]
    qn = n2.groupby("target_quarter").agg(sws_hat=("sws_hat", "first"), sws_target=("sws_target", "first"))
    qn["sws_known"] = qt.loc[qn.index, "sws_hunger"]
    res["nowcast_quality_outer"] = {"mae_nowcast": round(float((qn["sws_hat"] - qn["sws_target"]).abs().mean()), 3),
                                    "mae_latest_known": round(float((qn["sws_known"] - qn["sws_target"]).abs().mean()), 3),
                                    "by_quarter": qn.round(2).to_dict(orient="index")}
    pd.concat([v.assign(model=k) for k, v in runs.items()]).to_csv(EXP / "stageA_predictions.csv", index=False)

    # news re-geocoding (documented geocoder; approved threshold unchanged)
    nw = news_regeocode()
    nw.to_csv(EXP / "news_regeocode_candidates.csv", index=False)
    res["news"] = {"retained_2021plus_without_province": int(len(nw)),
                   "assigned_by_geocoder": int(nw["assigned_province"].notna().sum()),
                   "assignments": nw[nw["assigned_province"].notna()][["quarter", "title", "assigned_province", "assigned_lgu"]]
                   .to_dict(orient="records")}

    # frozen label-blind 2026 forecasts for N2 (retrospective simulation)
    feats = f[f["quarter"].isin(["2025-Q4", "2026-Q1"])].copy()
    feats["target_quarter"] = feats["quarter"].map(T.nxt)
    fq = feats.groupby("target_quarter").agg(sws_hunger=("sws_hunger", "first"), sws_change=("sws_change", "first"),
                                             sws_age=("sws_age", "first"), reg_food_cpi_yoy=("food_cpi_yoy", "mean"),
                                             reg_rice_accel=("rice_price_regular_accel", "mean"),
                                             news_ph_count=("news_ph_count", "first"))
    fc = []
    for Tq, g in feats.groupby("target_quarter"):
        trq = [s for s in qt.index if released_before(s, Tq)]
        tr = d[d["target_quarter"].isin(trq)]
        m = Nowcast("N2").fit(tr, qt.loc[sorted(trq, key=qi)])
        p, sh = m.predict(g, fq.loc[[Tq]])
        fc.append(pd.DataFrame({"candidate": "N2 nowcast + Eq.3", "target_quarter": Tq,
                                "province": g["province_code"].map(W.NAMES).values, "p_high": np.round(p, 4),
                                "pred_high": (p >= CUT).astype(int), "sws_hat": np.round(sh, 2),
                                "train_quarters": len(trq), "kind": "retrospective simulation (label-blind)"}))
    fc = pd.concat(fc, ignore_index=True)
    fc.to_csv(EXP / "FROZEN_2026_N2.csv", index=False)
    res["frozen_2026_N2_sha256"] = hashlib.sha256((EXP / "FROZEN_2026_N2.csv").read_bytes()).hexdigest()

    # provenance of the v3 frozen forecasts
    prov = {}
    for tab in ("psa_indicators", "oil_prices", "bsp_macro", "pagasa_climate", "psa_rice_prices", "fssi_quarterly",
                "trigger_proportions", "sws_hunger", "corpus_geocoded", "province_rainfall"):
        df = pd.read_parquet(f"data/processed/{tab}.parquet")
        prov[tab] = str(df["fetched_at"].max()) if "fetched_at" in df else "no fetched_at column"
    res["frozen_2026_provenance"] = {
        "origins": {"2026-Q1": "2026-01-01", "2026-Q2": "2026-04-01"},
        "source_fetched_at_max": prov,
        "sws_used": {"2026-Q1": W.sws_known("2025-Q4")[3], "2026-Q2": W.sws_known("2026-Q1")[3],
                     "release_of_2025-Q1_round": str(REL["2025-Q1"].date())},
        "government_values_used": {"2026-Q1": "quarter 2025-Q3 (strict timing)", "2026-Q2": "quarter 2025-Q4 (strict timing)"},
        "classification": "RETROSPECTIVE SIMULATION: every input table was fetched after both origins, so values reflect current vintages, not what was published at the origin. Label-blind: no 2026 SWS round is in the project.",
    }
    (EXP / "stageA_results.json").write_text(json.dumps(res, indent=2, default=str))
    return res


if __name__ == "__main__":
    r = main()
    print(json.dumps({k: (v["metrics"]["correct"], v["metrics"]["accuracy_mean_quarter"]) for k, v in r["results"].items()}, default=str))
