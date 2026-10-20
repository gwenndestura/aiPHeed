"""E67 r5 (PROTOCOL 6): build backend/data/e67/e67_disclosure.json, the serving disclosure of the e67 mode, from the
E67 R1-R4 outputs only (every number shown in the dashboard is traceable to an E67 table; a test rebuilds and compares).

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E67_Lead2_Best_Model_Objectives_1_4/runner/r5_build_disclosure.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e67_lib as K  # noqa: E402

H, pd = K.H, K.pd
DEST = H.BACKEND / "data" / "e67" / "e67_disclosure.json"
LABEL = {"market": "Market / Prices", "climate": "Climate Stress", "fish_kill": "Fish Kill", "employment": "Employment",
         "ofw_remittance": "OFW Remittance", "news": "News signals"}
ARM_OF = {"climate": "X_climate", "fish_kill": "X_fish", "employment": "X_employment", "ofw_remittance": "X_ofw",
          "news": "X_news"}
# what each group actually feeds the model (E60 FEATURE_AVAILABILITY_AND_TIMING.csv, E67 r2)
DATA_USED = {
    "market": "PSA provincial food and headline CPI (projection of food inflation two quarters ahead), PSA wholesale "
              "rice prices, national rice-policy orders",
    "climate": "observed ENSO phase (NOAA ONI, quarters t-1 and t-2), typhoons within 300 km (IBTrACS), PSA provincial "
               "palay and corn production; no rainfall, drought or forward PAGASA outlook",
    "fish_kill": "PSA provincial fisheries and aquaculture production; no official fish-kill event series exists",
    "employment": "PSA Labor Force Survey unemployment and underemployment (national)",
    "ofw_remittance": "BSP OF cash remittances (national; file ends 2025-Q4) and the USD/PHP rate",
    "news": "share of the quarter's news titles tagged to each trigger and the article count (E40 keyword tagging)",
}
# latest period used at the 2026-10-01 issue (2027-Q1 forecast): E56 tables/data_freshness.csv
LATEST_2027Q1 = {"market": "CPI through 2026-08; wholesale rice 2026-Q2; policy orders through 2025-10-30",
                 "climate": "ENSO 2026-Q2; typhoons 2026-Q3 (incomplete quarter, fetched 2026-09-09); palay/corn 2026-Q2",
                 "fish_kill": "2026-Q2", "employment": "2026-Q2 (months of quarter t-1)",
                 "ofw_remittance": "remittances 2025-Q4 (none for 2026); USD/PHP 2026-Q2", "news": "articles of 2026-Q3"}
GEOGRAPHY = {"market": "province (policy orders national)", "climate": "province (ENSO national)",
             "fish_kill": "province", "employment": "national", "ofw_remittance": "national", "news": "province"}


def main():
    K.verify_protocol()
    cov = pd.read_csv(K.TABLES / "r2_coverage_summary.csv")
    eff = pd.read_csv(K.TABLES / "r3_trigger_group_effects.csv").set_index("arm")
    goal = pd.read_csv(K.TABLES / "r3_goal_test.csv").set_index("reading")
    trace = pd.read_csv(K.TABLES / "r4_el_nino_trace.csv")
    r1 = json.loads((K.OUT / "r1_ablation.json").read_text())
    groups = []
    for g in ["market", "climate", "fish_kill", "employment", "ofw_remittance", "news"]:
        c = cov[cov["group"] == g]
        missing = c.loc[c["test_nan_at_2027Q1_origin"] > 0, "feature"].tolist()
        zero = c.loc[c["eval_test_zero_share"] >= 0.95, "feature"].tolist()
        if g == "market":
            effect = "not ablated (every arm keeps it; the market-only arm was not distinguishable from all groups)"
        else:
            e = eff.loc[f"{ARM_OF[g]}_p"]
            effect = e["effect"]
        notes = []
        if missing:
            notes.append(f"missing at the 2026-10-01 issue: {', '.join(missing)} (treated as unknown, not as zero)")
        if zero:
            notes.append(f"almost always zero in 2024-2026: {', '.join(zero)} (too thin to carry a signal)")
        if g == "fish_kill":
            notes.append("measures production, not fish-kill events")
        if g in ("employment", "ofw_remittance"):
            notes.append("national figures, the same for every province")
        if g == "climate":
            notes.append("observed conditions only, so an approaching El Nino is not in the model")
        groups.append({"key": g, "label": LABEL[g], "dataUsed": DATA_USED[g], "geography": GEOGRAPHY[g],
                       "latestAtIssue": LATEST_2027Q1[g],
                       "missingAtIssue": bool(missing), "measuredEffect": effect,
                       "note": ("; ".join(notes) + ".") if notes else "Observed at the issue date."})
    e56, ew = goal.loc["E56"], goal.loc["EW"]
    acc_text = (f"Lead-2 development back-test, 50 province-quarters 2024-Q2..2026-Q3: accuracy "
                f"{e56['T43_accuracy']:.2f} ({int(e56['correct'])}/50), balanced accuracy {e56['T43_balanced_accuracy']:.2f}; "
                f"the early-warning reading {ew['T43_accuracy']:.2f} ({int(ew['correct'])}/50). Always-LOW scores "
                f"{goal.loc['MAJORITY', 'T43_accuracy']:.2f}; neither result is distinguishable from it, and the 75% "
                "goal is not legitimately met.")
    low = {}
    for r in trace.itertuples():
        if r.target not in ("2026-Q4", "2027-Q1"):
            continue
        low.setdefault(r.target, {})[r.province] = {
            "issueDate": r.issue_date, "config": int(r.A0_config), "foodProjection": round(float(r.food_projection), 2),
            "foodThreshold": round(float(r.threshold_food), 2), "gapProjection": round(float(r.gap_projection), 2),
            "gapThreshold": round(float(r.threshold_gap), 2), "pricePart": round(float(r.P_price), 4),
            "maxPricePartAnyAblation": round(float(r.max_p_price_any_ablation), 4)}
    body = {
        "schema": "aipheed.e67.disclosure/1", "experiment": "E67_Lead2_Best_Model_Objectives_1_4",
        "protocolSha256": K.verify_protocol(),
        "evidenceStatus": "development evidence only (all 50 back-test rows were examined before E67); not validated",
        "lead2Accuracy": acc_text,
        "triggerCoverage": groups,
        "lowUnderWatch": low,
        "A0ReproductionMaxAbsDiff": r1["A0_vs_E57_max_abs_diff"],
    }
    body["content_sha256"] = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_bytes(json.dumps(body, indent=1, sort_keys=True).encode("utf-8"))
    print(json.dumps(body, indent=1)[:4000])


if __name__ == "__main__":
    main()
