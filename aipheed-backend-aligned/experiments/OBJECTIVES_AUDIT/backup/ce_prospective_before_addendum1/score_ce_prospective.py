"""Score the sealed C-E prospective forecasts beside C-b and the 7 baselines (CE_PROSPECTIVE_PLAN.md section 5).

    python score_ce_prospective.py --date 2028-03-01 [--out DIR]   # real scoring: only labels published before the date
    python score_ce_prospective.py --replay-validate               # validation of this code on the stored development
                                                                   # forecasts (2010-Q1..2026-Q3); must reproduce
                                                                   # ce6_results.json; never written as prospective evidence

Real scoring:
- reads C-b and the baselines from the C-b protocol (score_prospective.collect: SENIOR_REVIEW ledger + the C-b seal by
  reference; read only) and C-E2/C-E6 from prospective_ce/SEAL_LEDGER_CE.md. Every SHA-256 must match its ledger.
- labels: prospective_lib.labels_at(date). Targets >= 2027-Q1 only; a target with no published label is never scored.
- per model and lead: score_prospective.score_lead (metrics, frozen R1-R7, 75% rule, Wilson 90%) and algorithm4.
- families P1 (C-E6 vs 7 baselines, Holm 14), P2 (C-E6 vs C-E2 and C-b, Holm 4), P3 (C-E2 vs 7 baselines, Holm 14):
  phase_c._paired (paired Brier, one-sided cluster bootstrap, seed 2036, B 5000), only once every model in the family
  has >= 20 labelled prospective quarters per lead. McNemar on discordant calls (descriptive).
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binomtest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ce_prospective as C  # noqa: E402
import ce_model as CE  # noqa: E402
import score_prospective as SP  # noqa: E402

P, H, V, PC, R_ = C.P, CE.H, CE.V, CE.PC, CE.R
BASELINES = list(P.COMPARATORS)                     # PERSIST, PSA-only, LOGIT, NLP-only, LGBM-GOV, LGBM-NLP, ALWAYS-HIGH
FAMILIES = {"P1": ("C-E6", BASELINES), "P2": ("C-E6", ["C-E2", "C-b"]), "P3": ("C-E2", BASELINES)}
LEADS = (1, 2)


def collect_ce(ledger: Path) -> pd.DataFrame:
    rows = []
    for e in C.read_ledger(ledger):
        f = ledger.parent / e["file"]
        assert f.exists() and C.sha(f) == e["sha256"], f"{e['file']} is missing or its SHA-256 differs: nothing is scored"
        x = pd.read_csv(f)
        assert (x["issue_date"] == e["issue"]).all() and not x["dry_run"].astype(bool).any(), f"{e['file']}: not a real seal"
        for r in x.itertuples():
            rows.append({"model": r.model, "lead": int(r.lead), "q": H.qi(r.target_quarter), "p": float(r.p_high),
                         "persist": float(r.persist_si), "clim": float(r.clim), "issue": r.issue_date, "file": e["file"]})
    return pd.DataFrame(rows, columns=["model", "lead", "q", "p", "persist", "clim", "issue", "file"])


def mcnemar(W: pd.DataFrame, a: str, b: str) -> dict:
    g = W[[a, b, "y"]].dropna()
    ra, rb = (g[a] >= .5) == (g["y"] == 1), (g[b] >= .5) == (g["y"] == 1)
    n01, n10 = int((ra & ~rb).sum()), int((~ra & rb).sum())
    p = float(binomtest(n01, n01 + n10, .5).pvalue) if n01 + n10 else None
    return {"n": int(len(g)), f"{a}_right_{b}_wrong": n01, f"{a}_wrong_{b}_right": n10, "p_two_sided_exact": p}


def families(R: pd.DataFrame, labels: pd.DataFrame, first_q: int, min_n: int) -> dict:
    R = R[R["q"] >= first_q]
    out = {}
    for name, (cand, comps) in FAMILIES.items():
        W = {k: R[R["lead"] == k].pivot_table(index="q", columns="model", values="p", aggfunc="first")
             .join(labels.set_index("q")["y"], how="inner").reset_index() for k in LEADS}
        n = {k: {m: int(W[k][m].notna().sum()) if m in W[k] else 0 for m in [cand, *comps]} for k in LEADS}
        if any(v < min_n for k in LEADS for v in n[k].values()):
            out[name] = {"status": f"not yet: needs >= {min_n} labelled prospective quarters per lead for every model",
                         "labelled": n}
            continue
        tests = {(k, b): PC._paired(W[k], cand, b) for k in LEADS for b in comps}
        hp = R_.holm({key: v["p_one_sided"] for key, v in tests.items()})
        res = [{"lead": k, "comparator": b, **v, "p_holm": hp[(k, b)], "significant": bool(v["diff"] < 0 and hp[(k, b)] < .05)}
               for (k, b), v in tests.items()]
        out[name] = {"status": "computed", "candidate": cand, "tests": res,
                     "all_significant": all(x["significant"] for x in res),
                     "mcnemar": {f"L{k} vs {b}": mcnemar(W[k], cand, b) for k in LEADS for b in comps}}
    return out


def evaluate(R: pd.DataFrame, labels: pd.DataFrame, first_q: int, min_n: int) -> dict:
    models = ["C-E6", "C-E2", "C-b", *BASELINES]
    per = {m: {str(k): SP.score_lead(R, m, k, labels, first_q) for k in (*LEADS, 3) if (R["model"].eq(m) & R["lead"].eq(k)).any()}
           for m in models}
    alg4 = {m: {str(k): SP.algorithm4(R, m, k, labels, first_q) for k in LEADS} for m in ("C-E6", "C-E2", "C-b")}
    return {"per_model": per, "algorithm4": alg4, "families": families(R, labels, first_q, min_n)}


def real(date: str, out: Path | None):
    plan = C.check_plan()
    d = H.load()
    lab = V.area_labels(d)
    Rb, files = SP.collect(P.LEDGER, True, d, lab)
    Rc = collect_ce(C.LEDGER_CE)
    R = pd.concat([Rb, Rc], ignore_index=True)
    labels = P.labels_at(date)
    labels = labels[labels["q"] >= P.FIRST_TARGET]
    res = {"scoring_date": date, "plan_sha256": plan, "files_cb_protocol": files,
           "files_ce": C.read_ledger(C.LEDGER_CE), "labelled_prospective_quarters": [H.qs(int(q)) for q in labels["q"]],
           **evaluate(R, labels, P.FIRST_TARGET, P.FAMILY_MIN)}
    text = C.dumps(res)
    if out:
        out.mkdir(parents=True, exist_ok=True)
        (out / f"ce_prospective_scores_{date}.json").write_text(text, encoding="utf-8")
    print(text)


def replay_validate():
    """Run the scorer on the stored development forecasts and check that P1 equals ce6_results.json exactly."""
    d = H.load()
    lab = V.area_labels(d)
    lb = lab[lab["area"] == "BL"][["q", "H", "y"]].assign(mode="face-to-face", base="")
    iv2 = pd.read_csv(C.EXP / "IMPROVE_V2" / "out" / "forecasts.csv")
    h3 = pd.read_csv(C.EXP / "OBJECTIVES_COMPLETION" / "out" / "h3_forecasts.csv")
    L = pd.read_csv(CE.N.LEADS_FILE)
    CBF = pd.read_csv(CE.N.OUT / "forecasts.csv")
    F2, F6 = pd.read_csv(C.HERE / "out" / "ce2_fits.csv"), pd.read_csv(C.HERE / "out" / "ce6_fits.csv")
    parts = [iv2[iv2["name"].isin(["LOGIT", "PSA-only", "NLP-only"])], h3, L[L["name"].isin(["PERSIST", "CLIM"])],
             CBF[CBF["name"] == "C-b"], F2, F6]
    X = pd.concat([x[["name", "t", "lead", "q", "p"]] for x in parts], ignore_index=True)
    lo, hi = R_.VERDICT
    X = X[X["q"].between(lo, hi) & (X["t"] <= V.LAST_ORIGIN - 1)]
    ref = X[X["name"].isin(["PERSIST", "CLIM"])].pivot_table(index=["t", "lead"], columns="name", values="p").reset_index()
    rows = X[~X["name"].isin(["PERSIST", "CLIM"])].merge(ref, on=["t", "lead"], how="left")
    R = pd.DataFrame({"model": rows["name"], "lead": rows["lead"], "q": rows["q"], "p": rows["p"],
                      "persist": rows["PERSIST"], "clim": rows["CLIM"]})
    const = {"PERSIST": ref["PERSIST"], "ALWAYS-HIGH": 1.0}
    R = pd.concat([R, *[pd.DataFrame({"model": m, "lead": ref["lead"], "q": ref["t"] + ref["lead"], "p": p,
                                      "persist": ref["PERSIST"], "clim": ref["CLIM"]}) for m, p in const.items()]],
                  ignore_index=True)
    R = R[R["q"].between(lo, hi)]
    fam = families(R, lb, lo, 0)
    hist = json.loads((C.HERE / "out" / "ce6_results.json").read_text(encoding="utf-8"))["holm_family_14"]
    H6 = {(f["lead"], f["comparator"]): f for f in hist}
    cmp = []
    for x in fam["P1"]["tests"]:
        h = H6[(x["lead"], x["comparator"])]
        cmp.append({"lead": x["lead"], "comparator": x["comparator"], "diff_replay": x["diff"], "diff_hist": h["diff"],
                    "p_replay": x["p_one_sided"], "p_hist": h["p_one_sided"], "holm_replay": x["p_holm"],
                    "holm_hist": h["p_holm_14"], "n_replay": x["n_quarters"], "n_hist": h["n_quarters"]})
    ok = all(abs(c["diff_replay"] - c["diff_hist"]) < 1e-12 and abs(c["p_replay"] - c["p_hist"]) < 1e-12
             and c["n_replay"] == c["n_hist"] for c in cmp)
    per = {f"{m} L{k}": SP.score_lead(R, m, k, lb, lo)["metrics"]["brier"] for m in ("C-E6", "C-E2") for k in LEADS}
    res = {"replay_validation": "stored development forecasts scored by the prospective code (NOT prospective evidence)",
           "P1_matches_ce6_results": ok, "P1": cmp, "P2": fam["P2"].get("tests"), "C-E6_brier_by_score_lead": per,
           "P2_mcnemar": fam["P2"].get("mcnemar")}
    print(C.dumps(res))
    if not ok:
        raise SystemExit("replay validation FAILED: the prospective scorer does not reproduce the historical family")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--out")
    ap.add_argument("--replay-validate", action="store_true")
    a = ap.parse_args()
    if a.replay_validate:
        replay_validate()
    else:
        assert a.date, "--date is required"
        real(a.date, Path(a.out) if a.out else None)


if __name__ == "__main__":
    main()
