"""
PFI engine: build the model once, issue the next-quarter forecast from the saved artifact, keep a prospective register.

    python -m app.pfi.engine build     # fit level + bridge, write data/pfi/model/pfi_model.json and data/pfi/out/evaluation.json
    python -m app.pfi.engine issue     # forecast for the next calendar quarter (AIPHEED_NOW overrides the date)

`issue` never refits: it reads the sealed artifact and refuses to run if the artifact is missing or its hash does not
match. Every issued forecast is appended to data/pfi/out/register.jsonl once per issue quarter (never overwritten), so
it can be scored when the next FIES wave (FNRI NNS / PSA) is published.

State of the regional food-insecurity level (logit scale):
    2023  direct CALABARZON FIES estimate (verified, 19.1%, CI 17.0-21.1)
    2025  bridge prediction from 2023 combined with the 2025 FNRI Updating Survey value (provisional secondary; its SE is
          not published, so the 2023 SE x 1.5 is assumed) by inverse-variance weighting. The bridge was scored on this
          wave before the update (evaluation.json: bridge.holdout).
    T     2025 state bridged by lambda x (logit SWS12_T - logit SWS12_2025); SWS12_T uses observed and projected quarters.
Province p at any time: expit(logit region_t + delta_p), delta_p = benchmarked level-model offset (2023).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from app.fi9 import quarters as Q
from app.paths import BACKEND_DIR
from app.pfi import MODEL, OUT, PROVINCES, VERSION
from app.pfi import model as M
from app.pfi import sources as S
from app.pfi.sources import expit, logit

ARTIFACT = MODEL / "pfi_model.json"
FI9_MODEL = BACKEND_DIR / "data" / "fi9" / "model" / "lead1_model.json"
PROVISIONAL_SE_FACTOR = 1.5
DRIFT_SD_LOGIT = 0.10
ACCURACY_TARGET = 0.75


class ArtifactMissing(RuntimeError):
    pass


def now() -> pd.Timestamp:
    """Serving clock in Philippine time (the dashboard's calendar); AIPHEED_NOW overrides it for tests and replays."""
    v = os.getenv("AIPHEED_NOW")
    return pd.Timestamp(v).normalize() if v else pd.Timestamp(datetime.now(ZoneInfo("Asia/Manila")).date().isoformat())


def _sha(body: dict) -> str:
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=float).encode()).hexdigest()


def _jsonable(x):
    if isinstance(x, dict):
        return {k: _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    if isinstance(x, (np.floating, float)):
        return None if not np.isfinite(x) else round(float(x), 6)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, np.ndarray):
        return _jsonable(x.tolist())
    return x


# --------------------------------------------------------------------------------------------------- province inputs
def _province_covariates(covs: list[str], year: int = 2023) -> pd.DataFrame:
    """Provincial covariates with their published sampling error, shrunk toward the CALABARZON value by reliability
    (empirical Bayes on the covariate, as in Ybarra & Lohr 2008): x~ = w x + (1-w) x_region, w = tau2 / (tau2 + se2)."""
    rows = []
    for c in covs:
        if c in ("poverty", "subsistence"):
            fname = ("psa_poverty_incidence_all_regions_2018_2023.csv" if c == "poverty"
                     else "psa_subsistence_families_2018_2023.csv")
            d = pd.read_csv(S.RAW / fname, dtype=str)
            name = d.iloc[:, 0].str.replace(r"^\.+", "", regex=True).str.replace(r"\s*(r\d,?\s*)?((\d|[a-z])/,?\s*|\*\*,?\s*)+$", "", regex=True).str.strip()
            vcol = next(k for k in d.columns if ("Incidence" in k) and k.endswith(str(year)))
            ccol = next(k for k in d.columns if k.startswith("Coefficient of Variation") and k.endswith(str(year)))
            reg = d[name == "Region IV-A (CALABARZON)"]
            x_reg = float(reg[vcol].iloc[0])
            for p in PROVINCES:
                r = d[name == p]
                v, cv = float(r[vcol].iloc[0]), float(r[ccol].iloc[0]) / 100
                rows.append({"covariate": c, "province": p, "value": v, "cv": cv, "region_value": x_reg})
        else:
            pt = S.province_table(year).set_index("province")[c]
            reg = S.region_table(year).set_index("key").loc["IV-A", c]
            for p in PROVINCES:
                rows.append({"covariate": c, "province": p, "value": float(pt[p]), "cv": np.nan, "region_value": float(reg)})
    t = pd.DataFrame(rows)
    out = []
    for c, g in t.groupby("covariate", sort=False):
        rate = c in M.RATE_COVS
        z = logit(g["value"] / 100) if rate else g["value"].to_numpy(float)
        zr = float(logit(g["region_value"].iloc[0] / 100)) if rate else float(g["region_value"].iloc[0])
        se = (g["cv"] / (1 - g["value"] / 100)).to_numpy(float) if rate else np.zeros(len(g))
        se = np.nan_to_num(se, nan=0.0)
        tau2 = max(float(np.var(z, ddof=1) - np.mean(se ** 2)), 0.0)
        w = np.where(se > 0, tau2 / (tau2 + se ** 2), 1.0) if tau2 > 0 else np.where(se > 0, 0.0, 1.0)
        zs = w * z + (1 - w) * zr
        post_sd = np.sqrt(w * se ** 2)
        for i, (_, r) in enumerate(g.iterrows()):
            out.append({**r.to_dict(), "scale": "logit" if rate else "raw", "z": float(z[i]), "se_z": float(se[i]),
                        "reliability_w": float(w[i]), "z_shrunk": float(zs[i]), "z_posterior_sd": float(post_sd[i]),
                        "tau2_between_provinces": tau2, "z_region": zr})
    return pd.DataFrame(out)


def _direct_offsets() -> list[dict]:
    h = S.hfias_2015().set_index("geography")
    p_r = h.loc["CALABARZON", "mod_sev_pct"] / 100
    se_r = h.loc["CALABARZON", "se_pp"] / 100 / (p_r * (1 - p_r))
    out = []
    for p in PROVINCES:
        q = h.loc[p, "mod_sev_pct"] / 100
        se = h.loc[p, "se_pp"] / 100 / (q * (1 - q))
        out.append({"province": p, "hfias_mod_sev_pct": float(100 * q), "offset_logit": float(logit(q) - logit(p_r)),
                    "se_logit": float(np.sqrt(se ** 2 + se_r ** 2)), "n_households": int(h.loc[p, "n_households"])})
    return out


def _population_weights() -> pd.Series:
    pop = S.population().groupby("province_name")["population_2024"].sum()
    return pop.reindex(PROVINCES)


# -------------------------------------------------------------------------------------------------------------- build
def build(as_of=None) -> dict:
    as_of = pd.Timestamp(as_of) if as_of else now()
    f = S.fies()
    used = f[f["in_study_window"] & (f["status"] == "verified_primary")]
    late = used[used["available_from"] > as_of]
    if len(late):
        raise RuntimeError(f"build as of {as_of.date()} would use unreleased FIES rows: {late[['key', 'year']].values.tolist()}")
    nat23 = float(f[(f["key"] == "PH") & (f["year"] == 2023)]["pct"].iloc[0])
    R = S.region_table(2023)
    scores = {k: M.loo_level(R, c, nat23) for k, c in M.CANDIDATES.items()}
    sel = M.select_level(scores)
    fit = M.fit_level(R, M.CANDIDATES[sel])
    pc = _province_covariates(fit["covariates"])
    rng = np.random.default_rng(M.SEED)
    br = M.bridge_lambda(rng)
    hold = M.bridge_holdout(br["lambda"], br["draws"])
    iva = f[(f["key"] == "IV-A") & (f["year"] == 2023)].iloc[0]
    se23 = (float(iva["ci_high"]) - float(iva["ci_low"])) / (2 * 1.96)
    r25 = f[(f["key"] == "IV-A") & (f["year"] == 2025)]
    body = {"version": VERSION, "built_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "as_of": as_of.date().isoformat(), "seed": M.SEED, "n_draws": M.N_DRAWS,
            "outcome": "FIES moderate-or-severe food insecurity, % of households (SDG 2.1.2; 12-month recall)",
            "level": {"selected": sel, "selection_rule": f"lowest LOO MAE (pp); fewer covariates within {M.TIE_PP} pp",
                      "terms": fit["terms"], "beta": fit["beta"], "cov": fit["cov"], "residual_var_logit": fit["s2"],
                      "dof": fit["dof"], "n_regions": int(len(R)), "fit_year": 2023},
            "province_covariates": pc.to_dict(orient="records"),
            "composite": {"direct_source": "FNRI 2015 Food Security Survey, HFIAS moderate+severe, province minus CALABARZON "
                                           "(verified, published SEs; n 735-1,076 households per province)",
                          "drift_sd_logit": DRIFT_SD_LOGIT,
                          "drift_note": "assumed allowance for change since 2015 and for HFIAS vs FIES (about +/-2 points at "
                                        "20%); sensitivity at 0 and 0.2 in evaluation.json",
                          "direct": _direct_offsets()},
            "benchmark": {"region": "Region IV-A", "year": 2023, "pct": float(iva["pct"]), "se_pp": se23,
                          "ci95": [float(iva["ci_low"]), float(iva["ci_high"])]},
            "state_update_2025": ({"pct": float(r25["pct"].iloc[0]), "status": str(r25["status"].iloc[0]),
                                   "assumed_se_pp": se23 * PROVISIONAL_SE_FACTOR} if len(r25) else None),
            "bridge": {k: v for k, v in br.items() if k != "draws"},
            "population_weights": _population_weights().astype(int).to_dict(),
            "projection": {"source": "FI9 damped persistence (frozen)", "fi9_artifact": str(FI9_MODEL.relative_to(BACKEND_DIR)),
                           **{k: json.loads(FI9_MODEL.read_text())["params"][k] for k in ("phi", "conformal_halfwidth_95")}}}
    body = _jsonable(body)
    body["sha256"] = _sha(body)
    MODEL.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(body, indent=1))
    ev = evaluation_body(body, scores, hold, br)
    (OUT / "evaluation.json").write_text(json.dumps(_jsonable(ev), indent=1))
    return body


def load_artifact() -> dict:
    if not ARTIFACT.exists():
        raise ArtifactMissing(f"{ARTIFACT.relative_to(BACKEND_DIR)} not built yet: run `python -m app.pfi.engine build`")
    a = json.loads(ARTIFACT.read_text())
    sha = a.pop("sha256")
    if _sha(a) != sha:
        raise ArtifactMissing("pfi_model.json hash mismatch: the artifact was edited after it was built")
    a["sha256"] = sha
    return a


# ---------------------------------------------------------------------------------------------------------- simulate
def _synthetic_offsets(a: dict, rng: np.random.Generator, n: int) -> np.ndarray:
    """Draws of the level model's province offsets relative to their population-weighted mean (logit), carrying
    coefficient uncertainty and the sampling error of the provincial covariates."""
    lv = a["level"]
    beta = rng.multivariate_normal(np.array(lv["beta"]), np.array(lv["cov"]), n)          # (n, k)
    pc = pd.DataFrame(a["province_covariates"])
    cols = [np.ones((n, len(PROVINCES)))]
    for c in lv["terms"][1:]:
        name = c.replace("logit(", "").rstrip(")")
        g = pc[pc["covariate"] == name].set_index("province").reindex(PROVINCES)
        cols.append(g["z_shrunk"].to_numpy(float) + rng.standard_normal((n, len(PROVINCES))) * g["z_posterior_sd"].to_numpy(float))
    eta = np.einsum("npk,nk->np", np.stack(cols, axis=2), beta)
    return eta - (eta * _weights(a)).sum(axis=1, keepdims=True)


def _weights(a: dict) -> np.ndarray:
    w = np.array([a["population_weights"][p] for p in PROVINCES], float)
    return w / w.sum()


def composite_offsets(a: dict, rng: np.random.Generator, n: int, drift_sd: float | None = None) -> dict:
    """Fay-Herriot composite of each province's offset from the regional level (logit):
        direct    FNRI 2015 HFIAS moderate+severe, province minus CALABARZON (verified; published SEs), with extra
                  variance drift_sd**2 for the eight years and the change of instrument since;
        synthetic the level model's offset (regional regression applied to provincial covariates);
        weight on direct  gamma = sigma_u2 / (sigma_u2 + v_direct), sigma_u2 = the level model's between-area variance.
    Returns the composite mean, variance and weight per province (the provincial evidence the directive requires)."""
    drift_sd = a["composite"]["drift_sd_logit"] if drift_sd is None else drift_sd
    syn = _synthetic_offsets(a, rng, n)
    h = pd.DataFrame(a["composite"]["direct"]).set_index("province").reindex(PROVINCES)
    v_dir = h["se_logit"].to_numpy(float) ** 2 + drift_sd ** 2
    s_u2 = a["level"]["residual_var_logit"]
    gamma = s_u2 / (s_u2 + v_dir)
    m_syn, v_syn = syn.mean(axis=0), syn.var(axis=0)
    mean = gamma * h["offset_logit"].to_numpy(float) + (1 - gamma) * m_syn
    var = gamma * v_dir + (1 - gamma) ** 2 * v_syn
    return {"mean": mean, "var": var, "gamma": gamma, "synthetic_mean": m_syn, "direct": h["offset_logit"].to_numpy(float)}


def _draw_offsets(a: dict, rng: np.random.Generator, n: int) -> tuple[np.ndarray, np.ndarray]:
    """Draws of the 2023 province levels (logit) and the regional 2023 anchor (logit), benchmarked per draw."""
    comp = composite_offsets(a, rng, n)
    eta = comp["mean"] + rng.standard_normal((n, len(PROVINCES))) * np.sqrt(comp["var"])
    w = _weights(a)
    bm = a["benchmark"]
    target = np.clip(rng.normal(bm["pct"], bm["se_pp"], n), 1, 99) / 100
    lo, hi = np.full(n, -5.0), np.full(n, 5.0)
    for _ in range(60):
        mid = (lo + hi) / 2
        m = (expit(eta + mid[:, None]) * w).sum(axis=1) < target
        lo, hi = np.where(m, mid, lo), np.where(m, hi, mid)
    c = (lo + hi) / 2
    prov = eta + c[:, None]
    return prov, logit(target)


def _lambda_draws(a: dict, rng: np.random.Generator, n: int) -> np.ndarray:
    br = M.bridge_lambda(rng, n)
    return br["draws"]


def simulate(a: dict, as_of) -> dict:
    """All draws needed for one issue date; deterministic given the artifact and the release-filtered inputs."""
    as_of = pd.Timestamp(as_of)
    rng = np.random.default_rng(a["seed"])
    n = a["n_draws"]
    prov23, reg23 = _draw_offsets(a, rng, n)
    delta = prov23 - reg23[:, None]                                                         # province offsets (logit)
    lam = _lambda_draws(a, rng, n)
    ph, hw = a["projection"]["phi"], a["projection"]["conformal_halfwidth_95"]
    sws23 = M.sws_annual("balance_luzon", 2023, as_of)
    s23 = np.clip(rng.normal(sws23[0], sws23[1], n), 0.5, 99)
    reg_ref, s_ref, ref_year, update = reg23, s23, 2023, None
    st = a.get("state_update_2025")
    if st and pd.Timestamp(S.FIES_RELEASE[2025][0]) <= as_of:
        sws25 = M.sws_annual("balance_luzon", 2025, as_of)
        s25 = np.clip(rng.normal(sws25[0], sws25[1], n), 0.5, 99)
        prior = reg23 + lam * (logit(s25 / 100) - logit(s23 / 100))
        mu_p, v_p = float(np.mean(prior)), float(np.var(prior))
        p25 = st["pct"] / 100
        v_m = (st["assumed_se_pp"] / 100 / (p25 * (1 - p25))) ** 2
        k = v_p / (v_p + v_m)
        post = prior + k * (rng.normal(logit(p25), np.sqrt(v_m), n) - prior)                 # Gaussian posterior draws
        update = {"prior_pct": 100 * float(expit(mu_p)), "measured_pct": st["pct"], "weight_on_measurement": k,
                  "posterior_pct": 100 * float(np.median(expit(post))), "status": st["status"]}
        reg_ref, s_ref, ref_year = post, s25, 2025
    cur_qi = Q.qi_of(as_of)
    tgt_qi = cur_qi + 1
    sws_t = M.project_sws(as_of, tgt_qi, ph, hw)
    sws_c = M.project_sws(as_of, int(S.sws_quarterly("balance_luzon", as_of)["qi"].iloc[-1]), ph, hw)
    w_t = M.window_draws(sws_t["window"], rng, n)
    w_c = M.window_draws(sws_c["window"], rng, n)
    reg_t = reg_ref + lam * (logit(w_t / 100) - logit(s_ref / 100))
    reg_c = reg_ref + lam * (logit(w_c / 100) - logit(s_ref / 100))
    return {"delta": delta, "reg23": reg23, "reg_ref": reg_ref, "ref_year": ref_year, "reg_target": reg_t, "reg_current": reg_c,
            "lam": lam, "sws_target": sws_t, "sws_current": sws_c, "w_t": w_t, "w_c": w_c, "s_ref": s_ref, "update": update,
            "current_qi": cur_qi, "target_qi": tgt_qi}


def _q(x, qs=(0.05, 0.1, 0.5, 0.9, 0.95)):
    return {f"p{int(100 * q):02d}": 100 * float(np.quantile(expit(x), q)) for q in qs}


# ------------------------------------------------------------------------------------------------------------- issue
def issue(as_of=None, register: bool = True) -> dict:
    a = load_artifact()
    as_of = pd.Timestamp(as_of) if as_of else now()
    sim = simulate(a, as_of)
    clock = Q.lead1(as_of)
    bm = a["benchmark"]
    line_gap = (bm["ci95"][1] - bm["ci95"][0]) / 2
    pop = a["population_weights"]
    provinces = []
    for i, p in enumerate(PROVINCES):
        d = sim["delta"][:, i]
        lvl23 = sim["reg23"] + d
        ref = sim["reg_ref"] + d
        cur = sim["reg_current"] + d
        tgt = sim["reg_target"] + d
        m23, mt, mc = (100 * float(np.median(expit(x))) for x in (lvl23, tgt, cur))
        line = m23 + line_gap
        p_high = float(np.mean(100 * expit(tgt) >= line))
        p_rise = float(np.mean(expit(tgt) > expit(cur)))

        def f(z, d_i=float(np.median(d))):
            return 100 * float(expit(np.median(sim["reg23"]) + z["structure"] * d_i + z["hunger"]))
        dyn = float(np.median(sim["reg_target"] - sim["reg23"]))
        sh = M.shapley_two(f, {"structure": 0.0, "hunger": 0.0}, {"structure": 1.0, "hunger": dyn})
        provinces.append({
            "province": p, "population_2024": int(pop[p]),
            "estimate_2023": {"pct": m23, "kind": "model estimate anchored to the 2023 CALABARZON survey", **_q(lvl23)},
            "current": {"pct": mc, "kind": "model estimate (latest SWS quarters, no projection)", "through_quarter":
                        sim["sws_current"]["latest_quarter"], **_q(cur)},
            "forecast": {"pct": mt, "kind": "forecast", "target_quarter": clock["target_quarter"], **_q(tgt),
                         "class": "HIGH" if p_high >= 0.5 else "LOW", "p_high": p_high, "p_rise_vs_current": p_rise,
                         "high_line_pct": line,
                         "persons_in_food_insecure_households_approx": int(round(mt / 100 * pop[p], -3))},
            "contributions_pp": {"regional_2023_level": 100 * float(np.median(expit(sim["reg23"]))),
                                 "province_structure": sh["structure"], "change_since_2023": sh["hunger"]},
        })
    ranks = sorted(provinces, key=lambda r: -r["forecast"]["pct"])
    for k, r in enumerate(ranks, 1):
        r["priority_rank"] = k
    region = {"current_pct": 100 * float(np.median(expit(sim["reg_current"]))),
              "forecast": {"pct": 100 * float(np.median(expit(sim["reg_target"]))), **_q(sim["reg_target"])},
              "survey_2023_pct": bm["pct"], "survey_2023_ci95": bm["ci95"], "state_update_2025": sim["update"]}
    body = {"version": VERSION, "model_version": VERSION, "artifact_sha256": a["sha256"],
            "issued_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "issue_date": as_of.date().isoformat(),
            "current_quarter": clock["current_quarter"], "target_quarter": clock["target_quarter"], "horizon": 1,
            "what_is_forecast": a["outcome"], "geographic_resolution": "province (5); LGUs inherit their province's value",
            "data_cutoff": max(sim["sws_target"]["latest_published"], S.FIES_RELEASE[sim["ref_year"]][0]),
            "inputs": {"sws_balance_luzon_window": sim["sws_target"]["window"], "sws_latest_quarter": sim["sws_target"]["latest_quarter"],
                       "sws_latest_published": sim["sws_target"]["latest_published"], "sws_normal_5y": sim["sws_target"]["normal_5y"],
                       "state_reference_year": sim["ref_year"], "lambda_median": float(np.median(sim["lam"])),
                       "level_model": a["level"]["selected"]},
            "region": region, "provinces": provinces,
            "class_rule": (f"HIGH when the chance is at least 50% that the province's rate in {clock['target_quarter']} is above "
                           f"its 2023 estimate plus {line_gap:.1f} points (the 2023 survey's margin of error): significantly "
                           "above the last measured level."),
            "evidence_status": ("Forecast from a survey-anchored model. Provincial levels are model estimates (no provincial "
                                "FIES measurement exists after the 2023 regional one); quarterly values are not measured by any "
                                "survey, so this forecast cannot be scored quarterly. It is registered and will be scored "
                                "against the next published FIES wave.")}
    out = _jsonable(body)
    out["sha256"] = _sha({k: v for k, v in out.items() if k != "issued_utc"})
    (OUT / "forecast.json").write_text(json.dumps(out, indent=1))
    if register:
        _register(out)
    return out


def _register(f: dict) -> None:
    p = OUT / "register.jsonl"
    seen = set()
    if p.exists():
        seen = {json.loads(line)["issue_quarter"] for line in p.read_text().splitlines() if line.strip()}
    if f["current_quarter"] in seen:
        return
    rec = {"issue_quarter": f["current_quarter"], "target_quarter": f["target_quarter"], "issue_date": f["issue_date"],
           "artifact_sha256": f["artifact_sha256"], "forecast_sha256": f["sha256"],
           "region_pct": f["region"]["forecast"]["pct"],
           "provinces": {r["province"]: {"pct": r["forecast"]["pct"], "p05": r["forecast"]["p05"], "p95": r["forecast"]["p95"],
                                         "class": r["forecast"]["class"]} for r in f["provinces"]},
           "scored": None, "score_against": "next FIES wave covering the target quarter (FNRI NNS/ENNS or PSA FIES)"}
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec) + "\n")


def register() -> list[dict]:
    p = OUT / "register.jsonl"
    return [json.loads(line) for line in p.read_text().splitlines() if line.strip()] if p.exists() else []


# -------------------------------------------------------------------------------------------------------- evaluation
def evaluation_body(a: dict, scores: dict, hold: dict, br: dict) -> dict:
    sel = a["level"]["selected"]
    s = scores[sel]
    c = s["classification_above_national"]
    groups = {
        "Market and food prices": {"families": ["A1", "A2", "A3"], "tested_as": "M4 rice inflation; M6 poverty + rice inflation",
                                   "result": _vs(scores, "M4 rice inflation", "M0 no covariate (mean of regions)", sel),
                                   "role": "Secondary task: provincial food-price pressure forecast (FI10). Not a level predictor."},
        "Climate and agricultural production": {"families": ["C1", "C2", "C3", "C4"],
                                                "tested_as": "not testable for the level: no region-level 2023 series on file for all 17 FIES regions",
                                                "result": None, "role": "Context and drivers of the price task; shown as supporting indicators."},
        "Employment and remittances": {"families": ["E1", "E2"], "tested_as": "M3 unemployment; M5 poverty + unemployment",
                                       "result": _vs(scores, "M3 unemployment", "M0 no covariate (mean of regions)", sel),
                                       "role": "Supporting indicator. Remittances (E2) are national only and cannot be tested across regions."},
        "Poverty and social vulnerability": {"families": ["V1"], "tested_as": "M1 poverty; M2 subsistence (food poverty)",
                                             "result": _vs(scores, sel, "M0 no covariate (mean of regions)", sel),
                                             "role": "Selected: sets the provincial level (structure)."},
        "News and NLP": {"families": ["N1"], "tested_as": "no region-level news series matched to the FIES regions",
                         "result": None, "role": "Food-stress intelligence shown beside the forecast; not a model input."},
        "Regional hunger (SWS)": {"families": ["H1"], "tested_as": "bridge lambda (national 2021->2023) and held-out CALABARZON 2025",
                                  "result": {"holdout_error_pp": hold["error_pp"], "no_change_error_pp": hold["no_change_baseline_error_pp"]},
                                  "role": "Selected: moves the level between survey waves and drives the next-quarter forecast."},
    }
    fi9 = _fi9_component()
    hfias, enns, sens = _consistency(a)
    level_met = c["accuracy"] >= ACCURACY_TARGET and (c["balanced_accuracy"] or 0) >= ACCURACY_TARGET
    return {
        "version": VERSION, "artifact_sha256": a["sha256"], "built_utc": a["built_utc"],
        "level": {"task": "Food-insecurity level (FIES moderate-or-severe), 17 regions, 2023, leave-one-region-out",
                  "selection_rule": a["level"]["selection_rule"], "selected": sel, "candidates": scores,
                  "classification_target": "region above the national prevalence (31.4%)"},
        "bridge": {"lambda": br["lambda"], "lambda_ci90": br["lambda_ci90"], "fit": br["fit_interval"],
                   "sensitivity_pre_window": br["sensitivity_pre_window"], "holdout": hold},
        "provincial_consistency": {"hfias_2015": hfias, "enns_secondary": enns, "sensitivity": sens},
        "regional_quarterly_component": fi9,
        "information_groups": groups,
        "objective_75": {
            "target": ACCURACY_TARGET,
            "level_classification": {"accuracy": c["accuracy"], "accuracy_ci95": c["accuracy_ci95"],
                                     "balanced_accuracy": c["balanced_accuracy"], "n": c["n"], "met": level_met,
                                     "type": "independent observation-level validation (leave-one-region-out, one wave)"},
            "bridge_holdout_class": {"correct": hold["observed_class"] == hold["predicted_class"], "n": 1,
                                     "type": "one held-out survey wave (provisional value)"},
            "provincial_quarterly": {"met": None, "status": "NOT EVALUABLE: no quarterly or repeated provincial FIES "
                                     "measurement exists; scored prospectively from the register"},
            "statement": ("The 75% target is met for classifying measured food-insecurity levels of held-out regions "
                          f"({c['tp'] + c['tn']}/{c['n']}; 95% CI {c['accuracy_ci95'][0]:.2f}-{c['accuracy_ci95'][1]:.2f}). It is "
                          "not shown for provincial next-quarter forecasts, which no survey measures; those are registered "
                          "and scored when the next FIES wave is published." if level_met else
                          "The 75% target is not met on the held-out regions."),
        },
    }


def _vs(scores: dict, k: str, base: str, sel: str) -> dict:
    return {"model": k, "loo_mae_pp": scores[k]["mae_pp"], "baseline_loo_mae_pp": scores[base]["mae_pp"],
            "accuracy_above_national": scores[k]["classification_above_national"]["accuracy"],
            "selected_model_loo_mae_pp": scores[sel]["mae_pp"]}


def _fi9_component() -> dict | None:
    z = BACKEND_DIR / "data" / "fi9z" / "out" / "evaluation.json"
    if not z.exists():
        return None
    e = json.loads(z.read_text())["evaluation"]["OP1"]
    out = {}
    for k in ("C0 damped persistence (production)", "Naive persistence"):
        if k in e:
            m = e[k]["full"]
            out[k] = {kk: m.get(kk) for kk in ("n", "accuracy", "balanced_accuracy", "high_recall", "high_precision", "low_recall", "brier")}
    return {"task": "SWS hunger in Balance Luzon significantly above normal, next quarter (regional; walk-forward 2010-2026)",
            "note": "Regional measured hunger, the input of the bridge; not a provincial food-insecurity result.", "models": out}


def _consistency(a: dict) -> tuple[dict, dict, dict]:
    """Agreement of the provincial 2023 estimates with the provincial survey values, and their sensitivity to the
    composite's assumptions. HFIAS 2015 is an input of the composite, so its agreement is not independent; the ENNS
    values (secondary) are not used anywhere in the model."""
    from scipy.stats import spearmanr

    def est(drift=None, gamma_zero=False):
        rng = np.random.default_rng(a["seed"])
        if gamma_zero:
            off = _synthetic_offsets(a, rng, 4000).mean(axis=0)
        else:
            off = composite_offsets(a, rng, 4000, drift)["mean"]
        c = M.benchmark_shift(off, _weights(a), a["benchmark"]["pct"] / 100)
        return pd.Series(100 * expit(off + c), index=PROVINCES)

    base = est()
    h = S.hfias_2015().set_index("geography")["mod_sev_pct"].reindex(PROVINCES)
    e = S.workbook_secondary()
    e = e[e["indicator"].str.startswith("Moderate")].set_index("province")
    ev, ey = e["pct"].reindex(PROVINCES), e["year"].reindex(PROVINCES)
    hf = {"what": "2015 FNRI HFIAS moderate+severe by province (verified; an input of the composite, so not independent)",
          "spearman": float(spearmanr(base, h).correlation), "n": 5,
          "rows": [{"province": p, "model_2023_pct": float(base[p]), "hfias_2015_pct": float(h[p])} for p in PROVINCES]}
    en = {"what": "ENNS moderate-to-severe by province (RDP results matrix; secondary, unverified, instrument not stated, "
                  "years differ by province); not used by the model",
          "spearman": float(spearmanr(base, ev).correlation), "n": 5,
          "rows": [{"province": p, "model_2023_pct": float(base[p]), "enns_pct": float(ev[p]), "enns_year": int(ey[p])}
                   for p in PROVINCES]}
    variants = {"composite, drift 0.10 (served)": base, "composite, drift 0": est(0.0), "composite, drift 0.20": est(0.2),
                "synthetic only (level model)": est(gamma_zero=True)}
    sens = {k: {"by_province_pct": {p: float(v[p]) for p in PROVINCES}, "spearman_vs_enns": float(spearmanr(v, ev).correlation),
                "range_pp": float(v.max() - v.min())} for k, v in variants.items()}
    return hf, en, sens


def main() -> None:
    ap = argparse.ArgumentParser(prog="python -m app.pfi.engine")
    ap.add_argument("cmd", choices=["build", "issue"])
    ap.add_argument("--as-of", default=None)
    args = ap.parse_args()
    r = build(args.as_of) if args.cmd == "build" else issue(args.as_of)
    print(json.dumps({k: r[k] for k in ("version", "sha256") if k in r}, indent=1))


if __name__ == "__main__":
    main()
