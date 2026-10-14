"""
app/quarterly/pcf_engine.py
---------------------------
E24v2 forecasting engine: the probabilistic component forecaster (PCF), applied with the same publication-time
rules as the research runs (experiments/2026-10-14_E24v2_Reliable_Forecasting/FROZEN_EVALUATION_PROTOCOL.md).

The approved label is S1 = H + 2D (HIGH if S1 > tau):
  H  regional SWS hunger (Balance Luzon; one value shared by the five provinces), measured by a sample survey;
  D  provincial food inflation minus the five-province mean (PSA provincial CPI), a provincial measurement.
The engine forecasts each component at its own geography and combines them:
  H: local level (random walk + sampling noise) on the SWS rounds published before the origin;
  D: least squares without intercept on the latest published quarterly D (PCF) and, for the provincial
     price-pressure indicator, also on Dnow = months 1-2 of the reference quarter (PCF-D-NOW);
  P(S1 > tau) = 1 - Phi((tau - mu_H - 2 mu_D) / sqrt(V_H + 4 sigma_D^2)).
Every number in the output is either an official measurement (labelled "measured") or a model estimate
(labelled "model"), and every forecast carries its interval and the validation status of its lead.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm

SIGMA_ETA_GRID = np.round(np.arange(0.0, 8.0001, 0.1), 1)
N_SWS = 600
PROVINCES = ["PH040100000", "PH040200000", "PH040300000", "PH040400000", "PH040500000"]
PROVINCE_NAMES = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon",
                  "PH040400000": "Rizal", "PH040500000": "Batangas"}
FIRST_D_QUARTER = "2021-Q1"      # E25 fix F1: study window starts 2021-Q1 (E24v2 trained D from 1995)
STUDY_FIRST_QUARTER = "2021-Q1"


def qk(q: str) -> int:
    y, n = q.split("-Q")
    return int(y) * 4 + int(n) - 1


def qs(i: int) -> str:
    return f"{i // 4}-Q{i % 4 + 1}"


def samp_var(h: float, n: int = N_SWS) -> float:
    h = float(np.clip(h, 0.5, 99.5))
    return h * (100.0 - h) / n


# --------------------------------------------------------------------------------------------- H component
def _filter(times, ys, q, n):
    order = np.argsort(times, kind="stable")
    t, y = np.asarray(times, float)[order], np.asarray(ys, float)[order]
    L, P = y[0], samp_var(y[0], n)
    ll, last = 0.0, t[0]
    for i in range(1, len(y)):
        P = P + q * (t[i] - last)
        last = t[i]
        F = P + samp_var(y[i], n)
        v = y[i] - L
        ll += -0.5 * (np.log(2 * np.pi * F) + v * v / F)
        K = P / F
        L, P = L + K * v, (1 - K) * P
    return ll, L, P, last


def h_forecast(times, ys, target_time: float, n: int = N_SWS) -> dict:
    times, ys = np.asarray(times, float), np.asarray(ys, float)
    if len(ys) < 2:
        raise ValueError("the H component needs at least two published SWS rounds")
    if target_time <= times.max():
        raise ValueError("the target quarter must be after the last observed round")
    best = None
    for se in SIGMA_ETA_GRID:
        ll, L, P, last = _filter(times, ys, se * se, n)
        if best is None or ll > best[0] + 1e-12:
            best = (ll, se, L, P, last)
    ll, se, L, P, last = best
    g = target_time - last
    return {"mu_H": float(L), "V_H": float(P + g * se * se + samp_var(L, n)), "sigma_eta": float(se),
            "gap_quarters": float(g), "n_rounds": int(len(ys)), "last_round_quarter": qs(int(last))}


def _usable_from(r: pd.DataFrame) -> pd.Series:
    """E25 fix F2: the time from which a round may be used. A verified publication date where one exists; for a
    round whose date is unverified, the documented upper bound (published_eff, e.g. the time the authorized file
    shows it had been fetched). No date at all = never usable. E24v2 dropped every unverified round, so an
    authorized round (e.g. March/June 2026) stayed unused even at origins long after it was certainly public."""
    pub = pd.to_datetime(r["published"], errors="coerce", format="ISO8601")   # mixed ISO forms (E25 fix F3)
    verified = r["date_type"].astype(str).str.startswith("verified")
    eff = pd.to_datetime(r["published_eff"], errors="coerce", format="ISO8601") if "published_eff" in r.columns else pd.Series(pd.NaT, index=r.index)
    return pub.where(verified & pub.notna(), eff)


def rounds_at_origin(rounds: pd.DataFrame, origin: pd.Timestamp, include_supplementary: bool = False) -> pd.DataFrame:
    """SWS rounds usable at the origin: usable-from time (verified date, else documented upper bound) strictly
    before the origin; rows without either are unusable. Rounds before the study window are never used."""
    r = rounds.copy()
    o = origin.tz_localize(None) if origin.tzinfo else origin
    u = _usable_from(r)
    ok = u.notna() & (u < o) & (r["quarter"].map(qk) >= qk(STUDY_FIRST_QUARTER))
    kind = r["definition_A"].astype(bool) | (include_supplementary & (r["source"] == "supplementary"))
    return r[ok & kind]


# --------------------------------------------------------------------------------------------- D component
def d_fit(Dm: dict, Nm: dict, t: int, k: int, use_now: bool):
    X, y = [], []
    for tp in range(qk(FIRST_D_QUARTER) + 1, t - k):          # target t'+k <= t-1 (published)
        for p in PROVINCES:
            dl, dt = Dm.get((p, tp - 1)), Dm.get((p, tp + k))
            if dl is None or dt is None or np.isnan(dl) or np.isnan(dt):
                continue
            if use_now:
                dn = Nm.get((p, tp))
                if dn is None or np.isnan(dn):
                    continue
                X.append([dn, dl])
            else:
                X.append([dl])
            y.append(dt)
    if len(y) < 40:
        raise ValueError("the D component needs at least 40 published province-quarter pairs")
    X, y = np.asarray(X, float), np.asarray(y, float)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ beta
    return beta, float(np.sqrt((r ** 2).sum() / max(len(y) - 1, 1))), len(y)


def d_inputs_at_origin(Dm: dict, Nm: dict, t: int, use_now: bool) -> dict:
    """Latest published quarterly D is quarter t-1; Dnow is months 1-2 of quarter t (published before O(t))."""
    out = {}
    for p in PROVINCES:
        dl = Dm.get((p, t - 1))
        dn = Nm.get((p, t)) if use_now else 0.0
        if dl is None or (use_now and dn is None):
            raise KeyError(f"missing D input for {p} at origin of {qs(t)}")
        out[p] = [dn, dl] if use_now else [dl]
    return out


# --------------------------------------------------------------------------------------------- combine
def threshold_at(S1: pd.DataFrame, rounds: pd.DataFrame, t: int, origin: pd.Timestamp) -> tuple[float, int]:
    """E23 rule: median S1 over province-quarters <= t-1 whose definition-A rounds were ALL published before O(t)."""
    r = rounds[rounds["definition_A"].astype(bool)].copy()
    r["usable_from"] = _usable_from(r)
    o = origin.tz_localize(None) if origin.tzinfo else origin
    ok = set()
    for q, g in r.groupby("quarter"):
        if qk(STUDY_FIRST_QUARTER) <= qk(q) <= t - 1 and g["usable_from"].notna().all() and (g["usable_from"] < o).all():
            ok.add(q)
    s = S1[S1["quarter"].isin(ok)]["S1"]
    return float(s.median()), int(len(s))


def signal_level(p: float) -> str:
    if p >= 0.80 or p <= 0.20:
        return "STRONG"
    if p >= 0.65 or p <= 0.35:
        return "MODERATE"
    return "UNCERTAIN"


def forecast(origin: pd.Timestamp, t: int, leads, rounds: pd.DataFrame, S1: pd.DataFrame, Dm: dict, Nm: dict,
             evidence: dict) -> dict:
    """Full PCF forecast at origin O(t) for the given leads. evidence = {"T1": {lead: {...}}, "T2": {...}}."""
    tau, n_tau = threshold_at(S1, rounds, t, origin)
    rr = rounds_at_origin(rounds, origin)
    times, ys = rr["quarter"].map(qk).to_numpy(float), rr["H"].to_numpy(float)
    out = {"origin": origin.isoformat(), "reference_quarter": qs(t), "threshold": tau, "threshold_labels": n_tau,
           "sws_rounds_used": rr[["quarter", "H", "published"]].astype(str).to_dict("records"), "leads": {}}
    for k in leads:
        hf = h_forecast(times, ys, float(t + k))
        b3, s3, n3 = d_fit(Dm, Nm, t, k, False)
        b4, s4, n4 = d_fit(Dm, Nm, t, k, True)
        x3, x4 = d_inputs_at_origin(Dm, Nm, t, False), d_inputs_at_origin(Dm, Nm, t, True)
        ev1 = evidence.get("T1", {}).get(str(k), {"status": "NOT_EVALUATED"})
        ev2 = evidence.get("T2", {}).get(str(k), {"status": "NOT_EVALUATED"})
        prov = {}
        for p in PROVINCES:
            muD = float(np.dot(b3, x3[p]))
            sd = float(np.sqrt(hf["V_H"] + 4 * s3 ** 2))
            mu = hf["mu_H"] + 2 * muD
            ph = float(1 - norm.cdf((tau - mu) / sd))
            muD4 = float(np.dot(b4, x4[p]))
            pp = float(norm.cdf(muD4 / max(s4, 1e-9)))
            prov[p] = {
                "province": PROVINCE_NAMES[p],
                "risk": {"p_high": ph, "decision": "HIGH" if ph >= 0.5 else "LOW", "signal": signal_level(ph),
                         "S1_forecast": mu, "S1_80pct_interval": [mu - 1.2816 * sd, mu + 1.2816 * sd],
                         "threshold": tau, "evidence": ev1, "indicative_only": ev1.get("status") != "VALIDATED",
                         "components": {"regional_hunger_H": {"value": hf["mu_H"], "kind": "model (filtered SWS level, regional)",
                                                              "contribution": hf["mu_H"]},
                                        "provincial_price_pressure_2D": {"value": muD, "kind": "model (provincial)",
                                                                         "contribution": 2 * muD}}},
                "price_pressure": {"p_above_regional_mean": pp, "D_forecast": muD4,
                                   "D_80pct_interval": [muD4 - 1.2816 * s4, muD4 + 1.2816 * s4],
                                   "signal": signal_level(pp), "evidence": ev2, "indicative_only": ev2.get("status") != "VALIDATED",
                                   "latest_measured_D": {"quarter": qs(t - 1), "value": float(x4[p][1]), "kind": "measured (PSA)"},
                                   "latest_measured_Dnow": {"months": f"months 1-2 of {qs(t)}", "value": float(x4[p][0]),
                                                            "kind": "measured (PSA)"}}}
        out["leads"][str(k)] = {"target_quarter": qs(t + k), "H": hf, "D_model": {"beta": b3.tolist(), "sigma": s3, "pairs": n3},
                                "D_now_model": {"beta": b4.tolist(), "sigma": s4, "pairs": n4}, "provinces": prov}
    return out


def panels_from_tables(dq: pd.DataFrame, dnow: pd.DataFrame) -> tuple[dict, dict]:
    Dm = {(r.province_code, qk(r.quarter)): float(r.D) for r in dq.itertuples() if pd.notna(r.D)}
    Nm = {(r.province_code, qk(r.quarter)): float(r.Dnow) for r in dnow.itertuples() if pd.notna(r.Dnow)}
    return Dm, Nm
