"""Score the sealed prospective forecasts (PROSPECTIVE_PLAN.md sections 2-5).

    python score_prospective.py --date 2028-03-01                     # real annual scoring (on or after the date)
    python score_prospective.py --date 2027-03-01 --dry-run --out DIR --ledger DIR/SEAL_LEDGER.md [--replay-first 2010-Q1]

Steps:
1. Plan hash; every ledger file's SHA-256 (any mismatch aborts); the OPTION_1 2027-Q1 Lead-2 seal (cc1ff11b...) by
   reference, its CLIM computed by the section-1 rule from labels published before 2026-10-01.
2. Missed seals: every quarter-start issue date from the first issue whose 14-day window has closed by the scoring date
   and that has no ledger row (never back-filled).
3. Labels known on the scoring date (section 2); one row per target quarter; prospective targets only.
4. Per model and lead: metrics, the frozen R1-R7 (hr_lib.evaluate, unedited) and an independent recomputation that must
   agree (else abort), the 75% rule with a 90% Wilson interval, survey-mode notes, the review trigger (section 5.3).
5. Status per lead: "insufficient prospective evidence" below 40 labelled quarters. The single-look verdict (section 5.2)
   is written once, to VERDICT.json, at the first scoring date (1 March) on which REF+news has >= 40 labelled quarters
   at both leads; an existing VERDICT.json is reported and never changed.
Dry runs write only into --out and may use a replay ledger (--replay-first sets the first prospective target).
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prospective_lib as P  # noqa: E402

H, V = P.H, P.V


def issues_between(first: str, last: str) -> list[str]:
    out, d = [], pd.Timestamp(first)
    while d <= pd.Timestamp(last):
        out.append(d.strftime("%Y-%m-%d"))
        d = d + pd.DateOffset(months=3)
    return out


def collect(ledger: Path, include_option1: bool, d, lab) -> tuple[pd.DataFrame, list[dict]]:
    rows, files = [], []
    for e in P.read_ledger(ledger):
        f = ledger.parent / e["file"]
        ok = f.exists() and P.sha(f) == e["sha256"]
        files.append({**e, "hash_ok": ok})
        assert ok, f"sealed file {e['file']} is missing or its SHA-256 does not match the ledger: nothing is scored"
        x = pd.read_csv(f)
        assert (x["issue_date"] == e["issue"]).all(), f"{e['file']}: issue date differs from the ledger"
        for r in x.itertuples():
            rows.append({"model": r.model, "lead": int(r.lead), "q": H.qi(r.target_quarter), "p": float(r.p_high),
                         "persist": float(r.persist_si), "clim": float(r.clim), "issue": r.issue_date, "file": e["file"]})
    if include_option1:
        ok = P.sha(P.OPT_SEAL) == P.OPT_SEAL_SHA
        files.append({"file": "OPTION_1/sealed_prospective_REFNEWS.csv", "sha256": P.OPT_SEAL_SHA, "hash_ok": ok,
                      "issue": "2026-10-01"})
        assert ok, "the OPTION_1 2027-Q1 seal does not match cc1ff11b...: nothing is scored"
        s = pd.read_csv(P.OPT_SEAL).iloc[0]
        t = P.origin_of_issue(s["issue_date"])
        b = P.baselines(d, lab, t)
        assert float(s["persist_p"]) == b["persist_si"], "OPTION_1 seal persistence differs from the rule"
        rows.append({"model": s["arm"], "lead": int(s["lead"]), "q": H.qi(s["target_quarter"]), "p": float(s["p_high"]),
                     "persist": float(s["persist_p"]), "clim": b["clim"], "issue": s["issue_date"],
                     "file": "OPTION_1/sealed_prospective_REFNEWS.csv"})
        # Addendum CB: C-b's forecasts issued 2026-10-01, sealed in NEWS_V2 (only targets from 2027-Q1 are scored)
        ok = P.sha(P.CB_SEAL) == P.CB_SEAL_SHA
        files.append({"file": "NEW_MODEL/NEWS_V2/sealed_prospective_CB.csv", "sha256": P.CB_SEAL_SHA, "hash_ok": ok,
                      "issue": "2026-10-01"})
        assert ok, "the NEWS_V2 C-b seal does not match 67baec66...: nothing is scored"
        for s in pd.read_csv(P.CB_SEAL).itertuples():
            rows.append({"model": "C-b", "lead": int(s.lead), "q": H.qi(s.target_quarter), "p": float(s.p_high),
                         "persist": float(s.persist_si), "clim": float(s.clim), "issue": s.issue_date,
                         "file": "NEW_MODEL/NEWS_V2/sealed_prospective_CB.csv"})
    R = pd.DataFrame(rows)
    if len(R):
        dup = R.duplicated(["model", "lead", "q"], keep=False)
        assert not dup.any(), f"two sealed forecasts for the same model, lead and target: {R[dup].to_dict('records')}"
    return R, files


def _safe_eval(g: pd.DataFrame, col: str) -> dict:
    try:
        r = H.evaluate(g, col)
        return {"metrics": r["metrics"], "rules": {k.split()[0]: {"pass": v["pass"], "value": v["value"]}
                                                   for k, v in r["rules"].items()}}
    except Exception as e:  # noqa: BLE001  (e.g. one class only: AUC undefined)
        m = H.rp().cm(g["y"].to_numpy(int), g[col].to_numpy(float)) if len(g) else {}
        m["brier"] = float(np.mean((g[col] - g["y"]) ** 2)) if len(g) else None
        return {"metrics": m, "rules": None, "rules_error": f"{type(e).__name__}: {e}"}


def score_lead(R: pd.DataFrame, model: str, k: int, labels: pd.DataFrame, first_q: int) -> dict:
    x = R[(R["model"] == model) & (R["lead"] == k) & (R["q"] >= first_q)]
    g = x.merge(labels[["q", "y", "H", "mode", "base"]], on="q", how="inner").sort_values("q").reset_index(drop=True)
    n = int(len(g))
    out = {"model": model, "lead": k, "sealed_rows": int(len(x)), "labelled_quarters": n,
           "period": f"{H.qs(int(g['q'].min()))}..{H.qs(int(g['q'].max()))}" if n else None,
           "unlabelled_targets": [H.qs(int(q)) for q in sorted(set(x["q"]) - set(g["q"]))]}
    if not n:
        return {**out, "status": "insufficient prospective evidence"}
    g = g.assign(**{model: g["p"], "PERSIST-SI_p": g["persist"], "CLIM_p": g["clim"], "ALWAYS-LOW_p": 0.0,
                    "ALWAYS-HIGH_p": 1.0, "PERSIST": g["persist"], "CLIM": g["clim"]})
    ev = _safe_eval(g, model)
    if ev["rules"] is not None:
        mine = P.independent_rules(g, model)
        frozen = {r: v["pass"] for r, v in ev["rules"].items()}
        assert mine == frozen, f"independent R1-R7 disagree with the frozen code at {model} L{k}: {mine} vs {frozen}"
        out["independent_check"] = "agrees"
    c = (g[model] >= .5).astype(int)
    kk = int((c == g["y"]).sum())
    ps_acc = float(((g["PERSIST-SI_p"] >= .5).astype(int) == g["y"]).mean())
    out.update({"metrics": ev["metrics"], "rules": ev["rules"], **({"rules_error": ev["rules_error"]}
                                                                  if "rules_error" in ev else {}),
                "rule_75pct": {"accuracy": kk / n, "wilson90": P.wilson(kk, n), "passes_point": kk / n >= .75},
                "persistence_accuracy": ps_acc,
                "survey_notes": [f"{H.qs(int(r.q))}: mode {r.mode}, base {r.base}" for r in g.itertuples()
                                 if r.mode != "face-to-face"]})
    if n >= P.REVIEW_MIN:
        dv = ((g[model] - g["y"]) ** 2 - (g["PERSIST-SI_p"] - g["y"]) ** 2).to_numpy(float)
        p_worse = float(np.mean(H.boot_mean(g["q"].to_numpy(), dv, H.rp()) <= 0))
        trig = bool(kk / n < ps_acc and dv.mean() > 0 and p_worse < P.REVIEW_P)
        out["review_trigger"] = {"accuracy_below_persistence": kk / n < ps_acc, "brier_diff_vs_persistence": float(dv.mean()),
                                 "p_one_sided_worse": p_worse, "flag": trig,
                                 "message": "underperforming persistence: review the served model" if trig else None}
    out["status"] = ("insufficient prospective evidence" if n < P.MIN_QUARTERS else
                     "all R1-R7 pass" if ev["rules"] and all(v["pass"] for v in ev["rules"].values()) else
                     "R1-R7 fail")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--ledger", help="dry run only: a replay ledger")
    ap.add_argument("--replay-first", help="dry run only: first prospective target quarter of the replay (e.g. 2010-Q1)")
    a = ap.parse_args()
    plan = P.check_plan()
    if not a.dry_run:
        assert not (a.out or a.ledger or a.replay_first), "--out, --ledger and --replay-first are for dry runs only"
        assert a.date[5:] == "03-01" and a.date >= "2028-03-01", "real scorings are on 1 March, from 2028"
        assert a.date <= P.today(), "a scoring date cannot be in the future"
        out_dir, ledger, first_q, first_issue, opt1 = P.PROS, P.LEDGER, P.FIRST_TARGET, P.FIRST_ISSUE, True
    else:
        assert a.out, "a dry run needs --out"
        out_dir = Path(a.out).resolve()
        assert P.PROS.resolve() not in [out_dir, *out_dir.parents], "a dry run never writes into prospective/"
        ledger = Path(a.ledger) if a.ledger else P.LEDGER
        first_q = H.qi(a.replay_first) if a.replay_first else P.FIRST_TARGET
        first_issue = H.issue(first_q - 2) if a.replay_first else P.FIRST_ISSUE
        opt1 = not a.replay_first
    path = out_dir / f"score_{a.date}.json"
    assert not path.exists(), f"{path.name} exists: a scoring report is never overwritten"

    d = H.load()
    lab = V.area_labels(d)
    R, files = collect(ledger, opt1, d, lab)
    labels = P.labels_at(a.date)
    last_closed = (pd.Timestamp(a.date) - pd.Timedelta(days=P.SEAL_WINDOW_DAYS)).strftime("%Y-%m-%d")
    expected = issues_between(first_issue, last_closed)
    have = {e["issue"] for e in P.read_ledger(ledger)} | ({"2026-10-01"} if opt1 else set())
    missed = [i for i in expected if i not in have]
    leads = {m: {str(k): score_lead(R, m, k, labels, first_q) if len(R) else
                 {"status": "insufficient prospective evidence", "labelled_quarters": 0} for k in P.LEADS}
             for m in P.MODELS}
    rep = {"plan_sha256": plan, "scoring_date": a.date, "dry_run": a.dry_run, "first_prospective_target": H.qs(first_q),
           "sealed_files": files, "missed_seals": missed, "n_missed": len(missed), "models": leads,
           "main_model": P.MAIN, "minimum_quarters": P.MIN_QUARTERS}
    vpath = out_dir / "VERDICT.json"
    main = leads[P.MAIN]
    if vpath.exists():
        rep["verdict"] = {**json.loads(vpath.read_text(encoding="utf-8")), "note": "taken earlier; unchanged"}
    elif a.date[5:] == "03-01" and all(main[str(k)].get("labelled_quarters", 0) >= P.MIN_QUARTERS for k in P.LEADS):
        l1 = main["1"]["status"] == "all R1-R7 pass"
        l2 = l1 and main["2"]["status"] == "all R1-R7 pass"
        v = {"taken_on": a.date, "single_look": True, "dry_run": a.dry_run,
             "lead1": "reliable" if l1 else "not reliable on prospective evidence",
             "lead2": "reliable" if l2 else "not reliable on prospective evidence",
             "maximum_reliable_lead": 2 if l2 else 1 if l1 else 0,
             "quarters": {k: main[k]["labelled_quarters"] for k in ("1", "2")}}
        out_dir.mkdir(parents=True, exist_ok=True)
        vpath.write_text(P.dumps(v), encoding="utf-8")
        rep["verdict"] = v
    else:
        rep["verdict"] = {"status": "not yet: needs >= 40 labelled prospective quarters at both leads on a 1 March "
                                    "scoring date", "quarters": {k: main[k].get("labelled_quarters", 0) for k in ("1", "2")}}
    out_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(P.dumps(rep), encoding="utf-8")
    lines = [f"# Prospective scoring {a.date}{' (DRY RUN)' if a.dry_run else ''}", "",
             f"Plan `{plan[:8]}`; sealed files verified: {len(files)}; missed seals: {len(missed)} {missed}", "",
             "| Model | Lead | Labelled quarters | Accuracy (90% Wilson) | Rules failed | Status |", "|---|---|---|---|---|---|"]
    for m, Ls in leads.items():
        for k, L in Ls.items():
            acc = L.get("rule_75pct")
            failed = [r for r, v in (L.get("rules") or {}).items() if not v["pass"]] if L.get("rules") else "n/a"
            ci = f"{acc['accuracy']:.3f} ({acc['wilson90'][0]:.2f}-{acc['wilson90'][1]:.2f})" if acc else "-"
            lines.append(f"| {m} | {k} | {L.get('labelled_quarters', 0)} | {ci} | {failed} | {L['status']} |")
    lines += ["", f"Verdict: {json.dumps(rep['verdict'])}"]
    path.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
