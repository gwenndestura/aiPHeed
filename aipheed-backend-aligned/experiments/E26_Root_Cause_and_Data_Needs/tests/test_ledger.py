"""Prospective ledger (section E and amendment A1): hash chain, refusal paths, scoring order, e-process and sign-flip
validity, and the single pre-registered look. SYNTHETIC forecasts and outcomes only."""
import hashlib
import itertools
import json
from datetime import datetime, timezone

import numpy as np
import pytest

import _paths  # noqa: F401
from app.quarterly import ledger as LG

PROVS = ["PH040100000", "PH040200000", "PH040300000", "PH040400000", "PH040500000"]
LATER = datetime(2032, 1, 1, tzinfo=timezone.utc)
INP = [{"source": "synthetic", "sha256": "x" * 64, "authorized": True}]


def qs(i):
    return f"{i // 4}-Q{i % 4 + 1}"


def origin_of(target):          # O(t) = first day of the target quarter (lead 1: reference quarter t-1)
    y, n = target.split("-Q")
    return f"{y}-{3 * (int(n) - 1) + 1:02d}-01T00:00:00+08:00"


def outcome_file(tmp_path, q, labels):
    f = tmp_path / f"outcome_{q}.json"
    f.write_text(json.dumps(labels, sort_keys=True))
    return {"path": str(f), "sha256": hashlib.sha256(f.read_bytes()).hexdigest(), "authorized_by": "test",
            "authorized_on": "2032-01-01"}


def seal_all(L, q, cand, b1, b1p):
    for arm, role, pr in (("PCF", "candidate", cand), ("B1", "baseline_persistence", b1),
                          ("B1p", "baseline_calibrated_persistence", b1p)):
        L.seal(arm=arm, role=role, target_quarter=q, origin=origin_of(q), info_cutoff=origin_of(q),
               probabilities=dict(zip(PROVS, pr)), model_sha256="m" * 64, inputs=INP, now=LATER)


# ---------------------------------------------------------------------------------------------- integrity
def test_hash_chain_and_tamper_detection(tmp_path):
    L = LG.Ledger(tmp_path / "l.jsonl")
    seal_all(L, "2027-Q1", [.8] * 5, [1] * 5, [.7] * 5)
    assert LG.Ledger(tmp_path / "l.jsonl").verify()
    lines = (tmp_path / "l.jsonl").read_text().splitlines()
    e = json.loads(lines[0])
    e["payload"]["probabilities"][PROVS[0]] = 0.1                   # edit a sealed probability
    (tmp_path / "l.jsonl").write_text("\n".join([json.dumps(e, sort_keys=True)] + lines[1:]) + "\n")
    with pytest.raises(LG.LedgerRefused):
        LG.Ledger(tmp_path / "l.jsonl")
    (tmp_path / "l.jsonl").write_text("\n".join(lines[1:]) + "\n")  # delete the first entry
    with pytest.raises(LG.LedgerRefused):
        LG.Ledger(tmp_path / "l.jsonl")


def test_seal_refusals(tmp_path):
    L = LG.Ledger(tmp_path / "l.jsonl")
    kw = dict(arm="PCF", role="candidate", target_quarter="2027-Q1", origin=origin_of("2027-Q1"),
              info_cutoff=origin_of("2027-Q1"), probabilities=dict(zip(PROVS, [.6] * 5)), model_sha256="m" * 64,
              inputs=INP)
    with pytest.raises(LG.LedgerRefused, match="future"):
        L.seal(**kw, now=datetime(2026, 12, 1, tzinfo=timezone.utc))
    with pytest.raises(LG.LedgerRefused, match="authorized"):
        L.seal(**{**kw, "inputs": [{"source": "x", "authorized": False}]}, now=LATER)
    with pytest.raises(LG.LedgerRefused, match="five"):
        L.seal(**{**kw, "probabilities": {PROVS[0]: .5}}, now=LATER)
    with pytest.raises(LG.LedgerRefused, match="role"):
        L.seal(**{**kw, "role": "oracle"}, now=LATER)
    L.seal(**kw, now=LATER)
    with pytest.raises(LG.LedgerRefused, match="already sealed"):
        L.seal(**kw, now=LATER)


def test_outcome_requires_matching_authorized_file_and_blocks_later_seals(tmp_path):
    L = LG.Ledger(tmp_path / "l.jsonl")
    auth = outcome_file(tmp_path, "2027-Q1", {p: 1 for p in PROVS})
    with pytest.raises(LG.LedgerRefused, match="64"):
        L.record_outcome(target_quarter="2027-Q1", labels={p: 1 for p in PROVS}, authorization={**auth, "sha256": auth["sha256"][:12]})
    with pytest.raises(LG.LedgerRefused, match="does not match"):
        L.record_outcome(target_quarter="2027-Q1", labels={p: 1 for p in PROVS},
                         authorization={**auth, "sha256": hashlib.sha256(b"other").hexdigest()})
    with pytest.raises(LG.LedgerRefused, match="authorization field"):
        L.record_outcome(target_quarter="2027-Q1", labels={p: 1 for p in PROVS}, authorization={**auth, "authorized_by": ""})
    L.record_outcome(target_quarter="2027-Q1", labels={p: 1 for p in PROVS}, authorization=auth, now=LATER)
    with pytest.raises(LG.LedgerRefused, match="already resolved"):
        L.seal(arm="PCF", role="candidate", target_quarter="2027-Q1", origin=origin_of("2027-Q1"),
               info_cutoff=origin_of("2027-Q1"), probabilities=dict(zip(PROVS, [.6] * 5)), model_sha256="m" * 64,
               inputs=INP, now=LATER)
    with pytest.raises(LG.LedgerRefused, match="already recorded"):
        L.record_outcome(target_quarter="2027-Q1", labels={p: 1 for p in PROVS}, authorization=auth)


def test_no_outcome_declaration_is_final(tmp_path):
    L = LG.Ledger(tmp_path / "l.jsonl")
    with pytest.raises(LG.LedgerRefused, match="reason"):
        L.record_missing(target_quarter="2027-Q2", reason="", evidence="")
    L.record_missing(target_quarter="2027-Q2", reason="no SWS production round", evidence="SWS release list", now=LATER)
    auth = outcome_file(tmp_path, "2027-Q2", {p: 1 for p in PROVS})
    with pytest.raises(LG.LedgerRefused, match="final"):
        L.record_outcome(target_quarter="2027-Q2", labels={p: 1 for p in PROVS}, authorization=auth)


def test_score_uses_only_seals_made_before_the_outcome(tmp_path):
    L = LG.Ledger(tmp_path / "l.jsonl")
    seal_all(L, "2027-Q1", [.9] * 5, [0] * 5, [.4] * 5)
    L.record_outcome(target_quarter="2027-Q1", labels={p: 1 for p in PROVS},
                     authorization=outcome_file(tmp_path, "2027-Q1", {p: 1 for p in PROVS}), now=LATER)
    # forge an entry that claims to be a seal after the outcome: it must not be scored (and the chain stays valid)
    L._append("SEAL", {"arm": "PCF", "role": "candidate", "target_quarter": "2027-Q1", "origin": "2027-01-02T00:00:00+08:00",
                       "info_cutoff": "x", "probabilities": {p: 0.0 for p in PROVS}, "model_sha256": "m" * 64,
                       "inputs": INP}, LATER)
    r = L.score("PCF")
    assert r["scored_dates"] == 1
    d = r["baselines"]["baseline_persistence"]["d_accuracy"]
    assert d == [1.0]                                   # the pre-outcome seal (0.9 -> correct) was used


# ---------------------------------------------------------------------------------------------- statistics
def test_signflip_matches_enumeration():
    rng = np.random.default_rng(3)
    for _ in range(100):
        n = int(rng.integers(1, 10))
        for d in (rng.integers(-5, 6, n) / 5, rng.uniform(-1, 1, n)):
            a = np.abs(d)
            bf = np.mean([np.dot(s, a) >= d.sum() - 1e-12 for s in itertools.product([-1, 1], repeat=n)])
            assert abs(LG.signflip_p(d)["p"] - bf) < 1e-12


def test_signflip_and_eprocess_type_I_error_under_null():
    """Symmetric per-date differences (no real advantage): P(claim) must not exceed the nominal level."""
    rng = np.random.default_rng(20261014)
    n_sim, rej_sf, rej_e = 4000, 0, 0
    for _ in range(n_sim):
        d = rng.choice([-0.4, -0.2, 0.0, 0.2, 0.4], size=20, p=[.1, .2, .4, .2, .1])
        rej_sf += LG.signflip_p(d)["p"] < LG.A1_ALPHA_EACH
        rej_e += LG.eprocess(d)["max_e"] >= LG.E_THRESHOLD
    se = np.sqrt(.025 * .975 / n_sim)
    assert rej_sf / n_sim <= LG.A1_ALPHA_EACH + 3 * se
    assert rej_e / n_sim <= 1 / LG.E_THRESHOLD + 3 * se


def test_eprocess_needs_many_dates_even_for_a_steady_advantage():
    """Documents the defect behind amendment A1: +0.1 per date for 20 dates gives e of about 2.6, far below 40."""
    e = LG.eprocess([0.1] * 20)["e_value"]
    assert 2.0 < e < 3.5
    assert LG.signflip_p([0.1] * 20)["p"] < 1e-5


# ---------------------------------------------------------------------------------------------- A1 single look
def build(tmp_path, n_quarters, cand_good=True, start="2027-Q1", missing=()):
    """Synthetic ledger: persistence repeats the previous label; the candidate is right every time (cand_good) or
    as bad as persistence. Labels alternate in blocks so both classes and label changes occur."""
    L = LG.Ledger(tmp_path / "l.jsonl")
    i0 = int(start[:4]) * 4 + int(start[-1]) - 1
    prev = {p: 1 for p in PROVS}
    for j in range(n_quarters):
        q = qs(i0 + j)
        y = {p: int(((j // 2) + k) % 2 == 0) for k, p in enumerate(PROVS)}
        cand = [(.9 if y[p] else .1) if cand_good else float(prev[p]) for p in PROVS]
        seal_all(L, q, cand, [float(prev[p]) for p in PROVS], [.6 if prev[p] else .4 for p in PROVS])
        if q in missing:
            L.record_missing(target_quarter=q, reason="no round", evidence="release list", now=LATER)
        else:
            L.record_outcome(target_quarter=q, labels=y, authorization=outcome_file(tmp_path, q, y), now=LATER)
            prev = y
    return L


def test_a1_first_eligible_year_and_single_look(tmp_path):
    L = build(tmp_path, 16)                              # 2027-Q1 .. 2030-Q4
    assert L.a1_first_eligible_year("PCF") == 2029       # 12 dates reached at the end of 2029
    with pytest.raises(LG.LedgerRefused, match="end of 2029"):
        L.a1_look("PCF", 2030, now=LATER)                # a later look is a different look time: refused
    res = L.a1_look("PCF", 2029, now=LATER)
    assert res["scored_dates"] == 12 and res["year_end"] == "2029-Q4"
    assert res["claim_accuracy"] and res["claim"]
    for role in ("baseline_persistence", "baseline_calibrated_persistence"):
        assert res["tests"][role]["accuracy"]["p"] < LG.A1_ALPHA_EACH
    with pytest.raises(LG.LedgerRefused, match="already taken"):
        L.a1_look("PCF", 2029, now=LATER)
    assert LG.Ledger(tmp_path / "l.jsonl").looks("PCF")[0]["payload"]["claim"] is True   # recorded in the chain


def test_a1_no_claim_when_the_candidate_is_persistence(tmp_path):
    L = build(tmp_path, 12, cand_good=False)
    res = L.a1_look("PCF", L.a1_first_eligible_year("PCF"), now=LATER)
    assert not res["claim"] and not res["claim_brier"]


def test_a1_look_refused_before_eligibility_and_missing_quarters_delay_it(tmp_path):
    L = build(tmp_path, 8)
    assert L.a1_first_eligible_year("PCF") is None
    with pytest.raises(LG.LedgerRefused, match="no year end"):
        L.a1_look("PCF", 2028, now=LATER)
    (tmp_path / "l.jsonl").unlink()
    L2 = build(tmp_path, 16, missing=("2027-Q3", "2028-Q2"))
    assert L2.a1_first_eligible_year("PCF") == 2030      # two quarters without an outcome push 12 dates to 2030


def test_a1_look_refused_while_a_sealed_target_is_unresolved(tmp_path):
    L2 = LG.Ledger(tmp_path / "l2.jsonl")
    for j in range(12):
        q = qs(2027 * 4 + j)
        seal_all(L2, q, [.9] * 5, [0] * 5, [.4] * 5)
        if q != "2029-Q2":
            y = {p: int((j + k) % 2 == 0) for k, p in enumerate(PROVS)}
            L2.record_outcome(target_quarter=q, labels=y, authorization=outcome_file(tmp_path, q, y), now=LATER)
    assert L2.a1_first_eligible_year("PCF") is None      # 2029-Q2 sealed, neither OUTCOME nor NO_OUTCOME yet


# ---------------------------------------------------------------------------------------------- origin matching, import
def test_baselines_must_share_the_candidate_origin(tmp_path):
    L = LG.Ledger(tmp_path / "l.jsonl")
    q = "2027-Q1"
    L.seal(arm="PCF", role="candidate", target_quarter=q, origin="2027-01-01T00:00:00+08:00", info_cutoff="x",
           probabilities=dict(zip(PROVS, [.9] * 5)), model_sha256="m" * 64, inputs=INP, now=LATER)
    for o in ("2026-10-01T00:00:00+08:00", "2027-01-01T00:00:00+08:00"):          # lead-2 baseline sealed first
        L.seal(arm=f"B1@{o[:7]}", role="baseline_persistence", target_quarter=q, origin=o, info_cutoff="x",
               probabilities=dict(zip(PROVS, [0.0 if o.startswith("2026") else 1.0] * 5)), model_sha256="b" * 64,
               inputs=INP, now=LATER)
    L.record_outcome(target_quarter=q, labels={p: 1 for p in PROVS},
                     authorization=outcome_file(tmp_path, q, {p: 1 for p in PROVS}), now=LATER)
    d = L.score("PCF")["baselines"]["baseline_persistence"]["d_accuracy"]
    assert d == [0.0]                                   # compared with the same-origin baseline (1.0), not the lead-2 one


def _synthetic_seal(tmp_path, sealed_utc="2026-10-14T00:25:48+00:00"):
    import pandas as pd
    rows = []
    for arm in ("PCF21", "B1_naive_persistence", "B1p_calibrated_persistence"):
        for q, k in (("2026-Q4", 1), ("2027-Q1", 2)):
            for p in PROVS:
                rows.append({"target": "T1_A", "arm": arm, "final": arm == "PCF21", "target_quarter": q, "lead": k,
                             "origin": "2026-10-01T00:00:00", "info_cutoff": "2026-09-30T23:59:59+08:00",
                             "province_code": p, "p": .7})
    csv = tmp_path / "prospective_forecasts.csv"
    pd.DataFrame(rows).to_csv(csv, index=False)
    meta = {"sealed_utc": sealed_utc, "sha256_forecasts": hashlib.sha256(csv.read_bytes()).hexdigest(),
            "targets": {"1": "2026-Q4", "2": "2027-Q1"}}
    sj = tmp_path / "SEAL.json"
    sj.write_text(json.dumps(meta))
    return sj, csv


ROLES = {"PCF21": "candidate", "B1_naive_persistence": "baseline_persistence",
         "B1p_calibrated_persistence": "baseline_calibrated_persistence"}


def test_import_of_an_existing_seal_verifies_its_hash(tmp_path):
    sj, csv = _synthetic_seal(tmp_path)
    L = LG.Ledger(tmp_path / "l.jsonl")
    out = L.import_sealed_file(seal_json=sj, forecasts_csv=csv, arm_roles=ROLES, now=LATER)
    assert len(out) == 6 and {e["payload"]["arm"] for e in out} >= {"PCF21:lead1", "PCF21:lead2"}
    assert all(e["payload"]["inputs"][0]["sealed_utc"] == "2026-10-14T00:25:48+00:00" for e in out)
    with pytest.raises(LG.LedgerRefused, match="already sealed"):
        L.import_sealed_file(seal_json=sj, forecasts_csv=csv, arm_roles=ROLES, now=LATER)
    csv.write_text(csv.read_text().replace("0.7", "0.8"))                        # tamper with the sealed bytes
    with pytest.raises(LG.LedgerRefused, match="does not match"):
        LG.Ledger(tmp_path / "l2.jsonl").import_sealed_file(seal_json=sj, forecasts_csv=csv, arm_roles=ROLES, now=LATER)


def test_import_refused_when_a_target_ended_before_the_seal(tmp_path):
    sj, csv = _synthetic_seal(tmp_path, sealed_utc="2027-04-02T00:00:00+00:00")
    with pytest.raises(LG.LedgerRefused, match="ended before"):
        LG.Ledger(tmp_path / "l.jsonl").import_sealed_file(seal_json=sj, forecasts_csv=csv, arm_roles=ROLES, now=LATER)


# ---------------------------------------------------------------------------------------------- A3 references
def _a3_ledger(tmp_path, name, block):
    """Perfect candidate; labels change every `block` quarters; climatology sealed at the same origins."""
    L = LG.Ledger(tmp_path / f"{name}.jsonl")
    prev = {p: 1 for p in PROVS}
    for j in range(12):
        q = qs(2027 * 4 + j)
        y = {p: int(((j // block) + k) % 2 == 0) for k, p in enumerate(PROVS)}
        seal_all(L, q, [(.9 if y[p] else .1) for p in PROVS], [float(prev[p]) for p in PROVS], [.5] * 5)
        L.seal(arm="CLIM", role="reference_climatology", target_quarter=q, origin=origin_of(q), info_cutoff="x",
               probabilities=dict(zip(PROVS, [.55] * 5)), model_sha256="c" * 64, inputs=INP, now=LATER)
        L.record_outcome(target_quarter=q, labels=y, authorization=outcome_file(tmp_path, f"{name}{q}", y), now=LATER)
        prev = y
    return L.a1_look("PCF", 2029, now=LATER)


def test_a3_tests_always_high_and_climatology(tmp_path):
    res = _a3_ledger(tmp_path, "every", block=1)        # persistence errs on (almost) every date
    assert set(res["a3_references"]) == {"baseline_persistence", "baseline_calibrated_persistence",
                                         "reference_climatology", LG.ALWAYS_HIGH}
    assert abs(res["a3_alpha_each"] - 0.05 / 4) < 1e-12
    assert res["claim"] and res["claim_vs_all_references"]


def test_a3_is_stricter_than_a1(tmp_path):
    """Labels change every 2 quarters: persistence errs on 6 of 12 dates, so its best p is 2^-6 = 0.0156. That
    passes A1 (0.025) but not A3 (0.05/4 = 0.0125) even for a perfect candidate: the power cost of A3."""
    res = _a3_ledger(tmp_path, "block2", block=2)
    assert abs(res["tests"]["baseline_persistence"]["accuracy"]["p"] - 2 ** -6) < 1e-12
    assert res["claim"] and not res["claim_vs_all_references"]


def test_a3_no_success_when_the_candidate_is_always_high(tmp_path):
    L = LG.Ledger(tmp_path / "l.jsonl")
    prev = {p: 1 for p in PROVS}
    for j in range(12):
        q = qs(2027 * 4 + j)
        y = {p: int(((j // 2) + k) % 2 == 0) for k, p in enumerate(PROVS)}
        seal_all(L, q, [1.0] * 5, [float(prev[p]) for p in PROVS], [.6 if prev[p] else .4 for p in PROVS])
        L.record_outcome(target_quarter=q, labels=y, authorization=outcome_file(tmp_path, q, y), now=LATER)
        prev = y
    res = L.a1_look("PCF", 2029, now=LATER)
    assert res["tests"][LG.ALWAYS_HIGH]["accuracy"]["p"] == 1.0 and not res["claim_vs_all_references"]
