"""
app/quarterly/ledger.py  (E26)
------------------------------
Prospective evaluation ledger: the only route to evidence on UNSEEN quarters (criterion C9).

* Append-only JSONL, hash-chained: every entry stores the SHA-256 of the previous one, so any edit, deletion or
  reordering is detected by verify().
* SEAL     a forecast (one arm, one target quarter, five provinces) is recorded BEFORE its outcome exists in the
           ledger. Refused if the target's outcome is already recorded, if the same (arm, target, origin) is
           already sealed, or if the origin lies in the future.
* OUTCOME  the realized labels of a target quarter, accepted only with a researcher authorization: the outcome
           file's path and full SHA-256 (re-verified from the bytes) and who authorized it.
* SCORE    computed on demand from sealed probabilities and authorized outcomes only.

Statistics (E26 FROZEN_ANALYSIS_PROTOCOL.md section E): per scored target quarter j, d_j = loss(baseline) -
loss(model), averaged over the five provinces (Brier, or 0/1 error for accuracy). The e-process
E_n = prod(1 + lambda_j d_j), lambda_j predictable (aGRAPA plug-in from dates < j, clipped to [0, 0.5]), is a
non-negative supermartingale when E[d_j | past] <= 0, so P(sup_n E_n >= 1/a) <= a at any stopping time
(Ville). The e-process claim needs e >= 40 against BOTH persistence baselines (alpha 0.05, Bonferroni) AND
evaluability on the unseen rows (>= 8 dates, >= 5 HIGH, >= 5 LOW).

Amendment A1 (E26 PROTOCOL_AMENDMENT_A1.md, pending adviser approval): the PRIMARY claim test is a single
pre-registered look. It is taken at the FIRST year end at which the record of targets <= Y-Q4 holds >= 12 scored dates
and is evaluable, and only once every sealed target <= Y-Q4 is resolved (OUTCOME or NO_OUTCOME), so the look time
cannot be chosen. One-sided exact sign-flip test against each baseline; claim if p < 0.025 against both. The look is
written to the ledger (LOOK) and can never be repeated. The e-process stays as a secondary monitor.

Amendment A3 (pending adviser approval): the look also tests always-HIGH (constant 1, computed at scoring time) and
climatology (role reference_climatology, where sealed); "success" (claim_vs_all_references) needs p < 0.05/K against
every one of the K baselines and references, with a positive mean difference against each.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

GENESIS = "0" * 64
E_THRESHOLD = 40.0
MIN_DATES, MIN_PER_CLASS = 8, 5
LAMBDA_MAX, LAMBDA_FIRST = 0.5, 0.25
A1_MIN_DATES, A1_ALPHA_EACH = 12, 0.025      # amendment A1 (pending adviser approval)
A1_EXACT_MAX_N = 26                         # exact enumeration of real-valued differences up to 2^26 signs
A3_ALPHA = 0.05                             # amendment A3: family-wise level over every baseline and reference
ROLES = ("candidate", "baseline_persistence", "baseline_calibrated_persistence", "reference_climatology")
ALWAYS_HIGH = "reference_always_high"       # computed, never sealed


class LedgerRefused(Exception):
    pass


def _qk(q: str) -> int:
    y, n = q.split("-Q")
    return int(y) * 4 + int(n) - 1


def _sha_file(p: str | Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _quarter_of(ts: datetime) -> str:
    return f"{ts.year}-Q{(ts.month - 1) // 3 + 1}"


PHT = timezone(timedelta(hours=8))


def _as_utc(ts) -> datetime:
    """ISO time -> aware UTC; a naive value is Philippine time (the aiPHeed convention)."""
    d = ts if isinstance(ts, datetime) else datetime.fromisoformat(str(ts))
    return (d if d.tzinfo else d.replace(tzinfo=PHT)).astimezone(timezone.utc)


def _quarter_end_utc(q: str) -> datetime:
    """00:00 PHT on the first day of the quarter after q (= the instant quarter q has ended)."""
    i = _qk(q) + 1
    return datetime(i // 4, 3 * (i % 4) + 1, 1, tzinfo=PHT).astimezone(timezone.utc)


def _entry_hash(e: dict) -> str:
    body = {k: e[k] for k in ("seq", "kind", "payload", "prev_hash", "created_utc")}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------------------------- e-process
def eprocess(d: list[float] | np.ndarray) -> dict:
    """Anytime-valid one-sided test that E[d] > 0 (model better). d in [-1, 1]. Returns the path of E_n."""
    d = np.asarray(d, float)
    if np.any(np.abs(d) > 1 + 1e-12):
        raise ValueError("score differences must lie in [-1, 1]")
    e, path, lams = 1.0, [], []
    for j in range(len(d)):
        if j == 0:
            lam = LAMBDA_FIRST
        else:
            past = d[:j]
            m, v = float(past.mean()), float(past.var())
            lam = float(np.clip(m / (v + m * m), 0.0, LAMBDA_MAX)) if (v + m * m) > 0 else 0.0
        e *= 1.0 + lam * d[j]
        path.append(e)
        lams.append(lam)
    return {"e_value": float(e), "max_e": float(max(path)) if path else 1.0, "path": path, "lambdas": lams}


def signflip_p(d: list[float] | np.ndarray) -> dict:
    """One-sided exact sign-flip p-value for H0: d symmetric about 0, against E[d] > 0. Zero differences are
    dropped (they do not change p). Differences that are multiples of 1/5 (accuracy over five provinces) use an exact
    integer convolution for any n; other real differences are enumerated exactly up to A1_EXACT_MAX_N non-zero dates."""
    d = np.asarray(d, float)
    nz = d[np.abs(d) > 1e-12]
    n = len(nz)
    if n == 0:
        return {"p": 1.0, "n_nonzero": 0, "method": "exact"}
    obs = float(nz.sum())
    k = np.round(nz * 5)
    if np.allclose(k, nz * 5, atol=1e-9):
        a = np.abs(k).astype(int)
        off = int(a.sum())
        dist = np.zeros(2 * off + 1)
        dist[off] = 1.0
        for v in a:                                   # distribution of sum(s_j * a_j), s_j = +-1 with prob 1/2
            dist = 0.5 * (np.roll(dist, v) + np.roll(dist, -v))
        thr = int(round(obs * 5)) + off
        return {"p": float(min(1.0, dist[thr:].sum())), "n_nonzero": n, "method": "exact"}
    if n > A1_EXACT_MAX_N:
        raise ValueError(f"exact enumeration limited to {A1_EXACT_MAX_N} non-zero dates")
    a = np.abs(nz)
    hits, chunk = 0, 1 << 16
    for start in range(0, 1 << n, chunk):
        idx = np.arange(start, min(start + chunk, 1 << n), dtype=np.int64)
        signs = 1 - 2 * ((idx[:, None] >> np.arange(n)) & 1)
        hits += int(np.sum(signs @ a >= obs - 1e-12))
    return {"p": hits / float(1 << n), "n_nonzero": n, "method": "exact"}


# --------------------------------------------------------------------------------------------- ledger
class Ledger:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.entries: list[dict] = []
        if self.path.exists():
            for ln in self.path.read_text(encoding="utf-8").splitlines():
                if ln.strip():
                    self.entries.append(json.loads(ln))
        self.verify()

    # ---- integrity
    def verify(self) -> bool:
        prev = GENESIS
        for i, e in enumerate(self.entries):
            if e["seq"] != i or e["prev_hash"] != prev or _entry_hash(e) != e["entry_hash"]:
                raise LedgerRefused(f"ledger integrity broken at entry {i}")
            prev = e["entry_hash"]
        return True

    def _append(self, kind: str, payload: dict, now: datetime | None = None) -> dict:
        e = {"seq": len(self.entries), "kind": kind, "payload": payload,
             "prev_hash": self.entries[-1]["entry_hash"] if self.entries else GENESIS,
             "created_utc": (now or datetime.now(timezone.utc)).isoformat(timespec="seconds")}
        e["entry_hash"] = _entry_hash(e)
        self.entries.append(e)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(e, sort_keys=True) + "\n")
        return e

    def outcomes(self) -> dict:
        return {e["payload"]["target_quarter"]: e for e in self.entries if e["kind"] == "OUTCOME"}

    def missing(self) -> dict:
        return {e["payload"]["target_quarter"]: e for e in self.entries if e["kind"] == "NO_OUTCOME"}

    def seals(self) -> list[dict]:
        return [e for e in self.entries if e["kind"] == "SEAL"]

    # ---- SEAL
    def seal(self, *, arm: str, role: str, target_quarter: str, origin: str, info_cutoff: str,
             probabilities: dict, model_sha256: str, inputs: list[dict], now: datetime | None = None,
             threshold: float | None = None, sealed_at: datetime | None = None) -> dict:
        """threshold: the label threshold tau in force at this origin (T1: median of the S1 labels published before
        the origin; T2: 0). Stored so that the outcome is labelled with THIS seal's tau (E27 fix L3).
        sealed_at: the time the forecast was actually frozen (an imported seal's verified seal time); the timing
        rules are checked against it. Defaults to now."""
        now = now or datetime.now(timezone.utc)
        at = sealed_at or now
        if target_quarter in self.outcomes() or target_quarter in self.missing():
            raise LedgerRefused(f"seal refused: {target_quarter} is already resolved")
        # E27 fix L1: a forecast frozen after its target quarter ended could have seen the outcome's fieldwork period
        if at >= _quarter_end_utc(target_quarter):
            raise LedgerRefused(f"seal refused: target {target_quarter} had ended before the seal time {at.isoformat()}")
        # E27 fix L2: the information cutoff must be at or before the origin
        try:
            ic = _as_utc(info_cutoff)
        except (TypeError, ValueError):
            raise LedgerRefused(f"seal refused: unparseable info_cutoff {info_cutoff!r}")
        if ic > _as_utc(origin):
            raise LedgerRefused("seal refused: the information cutoff lies after the origin")
        if any(e["payload"]["arm"] == arm and e["payload"]["target_quarter"] == target_quarter
               and e["payload"]["origin"] == origin for e in self.seals()):
            raise LedgerRefused(f"seal refused: {arm} for {target_quarter} at origin {origin} is already sealed")
        if _as_utc(origin) > at:
            raise LedgerRefused("seal refused: the origin lies in the future")
        if role not in ROLES:
            raise LedgerRefused(f"unknown role {role}")
        if len(probabilities) != 5 or any(not 0.0 <= float(p) <= 1.0 for p in probabilities.values()):
            raise LedgerRefused("seal refused: five provincial probabilities in [0, 1] are required")
        if any(not i.get("authorized") for i in inputs):
            raise LedgerRefused("seal refused: every input must be authorized")
        payload = {"arm": arm, "role": role, "target_quarter": target_quarter, "origin": origin,
                   "info_cutoff": info_cutoff, "probabilities": {k: float(v) for k, v in sorted(probabilities.items())},
                   "model_sha256": model_sha256, "inputs": inputs}
        if threshold is not None:
            payload["threshold"] = float(threshold)
        if sealed_at is not None:
            payload["sealed_at_utc"] = sealed_at.astimezone(timezone.utc).isoformat(timespec="seconds")
        return self._append("SEAL", payload, now)

    # ---- OUTCOME
    def record_outcome(self, *, target_quarter: str, labels: dict, authorization: dict,
                       now: datetime | None = None) -> dict:
        if target_quarter in self.outcomes():
            raise LedgerRefused(f"outcome of {target_quarter} already recorded")
        if target_quarter in self.missing():
            raise LedgerRefused(f"{target_quarter} was declared to have no outcome; that declaration is final")
        for k in ("path", "sha256", "authorized_by", "authorized_on"):
            if not authorization.get(k):
                raise LedgerRefused(f"outcome refused: authorization field {k!r} missing")
        if len(authorization["sha256"]) != 64:
            raise LedgerRefused("outcome refused: the full 64-character SHA-256 is required")
        p = Path(authorization["path"])
        if not p.exists() or _sha_file(p) != authorization["sha256"].lower():
            raise LedgerRefused("outcome refused: the outcome file does not match its authorized SHA-256")
        if len(labels) != 5 or any(int(v) not in (0, 1) for v in labels.values()):
            raise LedgerRefused("outcome refused: five 0/1 provincial labels are required")
        return self._append("OUTCOME", {"target_quarter": target_quarter,
                                        "labels": {k: int(v) for k, v in sorted(labels.items())},
                                        "authorization": authorization}, now)

    # ---- OUTCOME from measured values (E27 fix L3)
    def record_outcome_measured(self, *, target_quarter: str, target: str, measured: dict, authorization: dict,
                                now: datetime | None = None) -> dict:
        """Record the MEASURED components of a target quarter instead of labels. T1: {province: {"H", "D"}} (S1 =
        H + 2D, H regional so identical for the five provinces); T2: {province: {"D"}}. Each seal is then labelled
        with its OWN threshold (tau depends on the origin), so a lead-1 and a lead-2 forecast of the same quarter are
        each scored against the label rule in force when they were made."""
        if target_quarter in self.outcomes():
            raise LedgerRefused(f"outcome of {target_quarter} already recorded")
        if target_quarter in self.missing():
            raise LedgerRefused(f"{target_quarter} was declared to have no outcome; that declaration is final")
        if target not in ("T1", "T2"):
            raise LedgerRefused(f"unknown target {target}")
        for k in ("path", "sha256", "authorized_by", "authorized_on"):
            if not authorization.get(k):
                raise LedgerRefused(f"outcome refused: authorization field {k!r} missing")
        if len(authorization["sha256"]) != 64 or not Path(authorization["path"]).exists() or                 _sha_file(authorization["path"]) != authorization["sha256"].lower():
            raise LedgerRefused("outcome refused: the outcome file does not match its authorized SHA-256")
        if len(measured) != 5:
            raise LedgerRefused("outcome refused: five provinces are required")
        clean = {}
        for prov, m in sorted(measured.items()):
            d = float(m["D"])
            if target == "T1":
                h = float(m["H"])
                clean[prov] = {"H": h, "D": d, "S1": h + 2 * d}
            else:
                clean[prov] = {"D": d}
        if target == "T1" and len({v["H"] for v in clean.values()}) != 1:
            raise LedgerRefused("outcome refused: H is regional and must be identical for the five provinces")
        return self._append("OUTCOME", {"target_quarter": target_quarter, "target": target, "measured": clean,
                                        "authorization": authorization}, now)

    def _threshold(self, seal_pl: dict, target: str) -> float:
        if target == "T2":
            return 0.0
        if seal_pl.get("threshold") is not None:
            return float(seal_pl["threshold"])
        # an E25 seal imported by E26 before thresholds were stored: read tau from the hash-verified sealed file
        src = (seal_pl.get("inputs") or [{}])[0]
        sj = src.get("seal_json")
        if not sj:
            raise LedgerRefused(f"seal of {seal_pl['arm']} carries no threshold; a measured outcome cannot be labelled")
        csv = Path(sj).with_name("prospective_forecasts.csv")
        if _sha_file(csv) != src.get("forecasts_sha256"):
            raise LedgerRefused("sealed forecasts file changed: threshold lookup refused")
        import pandas as pd
        arm, lead = seal_pl["arm"].rsplit(":lead", 1)
        df = pd.read_csv(csv)
        g = df[(df["arm"] == arm) & (df["lead"] == int(lead)) & (df["target_quarter"] == seal_pl["target_quarter"])
               & (df["target"] == "T1_A")]
        if g.empty or g["tau"].nunique() != 1:
            raise LedgerRefused(f"no unique sealed tau for {seal_pl['arm']} {seal_pl['target_quarter']}")
        return float(g["tau"].iloc[0])

    def labels_for(self, seal_pl: dict, outcome_pl: dict) -> dict:
        """0/1 label per province for this seal: measured outcomes use the seal's own threshold; a legacy OUTCOME
        entry carries its labels directly."""
        if "measured" not in outcome_pl:
            return {k: int(v) for k, v in outcome_pl["labels"].items()}
        t = outcome_pl["target"]
        tau = self._threshold(seal_pl, t)
        key = "S1" if t == "T1" else "D"
        return {p: int(m[key] > tau) for p, m in outcome_pl["measured"].items()}

    # ---- NO_OUTCOME
    def record_missing(self, *, target_quarter: str, reason: str, evidence: str,
                       now: datetime | None = None) -> dict:
        """The target quarter has no official outcome (for example no SWS production round, or an incomplete CPI
        quarter). Final: no outcome can be recorded for it afterwards, so a quarter cannot be held back and scored
        later to move the A1 look."""
        if target_quarter in self.outcomes() or target_quarter in self.missing():
            raise LedgerRefused(f"{target_quarter} is already resolved")
        if not reason or not evidence:
            raise LedgerRefused("a reason and the evidence of non-availability are required")
        return self._append("NO_OUTCOME", {"target_quarter": target_quarter, "reason": reason,
                                           "evidence": evidence}, now)

    # ---- SCORE
    def score(self, arm: str, through: str | None = None) -> dict:
        """through: optional last target quarter included (used by the A1 look)."""
        outs = self.outcomes()
        if through is not None:
            outs = {q: e for q, e in outs.items() if _qk(q) <= _qk(through)}
        # only seals made BEFORE the outcome entry; a candidate is compared with baselines sealed at the SAME origin
        # (same information time and lead); if several qualify, the first sealed is used
        ok = [e["payload"] for e in self.seals()
              if e["payload"]["target_quarter"] in outs and outs[e["payload"]["target_quarter"]]["seq"] > e["seq"]]
        cand_pl = {}
        for pl in ok:
            if pl["arm"] == arm and pl["role"] == "candidate":
                cand_pl.setdefault(pl["target_quarter"], pl)
        cand = {q: pl["probabilities"] for q, pl in cand_pl.items()}
        bases = {}
        for pl in ok:
            q = pl["target_quarter"]
            if pl["role"] != "candidate" and q in cand_pl and pl["origin"] == cand_pl[q]["origin"]:
                bases.setdefault(pl["role"], {}).setdefault(q, pl["probabilities"])
        if cand:                                       # A3: always-HIGH is a constant, so it needs no seal
            bases[ALWAYS_HIGH] = {q: {p: 1.0 for p in pr} for q, pr in cand.items()}
        res = {"arm": arm, "baselines": {}, "claim": False}
        ys_all = []
        for role, bm in bases.items():
            dates = sorted(set(cand) & set(bm), key=_qk)
            dacc, dbri = [], []
            for q in dates:
                y = self.labels_for(cand_pl[q], outs[q]["payload"])     # the candidate's origin fixes tau
                provs = sorted(y)
                pc = np.array([cand[q][p] for p in provs]); pb = np.array([bm[q][p] for p in provs])
                yy = np.array([y[p] for p in provs])
                dbri.append(float(np.mean((pb - yy) ** 2) - np.mean((pc - yy) ** 2)))
                dacc.append(float(np.mean((pb >= .5) != yy) - np.mean((pc >= .5) != yy)))
                if role == ALWAYS_HIGH:
                    ys_all.extend(yy.tolist())
            res["baselines"][role] = {"dates": dates, "accuracy": eprocess(dacc), "brier": eprocess(dbri),
                                      "d_accuracy": dacc, "d_brier": dbri}
        n_dates = len(res["baselines"][ALWAYS_HIGH]["dates"]) if ALWAYS_HIGH in res["baselines"] else 0
        nH, nL = int(sum(ys_all)), int(len(ys_all) - sum(ys_all))
        res["evaluable"] = bool(n_dates >= MIN_DATES and nH >= MIN_PER_CLASS and nL >= MIN_PER_CLASS)
        res.update({"scored_dates": n_dates, "HIGH": nH, "LOW": nL})
        need = ("baseline_persistence", "baseline_calibrated_persistence")
        for metric in ("accuracy", "brier"):
            passed = all(r in res["baselines"] and res["baselines"][r][metric]["e_value"] >= E_THRESHOLD for r in need)
            res[f"claim_{metric}"] = bool(res["evaluable"] and passed)
        res["claim"] = res["claim_accuracy"]          # approved metric (C2); Brier only if the adviser approves P2
        res["claim_note"] = ("accuracy is the approved C2 metric; the Brier claim counts only after adviser approval "
                             "of P2")
        return res

    # ---- import of an existing sealed file (no new forecast is made)
    def import_sealed_file(self, *, seal_json: str | Path, forecasts_csv: str | Path, arm_roles: dict,
                           target: str = "T1_A", now: datetime | None = None) -> list[dict]:
        """Register the forecasts of an existing seal (e.g. E25 SEAL.json + prospective_forecasts.csv). The CSV
        bytes must match the SHA-256 recorded in the seal, and the seal time must precede every outcome of its
        targets (enforced by seal()). arm_roles maps a sealed arm name to a ledger role. Each imported seal is
        recorded with its original seal time and the hashes, as arm '<arm>:lead<k>'."""
        import pandas as pd
        meta = json.loads(Path(seal_json).read_text(encoding="utf-8"))
        got = _sha_file(forecasts_csv)
        if got != meta.get("sha256_forecasts"):
            raise LedgerRefused("import refused: the forecasts file does not match the SHA-256 in its seal")
        sealed_utc = datetime.fromisoformat(meta["sealed_utc"])
        if any(_qk(q) < _qk(_quarter_of(sealed_utc)) for q in meta.get("targets", {}).values()):
            raise LedgerRefused("import refused: a target quarter had ended before the seal time")
        df = pd.read_csv(forecasts_csv, dtype={"province_code": str})
        df = df[(df["target"] == target) & df["arm"].isin(arm_roles)]
        prov = {"inputs": [{"source": "existing seal", "seal_json": str(seal_json), "seal_json_sha256": _sha_file(seal_json),
                            "forecasts_sha256": got, "sealed_utc": meta["sealed_utc"], "authorized": True}]}
        out = []
        for (a, q, k, o), g in df.groupby(["arm", "target_quarter", "lead", "origin"]):
            tau = float(g["tau"].iloc[0]) if "tau" in g.columns and g["tau"].notna().all() and                 g["tau"].nunique() == 1 else None
            out.append(self.seal(arm=f"{a}:lead{int(k)}", role=arm_roles[a], target_quarter=q, origin=o,
                                 info_cutoff=str(g["info_cutoff"].iloc[0]),
                                 probabilities=dict(zip(g["province_code"], g["p"].astype(float))),
                                 model_sha256=_sha_file(seal_json), inputs=prov["inputs"], now=now,
                                 threshold=tau, sealed_at=sealed_utc))
        return out

    # ---- A1 single look (pending adviser approval)
    def looks(self, arm: str) -> list[dict]:
        return [e for e in self.entries if e["kind"] == "LOOK" and e["payload"]["arm"] == arm]

    def _resolved_through(self, year: int) -> bool:
        res = set(self.outcomes()) | set(self.missing())
        return all(e["payload"]["target_quarter"] in res for e in self.seals()
                   if _qk(e["payload"]["target_quarter"]) <= _qk(f"{year}-Q4"))

    def a1_first_eligible_year(self, arm: str) -> int | None:
        """The first year end at which targets <= Y-Q4 hold >= 12 scored dates, are evaluable and are all resolved."""
        tq = [_qk(e["payload"]["target_quarter"]) for e in self.seals() if e["payload"]["arm"] == arm]
        if not tq:
            return None
        for year in range(min(tq) // 4, max(tq) // 4 + 1):
            if not self._resolved_through(year):
                return None                            # a later year cannot be eligible before this one resolves
            r = self.score(arm, through=f"{year}-Q4")
            if r["scored_dates"] >= A1_MIN_DATES and r["evaluable"]:
                return year
        return None

    def a1_look(self, arm: str, year: int, now: datetime | None = None) -> dict:
        """Take the single pre-registered look. Refused if a look was already taken for this arm, or if `year` is not
        the first eligible year end. The result is written to the ledger and returned."""
        if self.looks(arm):
            raise LedgerRefused(f"A1 look for {arm} was already taken (seq {self.looks(arm)[0]['seq']}); "
                                "a new pre-registration is required for any further test")
        first = self.a1_first_eligible_year(arm)
        if first is None:
            raise LedgerRefused("A1 look refused: no year end yet has >= 12 scored, evaluable, fully resolved dates")
        if year != first:
            raise LedgerRefused(f"A1 look refused: the pre-registered look is at the end of {first}, not {year}")
        r = self.score(arm, through=f"{year}-Q4")
        need = ("baseline_persistence", "baseline_calibrated_persistence")
        tests = {}
        for role in need:
            if role not in r["baselines"]:
                raise LedgerRefused(f"A1 look refused: no sealed {role} arm")
        for role, b in r["baselines"].items():
            tests[role] = {"dates": b["dates"], "accuracy": signflip_p(b["d_accuracy"]),
                           "brier": signflip_p(b["d_brier"]),
                           "mean_d_accuracy": float(np.mean(b["d_accuracy"])),
                           "mean_d_brier": float(np.mean(b["d_brier"]))}
        claim_acc = all(tests[q]["accuracy"]["p"] < A1_ALPHA_EACH and tests[q]["mean_d_accuracy"] > 0 for q in need)
        claim_bri = all(tests[q]["brier"]["p"] < A1_ALPHA_EACH and tests[q]["mean_d_brier"] > 0 for q in need)
        k = len(tests)
        a3 = {m: all(tests[q][m]["p"] < A3_ALPHA / k and tests[q][f"mean_d_{m}"] > 0 for q in tests)
              for m in ("accuracy", "brier")}
        payload = {"arm": arm, "year_end": f"{year}-Q4", "scored_dates": r["scored_dates"], "HIGH": r["HIGH"],
                   "LOW": r["LOW"], "alpha_each": A1_ALPHA_EACH, "tests": tests,
                   "claim_accuracy": bool(claim_acc), "claim_brier": bool(claim_bri), "claim": bool(claim_acc),
                   "a3_references": sorted(tests), "a3_alpha_each": A3_ALPHA / k,
                   "claim_vs_all_references": bool(a3["accuracy"]),
                   "claim_vs_all_references_brier": bool(a3["brier"]),
                   "note": "amendment A1, pending adviser approval; accuracy is the approved C2 metric; "
                           "Brier counts only if the adviser approves P2; a failed look means 'not established'"}
        self._append("LOOK", payload, now)
        return payload
