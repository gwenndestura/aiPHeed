"""E40: freeze the primary label (P60, sustain = 2) and its gates (researcher's amended rule, 2026-10-15), with the
P75 sensitivity and the 21.1% SWS report-only variant. Writes label_spec.json, label_primary.csv,
label_sensitivity_P75.csv, label_variant_sws21_1.csv and frozen/E40_LABEL_FREEZE.json. Refuses to overwrite.

    <backend venv python> -B runner/e40_freeze_label.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e40_label as L  # noqa: E402

E40 = L.E40
PRIMARY_PCT, SUSTAIN = 60, 2


def gates(p: dict, dev_quarters: list[str]) -> dict:
    years = {}
    for q in dev_quarters:
        years.setdefault(q[:4], []).append(q)
    capped = {y: v for y, v in p["HIGH_share_by_year"].items() if len(years.get(y, [])) >= 3}
    return {"overall_share_in_5_30pct": 0.05 <= p["HIGH_share"] <= 0.30,
            "year_cap_40pct_on_years_with_3plus_dev_quarters": all(v <= 0.40 for v in capped.values()),
            "years_checked": {y: v for y, v in capped.items()},
            "years_exempt_fewer_than_3_dev_quarters": sorted(set(p["HIGH_share_by_year"]) - set(capped))}


def main():
    if (E40 / "frozen" / "E40_LABEL_FREEZE.json").exists():
        raise SystemExit("label already frozen")
    q = L.quarterly_inputs()
    labelled = sorted(q.dropna(subset=["H"])["quarter"].unique())
    scored = [x for x in labelled if x >= L.SCORE_FROM]
    holdout, dev = scored[-4:], scored[:-4]
    thr = L.frozen_thresholds(q, PRIMARY_PCT)
    lab = L.label(q, thr)
    prev = L.prevalence(lab, dev)
    g = gates(prev, dev)
    assert all(v for k, v in g.items() if isinstance(v, bool)), f"primary label fails a gate: {g}"
    spec = {
        "name": "aiPHeed E40 binary food-stress label (exploratory)", "version": "E40-label-1.0",
        "frozen_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rule": "HIGH (1) if sws_hi AND (cpi_hi OR gap_hi) in quarter q AND in quarter q-1 (sustain = 2); LOW (0) "
                "otherwise; no label where the quarter has no approved SWS round (never zero-filled)",
        "signals": {"sws_hi": "Balance Luzon hunger H_q > P60 of H over the frozen window",
                    "cpi_hi": "province food CPI YoY (PSA published, quarter mean) > P60 of that province over the window",
                    "gap_hi": "food minus headline CPI YoY > P60 of that province over the window",
                    "cpi_rel": "food YoY minus the five-province mean (reported; ranking and ties)"},
        "frozen_window": list(L.WINDOW), "window_never_recomputed": True, "thresholds": thr,
        "percentile": PRIMARY_PCT, "sustain_quarters": SUSTAIN,
        "selection": "researcher's choice (2026-10-15) after the P60-P85 grid; amended gates: 5-30% overall HIGH share "
                     "of the development sample; 40% per-year cap only on years with >= 3 development quarters",
        "development_quarters": dev, "holdout_quarters_untouched": holdout, "development_prevalence": prev, "gates": g,
        "sensitivity_P75": "reported only (label_sensitivity_P75.csv)",
        "variant_sws_21_1": L.SWS_ABS_NOTE,
        "training_use_of_burn_in_labels": "labels of 2021-2022 quarters (computed with the frozen thresholds) are used "
                                          "as training targets only, never scored",
        "data": {"cpi": "PSA OpenStat 0012M4ACP23 published monthly YoY, All items and 01.1 Food, 2021-01..2026-09",
                 "sws": "backend/data/inputs/sws_rounds.csv, definition_A rounds", "earliest_month": L.EARLIEST},
        "not": "not a validated measure of food insecurity; indicative, not an official classification"}
    files = {"label_spec.json": json.dumps(spec, indent=1, default=float).encode()}
    cols = ["quarter", "province_code", "H", "H_posted", "food", "headline", "cpi_gap", "cpi_rel", "sws_hi", "cpi_hi",
            "gap_hi", "both", "y_high", "label", "scored_period"]
    files["label_primary.csv"] = lab[cols].to_csv(index=False, float_format="%.10g", lineterminator="\n").encode()
    files["label_sensitivity_P75.csv"] = L.label(q, L.frozen_thresholds(q, 75))[cols].to_csv(
        index=False, float_format="%.10g", lineterminator="\n").encode()
    files["label_variant_sws21_1.csv"] = L.label(q, thr, sws_abs=L.SWS_ABS)[cols].to_csv(
        index=False, float_format="%.10g", lineterminator="\n").encode()
    for n, b in files.items():
        (E40 / n).write_bytes(b)
    fr = {"frozen_at_utc": spec["frozen_at_utc"], "before_any_model_run": True,
          "sha256": {n: hashlib.sha256(b).hexdigest() for n, b in files.items()}}
    (E40 / "frozen" / "E40_LABEL_FREEZE.json").write_bytes(json.dumps(fr, indent=1).encode())
    print(json.dumps({"gates": g, "dev_prevalence": prev["HIGH_share"], "by_year": prev["HIGH_share_by_year"],
                      "sha256": fr["sha256"]}, indent=1, default=float))
    allq = lab[lab.y_high.notna()]
    print("HIGH rows by quarter (all labelled, incl. burn-in; holdout rows listed but not used):",
          allq.groupby("quarter")["y_high"].sum().astype(int).to_dict())


if __name__ == "__main__":
    main()
