"""Seal the prospective REF+news (and REF) forecasts of one issue date (PROSPECTIVE_PLAN.md section 1).

    python seal_next.py --issue 2027-01-01                      # real seal (only within 14 days after the issue date)
    python seal_next.py --issue 2026-10-01 --dry-run --out DIR  # dry run: nothing written outside DIR, ledger untouched

Real mode refuses unless all of these hold:
- the plan hash is intact; the issue date is a quarter start on or after 2027-01-01;
- today is between the issue date and 14 days after it;
- no SWS round of either target quarter is in the round table as published by today;
- the seal file does not exist yet;
- every input source has been refreshed to what the release rules allow at O(t), unless named in --allow-stale. A named
  source is recorded in the seal; its columns are whatever the refreshed files hold (NaN when missing).

It rebuilds the whole BL input table from the current data files (iv2_lib.rows_origin, origins 1998-Q3..t), refits
REF+news and REF at origin t exactly as OPTION_1 (IMPROVE_V2 grid, selection, settings, seed), and writes one file with
4 rows (2 models x Leads 1-2) plus the baselines. In real mode it appends the file's SHA-256 to the ledger and prints the
git commands to commit both; it never commits or pushes by itself.

In a dry run for an origin that has stored development outputs (t <= 2026-Q3), the rebuilt table rows and the four
forecasts are compared with the stored IMPROVE_V2 / OPTION_1 / IMPROVE_V2_LEADS values (replay check).
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prospective_lib as P  # noqa: E402

H, V = P.H, P.V


def replay_check(t: int, T: pd.DataFrame, out: pd.DataFrame) -> dict:
    stored = pd.read_csv(P.STORED_TABLE, dtype={"area": str})
    s = stored[(stored["area"] == "BL") & (stored["t"] == t)].sort_values("lead").reset_index(drop=True)
    r = T[T["t"] == t].sort_values("lead").reset_index(drop=True)[s.columns]
    num = [c for c in s.columns if pd.api.types.is_numeric_dtype(s[c])]
    tab = {"max_abs_diff": float(np.nanmax(np.abs(r[num].to_numpy(float) - s[num].to_numpy(float)))),
           "nan_pattern_equal": bool((r[num].isna().to_numpy() == s[num].isna().to_numpy()).all())}
    opt = pd.read_csv(P.EXP / "OPTION_1" / "out" / "forecasts_refnews.csv")
    lds = pd.read_csv(P.EXP / "IMPROVE_V2_LEADS" / "out" / "forecasts_leads.csv")
    cbf = pd.read_csv(P.CB_DIR / "out" / "forecasts.csv")
    cbz = pd.read_csv(P.CB_DIR / "out" / "news_anomalies.csv").set_index("t")["z_N1R"]
    zt = T[T["t"] == t]["z_N1R"].iloc[0]
    tab["z_N1R_equal"] = bool((np.isnan(zt) and np.isnan(cbz.get(t, np.nan))) or abs(zt - cbz.get(t, np.nan)) <= 1e-12)
    ref = {("REF+news", k): float(opt[(opt["name"] == "REF+news") & (opt["t"] == t) & (opt["lead"] == k)]["p"].iloc[0])
           for k in P.LEADS}
    ref.update({("REF", k): float(lds[(lds["name"] == "REF") & (lds["t"] == t) & (lds["lead"] == k)]["p"].iloc[0])
                for k in P.LEADS})
    ref.update({("C-b", k): float(cbf[(cbf["name"] == "C-b") & (cbf["t"] == t) & (cbf["lead"] == k)]["p"].iloc[0])
                for k in P.LEADS})
    ps = float(lds[(lds["name"] == "PERSIST") & (lds["t"] == t) & (lds["lead"] == 1)]["p"].iloc[0])
    cl = float(lds[(lds["name"] == "CLIM") & (lds["t"] == t) & (lds["lead"] == 1)]["p"].iloc[0])
    fc = {f"{m} L{k}": abs(float(out[(out["model"] == m) & (out["lead"] == k)]["p_high"].iloc[0]) - v)
          for (m, k), v in ref.items()}
    base = {"persist_si": abs(float(out["persist_si"].iloc[0]) - ps), "clim": abs(float(out["clim"].iloc[0]) - cl)}
    ok = tab["max_abs_diff"] <= 1e-9 and tab["nan_pattern_equal"] and tab["z_N1R_equal"] and max(fc.values()) <= 1e-12 \
        and max(base.values()) <= 1e-12
    return {"table_rows": tab, "forecast_abs_diff": fc, "baseline_abs_diff": base, "replay_matches": bool(ok)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--issue", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", help="dry run only: directory for the dry-run file")
    ap.add_argument("--today", help="dry run only: pretend today is this date")
    ap.add_argument("--allow-stale", default="", help="comma-separated freshness keys accepted as stale (recorded)")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()

    plan = P.check_plan()
    t = P.origin_of_issue(a.issue)
    targets = [t + k for k in P.LEADS]
    now = a.today if (a.dry_run and a.today) else P.today()
    if not a.dry_run:
        assert a.today is None and a.out is None, "--today and --out are for dry runs only"
        assert a.issue >= P.FIRST_ISSUE, "real seals start at 2027-01-01"
        lag = (pd.Timestamp(now) - pd.Timestamp(a.issue)).days
        assert lag >= 0, f"too early: the issue date {a.issue} is {-lag} days away"
        assert lag <= P.SEAL_WINDOW_DAYS, f"MISSED: today is {lag} days after the issue date (allowed 0..14); " \
                                          "the forecast is recorded as missing, never back-filled"
        out_dir = P.PROS
    else:
        assert a.out, "a dry run needs --out"
        out_dir = Path(a.out).resolve()
        assert P.PROS.resolve() not in [out_dir, *out_dir.parents], "a dry run never writes into prospective/"
    s = pd.read_csv(P.SWS_FILE)
    pub = s[s["quarter"].isin([H.qs(q) for q in targets]) & (s["published"].astype(str).str[:10] <= now)]
    assert pub.empty, f"an SWS round of a target quarter is already published: {pub['quarter'].tolist()}"
    path = out_dir / f"sealed_{a.issue}.csv"
    assert not path.exists(), f"{path.name} exists: a sealed file is never overwritten"

    d = H.load()
    fresh = P.freshness(d, t)
    allowed = {x for x in a.allow_stale.split(",") if x}
    stale = sorted(k for k, ok in fresh.items() if not ok)
    if not a.dry_run:
        assert set(stale) <= allowed, f"inputs not refreshed for this issue date: {sorted(set(stale) - allowed)}"

    lab = V.area_labels(d)
    T = P.add_news_anomaly(P.build_table(list(range(H.FIRST_ORIGIN, t + 1)), a.workers))   # C-b's z_N1R (Addendum CB)
    base = P.baselines(d, lab, t)
    kn = H.known(d, t, "BL")
    commit = P.code_commit()
    if not a.dry_run:
        assert not commit["model_code_dirty"], "model code has uncommitted changes: commit it first"
    hashes = P.input_hashes()
    sealed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    for m, cols in P.MODELS.items():
        f = P.fit_origin(T, d, lab, t, cols)
        for r in f.itertuples():
            rows.append({"issue_date": a.issue, "origin": H.qs(t), "lead": int(r.lead), "target_quarter": H.qs(int(r.q)),
                         "model": m, "p_high": float(r.p), "class": "HIGH" if r.p >= .5 else "LOW",
                         "persist_si": base["persist_si"], "clim": base["clim"], "clim_quarters": base["clim_quarters"],
                         "newest_sws_q": H.qs(kn[-1][0]) if kn else "", "newest_sws_reading": kn[-1][1] if kn else "",
                         "newest_sws_published": kn[-1][2] if kn else "", "fallback": bool(r.fallback),
                         "cfg": r.cfg, "n_train": int(r.n_train), "code_commit": commit["commit"],
                         "model_code_dirty": commit["model_code_dirty"], "plan_sha256": plan,
                         "stale_sources": ";".join(stale), "input_hashes": json.dumps(hashes, sort_keys=True),
                         "sealed_at": sealed_at, "dry_run": bool(a.dry_run)})
    out = pd.DataFrame(rows)
    out_dir.mkdir(parents=True, exist_ok=True)
    out.to_csv(path, index=False)
    digest = P.sha(path)
    report = {"issue": a.issue, "origin": H.qs(t), "file": str(path), "sha256": digest, "freshness": fresh,
              "stale": stale, "dry_run": a.dry_run,
              "forecasts": out[["model", "lead", "target_quarter", "p_high", "class"]].to_dict("records"),
              "baselines": base}
    if a.dry_run and t <= V.LAST_ORIGIN:
        report["replay"] = replay_check(t, T, out)
    if not a.dry_run:
        P.append_ledger(P.LEDGER, {"file": path.name, "sha256": digest, "issue": a.issue,
                                   "targets": ", ".join(H.qs(q) for q in targets), "sealed_at": sealed_at,
                                   "commit": commit["commit"][:12]})
        report["next"] = ("git add " + str(path.relative_to(P.ROOT)) + " " + str(P.LEDGER.relative_to(P.ROOT))
                          + f' && git commit -m "Prospective seal {a.issue}"  (within 14 days of the issue date)')
    print(P.dumps(report))


if __name__ == "__main__":
    main()
