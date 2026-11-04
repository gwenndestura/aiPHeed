"""Seal the C-E2 and C-E6 prospective forecasts of one issue date (CE_PROSPECTIVE_PLAN.md sections 2-4).

    python seal_ce.py --issue 2026-10-01 --dry-run --out DIR                    # dry run + replay vs stored fits
    python seal_ce.py --issue 2027-01-01 --dry-run --out DIR --today 2027-01-05 # dry run of the first real issue
    python seal_ce.py --issue 2027-01-01 --seal [--allow-stale KEY,...]        # REAL seal: needs authorization

A real seal refuses unless:
- --seal is given;
- prospective_ce/AUTHORIZATION_<issue>.txt says 'AUTHORIZED: seal_ce <issue>';
- the issue date is on or after 2027-01-01, and today is within 14 days after it;
- no SWS round of a target quarter is published by today;
- the plan and both pre-registrations are intact, and the model code is committed;
- every stale input is named in --allow-stale;
- the seal file does not exist yet.

A dry run writes only into --out (never prospective_ce/ or SENIOR_REVIEW/prospective/) and never touches a ledger.
For an origin with stored development fits (<= 2026-Q3), it checks that the rebuilt inputs and every C-E2/C-E6
forecast equal the stored ones (replay).
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ce_prospective as C  # noqa: E402
import ce2_model as CE2  # noqa: E402
import ce6_model as CE6  # noqa: E402
import ce_model as CE  # noqa: E402

P, H, V, N = C.P, CE.H, CE.V, CE.N


def ce_table(T: pd.DataFrame, origins: list[int]) -> pd.DataFrame:
    """Add E2 (quarters <= t-2) and ST1/ST2 (stock month <= issue month - 4) to the rebuilt table."""
    e2 = CE.e2_series(CE._pt(), origins)
    S = CE6._stocks()
    st = pd.DataFrame([{"t": t, **dict(zip(CE6.ST, CE6.st_values(S, t)))} for t in origins])
    return T.merge(pd.DataFrame({"t": e2.index, "E2": e2.to_numpy()}), on="t", how="left").merge(st, on="t", how="left")


def ce_freshness(t: int) -> dict:
    iss = H.issue(t)
    m = int(iss[:4]) * 12 + int(iss[5:7]) - 1 - CE6.LAG_MONTHS
    return {"remittance_quarter_t-2": (t - 2) in CE._pt().index, "rice_stock_month_issue-4": m in CE6._stocks().index,
            "rice_stock_month_used": f"{m // 12}-{m % 12 + 1:02d}"}


def replay(t: int, T: pd.DataFrame, out: pd.DataFrame) -> dict:
    """Rebuilt inputs and forecasts vs the stored development artifacts at origin t."""
    st = pd.read_csv(C.HERE / "out" / "ce6_features.csv")
    stored = pd.read_csv(CE.N.IV2_OUT / "table_pooled.csv", dtype={"area": str})
    stored = stored[(stored["area"] == "BL") & (stored["t"] == t)].merge(
        pd.read_csv(N.OUT / "news_anomalies.csv"), on="t", how="left").merge(
        pd.read_csv(C.HERE / "out" / "ce_features.csv"), on="t", how="left").merge(st, on="t", how="left")
    cols = [c for c in CE.CE + CE6.ST if c != "lead"]
    a = T[(T["area"] == "BL") & (T["t"] == t)].set_index("lead").sort_index()[cols]
    b = stored.set_index("lead").sort_index()[cols].loc[a.index]
    tab = float(np.nanmax(np.abs(a.to_numpy(float) - b.to_numpy(float)))) if len(a) else None
    nan_match = bool((a.isna().to_numpy() == b.isna().to_numpy()).all())
    diffs = {}
    for m, f in (("C-E2", "ce2_fits.csv"), ("C-E6", "ce6_fits.csv")):
        s = pd.read_csv(C.HERE / "out" / f)
        s = s[s["t"] == t].set_index("lead")["p"]
        for r in out[out["model"] == m].itertuples():
            diffs[f"{m} L{r.lead}"] = abs(float(r.p_high) - float(s[int(r.lead)]))
    return {"table_max_abs_diff": tab, "table_nan_pattern_equal": nan_match, "forecast_abs_diff": diffs,
            "replay_matches": bool((tab is None or tab < 1e-9) and nan_match and max(diffs.values()) < 1e-9)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--issue", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--seal", action="store_true", help="REAL seal (requires the authorization file)")
    ap.add_argument("--out")
    ap.add_argument("--today")
    ap.add_argument("--allow-stale", default="")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    assert a.dry_run != a.seal, "choose exactly one of --dry-run or --seal"

    plan = C.check_plan()
    pre = {m: C.hash_line(C.HERE / f) for m, f in C.CE_MODELS.items()}
    t = P.origin_of_issue(a.issue)
    targets = [t + k for k in C.SEAL_LEADS]
    now = a.today if (a.dry_run and a.today) else P.today()
    if a.seal:
        assert a.today is None and a.out is None, "--today and --out are for dry runs only"
        assert C.authorized(a.issue), f"not authorized: prospective_ce/AUTHORIZATION_{a.issue}.txt is missing or wrong"
        assert a.issue >= P.FIRST_ISSUE, "real seals start at 2027-01-01"
        lag = (pd.Timestamp(now) - pd.Timestamp(a.issue)).days
        assert 0 <= lag <= P.SEAL_WINDOW_DAYS, f"outside the window (day {lag}; allowed 0..14): recorded as missing"
        assert not C.ce_code_dirty() and not P.code_commit()["model_code_dirty"], "model code is not committed"
        out_dir = C.PROS_CE
    else:
        assert a.out, "a dry run needs --out"
        out_dir = Path(a.out).resolve()
        for forbidden in (C.PROS_CE, P.PROS):
            assert forbidden.resolve() not in [out_dir, *out_dir.parents], f"a dry run never writes into {forbidden}"
    s = pd.read_csv(P.SWS_FILE)
    pub = s[s["quarter"].isin([H.qs(q) for q in targets]) & (s["published"].astype(str).str[:10] <= now)]
    if a.seal:
        assert pub.empty, f"an SWS round of a target quarter is already published: {pub['quarter'].tolist()}"
    path = out_dir / f"sealed_ce_{a.issue}.csv"
    assert not path.exists(), f"{path.name} exists: a sealed file is never overwritten"

    d = H.load()
    fresh = {**P.freshness(d, t), **{k: v for k, v in ce_freshness(t).items() if isinstance(v, bool)}}
    stale = sorted(k for k, ok in fresh.items() if not ok)
    if a.seal:
        allowed = {x for x in a.allow_stale.split(",") if x}
        assert set(stale) <= allowed, f"inputs not refreshed for this issue date: {sorted(set(stale) - allowed)}"
    origins = list(range(H.FIRST_ORIGIN, t + 1))
    T = ce_table(P.add_news_anomaly(P.build_table(origins, a.workers)), origins)
    lab = V.area_labels(d)
    N._G.update({"d": d, "T": T, "lab": lab})
    fits = {"C-E2": CE2._origin(t), "C-E6": CE6._origin(t)}
    base = P.baselines(d, lab, t)
    kn = H.known(d, t, "BL")
    commit = P.code_commit()
    code = C.code_hashes()
    cut = {**P.feature_cutoff(d, t), "rice_stock_month": ce_freshness(t)["rice_stock_month_used"],
           "remittance_quarter": H.qs(t - 2)}
    inputs = {**P.input_hashes(), "rice_stocks": C.sha(CE6.STOCKS), "remittances": C.sha(CE.REMIT)}
    sealed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    for m, f in fits.items():
        for r in f[f["lead"].isin(C.SEAL_LEADS)].itertuples():
            rows.append({"issue_date": a.issue, "origin": H.qs(t), "lead": int(r.lead), "target_quarter": H.qs(int(r.q)),
                         "model": m, "model_id": m, "prereg_sha256": pre[m], "plan_sha256": plan,
                         "p_high": float(r.p), "class": "HIGH" if r.p >= .5 else "LOW", "fallback": bool(r.fallback),
                         "persist_si": base["persist_si"], "clim": base["clim"], "clim_quarters": base["clim_quarters"],
                         "newest_sws_q": H.qs(kn[-1][0]) if kn else "", "newest_sws_published": kn[-1][2] if kn else "",
                         "feature_cutoff": json.dumps(cut, sort_keys=True), "stale_sources": ";".join(stale),
                         "code_sha256": json.dumps(code, sort_keys=True), "input_sha256": json.dumps(inputs, sort_keys=True),
                         "code_commit": commit["commit"], "code_dirty": bool(C.ce_code_dirty() or commit["model_code_dirty"]),
                         "sealed_at": sealed_at, "dry_run": bool(a.dry_run)})
    out = pd.DataFrame(rows)
    out_dir.mkdir(parents=True, exist_ok=True)
    out.to_csv(path, index=False)
    digest = C.sha(path)
    report = {"issue": a.issue, "origin": H.qs(t), "file": str(path), "sha256": digest, "dry_run": a.dry_run,
              "plan_sha256": plan, "prereg": pre, "freshness": fresh, "stale": stale, "feature_cutoff": cut,
              "published_target_rounds_at_today": pub["quarter"].tolist(),
              "forecasts": out[["model", "lead", "target_quarter", "p_high", "class"]].to_dict("records")}
    if a.dry_run and t <= V.LAST_ORIGIN:
        report["replay"] = replay(t, T, out)
    if a.seal:
        C.append_ledger(C.LEDGER_CE, {"file": path.name, "sha256": digest, "issue": a.issue,
                                      "targets": ", ".join(H.qs(q) for q in targets), "sealed_at": sealed_at,
                                      "commit": commit["commit"][:12]})
        report["next"] = f"git add {path.relative_to(C.ROOT)} {C.LEDGER_CE.relative_to(C.ROOT)} && git commit (needs approval)"
    print(C.dumps(report))


if __name__ == "__main__":
    main()
