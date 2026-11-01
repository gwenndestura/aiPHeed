"""Seal the Lead-2 candidates of backend/seals/PREREG_LEAD2.md for one issue date.

Additive research tooling: never imported by backend/app, changes nothing the backend serves. It reuses the
parity-verified experiment code read-only (LEAD2_POST_SWS_ISSUE/runner/score.py, LEAD2_POST_SWS_PRICE/runner/
price_refit.py); the served-cutoff and post-SWS-cutoff price refits run in separate child processes.

    python -B scripts/seal_lead2.py --issue 2026-10-15

The issue date must be O'(t) of an origin quarter t (the day after the quarter's last Balance Luzon SWS release, capped
at quarter end + 67 days); the target is t+2. Every input must be published before the issue date. The seal is written
to seals/<issue>_<target>.json (never overwritten), hashed, and appended to the append-only seals/LEDGER.md. A seal
written after its issue date is marked "late".
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
EXP = REPO / "aipheed-backend-aligned" / "experiments"
SEALS = BACKEND / "seals"
LEDGER = SEALS / "LEDGER.md"
PREREG = SEALS / "PREREG_LEAD2.md"
PRICE_RUNNER = EXP / "LEAD2_POST_SWS_PRICE" / "runner"
ISSUE_RUNNER = EXP / "LEAD2_POST_SWS_ISSUE" / "runner"
CODE_FILES = [ISSUE_RUNNER / "score.py", PRICE_RUNNER / "price_refit.py", Path(__file__).resolve()]
PROVINCES = ("PH040100000", "PH040200000", "PH040300000", "PH040400000", "PH040500000")
LEDGER_HEADER = ("# Lead-2 seal ledger (append-only)\n\n"
                 "Each row is written once, when the seal is made, before its target's outcome exists. Never edit or "
                 "delete a row. Pre-registration: PREREG_LEAD2.md.\n\n"
                 "| seal file | SHA-256 | issue date | target | sealed at (UTC) | timing | prereg SHA-256 | git commit |\n"
                 "|---|---|---|---|---|---|---|---|\n")


class SealError(Exception):
    """A sealing rule would be broken; nothing is written."""


# =============================================================================================== pure helpers
def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(Path(p).read_bytes())


def prereg_sha(path: Path = PREREG) -> str:
    """The pre-registration's embedded hash, after checking it equals the hash of every byte before its last line
    (`PREREG-SHA256: <hex>`, the only line allowed after it is none)."""
    b = Path(path).read_bytes()
    i = b.rfind(b"\nPREREG-SHA256:") + 1
    tail = b[i:].decode("utf-8", "replace")
    if i == 0 or tail.count("\n") > 1 or not tail.endswith("\n"):
        raise SealError(f"{Path(path).name}: the last line must be 'PREREG-SHA256: <hex>'")
    want = tail.split(":", 1)[1].strip()
    if sha256_bytes(b[:i]) != want:
        raise SealError(f"{path.name} changed after it was hashed")
    return want


def as_date(x) -> dt.date:
    if isinstance(x, dt.datetime):
        return x.date()
    if isinstance(x, dt.date):
        return x
    return dt.date.fromisoformat(str(x)[:10])


def assert_published_before(items: list[dict], issue, what: str) -> None:
    """Every item's `published` date must be strictly before the issue date (so it was public on the issue date)."""
    iss = as_date(issue)
    late = [i for i in items if i.get("published") in (None, "") or as_date(i["published"]) >= iss]
    if late:
        raise SealError(f"{what}: {len(late)} input(s) not published before {iss}: {late[:3]}")


def cpi_month_available(ym: int, issue) -> bool:
    """CPI month ym (year*12 + month-1) is available from the first day of month ym+2."""
    return dt.date((ym + 2) // 12, (ym + 2) % 12 + 1, 1) <= as_date(issue)


def seal_bytes(payload: dict) -> bytes:
    return (json.dumps(payload, indent=1, sort_keys=True, default=str) + "\n").encode("utf-8")


def write_seal(path: Path, payload: dict) -> str:
    """Create the seal file exclusively (never overwrite) and return its SHA-256."""
    b = seal_bytes(payload)
    try:
        with open(path, "xb") as f:
            f.write(b)
    except FileExistsError:
        raise SealError(f"refusing to overwrite existing seal {Path(path).name}") from None
    return sha256_bytes(b)


def ledger_entries(ledger: Path = LEDGER) -> dict[str, dict]:
    out = {}
    if not Path(ledger).exists():
        return out
    for line in Path(ledger).read_text(encoding="utf-8").splitlines():
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) == 8 and c[0].endswith(".json"):
            out[c[0]] = {"sha256": c[1], "issue": c[2], "target": c[3], "sealedAt": c[4], "timing": c[5],
                         "prereg": c[6], "commit": c[7]}
    return out


def ledger_append(row: dict, ledger: Path = LEDGER) -> None:
    """Append one row; the ledger is only ever opened for appending, and a seal file is listed at most once."""
    if row["file"] in ledger_entries(ledger):
        raise SealError(f"{row['file']} is already in the ledger")
    if not Path(ledger).exists():
        with open(ledger, "x", encoding="utf-8", newline="\n") as f:
            f.write(LEDGER_HEADER)
    with open(ledger, "a", encoding="utf-8", newline="\n") as f:
        f.write(f"| {row['file']} | {row['sha256']} | {row['issue']} | {row['target']} | {row['sealedAt']} | "
                f"{row['timing']} | {row['prereg']} | {row['commit']} |\n")


def verify_seal(path: Path, ledger: Path = LEDGER) -> dict:
    """The seal's bytes must hash to its ledger entry; returns the parsed seal."""
    e = ledger_entries(ledger).get(Path(path).name)
    if e is None:
        raise SealError(f"{Path(path).name} is not in the ledger")
    if sha256_file(path) != e["sha256"]:
        raise SealError(f"{Path(path).name} does not match its ledger hash (edited after sealing)")
    return json.loads(Path(path).read_text(encoding="utf-8"))


def qs(i: int) -> str:
    return f"{int(i) // 4}-Q{int(i) % 4 + 1}"


def quarter_of(d: dt.date) -> int:
    return d.year * 4 + (d.month - 1) // 3


def git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short=12", "HEAD"], cwd=REPO, capture_output=True, text=True,
                              check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


# =============================================================================================== child: one price refit
class _FileLog:
    """Records every data file read in this process (path, size, SHA-256, modification time)."""

    def __init__(self):
        self.paths: set[str] = set()

    def install(self):
        import builtins
        import pandas as pd
        log = self
        real_open = builtins.open

        def opener(file, mode="r", *a, **k):
            if isinstance(file, (str, os.PathLike)) and "r" in mode and "+" not in mode:
                log.note(file)
            return real_open(file, mode, *a, **k)
        builtins.open = opener
        for name in ("read_csv", "read_parquet", "read_json", "read_excel"):
            real = getattr(pd, name)

            def wrap(path, *a, _real=real, **k):
                if isinstance(path, (str, os.PathLike)):
                    log.note(path)
                return _real(path, *a, **k)
            setattr(pd, name, wrap)

    def note(self, p):
        q = Path(p).resolve()
        if q.is_file() and q.suffix.lower() in (".csv", ".parquet", ".json", ".xlsx", ".txt") and REPO in q.parents:
            self.paths.add(str(q))

    def report(self) -> list[dict]:
        out = []
        for p in sorted(self.paths):
            q = Path(p)
            st = q.stat()
            out.append({"path": q.relative_to(REPO).as_posix(), "bytes": st.st_size, "sha256": sha256_file(q),
                        "modified": dt.datetime.fromtimestamp(st.st_mtime, dt.timezone.utc).isoformat(timespec="seconds")})
        return out


def child(mode: str, origin: int, out: Path) -> None:
    log = _FileLog()
    log.install()
    sys.path.insert(0, str(PRICE_RUNNER))
    import price_refit as PR
    PR.frozen_ok()
    PR.U.setup()
    PR.install(mode)
    E = PR.E
    if origin > E.LAST_ORIGIN:
        raise SealError(f"origin {qs(origin)} is after the feature tables' last origin {qs(E.LAST_ORIGIN)}: the input "
                        "data and E107 LAST_ORIGIN must be extended first (not done here)")
    S = PR.U.stack(PR.K)
    leak = PR.leakage(mode, [origin])                                 # CPI cutoff available at the issue date
    f, info = PR.p0_origin(S, origin)
    if f is None:
        raise SealError(f"no eligible training rows for origin {qs(origin)}")
    f = f[f["lead"] == 2]
    te = S[(S["t"] == origin) & (S["lead"] == 2)].set_index("province_code")
    rows = {}
    for _, r in f.iterrows():
        p = r["province_code"]
        x = te.loc[p]
        rows[p] = {"price": float(r["P0_price"]), "cfg": r["P0_cfg"],
                   "features": {"issue_date": str(x["issue_date"]), "sws_newest_q": x.get("sws_newest_q"),
                                "sws_newest_published": str(x.get("sws_newest_published")),
                                "psa_newest_month": x.get("psa_newest_month"),
                                "news_latest_published": None if x.get("news_latest_published") in (None, "None") else
                                str(x.get("news_latest_published"))}}
    cpi = {"cutoff": leak[0]["cpiCutoff"], "availableFrom": leak[0]["cutoffAvailableFrom"],
           "newestInCut": leak[0]["newestCpiInCut"], "issue": leak[0]["issue"]}
    out.write_text(json.dumps({"mode": mode, "origin": qs(origin), "fit": info, "rows": rows, "cpi": cpi,
                               "filesRead": log.report()}, default=str), encoding="utf-8")


def run_child(mode: str, origin: int) -> dict:
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / f"{mode}.json"
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        env.pop("AIPHEED_LEAD2_MODEL", None)
        r = subprocess.run([sys.executable, "-B", __file__, "--_child", mode, "--origin", str(origin), "--out", str(out)],
                           capture_output=True, text=True, env=env)
        if r.returncode != 0 or not out.exists():
            raise SealError(f"{mode} price refit failed:\n{r.stdout[-2000:]}\n{r.stderr[-3000:]}")
        return json.loads(out.read_text(encoding="utf-8"))


# =============================================================================================== seal
def build(issue: dt.date, sealed_at: dt.datetime) -> tuple[Path, dict]:
    pre = prereg_sha()
    t = quarter_of(issue) - 1
    target = t + 2
    path = SEALS / f"{issue.isoformat()}_{qs(target)}.json"
    if path.exists():
        raise SealError(f"refusing to overwrite existing seal {path.name}")
    sys.path.insert(0, str(PRICE_RUNNER))
    import price_refit as PR                                          # also loads LEAD2_POST_SWS_ISSUE/score.py as SI
    SI = PR.SI
    o_post = SI.post_issue(t)
    if as_date(o_post) != issue:
        raise SealError(f"{issue} is not an issue date: O'({qs(t)}) = {as_date(o_post)}")
    X = SI.setup()
    R, L, E = SI.R, X.L, X.E
    o_served = as_date(R.issue(t))

    served, post = run_child("served", t), run_child("post", t)

    # hunger part at O(t) (C0) and O'(t) (C1, C2), with every SWS round used
    h0, i0 = SI.h4_at(X, o_served.isoformat(), t, 2)
    h2, i2 = SI.h4_at(X, issue.isoformat(), t, 2)
    rounds = R.rounds()
    used = rounds[rounds["published"] < pd_ts(issue)]
    sws_used = [{"area": a, "quarter": qs(q), "H": float(h), "published": str(p)[:10]}
                for a, q, h, p in zip(used["area"], used["q"], used["H"], used["published"])]
    assert_published_before(sws_used, issue, "SWS rounds")
    assert_published_before([{"published": i0["newestSwsPublished"]}], o_served, "SWS round of C0")
    assert_published_before([{"published": i2["newestSwsPublished"]}], issue, "SWS round of C1/C2")

    # every price input: features as of O(t), CPI cutoffs available at their issue dates
    for name, ch, iss in (("served", served, o_served), ("post", post, issue)):
        ym = int(ch["cpi"]["cutoff"][:4]) * 12 + int(ch["cpi"]["cutoff"][5:7]) - 1
        if not cpi_month_available(ym, iss):
            raise SealError(f"{name}: CPI {ch['cpi']['cutoff']} not available at {iss}")
        for p, r in ch["rows"].items():
            fe = r["features"]
            assert_published_before([{"published": fe["sws_newest_published"]}], o_served, f"{name} {p} SWS feature")
            if fe["news_latest_published"]:
                assert_published_before([{"published": fe["news_latest_published"]}], o_served, f"{name} {p} news")
            if fe["issue_date"][:10] != o_served.isoformat():
                raise SealError(f"{name} {p}: feature row issued {fe['issue_date']}, not O(t) {o_served}")

    provs = sorted(served["rows"])
    if tuple(provs) != PROVINCES:
        raise SealError(f"expected the five CALABARZON provinces, got {provs}")
    ps_post, clim_post = SI.persist_clim_at(X, issue.isoformat(), t, provs, SI.cpi_newest(pd_ts(issue)))
    ps_o, clim_o = SI.persist_clim_at(X, o_served.isoformat(), t, provs, PR.M0_SERVED(t))

    # C0 must equal the served export where it exists (stored precision)
    import pandas as pd
    ex = pd.read_csv(BACKEND / "data" / "ch1_engine" / "rows.csv", dtype={"province_code": str})
    ex = ex[(ex["quarter"] == qs(target)) & (ex["lead"] == 2)].set_index("province_code")
    parity = {}
    for p in provs:
        if p in ex.index:
            d = {"pi_hunger": abs(h0 - ex.loc[p, "pi_hunger"]), "pi_price": abs(served["rows"][p]["price"] - ex.loc[p, "pi_price"]),
                 "probability": abs(h0 * served["rows"][p]["price"] - ex.loc[p, "probability"])}
            parity[p] = {k: float(v) for k, v in d.items()}
            if max(d.values()) > 5e-7:
                raise SealError(f"C0 for {p} differs from the served export rows.csv: {parity[p]}")

    def cand(h: float, price: float) -> dict:
        return {"hunger": round(h, 6), "price": round(price, 6), "probability": round(h * price, 6),
                "D0": "HIGH" if h * price >= 0.5 else "LOW", "D1": "HIGH" if (h >= 0.5 and price >= 0.5) else "LOW"}

    late = sealed_at.date() > issue
    payload = {
        "schema": "aipheed-lead2-seal/1", "preregSha256": pre,
        "origin": qs(t), "target": qs(target), "lead": 2,
        "issueDate": {"C0": o_served.isoformat(), "C1": issue.isoformat(), "C2": issue.isoformat()},
        "sealedAtUTC": sealed_at.isoformat(timespec="seconds"), "timing": "late" if late else "on-time",
        "lateNote": (f"Sealed {sealed_at.date()}, after its issue date {issue}, using only inputs published before "
                     f"{issue}; reported separately and excluded from the PREREG section 6-7 evaluation.") if late else None,
        "candidates": {
            "C0_P0H4": {p: cand(h0, served["rows"][p]["price"]) for p in provs},
            "C1_M0": {p: cand(h2, served["rows"][p]["price"]) for p in provs},
            "C2_M2": {p: cand(h2, post["rows"][p]["price"]) for p in provs}},
        "baselines": {
            "atPostIssue": {"PERSIST-SI": {p: ps_post[p] for p in provs}, "CLIM": clim_post, "ALWAYS-LOW": 0.0},
            "atServedIssue": {"PERSIST-SI": {p: ps_o[p] for p in provs}, "CLIM": clim_o, "ALWAYS-LOW": 0.0}},
        "inputs": {
            "hunger": {"C0": i0, "C1_C2": i2, "swsRoundsUsedForC1C2": sws_used},
            "cpi": {"served": served["cpi"], "post": post["cpi"],
                    "rule": "month M available from the first day of M+2 (PSA releases about the first week of M+1)"},
            "priceFeatures": {"served": {p: r["features"] for p, r in served["rows"].items()}},
            "priceFits": {"served": served["fit"], "post": post["fit"]},
            "filesRead": {"served": served["filesRead"], "post": post["filesRead"]},
            "vintageNote": ("Data files are hashed as they stood when sealed. Each value's publication is checked "
                            "against its date or availability rule; later revisions of already-published values "
                            "cannot be excluded from the project files."),
        },
        "c0ParityWithServedExport": parity or "no lead-2 row for this target in rows.csv",
        "code": {"gitCommit": git_commit(),
                 "sha256": {f.relative_to(REPO).as_posix(): sha256_file(f) for f in CODE_FILES}},
    }
    return path, payload


def pd_ts(d):
    import pandas as pd
    return pd.Timestamp(d)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--issue")
    ap.add_argument("--_child", choices=("served", "post"))
    ap.add_argument("--origin", type=int)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    if a._child:
        child(a._child, a.origin, Path(a.out))
        return 0
    if not a.issue:
        ap.error("--issue YYYY-MM-DD is required")
    try:
        issue = dt.date.fromisoformat(a.issue)
        now = dt.datetime.now(dt.timezone.utc)
        path, payload = build(issue, now)
        SEALS.mkdir(exist_ok=True)
        sha = write_seal(path, payload)
        ledger_append({"file": path.name, "sha256": sha, "issue": issue.isoformat(), "target": payload["target"],
                       "sealedAt": payload["sealedAtUTC"], "timing": payload["timing"], "prereg": payload["preregSha256"],
                       "commit": payload["code"]["gitCommit"]})
    except SealError as e:
        print(f"SEAL REFUSED: {e}", file=sys.stderr)
        return 2
    print(f"sealed {path.name}  sha256 {sha}  ({payload['timing']})")
    for c, rows in payload["candidates"].items():
        for p, r in rows.items():
            print(f"  {c:8s} {p}  hunger {r['hunger']:.3f}  price {r['price']:.3f}  prob {r['probability']:.3f}  "
                  f"D0 {r['D0']}  D1 {r['D1']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
