"""Y16 evaluation (EXPERIMENT_PLAN.md section 5; Amendment 1 = BOOTSTRAP_AMENDMENT.md). Reads valid seals from
prospective/ and resolved outcomes only.

Stages (unchanged): fewer than 8 resolved quarters -> integrity only (no metrics); 8..19 -> descriptive (no test);
>= 20 -> the registered primary analysis on the first 20 resolved target quarters (by issue date), locked after the
first run. Amendment 1 adds, without changing the primary analysis: the moving-block sensitivity analysis, and the
registered reporting items calibration, missed issues and overlay verification (labelled supplementary).

    python -B evaluate.py
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pandas as pd  # noqa: E402

import kprospect as K  # noqa: E402

PRIMARY_N, DESCRIPTIVE_N = 20, 8


def evaluate(pdir: Path, overlay: Path, today: dt.date, out_dir: Path | None = None,
             allow_clock_override: bool = False) -> dict:
    plan, amend = K.plan_sha(), K.amendment_sha()
    K.install_overlay(overlay)
    d = K.load_seals(pdir, allow_clock_override=allow_clock_override)          # raises on any registry inconsistency
    rec = d.attrs["reconcile"]
    res = {"today": str(today), "planSha256": plan, "amendment1Sha256": amend, "validSeals": int(len(d)),
           "integrity": {"registryConsistent": rec["ok"], "reissues": rec["reissues"], "limits": rec["limits"]},
           "supplementary": {"label": "supplementary (registered reporting items; not part of the superiority decision)",
                             "missedIssues": K.missed_issues(d, today),
                             "failedIssueAttempts": [a for a in K.read_attempts(pdir) if a.get("result") == "failed"],
                             "attestationStatus": K.attestation_status(pdir)}}
    if d.empty:
        res["stage"] = "no valid seals yet"
        return res
    res["integrity"]["overlayRowsVerified"] = K.verify_overlay(d, overlay)    # raises if overlay history changed
    d["H_obs"] = [K.outcome(tg, today) for tg in d["target"]]
    res["unresolved"] = d.loc[d["H_obs"].map(lambda v: v is None), "target"].tolist()
    r = d[d["H_obs"].map(lambda v: v is not None)].copy()
    res["missingOutcome"] = r.loc[r["H_obs"].isna(), "target"].tolist()
    res["noForecast"] = r.loc[r["PERS"].isna() | r["KAL"].isna(), "target"].tolist()
    r = r[r["H_obs"].notna() & r["PERS"].notna() & r["KAL"].notna()].sort_values("issue")
    r["y"] = (r["H_obs"] > K.R.H_LINE).astype(int)
    res["resolvedPaired"] = int(len(r))
    if len(r) < DESCRIPTIVE_N:
        res["stage"] = f"integrity only ({len(r)} < {DESCRIPTIVE_N} resolved quarters): no metrics reported"
        return res
    if len(r) < PRIMARY_N:
        res["stage"] = "descriptive (no hypothesis test before 20 resolved quarters)"
        res["descriptive"] = {m: K.metrics(r["y"], r[m]) for m in ("PERS", "KAL")}
        res["supplementary"]["calibration"] = {m: K.calibration(r["y"], r[m]) for m in ("PERS", "KAL")}
        return res
    p = r.head(PRIMARY_N)
    res["stage"] = "PRIMARY ANALYSIS (first 20 resolved target quarters)"
    primary = {"targets": p["target"].tolist(), "issues": p["issue"].tolist(), "seals": p["file"].tolist(),
               "outcomes": [float(x) for x in p["H_obs"]],
               "metrics": {m: K.metrics(p["y"], p[m]) for m in ("PERS", "KAL")}, "paired": K.paired(p)}
    pr = primary["paired"]
    primary["superiority"] = bool(pr["p_one_sided_bootstrap"] < 0.05 and pr["CI95"][1] < 0
                                  and pr["signTest"]["p_one_sided"] is not None and pr["signTest"]["p_one_sided"] < 0.10)
    primary["sevenRules"] = {m: K.seven_rules(p, m) for m in ("PERS", "KAL")}
    sens = K.block_paired(p)
    if primary["superiority"]:
        verdict = "superiority, robust to serial dependence" if sens.get("robust") else \
            "superiority under the registered test; NOT robust to serial dependence (Amendment 1)"
    else:
        verdict = "no superiority"
    primary["sensitivity_blockBootstrap"] = sens
    primary["reportedVerdict"] = verdict
    primary["calibration_supplementary"] = {m: K.calibration(p["y"], p[m]) for m in ("PERS", "KAL")}
    res.update(primary)
    if out_dir is not None:
        res["primaryLock"] = K.lock_primary(out_dir, primary)
    return res


def main():
    today = dt.datetime.now(K.MANILA).date()
    out_dir = K.Y16 / "out"
    res = evaluate(K.Y16 / "prospective", K.DEFAULT_OVERLAY, today, out_dir=out_dir)
    out = out_dir / f"evaluation_{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    out.parent.mkdir(exist_ok=True)
    with open(out, "x", encoding="utf-8") as g:                  # every evaluation is kept; none is overwritten
        g.write(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
