"""Y16 (EXPERIMENT_PLAN.md; Amendment 1 = BOOTSTRAP_AMENDMENT.md): issuance, sealing and evaluation for the prospective
comparison of hunger persistence (PERS = H1) and the Kalman challenger (KAL) for TFI-2 at Lead 2.

The two forecasts are computed by the same functions that produced the historical results (rlib.forecast RW,
hmodels.kalman), imported read-only. New SWS rounds enter through data/sws_rounds_overlay.csv (append-only), which is
merged in memory with the project series; no protected file is read for writing and none is modified.

Y18 integrity repairs (y17_integrity_audit/FIX_REPORT.md): every integrity check raises an explicit exception (no
`assert`, so nothing disappears under python -O); strict overlay validation; duplicate and conflict rejection; the
overlay rows used are recorded in each seal; registry reconciliation; refused re-issues; an append-only attempt log;
a local attestation payload. Model specification and forecast values are unchanged.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import platform
import re
import subprocess
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

sys.dont_write_bytecode = True

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

HERE = Path(__file__).resolve().parent
Y16 = HERE.parent
RES = Y16.parent
EXP = RES.parent
sys.path.insert(0, str(RES / "common"))
import p2lib as P  # noqa: E402
import hmodels as HM  # noqa: E402

R = P.R
AREAS = tuple(R.AREAS)                                    # NCR, BL, VIS, MIN
MANILA = ZoneInfo("Asia/Manila")
WINDOW_DAYS = 7
RESOLVE_DAYS = 120
FIRST_ISSUE = "2027-01-01"
OVERLAY_COLS = ["area", "quarter", "H", "published", "moe", "source_url", "entered_utc"]
DEFAULT_OVERLAY = Y16 / "data" / "sws_rounds_overlay.csv"
ATTEMPT_LOG, ATTEST_LOG, REGISTRY = "ISSUE_ATTEMPTS.log", "ATTESTATIONS.log", "SEALS.txt"
_BASE_ROUNDS = R.rounds                                   # the original (cached) project series
OVERLAY_REPORT: dict = {}

QUARTER_RE = re.compile(r"^\d{4}-Q[1-4]$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
URL_RE = re.compile(r"^https://\S+$")
LOCAL_LIMITS = ("Local tamper detection only: the registry and seals are ordinary files. Someone able to rewrite every "
                "local file consistently (seal, registry, logs) is not detected locally; only the external attestation "
                "of each seal hash (ATTESTATIONS.log, completed out of band) protects against that.")


class IntegrityError(RuntimeError):
    """Plan, amendment, seal, registry or overlay-history integrity failure."""


class OverlayError(ValueError):
    """Invalid, duplicate or conflicting overlay row."""


class IssueWindowError(RuntimeError):
    """Issuance outside the registered window."""


class ReissueError(RuntimeError):
    """A valid seal already exists for this issue date."""


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _frozen(doc: str, hashfile: str) -> str:
    want = (Y16 / hashfile).read_text(encoding="utf-8").split()[0]
    got = sha(Y16 / doc)
    if got != want:
        raise IntegrityError(f"{doc} changed after freezing (sha {got[:12]} != registered {want[:12]})")
    return want


def plan_sha() -> str:
    return _frozen("EXPERIMENT_PLAN.md", "PLAN_SHA256.txt")


def amendment_sha() -> str:
    return _frozen("BOOTSTRAP_AMENDMENT.md", "BOOTSTRAP_AMENDMENT_SHA256.txt")


def environment() -> dict:
    import scipy
    import sklearn
    return {"python": sys.version.split()[0], "numpy": np.__version__, "scipy": scipy.__version__, "pandas": pd.__version__,
            "sklearn": sklearn.__version__, "os": platform.system(), "optimizeFlag": sys.flags.optimize}


# ------------------------------------------------------------------------------------------------ overlay
def _quarter_start(q: str) -> dt.date:
    y, k = int(q[:4]), int(q[-1])
    return dt.date(y, 3 * (k - 1) + 1, 1)


def read_overlay(path: Path = DEFAULT_OVERLAY) -> pd.DataFrame:
    """Strictly validated overlay (raises OverlayError naming the row and field). Data row 1 = file line 2."""
    path = Path(path)
    if not path.exists():
        raise OverlayError(f"overlay file not found: {path}")
    o = pd.read_csv(path, dtype=str, keep_default_na=False)
    if list(o.columns) != OVERLAY_COLS:
        raise OverlayError(f"overlay header must be exactly {','.join(OVERLAY_COLS)}; got {','.join(o.columns)}")
    rows = []
    for i, r in o.iterrows():
        n = i + 1

        def bad(field, why):
            raise OverlayError(f"overlay row {n} (file line {n + 1}) field '{field}': {why} (value {r[field]!r})")
        for f in OVERLAY_COLS:
            if r[f].strip() == "" or r[f] != r[f].strip():
                bad(f, "missing or surrounded by whitespace")
        if r["area"] not in AREAS:
            bad("area", f"must be one of {', '.join(AREAS)}")
        if not QUARTER_RE.match(r["quarter"]):
            bad("quarter", "must be YYYY-Qn with n in 1..4")
        try:
            h = float(r["H"])
        except ValueError:
            bad("H", "not a number")
        if not math.isfinite(h) or not 0 <= h <= 100:
            bad("H", "must be a finite percentage in [0, 100]")
        try:
            m = float(r["moe"])
        except ValueError:
            bad("moe", "not a number")
        if not math.isfinite(m) or not 0 < m <= 15:
            bad("moe", "must be a finite margin of error in (0, 15] percentage points")
        if not DATE_RE.match(r["published"]):
            bad("published", "must be an ISO date YYYY-MM-DD (no time, no timezone; other formats are ambiguous)")
        try:
            pub = dt.date.fromisoformat(r["published"])
        except ValueError:
            bad("published", "not a real calendar date")
        if pub < _quarter_start(r["quarter"]):
            bad("published", f"precedes the start of quarter {r['quarter']}; a round cannot be published before its quarter")
        if not UTC_RE.match(r["entered_utc"]):
            bad("entered_utc", "must be ISO-8601 UTC YYYY-MM-DDTHH:MM:SSZ")
        try:
            ent = dt.datetime.strptime(r["entered_utc"], "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            bad("entered_utc", "not a real timestamp")
        if pub > ent.date():
            bad("published", f"is after the entry time {r['entered_utc']}; a round cannot be entered before it is published")
        if not URL_RE.match(r["source_url"]):
            bad("source_url", "must be an https:// URL of the publication")
        rows.append({"row": n, "area": r["area"], "quarter": r["quarter"], "H": h, "published": r["published"], "moe": m,
                     "source_url": r["source_url"], "entered_utc": r["entered_utc"]})
    d = pd.DataFrame(rows, columns=["row"] + OVERLAY_COLS)
    for key, g in d.groupby(["area", "quarter", "published"]):
        if len(g) > 1:
            same = g[["H", "moe"]].nunique().max() == 1
            raise OverlayError(f"overlay rows {g['row'].tolist()} share area/quarter/published {key}: "
                               + ("exact duplicate (would be counted twice)" if same else "conflicting values"))
    for key, g in d.groupby(["area", "quarter", "H"]):
        if g["published"].nunique() > 1:
            raise OverlayError(f"overlay rows {g['row'].tolist()} have the same area/quarter/value {key} with different "
                               "publication dates: probable duplicate with a mistyped date; resolve manually")
    return d


def install_overlay(path: Path = DEFAULT_OVERLAY) -> int:
    """Make rlib/hmodels see the project series plus validated overlay rounds (in memory only).
    Returns the number of rounds added; details in OVERLAY_REPORT. Raises OverlayError on any conflict."""
    global OVERLAY_REPORT
    base = _BASE_ROUNDS().copy()
    o = read_overlay(path)
    add, already, extra = [], [], []
    for _, r in o.iterrows():
        q, pub = R.qi(r["quarter"]), pd.Timestamp(r["published"])
        same_area_q = base[(base["area"] == r["area"]) & (base["q"] == q)]
        key = same_area_q[same_area_q["published"] == pub]
        if len(key):
            if (key["H"] - r["H"]).abs().max() > 1e-9:
                raise OverlayError(f"overlay row {r['row']} conflicts with the project series for {r['area']} {r['quarter']} "
                                   f"published {r['published']}: overlay {r['H']} vs project {key['H'].tolist()}")
            already.append(int(r["row"]))
            continue
        if ((same_area_q["H"] - r["H"]).abs() < 1e-9).any():
            raise OverlayError(f"overlay row {r['row']} has the same value as a project round of {r['area']} {r['quarter']} "
                               "but a different publication date: probable duplicate; resolve manually")
        if len(same_area_q):
            extra.append(int(r["row"]))
        add.append({"area": r["area"], "q": q, "H": float(r["H"]), "published": pub, "moe": float(r["moe"])})
    merged = pd.concat([base, pd.DataFrame(add)], ignore_index=True) if add else base
    R.rounds = lambda: merged
    for f in (R.known, HM._series, HM._kfit):
        f.cache_clear()
    OVERLAY_REPORT = {"overlaySha256": sha(path), "rowsValidated": int(len(o)), "added": len(add),
                      "rowsAlreadyInProjectSeries": already, "rowsAddingARoundToAnExistingQuarter": extra}
    return len(add)


def origin_of(issue: str) -> int:
    if not isinstance(issue, str) or not DATE_RE.match(issue):
        raise ValueError(f"issue date must be an ISO date YYYY-MM-DD, got {issue!r}")
    try:
        d = pd.Timestamp(dt.date.fromisoformat(issue))
    except ValueError as e:
        raise ValueError(f"issue date {issue!r} is not a real date") from e
    if d.day != 1 or d.month not in (1, 4, 7, 10):
        raise ValueError(f"issue dates are the first day of a quarter; got {issue}")
    t = d.year * 4 + (d.month - 1) // 3 - 1
    if R.issue(t) != d:
        raise IntegrityError(f"issue/origin round trip failed for {issue}")
    return t


# ------------------------------------------------------------------------------------------------ forecasts (unchanged)
def forecasts(issue: str) -> dict:
    t = origin_of(issue)
    iss = R.issue(t)
    kn = R.known("BL", iss)
    q_last = max(kn)
    rr = R.rounds()
    used = rr[(rr["area"] == "BL") & (rr["q"] == q_last) & (rr["published"] < iss)]
    f = R.forecast("BL", t, 2, AREAS)
    kal = HM.kalman("BL", t, 2, AREAS)
    obs = R.observed()
    pub = rr[rr["area"] == "BL"].groupby("q")["published"].max()
    kq = [q for q, p in pub.items() if p < iss]
    clim = float(np.mean([obs[("BL", q)] > R.H_LINE for q in kq])) if kq else float("nan")
    pers = None if f is None else float(f["RW"])
    return {"origin": R.qs(t), "target": R.qs(t + 2), "t": t,
            "newestSws": {"quarter": R.qs(q_last), "value": float(kn[q_last]), "rounds": int(len(used)),
                          "lastPublished": str(used["published"].max().date())},
            "trueHorizon": int(t + 2 - q_last),
            "PERS": pers, "KAL": None if (kal is None or math.isnan(kal)) else float(kal),
            "aux": {"PERSIST_binary": float(kn[q_last] > R.H_LINE), "CLIM": clim}}


def model_version() -> dict:
    files = {"hmodels.py": RES / "common" / "hmodels.py", "rlib.py": RES / "runner" / "rlib.py",
             "kprospect.py": HERE / "kprospect.py", "issue.py": HERE / "issue.py", "evaluate.py": HERE / "evaluate.py",
             "attest.py": HERE / "attest.py"}
    return {k: sha(v) for k, v in files.items() if v.exists()}


def input_files(overlay: Path) -> list[Path]:
    return [R.LONG / "sws_area_rounds_full.csv", R.ROOT / "backend" / "data" / "inputs" / "sws_rounds.csv", Path(overlay)]


def window_status(issue: str, now_utc: dt.datetime) -> dict:
    local = now_utc.astimezone(MANILA).date()
    d0 = pd.Timestamp(issue).date()
    late = (local - d0).days
    return {"localDateManila": str(local), "daysAfterIssue": late, "inWindow": 0 <= late <= WINDOW_DAYS}


# ------------------------------------------------------------------------------------------------ registry
def _parse_registry(pdir: Path) -> tuple[dict, list, list]:
    reg, invalid, dup = {}, [], []
    f = Path(pdir) / REGISTRY
    if f.exists():
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) != 3 or not re.match(r"^[0-9a-f]{64}$", parts[1]) or not parts[2].startswith("validProspective="):
                invalid.append(i)
                continue
            if parts[0] in reg:
                dup.append(parts[0])
            reg[parts[0]] = parts[1]
    return reg, invalid, dup


def reconcile(pdir: Path) -> dict:
    """Registry vs seal files. Reports missing files, unregistered files, hash mismatches, malformed or duplicate
    registry lines, and issue dates with more than one valid seal. Never repairs anything."""
    pdir = Path(pdir)
    reg, invalid, dup = _parse_registry(pdir)
    files = {p.name: p for p in pdir.glob("seal_issue_*.json")} if pdir.exists() else {}
    missing = sorted(n for n in reg if n not in files)
    unregistered = sorted(n for n in files if n not in reg)
    mismatch = sorted(n for n in files if n in reg and sha(files[n]) != reg[n])
    by_issue: dict[str, list] = {}
    for n, p in files.items():
        if n in reg and n not in mismatch:
            s = json.loads(p.read_text(encoding="utf-8"))
            if s.get("validProspective"):
                by_issue.setdefault(s["issueDate"], []).append((s["writtenUtc"], n))
    reissues = {k: [n for _, n in sorted(v)] for k, v in by_issue.items() if len(v) > 1}
    ok = not (missing or unregistered or mismatch or invalid or dup)
    return {"ok": ok, "registered": len(reg), "files": len(files), "missingFiles": missing, "unregisteredFiles": unregistered,
            "hashMismatch": mismatch, "malformedRegistryLines": invalid, "duplicateRegistryEntries": dup,
            "reissues": reissues, "validIssueDates": sorted(by_issue), "limits": LOCAL_LIMITS}


def issue_seal(issue: str, out_dir: Path, overlay: Path = DEFAULT_OVERLAY, now_utc: dt.datetime | None = None,
               dry_run: bool = False) -> Path:
    plan, amend = plan_sha(), amendment_sha()
    origin_of(issue)
    clock = "system" if now_utc is None else "caller-supplied"
    now = now_utc or dt.datetime.now(dt.timezone.utc)
    w = window_status(issue, now)
    if not w["inWindow"] and not dry_run:
        raise IssueWindowError(f"refusing: {issue} seal must be written between the issue date and {WINDOW_DAYS} days after "
                               f"(Manila date now {w['localDateManila']}); use --dry-run for a non-valid test run")
    out_dir = Path(out_dir)
    rec = reconcile(out_dir)
    if not rec["ok"]:
        raise IntegrityError(f"refusing to issue into an inconsistent registry in {out_dir}: "
                             + json.dumps({k: rec[k] for k in ("missingFiles", "unregisteredFiles", "hashMismatch",
                                                               "malformedRegistryLines", "duplicateRegistryEntries")}))
    if not dry_run and issue in rec["validIssueDates"]:
        raise ReissueError(f"a valid seal for {issue} already exists in {out_dir}; re-issues are refused (Amendment 1, section 4)")
    added = install_overlay(overlay)
    report = dict(OVERLAY_REPORT)
    fc = forecasts(issue)
    ov = read_overlay(overlay)
    used = ov[ov["published"] < issue].drop(columns="row").sort_values(["area", "quarter", "published"])
    excluded = ov[ov["published"] >= issue]
    used_rows = used.to_dict("records")
    snapshot = json.dumps(used_rows, sort_keys=True, separators=(",", ":"))
    seal = {"study": "Y16 Kalman vs persistence, prospective", "planSha256": plan, "amendment1Sha256": amend,
            "issueDate": issue, "origin": fc["origin"], "target": fc["target"],
            "targetDefinition": "TFI-2: Balance Luzon involuntary hunger > 11.3% (mean of the target quarter's SWS rounds)",
            "writtenUtc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "writtenManila": now.astimezone(MANILA).strftime("%Y-%m-%dT%H:%M:%S%z"), "clockSource": clock,
            "window": w, "validProspective": bool(w["inWindow"] and not dry_run), "dryRun": dry_run,
            "informationCutoff": f"SWS rounds published before {issue}",
            "newestSwsUsed": fc["newestSws"], "trueHorizon": fc["trueHorizon"], "overlayRoundsAdded": added,
            "overlayRowsUsed": used_rows, "overlaySnapshotSha256": hashlib.sha256(snapshot.encode()).hexdigest(),
            "overlayRowsExcludedByCutoff": [{k: r[k] for k in ("area", "quarter", "published")} for _, r in excluded.iterrows()],
            "overlayReport": report,
            "forecasts": {"PERS": {"model": "hunger persistence H1 (rlib.forecast RW)", "probability": fc["PERS"]},
                          "KAL": {"model": "Kalman SWS-sampling-error state space (hmodels.kalman)", "probability": fc["KAL"]}},
            "classAt050": {k: (None if v is None else ("HIGH" if v >= 0.5 else "LOW")) for k, v in (("PERS", fc["PERS"]), ("KAL", fc["KAL"]))},
            "auxiliaryBaselines": fc["aux"], "modelVersion": model_version(), "environment": environment(),
            "gitHead": subprocess.run(["git", "-C", str(R.ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(),
            "inputs": {str(p).replace("\\", "/"): (sha(p) if Path(p).exists() else None) for p in input_files(overlay)}}
    out_dir.mkdir(parents=True, exist_ok=True)
    f = out_dir / f"seal_issue_{issue}_written_{now.strftime('%Y%m%dT%H%M%SZ')}.json"
    with open(f, "x", encoding="utf-8") as g:                     # exclusive create: never overwrites (FileExistsError)
        g.write(json.dumps(seal, indent=1))
    with open(out_dir / REGISTRY, "a", encoding="utf-8") as g:
        g.write(f"{f.name} {sha(f)} validProspective={seal['validProspective']}\n")
    return f


# ------------------------------------------------------------------------------------------------ attempt log, attestation
def _append_jsonl(path: Path, rec: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as g:
        g.write(json.dumps(rec, sort_keys=True) + "\n")


def attestation_payload(seal_path: Path) -> str:
    s = json.loads(Path(seal_path).read_text(encoding="utf-8"))
    return (f"aiPHeed-Y16 issue={s['issueDate']} target={s['target']} seal={Path(seal_path).name} "
            f"sealSha256={sha(seal_path)} planSha256={s['planSha256']} amendment1Sha256={s['amendment1Sha256']} "
            f"writtenUtc={s['writtenUtc']}")


def log_failed_attempt(out_dir: Path, issue: str, error_type: str, message: str) -> None:
    """For a real attempt refused before issue_with_log is reached (e.g. a non-canonical overlay in issue.py)."""
    _append_jsonl(Path(out_dir) / ATTEMPT_LOG, {"attemptUtc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                                                "issueRequested": issue, "kind": "real-issue-attempt", "result": "failed",
                                                "errorType": error_type, "message": message[:1000], "environment": environment(),
                                                "clockSource": "system"})


def issue_with_log(issue: str, out_dir: Path, overlay: Path = DEFAULT_OVERLAY, now_utc: dt.datetime | None = None) -> Path:
    """A real (non-dry) issuance attempt. Every attempt, failed or sealed, is appended to ISSUE_ATTEMPTS.log; the
    original exception is re-raised unchanged. A successful seal gets an attestation payload with status 'pending'."""
    out_dir = Path(out_dir)
    t0 = (now_utc or dt.datetime.now(dt.timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    base = {"attemptUtc": t0, "issueRequested": issue, "kind": "real-issue-attempt", "environment": environment(),
            "clockSource": "system" if now_utc is None else "caller-supplied"}
    try:
        f = issue_seal(issue, out_dir, overlay, now_utc=now_utc, dry_run=False)
    except Exception as e:
        try:
            _append_jsonl(out_dir / ATTEMPT_LOG, {**base, "result": "failed", "errorType": type(e).__name__,
                                                  "message": str(e)[:1000]})
        except Exception as log_err:  # noqa: BLE001  never mask the original failure
            e.add_note(f"(attempt log could not be written: {log_err})")
        raise
    payload = attestation_payload(f)
    _append_jsonl(out_dir / ATTEMPT_LOG, {**base, "result": "sealed", "seal": f.name, "sealSha256": sha(f)})
    (out_dir / "attestations").mkdir(exist_ok=True)
    (out_dir / "attestations" / f"{f.stem}.attestation.txt").write_text(payload + "\n", encoding="utf-8")
    _append_jsonl(out_dir / ATTEST_LOG, {"seal": f.name, "sealSha256": sha(f), "status": "pending", "recordedUtc": t0,
                                         "method": None, "evidence": None})
    return f


def attestation_status(pdir: Path) -> dict:
    """Latest operator-recorded status per seal (pending / completed / unavailable). Never inferred."""
    out = {}
    f = Path(pdir) / ATTEST_LOG
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                out[r["seal"]] = r["status"]
    return out


def read_attempts(pdir: Path) -> list[dict]:
    f = Path(pdir) / ATTEMPT_LOG
    return [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines() if x.strip()] if f.exists() else []


# ------------------------------------------------------------------------------------------------ evaluation helpers
def load_seals(pdir: Path, allow_clock_override: bool = False) -> pd.DataFrame:
    """Valid seals after full registry reconciliation (raises IntegrityError on any inconsistency). The first valid
    seal by write time counts per issue date; the reconciliation (incl. re-issues) is in .attrs['reconcile']."""
    pdir = Path(pdir)
    rec = reconcile(pdir)
    if not rec["ok"]:
        raise IntegrityError("seal registry inconsistent: " + json.dumps(
            {k: rec[k] for k in ("missingFiles", "unregisteredFiles", "hashMismatch", "malformedRegistryLines", "duplicateRegistryEntries")}))
    rows = []
    for f in sorted(pdir.glob("seal_issue_*.json")) if pdir.exists() else []:
        s = json.loads(f.read_text(encoding="utf-8"))
        if not s["validProspective"]:
            continue
        clock = s.get("clockSource", "unknown")
        if clock != "system" and not allow_clock_override:
            raise IntegrityError(f"seal {f.name} was not written with the system clock (clockSource={clock}); refused")
        if "overlayRowsUsed" not in s:
            raise IntegrityError(f"seal {f.name} lacks overlayRowsUsed: its overlay provenance cannot be verified")
        rows.append({"file": f.name, "issue": s["issueDate"], "target": s["target"], "writtenUtc": s["writtenUtc"],
                     "PERS": s["forecasts"]["PERS"]["probability"], "KAL": s["forecasts"]["KAL"]["probability"],
                     "PERSIST": s["auxiliaryBaselines"]["PERSIST_binary"], "CLIM": s["auxiliaryBaselines"]["CLIM"],
                     "overlayRowsUsed": s["overlayRowsUsed"]})
    d = pd.DataFrame(rows)
    if len(d):
        d = d.sort_values("writtenUtc").drop_duplicates("issue", keep="first")   # first valid seal per issue date counts
    d.attrs["reconcile"] = rec
    return d


def verify_overlay(d: pd.DataFrame, overlay: Path) -> int:
    """Amendment 1 section 3: every overlay row recorded in a valid seal must still be present unchanged."""
    cur = read_overlay(overlay).drop(columns="row")
    have = {json.dumps(r, sort_keys=True) for r in cur.to_dict("records")}
    n = 0
    for f, rows in zip(d["file"], d["overlayRowsUsed"]):
        for r in rows:
            n += 1
            if json.dumps(r, sort_keys=True) not in have:
                raise IntegrityError(f"overlay history changed: a row used by {f} is missing or altered: {r}")
    return n


def missed_issues(d: pd.DataFrame, today: dt.date) -> list[str]:
    """Scheduled issue dates from FIRST_ISSUE whose window has closed with no valid seal (Amendment 1 section 3)."""
    have = set(d["issue"]) if len(d) else set()
    out, cur = [], dt.date.fromisoformat(FIRST_ISSUE)
    while cur + dt.timedelta(days=WINDOW_DAYS) < today:
        if str(cur) not in have:
            out.append(str(cur))
        cur = dt.date(cur.year + (cur.month == 10), (cur.month + 2) % 12 + 1, 1)
    return out


def outcome(target: str, today: dt.date) -> float | None:
    """Mean BL hunger of the target quarter's rounds published within RESOLVE_DAYS of quarter end; None until resolved."""
    q = R.qi(target)
    q_end = (pd.Timestamp(year=(q + 1) // 4, month=3 * ((q + 1) % 4) + 1, day=1) - pd.Timedelta(days=1)).date()
    resolve = q_end + dt.timedelta(days=RESOLVE_DAYS)
    if today < resolve:
        return None
    rr = R.rounds()
    g = rr[(rr["area"] == "BL") & (rr["q"] == q) & (rr["published"].dt.date <= resolve)]
    return float(g["H"].mean()) if len(g) else float("nan")


def metrics(y, p) -> dict:
    from sklearn.metrics import roc_auc_score
    y, p = np.asarray(y, int), np.asarray(p, float)
    yh = (p >= .5).astype(int)
    tp, fp, fn, tn = [int(((yh == a) & (y == b)).sum()) for a, b in ((1, 1), (1, 0), (0, 1), (0, 0))]
    r = lambda a, b: a / b if b else None  # noqa: E731
    rec, spec, prec = r(tp, tp + fn), r(tn, tn + fp), r(tp, tp + fp)
    return {"n": len(y), "prevalence": float(y.mean()) if len(y) else None, "TP": tp, "FP": fp, "FN": fn, "TN": tn,
            "accuracy": r(tp + tn, len(y)), "balanced": (rec + spec) / 2 if rec is not None and spec is not None else None,
            "precision": prec, "recall": rec, "specificity": spec,
            "f1": 2 * prec * rec / (prec + rec) if prec and rec else (0.0 if prec is not None and rec is not None else None),
            "auc": float(roc_auc_score(y, p)) if 0 < y.sum() < len(y) else None,
            "brier": float(np.mean((p - y) ** 2)) if len(y) else None}


def calibration(y, p) -> dict:
    """Amendment 1 section 3 (supplementary): 5 equal-count bins; logistic slope/intercept if n >= 10 and both classes."""
    from sklearn.linear_model import LogisticRegression
    y, p = np.asarray(y, int), np.asarray(p, float)
    out = {"label": "supplementary (registered reporting item)", "bins": [], "slope": "unavailable", "intercept": "unavailable"}
    if len(y) == 0:
        return out
    order = np.argsort(p, kind="mergesort")
    for chunk in np.array_split(order, min(5, len(y))):
        out["bins"].append({"n": int(len(chunk)), "meanForecast": float(p[chunk].mean()), "observed": float(y[chunk].mean())})
    if len(y) >= 10 and 0 < y.sum() < len(y):
        pc = np.clip(p, 1e-6, 1 - 1e-6)
        m = LogisticRegression(C=1e6, max_iter=5000).fit(np.log(pc / (1 - pc)).reshape(-1, 1), y)
        out["slope"], out["intercept"] = float(m.coef_[0, 0]), float(m.intercept_[0])
    return out


def paired(d: pd.DataFrame, seed: int = 2036, B: int = 5000) -> dict:
    from scipy.stats import binomtest
    di = ((d["KAL"] - d["y"]) ** 2 - (d["PERS"] - d["y"]) ** 2).to_numpy()
    rng = np.random.default_rng(seed)
    bs = di[rng.integers(0, len(di), size=(B, len(di)))].mean(1)
    nz = di[di != 0]
    k = int((nz < 0).sum())
    return {"n": len(di), "meanDiff_KAL_minus_PERS": float(di.mean()),
            "CI95": [float(np.quantile(bs, .025)), float(np.quantile(bs, .975))],
            "p_one_sided_bootstrap": float(np.mean(bs >= 0)),
            "signTest": {"KAL_better": k, "nonZero": int(len(nz)),
                         "p_one_sided": float(binomtest(k, len(nz), 0.5, alternative="greater").pvalue) if len(nz) else None}}


def block_paired(d: pd.DataFrame, L: int = 4, seed: int = 2036, B: int = 5000) -> dict:
    """Amendment 1 section 2: moving-block (non-circular) bootstrap of mean d over pairs ordered by target quarter."""
    g = d.assign(_q=d["target"].map(R.qi)).sort_values("_q")
    di = ((g["KAL"] - g["y"]) ** 2 - (g["PERS"] - g["y"]) ** 2).to_numpy()
    n = len(di)
    gaps = int((np.diff(g["_q"].to_numpy()) > 1).sum()) if n > 1 else 0
    res = {"label": "sensitivity: moving-block bootstrap (Amendment 1)", "n": n, "blockLength": L, "gapsInSeries": gaps}
    if n < 2 * L:
        return {**res, "result": "unavailable (n < 2L)"}
    rng = np.random.default_rng(seed)
    nb = math.ceil(n / L)
    st = rng.integers(0, n - L + 1, size=(B, nb))
    bs = di[(st[:, :, None] + np.arange(L)).reshape(B, -1)[:, :n]].mean(1)
    ci = [float(np.quantile(bs, .025)), float(np.quantile(bs, .975))]
    p = float(np.mean(bs >= 0))
    return {**res, "meanDiff_KAL_minus_PERS": float(di.mean()), "CI95": ci, "p_one_sided": p,
            "robust": bool(p < 0.05 and ci[1] < 0)}


def seven_rules(d: pd.DataFrame, model: str) -> dict:
    sys.path.insert(0, str(EXP / "FIRI_LEAD2_FEASIBILITY" / "runner"))
    import score_firi_l2 as F
    g = d.copy()
    g["q"] = g["target"].map(R.qi)
    g["F2"], g["H1"] = g[model], g["PERS"]
    g["ALWAYS-HIGH"], g["ALWAYS-LOW"] = 1.0, 0.0
    try:
        r = F.rules(g)["rules"]
    except Exception as e:  # noqa: BLE001
        return {"estimable": False, "reason": f"{type(e).__name__}: {e}"}
    out = {k.split()[0]: {"pass": bool(v["pass"]), "value": v["value"]} for k, v in r.items()}
    if model == "PERS":
        out["R5"] = {"pass": None, "value": "undefined: PERS is itself the H1 comparator (plan section 5)"}
    return {"estimable": True, "rules": out}


def lock_primary(out_dir: Path, content: dict) -> str:
    """Amendment 1 section 4: write PRIMARY_ANALYSIS.json once (exclusive); later runs must reproduce it exactly."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    body = json.dumps(content, sort_keys=True, default=str)
    h = hashlib.sha256(body.encode()).hexdigest()
    f = out_dir / "PRIMARY_ANALYSIS.json"
    if not f.exists():
        with open(f, "x", encoding="utf-8") as g:
            g.write(json.dumps({"lockedUtc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                                "contentSha256": h, "content": json.loads(body)}, indent=1))
        return "primary analysis written and locked"
    old = json.loads(f.read_text(encoding="utf-8"))
    if old["contentSha256"] != h:
        raise IntegrityError(f"primary analysis already locked ({old['lockedUtc']}) and this run differs "
                             f"(sha {h[:12]} != locked {old['contentSha256'][:12]}); nothing was overwritten")
    return f"primary locked (unchanged since {old['lockedUtc']})"
