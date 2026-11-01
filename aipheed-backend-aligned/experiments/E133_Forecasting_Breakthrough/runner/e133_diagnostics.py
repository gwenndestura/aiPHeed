"""
E133 diagnostics (protocol 9683aad section 6; never candidates):
  D1 achievability bound, D2 leading-indicator screen, D3 sharp-increase events, D4 high-hunger bias decomposition,
  D5 OCTA as an early channel.

    python -I runner/e133_diagnostics.py      (after e133_run.py)
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e133_models as M  # noqa: E402
import e133_run as R  # noqa: E402

X, L = R.X, R.L
OUT = R.OUT
SEED = 133


def d1_bound(rr, P) -> pd.DataFrame:
    """Required forecast SD of the true level for 75 % within, and the true-change SD over the horizon implied by
    HFM-NS fitted (a) on all data to 2026-Q3 and (b) on data before the 2024 surge (issue 2024-01-01)."""
    req = L.required_forecast_sd_over_se(0.75)
    rows = []
    for label, issue in (("all data to 2026-Q3", date(2026, 11, 1)), ("before the 2024 surge", date(2024, 1, 1))):
        qa = X.asof(rr, issue)
        idx, Y, Rr = R.matrices(qa)
        f = M.fit_variances(Y, Rr, idx, R.BRK, M.Spec(tau=True))
        for k in L.LEADS:
            g = P[(P.policy == "P-DASH") & (P.lead == k) & (P.n_obs >= 8)]
            h = float(g["h"].median())
            se = float(g["se"].median())
            sd_true = np.sqrt(h * f.q_c + f.q_d * (1 - f.rho ** (2 * h)) / (1 - f.rho ** 2 + 1e-12) + f.tau2)
            share_oracle_now = float(np.mean(np.abs(stats.norm.rvs(size=200000, random_state=SEED) *
                                                    np.sqrt(sd_true ** 2 + se ** 2)) <= L.Z90 * se))
            need = req * se
            rows.append({"fit": label, "lead": k, "median_h": h, "median_se": se, "q_c": f.q_c, "q_d": f.q_d,
                         "rho": f.rho, "tau2": f.tau2, "true_change_sd_over_horizon": sd_true,
                         "required_true_level_error_sd": need,
                         "share_within_if_current_true_level_known": share_oracle_now,
                         "share_of_true_change_variance_a_predictor_must_explain": max(0.0, 1 - need ** 2 / sd_true ** 2)})
    return pd.DataFrame(rows)


def _national_change(rr, issue: date, target: int) -> tuple[float, float]:
    qa = X.asof(rr, issue)
    qt = X.quarter_table(rr)
    latest = qa[qa.qi == qa.qi.max()]["y"].mean()
    tgt = qt[qt.qi == target]
    return float(latest), float(tgt["y"].mean()) if len(tgt) == 4 else np.nan


def d2_screen(rr) -> pd.DataFrame:
    """Spearman of each point-in-time E119 feature (FIRI families A1-H1) and the E133 drivers at the issue against
    the later change in 4-area mean SWS hunger (Lead 1 and Lead 2 targets); permutation p; Holm."""
    reg = pd.read_csv(R.E119)
    reg = reg[reg["lead"] == 1].copy()
    reg["issue"] = pd.to_datetime(reg["issue_date"]).dt.date
    feats = [c for c in reg.columns if not c.endswith(("__status", "__period")) and pd.api.types.is_numeric_dtype(reg[c])
             and c not in ("t", "lead", "target_q", "y_bl_hunger", "y_published", "H1_bl_latest_quarter")]
    drv = {"rice": R.Drivers("rice"), "b30": R.Drivers("b30")}
    rng = np.random.default_rng(SEED)
    rows = []
    for k in (1, 2):
        recs = []
        for x in reg.itertuples():
            D = L.quarter_of(x.issue)
            target = L.qi(D) - 1 + k
            latest, tgt = _national_change(rr, x.issue, target)
            rec = {"issue": x.issue, "chg": tgt - latest}
            for c in feats:
                rec[c] = getattr(x, c)
            for tag, d in drv.items():
                vals, last, _ = d.at(x.issue)
                for g in ("A",) if tag == "b30" else ("A", "C", "E", "N"):
                    rec[f"driver_{g}_{tag}"] = vals[g].get(last[g], np.nan) if last.get(g) is not None else np.nan
            recs.append(rec)
        df = pd.DataFrame(recs).dropna(subset=["chg"])
        for c in [c for c in df.columns if c not in ("issue", "chg")]:
            d = df[["chg", c]].dropna()
            if len(d) < 8 or d[c].nunique() < 3:
                continue
            rho = stats.spearmanr(d[c], d["chg"]).statistic
            perm = np.array([stats.spearmanr(d[c], rng.permutation(d["chg"].to_numpy())).statistic for _ in range(10000)])
            rows.append({"lead": k, "feature": c, "n_issues": len(d), "spearman": float(rho),
                         "p_perm": float((np.abs(perm) >= abs(rho)).mean())})
    out = pd.DataFrame(rows)
    out["p_holm"] = np.nan
    for k, g in out.groupby("lead"):
        o = g.sort_values("p_perm")
        m = len(o)
        adj = np.maximum.accumulate([(m - i) * p for i, p in enumerate(o["p_perm"])])
        out.loc[o.index, "p_holm"] = np.minimum(adj, 1.0)
    return out.sort_values(["lead", "p_perm"])


def d3_events(P) -> pd.DataFrame:
    g = P[(P.policy == "P-DASH") & (P.lead == 2) & (P.n_obs >= 8)].copy()
    g = g[(g["y_true"] - g["y_latest"]) > 2 * g["se"]]
    drv = {"rice": R.Drivers("rice"), "b30": R.Drivers("b30")}
    rows = []
    for _, x in g.iterrows():
        vals, last, _ = drv["rice"].at(x["issue"])
        vb, lb, _ = drv["b30"].at(x["issue"])
        rec = {"area": x["area"], "issue": x["issue"], "target": x["target"],
               "latest_obs_quarter": L.qs(int(x["target_q"] - x["h"])), "h": x["h"], "y_latest": x["y_latest"],
               "y_true": x["y_true"], "increase": x["y_true"] - x["y_latest"], "tol": x["tol"],
               "in_S_E132": bool(pd.notna(x["f_RIDGE-ALL"]) and pd.notna(x["f_PSA-ONLY"]) and pd.notna(x["f_NLP-ONLY"]))}
        for g_, (v, l_) in {"A_rice": (vals["A"], last["A"]), "A_b30": (vb["A"], lb["A"]), "C": (vals["C"], last["C"]),
                            "E": (vals["E"], last["E"]), "N": (vals["N"], last["N"])}.items():
            rec[f"z_{g_}_latest"] = v.get(l_, np.nan) if l_ is not None else np.nan
            rec[f"z_{g_}_quarter"] = L.qs(l_) if l_ is not None else None
        for m in ("PERSIST", "SEAS-LLM", "HFM-NS-DES", "HFM-X", "HFM-X-B30"):
            f = x[f"f_{m}"]
            rec[f"f_{m}"] = f
            rec[f"within_{m}"] = bool(abs(f - x["y_true"]) <= x["tol"])
            rec[f"captured_share_{m}"] = (f - x["y_latest"]) / (x["y_true"] - x["y_latest"])
        rows.append(rec)
    return pd.DataFrame(rows)


def d4_bias(P) -> pd.DataFrame:
    rows = []
    for st, mask in (("S-U", P.n_obs >= 8), ("S-E132", P["f_RIDGE-ALL"].notna() & P["f_PSA-ONLY"].notna() & P["f_NLP-ONLY"].notna())):
        g = P[mask & (P.policy == "P-DASH") & (P.lead == 2)].copy()
        terc = pd.qcut(g["y_true"], 3, labels=["low", "mid", "high"])
        for m in ("ORACLE-LEVEL", "ORACLE-NOW", "PERSIST", "SEAS-LLM", "HFM-NS-DES", "HFM-X"):
            for t in ("low", "mid", "high"):
                s = g[terc == t]
                rows.append({"set": st, "model": m, "tercile": t, "n": len(s),
                             "bias": float((s[f"f_{m}"] - s["y_true"]).mean()),
                             "mean_y": float(s["y_true"].mean())})
    return pd.DataFrame(rows)


def d5_octa(rr) -> dict:
    o = pd.read_csv(R.S.OCTA)
    o = o[~o["fieldwork"].str.contains("previous round")].copy()
    o["published"] = pd.to_datetime(o["published"]).dt.date
    o["start"] = pd.to_datetime(o["fieldwork"].str[:10])
    o["qi"] = (o["start"].dt.year * 4 + (o["start"].dt.month - 1) // 3).astype(int)
    rows = []
    for D, issue in X.schedule(rr, "P-DASH"):
        qa = X.asof(rr, issue)
        if qa.empty:
            continue
        latest = int(qa["qi"].max())
        early = o[(o.published < issue) & (o.qi > latest)]
        rows.append({"D": D, "latest_sws": L.qs(latest), "octa_newer_than_sws": len(early) > 0})
    d = pd.DataFrame(rows)
    return {"issues": len(d), "issues_with_newer_octa_reading": int(d["octa_newer_than_sws"].sum()),
            "octa_balance_luzon_readings": int(len(o)), "detail": d.to_dict("records")}


def main():
    rr = X.rounds()
    P = pd.read_csv(OUT / "e133_predictions.csv")
    P["issue"] = pd.to_datetime(P["issue"]).dt.date
    d1_bound(rr, P).to_csv(OUT / "d1_achievability_bound.csv", index=False)
    d2_screen(rr).to_csv(OUT / "d2_leading_indicator_screen.csv", index=False)
    d3_events(P).to_csv(OUT / "d3_sharp_increase_events.csv", index=False)
    d4_bias(P).to_csv(OUT / "d4_high_hunger_bias.csv", index=False)
    L.dump(d5_octa(rr), OUT / "d5_octa_early_channel.json")
    for f in ("d1_achievability_bound", "d2_leading_indicator_screen", "d3_sharp_increase_events", "d4_high_hunger_bias"):
        print(f)
        print(pd.read_csv(OUT / f"{f}.csv").round(3).head(40).to_string())


if __name__ == "__main__":
    main()
