"""Seal M3, the mid-quarter Lead-2 update (backend/seals/PREREG_LEAD2_ADDENDUM_2.md), for one issue date.

Additive research tooling: never imported by backend/app. Reuses the guards of seal_lead2.py (publication dates, no
overwrite, append-only ledger, hashes) and the M3 definitions of LEAD2_MIDQUARTER_UPDATE/runner/run_m3.py, read-only.
The price refit runs in a child process with every origin's CPI cutoff at its own mid-quarter issue date.

    python -B scripts/seal_lead2_m3.py --issue 2026-11-01

The issue date must be the first day of the second month of a quarter; the origin is the quarter before it and the
target the origin + 2. Writes seals/<issue>_<target>_M3.json and one ledger row ("late" if sealed after the issue date).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import seal_lead2 as SL  # noqa: E402

M3_RUNNER = SL.EXP / "LEAD2_MIDQUARTER_UPDATE" / "runner"
ADDENDUM_2 = SL.SEALS / "PREREG_LEAD2_ADDENDUM_2.md"
CODE_FILES = [M3_RUNNER / "run_m3.py", SL.PRICE_RUNNER / "price_refit.py", SL.ISSUE_RUNNER / "score.py",
              Path(__file__).resolve(), Path(SL.__file__).resolve()]


def m3_issue_date(origin: int) -> dt.date:
    n = origin + 1
    return dt.date(n // 4, (n % 4) * 3 + 2, 1)


def origin_of(issue: dt.date) -> int:
    t = SL.quarter_of(issue) - 1
    if m3_issue_date(t) != issue:
        raise SL.SealError(f"{issue} is not an M3 issue date (the first day of the second month of a quarter)")
    return t


def _m3():
    sys.path.insert(0, str(M3_RUNNER))
    import run_m3 as M
    return M


def child(origin: int, out: Path) -> None:
    log = SL._FileLog()
    log.install()
    M = _m3()
    PR, U, L, E = M.PR, M.U, M.L, M.E
    PR.frozen_ok()
    U.setup()
    if origin > E.LAST_ORIGIN:
        raise SL.SealError(f"origin {SL.qs(origin)} is after the feature tables' last origin {SL.qs(E.LAST_ORIGIN)}")
    U.world_features = PR.world_features_at
    L.m0_of = M.m0_m3
    S = U.stack(PR.K)
    for t in sorted(int(x) for x in S["t"].unique() if int(x) <= origin):
        m, D = M.m0_m3(t), M.issue_m3(t)
        dc = E.data()[0].cut(t)
        newest = int(max(dc.idx["ym"].max(), dc.yoy["ym"].max()))
        if newest > m or not SL.cpi_month_available(m, D.date()):
            raise SL.SealError(f"CPI leakage at origin {SL.qs(t)}")
    f, info = PR.p0_origin(S, origin)
    if f is None:
        raise SL.SealError(f"no eligible training rows for origin {SL.qs(origin)}")
    f = f[f["lead"] == 2]
    te = S[(S["t"] == origin) & (S["lead"] == 2)].set_index("province_code")
    rows = {}
    for _, r in f.iterrows():
        x = te.loc[r["province_code"]]
        rows[r["province_code"]] = {"price": float(r["P0_price"]), "features": {
            "issue_date": str(x["issue_date"]), "sws_newest_published": str(x.get("sws_newest_published")),
            "news_latest_published": None if x.get("news_latest_published") in (None, "None") else str(x.get("news_latest_published"))}}
    m = M.m0_m3(origin)
    out.write_text(json.dumps({"fit": info, "rows": rows, "cpiCutoff": L.ym_s(m), "filesRead": log.report()}, default=str),
                   encoding="utf-8")


def run_child(origin: int) -> dict:
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "m3.json"
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        for k in ("AIPHEED_LEAD2_MODEL", "AIPHEED_MAP_MODEL"):
            env.pop(k, None)
        r = subprocess.run([sys.executable, "-B", __file__, "--_child", "--origin", str(origin), "--out", str(out)],
                           capture_output=True, text=True, env=env)
        if r.returncode != 0 or not out.exists():
            raise SL.SealError(f"M3 price refit failed:\n{r.stdout[-2000:]}\n{r.stderr[-3000:]}")
        return json.loads(out.read_text(encoding="utf-8"))


def build(issue: dt.date, sealed_at: dt.datetime) -> tuple[Path, dict]:
    pre, add2 = SL.prereg_sha(), SL.prereg_sha(ADDENDUM_2)
    t = origin_of(issue)
    target = t + 2
    path = SL.SEALS / f"{issue.isoformat()}_{SL.qs(target)}_M3.json"
    if path.exists():
        raise SL.SealError(f"refusing to overwrite existing seal {path.name}")
    ch = run_child(t)
    M = _m3()
    SI = M.SI
    X = SI.setup()
    iss = issue.isoformat()
    h, info = SI.h4_at(X, iss, t, 2)
    SL.assert_published_before([{"published": info["newestSwsPublished"]}], issue, "SWS round of M3")
    o = SI.R.issue(t).date()
    for p, r in ch["rows"].items():
        fe = r["features"]
        SL.assert_published_before([{"published": fe["sws_newest_published"]}], issue, f"{p} SWS feature")
        if fe["news_latest_published"]:
            SL.assert_published_before([{"published": fe["news_latest_published"]}], issue, f"{p} news")
        if fe["issue_date"][:10] != o.isoformat():
            raise SL.SealError(f"{p}: feature row issued {fe['issue_date']}, not O(t) {o}")
    provs = sorted(ch["rows"])
    if tuple(provs) != SL.PROVINCES:
        raise SL.SealError(f"expected the five CALABARZON provinces, got {provs}")
    ps, cl = SI.persist_clim_at(X, iss, t, provs, SI.cpi_newest(SI.pd.Timestamp(issue)))
    late = sealed_at.date() > issue

    def cand(price: float) -> dict:
        prob = h * price
        return {"hunger": round(h, 6), "price": round(price, 6), "probability": round(prob, 6),
                "M3-D0": "HIGH" if prob >= 0.50 else "LOW", "M3-E1": "HIGH" if prob >= 0.45 else "LOW"}

    payload = {
        "schema": "aipheed-lead2-seal-m3/1", "preregSha256": pre, "addendum2Sha256": add2,
        "origin": SL.qs(t), "target": SL.qs(target), "lead": 2, "method": "M3 mid-quarter update",
        "issueDate": {"C3_M3": iss},
        "sealedAtUTC": sealed_at.isoformat(timespec="seconds"), "timing": "late" if late else "on-time",
        "lateNote": (f"Sealed {sealed_at.date()}, after its issue date {issue}, using only inputs published before "
                     f"{issue}; reported separately and excluded from the evaluation.") if late else None,
        "candidates": {"C3_M3": {p: cand(ch["rows"][p]["price"]) for p in provs}},
        "baselines": {"atIssue": {"PERSIST-SI": {p: ps[p] for p in provs}, "CLIM": cl, "ALWAYS-LOW": 0.0}},
        "inputs": {"hunger": info, "cpiCutoff": ch["cpiCutoff"],
                   "cpiRule": "month M available from the first day of M+2",
                   "priceFeatures": {p: r["features"] for p, r in ch["rows"].items()}, "priceFit": ch["fit"],
                   "filesRead": ch["filesRead"],
                   "vintageNote": ("Data files are hashed as they stood when sealed; later revisions of already-published "
                                   "values cannot be excluded from the project files.")},
        "code": {"gitCommit": SL.git_commit(),
                 "sha256": {f.relative_to(SL.REPO).as_posix(): SL.sha256_file(f) for f in CODE_FILES}},
    }
    return path, payload


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--issue")
    ap.add_argument("--_child", action="store_true")
    ap.add_argument("--origin", type=int)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    if a._child:
        child(a.origin, Path(a.out))
        return 0
    if not a.issue:
        ap.error("--issue YYYY-MM-DD is required")
    try:
        issue = dt.date.fromisoformat(a.issue)
        path, payload = build(issue, dt.datetime.now(dt.timezone.utc))
        sha = SL.write_seal(path, payload)
        SL.ledger_append({"file": path.name, "sha256": sha, "issue": issue.isoformat(), "target": payload["target"],
                          "sealedAt": payload["sealedAtUTC"], "timing": payload["timing"],
                          "prereg": payload["addendum2Sha256"], "commit": payload["code"]["gitCommit"]})
    except SL.SealError as e:
        print(f"SEAL REFUSED: {e}", file=sys.stderr)
        return 2
    print(f"sealed {path.name}  sha256 {sha}  ({payload['timing']})")
    for p, r in payload["candidates"]["C3_M3"].items():
        print(f"  M3 {p}  hunger {r['hunger']:.3f}  price {r['price']:.3f}  prob {r['probability']:.3f}  "
              f"M3-D0 {r['M3-D0']}  M3-E1 {r['M3-E1']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
