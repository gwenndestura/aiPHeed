"""
Scoring for the ISO/IEC 25010:2023 dashboard evaluation (docs/final/iso25010/ISO25010_EVALUATION_PACKAGE_E168.md). The rules
(interpretation bands, acceptability: mean >= 3.41 and >= 60 % agreeing) were fixed in the package before any response.

    python -m app.iso25010.score <responses.csv>   -> iso25010_results.json / .md beside the CSV

It refuses to report when the file has no responses: no result exists without real evaluators.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

CHAR = {
    "Functional suitability": ["FS1", "FS2", "FS3"], "Performance efficiency": ["PE1", "PE2"],
    "Compatibility": ["CO1", "CO2"], "Interaction capability": ["IC1", "IC2", "IC3", "IC4"], "Reliability": ["RE1", "RE2"],
    "Security": ["SE1", "SE2"], "Maintainability": ["MA1", "MA2"], "Flexibility": ["FL1", "FL2"], "Safety": ["SA1", "SA2"],
}
BANDS = [(4.21, "Strongly agree (very high quality)"), (3.41, "Agree (high quality)"), (2.61, "Neutral (moderate quality)"),
         (1.81, "Disagree (low quality)"), (1.0, "Strongly disagree (very low quality)")]
TASKS = [f"T{i}" for i in range(1, 7)]


def band(m: float) -> str:
    return next(lab for lo, lab in BANDS if m >= lo)


def cronbach(df: pd.DataFrame) -> float | None:
    d = df.dropna()
    k = d.shape[1]
    if k < 2 or len(d) < 5:
        return None
    var_items, var_total = d.var(ddof=1).sum(), d.sum(axis=1).var(ddof=1)
    return None if var_total == 0 else float(k / (k - 1) * (1 - var_items / var_total))


def sus(row: pd.Series) -> float | None:
    v = [row.get(f"SUS{i}") for i in range(1, 11)]
    if any(pd.isna(x) for x in v):
        return None
    return 2.5 * sum((x - 1) if i % 2 == 0 else (5 - x) for i, x in enumerate(v))


def score(df: pd.DataFrame) -> dict:
    if df.empty:
        raise SystemExit("no responses: nothing to score (the evaluation has not been administered)")
    items = [c for cs in CHAR.values() for c in cs]
    df[items] = df[items].apply(pd.to_numeric, errors="coerce")
    bad = df[items][(df[items] < 1) | (df[items] > 5)].stack()
    if len(bad):
        raise SystemExit(f"values outside 1-5: {bad.to_dict()}")
    out = {"n_respondents": int(len(df)), "characteristics": {}}
    for ch, cs in CHAR.items():
        per_resp = df[cs].mean(axis=1, skipna=True).dropna()
        allv = df[cs].stack().dropna()
        if per_resp.empty:
            out["characteristics"][ch] = {"n": 0}
            continue
        m = float(per_resp.mean())
        agree = float((per_resp >= 4).mean())
        out["characteristics"][ch] = {"n": int(len(per_resp)), "mean": round(m, 2), "sd": round(float(per_resp.std(ddof=1)), 2) if len(per_resp) > 1 else None,
                                      "pct_agree": round(100 * agree, 1), "alpha": None if (a := cronbach(df[cs])) is None else round(a, 2),
                                      "interpretation": band(m), "acceptable": bool(m >= 3.41 and agree >= 0.60),
                                      "items": {c: round(float(df[c].mean()), 2) for c in cs if df[c].notna().any()}}
    means = [v["mean"] for v in out["characteristics"].values() if v.get("n")]
    out["overall_mean"] = round(float(np.mean(means)), 2)
    out["overall_interpretation"] = band(out["overall_mean"])
    t = {}
    for k in TASKS:
        if f"{k}_done" in df:
            done = pd.to_numeric(df[f"{k}_done"].replace({"yes": 1, "no": 0}), errors="coerce").dropna()
            secs = pd.to_numeric(df.get(f"{k}_seconds"), errors="coerce").dropna()
            t[k] = {"completion_rate": round(float(done.mean()), 3) if len(done) else None, "median_seconds": float(secs.median()) if len(secs) else None}
    out["tasks"] = t
    s = df.apply(sus, axis=1).dropna()
    out["sus"] = {"n": int(len(s)), "mean": round(float(s.mean()), 1) if len(s) else None}
    return out


def markdown(r: dict) -> str:
    lines = [f"**N = {r['n_respondents']} evaluators.** Overall mean {r['overall_mean']} ({r['overall_interpretation']}).", "",
             "| Characteristic | n | Mean | SD | % agree | α | Interpretation | Acceptable |", "|---|---|---|---|---|---|---|---|"]
    for ch, v in r["characteristics"].items():
        if not v.get("n"):
            lines.append(f"| {ch} | 0 | – | – | – | – | – | – |")
            continue
        lines.append(f"| {ch} | {v['n']} | {v['mean']} | {v['sd'] if v['sd'] is not None else '–'} | {v['pct_agree']} | "
                     f"{v['alpha'] if v['alpha'] is not None else '–'} | {v['interpretation']} | {'yes' if v['acceptable'] else 'no'} |")
    if r["sus"]["n"]:
        lines += ["", f"SUS: {r['sus']['mean']} (n = {r['sus']['n']})."]
    return "\n".join(lines) + "\n"


def main(path: str):
    p = Path(path)
    r = score(pd.read_csv(p))
    (p.parent / "iso25010_results.json").write_text(json.dumps(r, indent=1), newline="\n")
    (p.parent / "iso25010_results.md").write_text(markdown(r), newline="\n")
    print(markdown(r))


if __name__ == "__main__":
    main(sys.argv[1])
