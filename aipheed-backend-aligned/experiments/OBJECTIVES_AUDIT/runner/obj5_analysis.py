"""Objective 5 / H4 / H5 analysis, exactly as OBJ5_ANALYSIS_PLAN.md (851ea697..., hash checked), from ACTUAL responses.

    python obj5_analysis.py score RESPONSES.csv [--model-dir DIR] [--quarter 2027-Q1] [--out out.json]
    python obj5_analysis.py selftest     # random answers in a temporary folder: checks the code only, saves nothing

RESPONSES.csv follows obj5/RESPONSES_TEMPLATE.csv; the item -> characteristic map is obj5/item_map.json (confirm it
against the deployed questionnaire first). No response is invented or imputed; invalid rows are excluded with reasons.

aiPHeed's province order and top-10 LGUs come from the served model's export (--model-dir, default the C-b export
backend/data/foodinsecurity_engine) for --quarter: provinces by score, LGUs by risk index (score x within-province
vulnerability, as served).
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import hashlib
import json
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binomtest, spearmanr, wilcoxon

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[2]
PLAN = HERE / "OBJ5_ANALYSIS_PLAN.md"
MAP = HERE / "obj5" / "item_map.json"
NEUTRAL, ALPHA = 3.40, 0.05
BANDS = [(1.80, "Strongly disagree"), (2.60, "Disagree"), (3.40, "Neutral"), (4.20, "Agree"), (5.00, "Strongly agree")]


def check_plan() -> str:
    b = PLAN.read_bytes()
    body, last = b.rstrip(b"\n").rsplit(b"\n", 1)
    h = hashlib.sha256(body + b"\n").hexdigest()
    assert last.split()[-1].decode() == h, "OBJ5_ANALYSIS_PLAN.md changed"
    return h


def verbal(x: float) -> str:
    return next(lbl for hi, lbl in BANDS if x <= hi + 1e-12)


def alpha(X: pd.DataFrame) -> float | None:
    X = X.dropna()
    k = X.shape[1]
    if k < 2 or len(X) < 2:
        return None
    v = X.var(ddof=1)
    tot = X.sum(axis=1).var(ddof=1)
    return float(k / (k - 1) * (1 - v.sum() / tot)) if tot > 0 else None


def holm(ps: dict) -> dict:
    items = sorted(ps.items(), key=lambda x: x[1])
    out, run = {}, 0.0
    for i, (k, p) in enumerate(items):
        run = max(run, min(1.0, (len(items) - i) * p))
        out[k] = run
    return out


def kendall_w(R: np.ndarray) -> float | None:
    m, n = R.shape
    if m < 2:
        return None
    s = ((R.sum(axis=0) - m * (n + 1) / 2) ** 2).sum()
    return float(12 * s / (m ** 2 * (n ** 3 - n)))


def served_order(model_dir: Path, quarter: str) -> tuple[list[str], list[str]]:
    r = pd.read_csv(model_dir / "rows.csv", dtype={"province_code": str})
    r = r[r["quarter"] == quarter]
    assert len(r), f"no served rows for {quarter} in {model_dir}"
    prov = r.sort_values("score", ascending=False)["province"].tolist()
    v = pd.read_csv(model_dir / "lgu_vulnerability.csv", dtype={"lgu_code": str})
    ps = dict(zip(r["province"], r["score"]))
    mm = lambda a: (a - a.min()) / (a.max() - a.min()) if a.max() > a.min() else a * 0  # noqa: E731
    v["dens"] = v["population_2024"] / v["land_area_km2"]
    v["idx"] = v.groupby("province", group_keys=False).apply(
        lambda g: ps[g.name] * (0.6 * mm(g["poverty_value_used"]) + 0.4 * mm(g["dens"])), include_groups=False)
    return prov, v.sort_values("idx", ascending=False)["lgu_code"].head(10).tolist()


def score(responses: Path, model_dir: Path, quarter: str) -> dict:
    plan = check_plan()
    M = json.loads(MAP.read_text(encoding="utf-8"))
    el = M["eligibility"]
    D = pd.read_csv(responses, dtype=str).fillna("")
    assert D["respondent_id"].is_unique, "respondent_id must be unique"
    items = [q for qs in M["characteristics"].values() for q in qs]
    L = D[items].apply(lambda c: pd.to_numeric(c.where(c.isin([str(x) for x in range(1, 6)])), errors="coerce"))
    excl = {}
    for i, r in D.iterrows():
        why = []
        if r[el["consent_column"]] not in el["consent_yes"]:
            why.append("no consent")
        if r[el["agency_column"]].strip() != el["agency_value"]:
            why.append("not DA Region IV-A")
        if L.loc[i].notna().mean() < el["min_likert_answered"]:
            why.append("fewer than 80% of Likert items answered")
        if why:
            excl[r["respondent_id"]] = why
    keep = ~D["respondent_id"].isin(excl)
    D, L = D[keep].reset_index(drop=True), L[keep].reset_index(drop=True)
    res = {"plan_sha256": plan, "n_received": int(len(keep)), "n_valid": int(keep.sum()), "excluded": excl,
           "items": {}, "characteristics": {}}
    for q in items:
        x = L[q].dropna()
        res["items"][q] = {"n": int(len(x)), "median": float(x.median()) if len(x) else None,
                           "mean": float(x.mean()) if len(x) else None, "sd": float(x.std(ddof=1)) if len(x) > 1 else None,
                           "pct_agree_4_5": float((x >= 4).mean()) if len(x) else None}
    char_means = {}
    for c, qs in M["characteristics"].items():
        m = L[qs].mean(axis=1, skipna=True)
        char_means[c] = m
        a = alpha(L[qs]) if len(qs) >= 3 else None
        itc = {q: float(spearmanr(L[q], L[qs].drop(columns=q).mean(axis=1), nan_policy="omit")[0])
               for q in qs} if len(qs) >= 3 else {}
        res["characteristics"][c] = {"items": qs, "mean": float(m.mean()) if m.notna().any() else None,
                                     "verbal": verbal(float(m.mean())) if m.notna().any() else None, "cronbach_alpha": a,
                                     "alpha_acceptable": None if a is None else a >= .70,
                                     "item_total_r": itc, "items_r_below_0.30": [q for q, v in itc.items() if v < .30]}
    res["overall_alpha"] = alpha(L[items])
    # H5: one-sided Wilcoxon that the respondent mean exceeds 3.40, Holm over the three characteristics
    p = {}
    for c in M["h5_characteristics"]:
        d = (char_means[c] - NEUTRAL).dropna()
        d = d[d != 0]
        p[c] = float(wilcoxon(d, alternative="greater").pvalue) if len(d) >= 1 else 1.0
        res["characteristics"][c]["h5_n"] = int(len(d))
    hp = holm(p)
    for c in M["h5_characteristics"]:
        d = (char_means[c] - NEUTRAL).dropna()
        d = d[d != 0]
        n = len(d)
        r_eff = None
        if n:                                   # r = Z / sqrt(n), Z from the signed-rank sum's normal approximation
            rk = d.abs().rank()
            w_plus = float(rk[d > 0].sum())
            z = (w_plus - n * (n + 1) / 4) / np.sqrt(n * (n + 1) * (2 * n + 1) / 24)
            r_eff = float(z / np.sqrt(n))
        res["characteristics"][c].update({"h5_p_one_sided": p[c], "h5_p_holm": hp[c],
                                          "h5_null_rejected_favorable": bool(hp[c] < ALPHA and d.mean() > 0),
                                          "effect_size_r": r_eff})
    # H4: provinces and LGUs
    prov, top10 = served_order(model_dir, quarter)
    rank_cols = M["province_rank_columns"]
    served_rank = {p_: i + 1 for i, p_ in enumerate(prov)}
    R, rhos = [], []
    for _, r in D.iterrows():
        rk = {p_: pd.to_numeric(r[c], errors="coerce") for p_, c in rank_cols.items()}
        if all(pd.notna(v) for v in rk.values()) and sorted(rk.values()) == [1, 2, 3, 4, 5]:
            R.append([rk[p_] for p_ in rank_cols])
            rhos.append(float(spearmanr([rk[p_] for p_ in rank_cols], [served_rank[p_] for p_ in rank_cols])[0]))
    pos = sum(x > 0 for x in rhos)
    nz = sum(x != 0 for x in rhos)
    p_prov = float(binomtest(pos, nz, .5, alternative="greater").pvalue) if nz else None
    ov = []
    for _, r in D.iterrows():
        sel = [x for x in str(r[M["lgu_top10_column"]]).split(";") if x.strip()][:10]
        if sel:
            ov.append(len(set(sel) & set(top10)) - len(sel) * 10 / 142)
    ov = np.array(ov)
    p_lgu = float(wilcoxon(ov[ov != 0], alternative="greater").pvalue) if (ov != 0).sum() >= 1 else None
    res["h4"] = {"served_model_dir": str(model_dir), "quarter": quarter, "served_province_order": prov,
                 "served_top10_lgus": top10, "n_province_rankings": len(rhos),
                 "median_spearman_rho": float(np.median(rhos)) if rhos else None, "sign_test_p_one_sided": p_prov,
                 "kendall_w_among_evaluators": kendall_w(np.array(R)) if len(R) >= 2 else None,
                 "n_lgu_selections": int(len(ov)), "mean_overlap_minus_chance": float(ov.mean()) if len(ov) else None,
                 "lgu_wilcoxon_p_one_sided": p_lgu,
                 "h4_null_rejected": bool(p_prov is not None and p_lgu is not None and p_prov < ALPHA and p_lgu < ALPHA)}
    res["iso_25010_2023_note"] = "usability reported as interaction capability (ISO/IEC 25010:2023); safety not assessed"
    return res


def selftest():
    """Random answers in a temporary folder exercise every path. Nothing is written to the project."""
    M = json.loads(MAP.read_text(encoding="utf-8"))
    rng = np.random.default_rng(0)
    cols = pd.read_csv(HERE / "obj5" / "RESPONSES_TEMPLATE.csv").columns
    lg = pd.read_csv(ROOT / "backend" / "data" / "foodinsecurity_engine" / "lgu_vulnerability.csv", dtype={"lgu_code": str})
    rows = []
    for i in range(12):
        r = {c: "" for c in cols}
        r.update({"respondent_id": f"T{i:02d}", "consent": "yes", "agency": M["eligibility"]["agency_value"]})
        for q in [q for qs in M["characteristics"].values() for q in qs]:
            r[q] = str(int(rng.integers(1, 6)))
        for c, v in zip(M["province_rank_columns"].values(), rng.permutation(5) + 1):
            r[c] = str(v)
        r[M["lgu_top10_column"]] = ";".join(rng.choice(lg["lgu_code"], 10, replace=False))
        rows.append(r)
    rows[0]["consent"] = "no"
    with tempfile.TemporaryDirectory() as t:
        f = Path(t) / "responses.csv"
        pd.DataFrame(rows).to_csv(f, index=False)
        res = score(f, ROOT / "backend" / "data" / "foodinsecurity_engine", "2026-Q4")
    assert res["n_valid"] == 11 and "T00" in res["excluded"]
    print("selftest passed (random answers, temporary folder, nothing saved):",
          {k: res[k] for k in ("n_received", "n_valid")}, "H4 rankings", res["h4"]["n_province_rankings"])


def main():
    if sys.argv[1] == "selftest":
        selftest()
        return
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd")
    ap.add_argument("responses")
    ap.add_argument("--model-dir", default=str(ROOT / "backend" / "data" / "foodinsecurity_engine"))
    ap.add_argument("--quarter", default="2026-Q4")
    ap.add_argument("--out")
    a = ap.parse_args()
    res = score(Path(a.responses), Path(a.model_dir), a.quarter)
    text = json.dumps(res, indent=1, default=str)
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
