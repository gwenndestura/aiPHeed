"""Score the aiPHeed Post-Survey Questionnaire export with the predeclared rules (DECISION_RULES.md).

Expected CSV columns (Google Form titles must START with the code): CONSENT, P4 (province name for the ranking
section), FS1..FS5, AC1..AC4, US1..US6, RK1, RK2_1..RK2_3, RK3_1..RK3_3 (LGU names). Likert answers may be the
number 1-5 or a label starting with it ("4 - Agree").
Usage: python instruments/score_responses.py <export.csv> --rankings <lgu_rankings.csv> [--out result.json]
This script never creates, edits or imputes responses."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

PARTS = {"FS": [f"FS{i}" for i in range(1, 6)], "AC": [f"AC{i}" for i in range(1, 5)],
         "US": [f"US{i}" for i in range(1, 7)]}
RATED = sum(PARTS.values(), []) + ["RK1"]
MIN_VALID, MIN_ANSWERED, FAVORABLE = 30, 0.8, 4.0


def _col(df, code):
    for c in df.columns:
        if re.match(rf"^\s*{re.escape(code)}(\b|[\s\-–:.])", str(c)):
            return c
    return None


def likert(v):
    if pd.isna(v):
        return np.nan
    m = re.match(r"^\s*([1-5])", str(v))
    return float(m.group(1)) if m else np.nan


def holm(p: dict) -> dict:
    items = sorted(p.items(), key=lambda kv: kv[1])
    out, run, m = {}, 0.0, len(items)
    for i, (k, v) in enumerate(items):
        run = max(run, min(1.0, (m - i) * v))
        out[k] = run
    return out


def cronbach(x: pd.DataFrame):
    x = x.dropna()
    k = x.shape[1]
    if len(x) < 3 or k < 2 or x.sum(axis=1).var(ddof=1) == 0:
        return None
    return float(k / (k - 1) * (1 - x.var(ddof=1).sum() / x.sum(axis=1).var(ddof=1)))


def boot_ci(v, seed=20261013, n=4000):
    v = np.asarray(v, float)
    rng = np.random.default_rng(seed)
    m = v[rng.integers(0, len(v), (n, len(v)))].mean(1)
    return [float(np.quantile(m, .025)), float(np.quantile(m, .975))]


def wil_greater(v, mu):
    d = np.asarray(v, float) - mu
    d = d[d != 0]
    if len(d) == 0:
        return 1.0
    return float(wilcoxon(d, alternative="greater").pvalue)


def score(df: pd.DataFrame, ranks: pd.DataFrame) -> dict:
    # Result-entry rule: only a genuine Google Forms export is scored. Forms adds a per-response "Timestamp";
    # a sheet without it (typed or simulated rows) is refused rather than scored.
    if "Timestamp" not in df.columns or df["Timestamp"].isna().any():
        raise ValueError("refused: not a Google Forms export (missing or empty 'Timestamp' column)")
    cc = _col(df, "CONSENT")
    cols = {c: _col(df, c) for c in RATED}
    R = pd.DataFrame({c: df[cols[c]].map(likert) if cols[c] else np.nan for c in RATED})
    consent = df[cc].astype(str).str.strip().str.lower().str.startswith("yes") if cc else pd.Series(False, index=df.index)
    answered = R.notna().mean(axis=1)
    valid = consent & (answered >= MIN_ANSWERED)
    out = {"n_rows": int(len(df)), "n_valid": int(valid.sum()),
           "excluded_no_consent": int((~consent).sum()), "excluded_incomplete": int((consent & ~valid).sum())}
    Rv = R[valid]
    if valid.sum() < MIN_VALID:
        out["H5"] = out["H4"] = {"decision": "insufficient responses", "why": f"{int(valid.sum())} < {MIN_VALID} valid"}
        return out
    # ---------------- H5
    parts, pv = {}, {}
    for p, items in PARTS.items():
        s = Rv[items].mean(axis=1, skipna=True)
        pv[p] = wil_greater(s, 3.0)
        parts[p] = {"n": int(s.notna().sum()), "median": float(s.median()), "mean": float(s.mean()),
                    "sd": float(s.std(ddof=1)), "mean_ci95": boot_ci(s.dropna()), "p_one_sided_vs_3": pv[p],
                    "cronbach_alpha": cronbach(Rv[items]),
                    "items": {i: Rv[i].value_counts().sort_index().to_dict() for i in items}}
    ph = holm(pv)
    for p in parts:
        parts[p]["p_holm"] = ph[p]
        parts[p]["favorable"] = bool(parts[p]["median"] >= FAVORABLE and ph[p] < 0.05)
    out["H5"] = {"decision": "rejected" if all(v["favorable"] for v in parts.values()) else "not rejected",
                 "characteristics": parts}
    # ---------------- H4
    names = {"cavite": "PH040100000", "laguna": "PH040200000", "quezon": "PH040300000", "rizal": "PH040400000",
             "batangas": "PH040500000"}
    p4 = _col(df, "P4")
    agree, agree_density, per_prov = [], [], {}
    for i in df.index[valid]:
        prov = names.get(str(df.at[i, p4]).split(",")[0].strip().lower()) if p4 else None
        if prov is None:
            continue
        g = ranks[ranks["province_code"] == prov].sort_values("risk_index", ascending=False)
        n = len(g)
        third = max(1, n // 3)
        top, bottom = set(g["lgu_name"].iloc[:third]), set(g["lgu_name"].iloc[n - third:])
        gd = g.sort_values("density", ascending=False)
        topd, botd = set(gd["lgu_name"].iloc[:third]), set(gd["lgu_name"].iloc[n - third:])
        rk2 = [str(df.at[i, c]).strip() for c in (_col(df, f"RK2_{j}") for j in (1, 2, 3)) if c]
        rk3 = [str(df.at[i, c]).strip() for c in (_col(df, f"RK3_{j}") for j in (1, 2, 3)) if c]
        if len(rk2) != 3 or len(rk3) != 3:
            continue
        a = (sum(x in top for x in rk2) + sum(x in bottom for x in rk3)) / 6
        ad = (sum(x in topd for x in rk2) + sum(x in botd for x in rk3)) / 6
        agree.append(a); agree_density.append(ad)
        per_prov.setdefault(prov, []).append(a)
    rk1 = Rv["RK1"].dropna()
    if len(agree) < MIN_VALID:
        out["H4"] = {"decision": "insufficient responses", "why": f"{len(agree)} usable ranking answers < {MIN_VALID}"}
    else:
        p = wil_greater(agree, 1 / 3)
        ok = p < 0.05 and float(rk1.median()) >= FAVORABLE
        out["H4"] = {"decision": "rejected" if ok else "not rejected", "n": len(agree),
                     "mean_agreement": float(np.mean(agree)), "agreement_ci95": boot_ci(agree),
                     "p_one_sided_vs_one_third": p, "median_RK1": float(rk1.median()),
                     "density_only_mean_agreement": float(np.mean(agree_density)),
                     "per_province_mean": {k: float(np.mean(v)) for k, v in per_prov.items()}}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--rankings", required=True)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    df = pd.read_csv(a.csv)
    ranks = pd.read_csv(a.rankings, dtype={"province_code": str})
    res = score(df, ranks)
    res["inputs"] = {Path(p).name: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in (a.csv, a.rankings)}
    txt = json.dumps(res, indent=1, default=float)
    if a.out:
        Path(a.out).write_text(txt, encoding="utf-8")
    print(txt)


if __name__ == "__main__":
    main()
