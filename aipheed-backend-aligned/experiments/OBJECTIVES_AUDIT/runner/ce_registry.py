"""The prospective research registry for C-b, C-E2 and C-E6 (CE_PROSPECTIVE_PLAN.md), built from the files themselves.

    python ce_registry.py build    # -> ../prospective_ce/REGISTRY_CE.json (refuses to overwrite a different registry)
    python ce_registry.py verify   # recompute every hash and compare with the stored registry

Every value is computed (hashes, feature lists, development metrics read from each model's own results file); nothing
is typed in. C-b's entry points to its own protocol (SENIOR_REVIEW) and seal, which this registry never modifies.
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ce_prospective as C  # noqa: E402
import ce6_model as CE6  # noqa: E402
import cb6_model as CB6  # noqa: E402
import ce_model as CE  # noqa: E402

P, H = C.P, CE.H
OUT = C.HERE / "out"
STABLE = ("generated_by",)


def _dev(results: Path, name: str) -> dict:
    r = json.loads(results.read_text(encoding="utf-8"))
    L = {k: r["leads"][k][name] for k in ("1", "2")}
    sig = sum(f["significant"] for f in r["holm_family_14"])
    return {"leads": {k: {x: v["metrics"][x] for x in ("accuracy", "balanced", "precision", "recall", "f1", "auc", "brier")}
                      | {"failed_rules": v["failed"]} for k, v in L.items()},
            "max_reliable_lead": r["algorithm3"][name], "holm_14_significant": sig,
            "evidence": "development (62 previously examined quarters)"}


def build() -> dict:
    plan = C.check_plan()
    cb_eval = json.loads((C.ROOT / "backend" / "data" / "foodinsecurity_engine" / "evaluation.json").read_text(encoding="utf-8"))
    common = {"target": "SWS Balance Luzon involuntary hunger > 11.3% (quarter mean of non-commissioned rounds)",
              "decision_rule": "HIGH when p >= 0.50", "validation": "chronological walk-forward from 1998-Q3; labels known at O(t)",
              "issuance": "first day of every quarter from 2027-01-01; seal within 14 days; missed = missing, never back-filled"}
    reg = {
        "registry": "C-E prospective research registry", "plan": {"file": "OBJECTIVES_AUDIT/CE_PROSPECTIVE_PLAN.md",
                                                                  "sha256": plan, "addenda": C.check_addenda()},
        "models": {
            "C-b": {**common, "status": "PREVIOUS MAIN MODEL (adopted 2026-11-03, superseded by C-B6 2026-11-04; sealed; reference)",
                    "adoption": "adopted 2026-11-03; superseded 2026-11-04 (ADOPTION_DECISION_CB6.md)",
                    "protocol": "SENIOR_REVIEW/PROSPECTIVE_PLAN.md (sealed by SENIOR_REVIEW/runner/seal_next.py; not by this registry)",
                    "protocol_plan_sha256": P.check_plan(),
                    "seal": {"file": "NEW_MODEL/NEWS_V2/sealed_prospective_CB.csv", "sha256": C.sha(P.CB_SEAL),
                             "matches_recorded": C.sha(P.CB_SEAL) == P.CB_SEAL_SHA},
                    "features": P.MODELS["C-b"], "leads_sealed": list(P.LEADS),
                    "artifacts": {"NEW_MODEL/NEWS_V2/out/forecasts.csv": C.sha(P.CB_DIR / "out" / "forecasts.csv")},
                    "development": {"leads": {k: {x: v["metrics"][x] for x in ("accuracy", "balanced", "auc", "brier")}
                                              | {"failed_rules": v["failed"]} for k, v in cb_eval["leads"].items() if k in "12"},
                                    "max_reliable_lead": cb_eval["max_reliable_lead"]}},
        }}
    for m, pre_file, results, fits, runner in (("C-E2", "CE2_PREREGISTRATION.md", "ce2_results.json", "ce2_fits.csv", "ce2_model.py"),
                                               ("C-E6", "CE6_PREREGISTRATION.md", "ce6_results.json", "ce6_fits.csv", "ce6_model.py"),
                                               ("C-B6", "CB6_PREREGISTRATION.md", "cb6_results.json", "cb6_fits.csv", "cb6_model.py")):
        feats = CB6.PC.CB + CB6.ST if m == "C-B6" else CE.CE + (CE6.ST if m == "C-E6" else [])
        main = m == "C-B6"
        e = {**common, "status": ("MAIN MODEL (team decision 2026-11-04; adviser approval pending)" if main else
                                  "DEVELOPMENT CANDIDATE" + (" (local demo, port 8081)" if m == "C-E2" else "")),
             "adoption": ("adopted by team decision 2026-11-04 (ADOPTION_DECISION_CB6.md); pre-registered H7 not met; "
                          "adviser approval pending" if main else
                          "not adopted (fails R3 and R7; pre-registered adoption rule not met)"),
             "version": f"{m} v1 ({runner} {C.sha(C.RUN / runner)[:12]})",
             "preregistration": {"file": f"OBJECTIVES_AUDIT/{pre_file}", "sha256": C.hash_line(C.HERE / pre_file)},
             "method": ("LightGBM, stacked leads; at each origin the setting chosen by hr_lib.lgbm_select on inner "
                        "chronological folds (C-b's procedure); TreeSHAP" if m == "C-B6" else
                        "LightGBM, stacked leads; at each origin the mean of the 8 hr_lib.GRID settings (depth 1/2 x 50/150 "
                        "trees x class weight none/balanced); mean TreeSHAP"),
             "features": feats, "n_features": len(feats),
             "sources_and_publication_rules": {
                 "table": "IMPROVE_V2 pooled BL table rebuilt by prospective_lib.build_table (release rules of iv2_lib)",
                 "E1": "PSA LFS national unemployment change (in the table)",
                 "E2": f"IMF BOP personal transfers ({C.sha(CE.REMIT)[:12]}), quarters <= t-2"},
             "leads_sealed": list(C.SEAL_LEADS), "sealing_script": "OBJECTIVES_AUDIT/runner/seal_ce.py",
             "artifacts": {f"OBJECTIVES_AUDIT/out/{fits}": C.sha(OUT / fits), f"OBJECTIVES_AUDIT/out/{results}": C.sha(OUT / results)},
             "development": _dev(OUT / results, m),
             "evaluation_criteria": ("CE_PROSPECTIVE_ADDENDUM_1.md (P4: C-B6 vs 7 baselines, Holm 14; P5: vs C-b, Holm 2)"
                                     if m == "C-B6" else "CE_PROSPECTIVE_PLAN.md section 5 (P1: C-E6 vs 7 baselines, Holm 14; P2: vs C-E2 and C-b, Holm 4)")}
        if m == "C-B6":
            e["sources_and_publication_rules"].pop("E1")
            e["sources_and_publication_rules"].pop("E2")
            e["added_by"] = "CE_PROSPECTIVE_ADDENDUM_1.md"
        if m in ("C-E6", "C-B6"):
            e["sources_and_publication_rules"]["ST1_ST2"] = {
                "source": "PSA OpenSTAT 2E/CS/0032E4ECNV0 rice stocks inventory (national, monthly, 1980-01..2026-09)",
                "file": f"LEAD2_RELIABILITY_RESEARCH/y12_domestic_rice_supply/data_acquired/tidy_stocks_national.csv ({C.sha(CE6.STOCKS)[:12]})",
                "ST1": "(total stock at M / total at M-12 - 1) x 100", "ST2": "NFA share of total at M minus at M-12 (points)",
                "availability": f"M <= issue month - {CE6.LAG_MONTHS} (verified release lags 31-92 days)",
                "features_file": f"OBJECTIVES_AUDIT/out/ce6_features.csv ({C.sha(OUT / 'ce6_features.csv')[:12]})",
                "limitation": "OpenSTAT serves the current vintage only; pre-2022 release dates unverified (bounded by the 4-month rule)"}
            e["artifacts"]["OBJECTIVES_AUDIT/out/ce6_features.csv"] = C.sha(OUT / "ce6_features.csv")
        reg["models"][m] = e
    reg["code_sha256"] = C.code_hashes()
    reg["prospective_seals"] = C.read_ledger(C.LEDGER_CE)
    return reg


def main():
    cmd = sys.argv[1]
    reg = build()
    if cmd == "build":
        if C.REGISTRY_CE.exists():
            old = json.loads(C.REGISTRY_CE.read_text(encoding="utf-8"))
            assert old == reg, "REGISTRY_CE.json exists and differs: run verify; an existing registry is never overwritten"
            print("registry unchanged")
            return
        C.PROS_CE.mkdir(parents=True, exist_ok=True)
        C.REGISTRY_CE.write_text(json.dumps(reg, indent=1), encoding="utf-8")
        print(f"written {C.REGISTRY_CE} ({C.sha(C.REGISTRY_CE)})")
    else:
        old = json.loads(C.REGISTRY_CE.read_text(encoding="utf-8"))
        diff = sorted(k for k in set(old) | set(reg) if old.get(k) != reg.get(k))
        print(json.dumps({"matches": not diff, "differing_sections": diff}, indent=1))
        if diff:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
