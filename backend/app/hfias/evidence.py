"""Release-gate evidence for the HFIAS candidate, derived from data/hfias/out/study_insecure.json (locked protocol)."""
from __future__ import annotations

import json

from app.hfias import OUT, VERSION
from app.hfias import panel as P

FAMILY_OF = {"rice_cpi_change": "A3", "food_cpi_change": "A1", "fish_cpi_change": "A2", "palay_corn_change": "C3",
             "fisheries_change": "C4", "poverty_2015": "V1", "subsistence_2015": "V1", "sws_change": "H1"}
GROUP_OF = {"A1": "market", "A2": "market", "A3": "market", "C3": "climate", "C4": "climate", "V1": "poverty"}


def build() -> dict:
    r = json.loads((OUT / "study_insecure.json").read_text())
    sel = r["selection"]["selected"]
    l1 = r["leads"]["1"]
    m = l1["primary"][sel]
    base = {n: v for n, v in l1["primary"].items() if n.startswith("B")}
    uses_features = sel.startswith("M")
    fams = sorted({FAMILY_OF[f] for f in P.FAMILIES if f in FAMILY_OF}) if uses_features else []
    passed_leads = [int(k) for k, v in r["leads"].items() if v["selected_checks"]["passed"]]
    abl = l1.get("ablation") or {}
    contrib = {g: {"tested_out_of_sample": g in (abl.get("drop") or {}), "mae_change_when_dropped_pp": (abl.get("drop") or {}).get(g)}
               for g in ("market", "climate", "poverty")}
    contrib["employment"] = {"tested_out_of_sample": False, "why": "no provincial employment series for 2015-2019 on file nationwide"}
    contrib["news"] = {"tested_out_of_sample": False, "why": "news corpus covers CALABARZON only; no nationwide provincial news series"}
    return {
        "model_id": VERSION, "artifact_loads": (OUT / "study_insecure.json").exists(), "artifact_path": "data/hfias/out/study_insecure.json",
        "target": {"construct": "HFIAS: share of households food insecure (any level), province, FNRI ENNS round",
                   "is_food_insecurity_measurement": True, "served_resolution": "province", "served_frequency": "survey round"},
        "families_used": fams + (["H1"] if uses_features else []),
        "groups_used": sorted({GROUP_OF[f] for f in fams if f in GROUP_OF}),
        "n1_version": None,
        "chronological": {"design": "train ENNS 2018 provinces, test ENNS 2019 provinces (later, different provinces)",
                          "n_targets": m["n"], "n_high": m["n_high"],
                          "metrics": {"accuracy": m["accuracy"], "balanced_accuracy": m["balanced_accuracy"] or 0,
                                      "high_recall": m["high_recall"] or 0, "high_precision": m["high_precision"] or 0},
                          "baselines": {"model_brier": m["brier"], "baseline_brier": {k: v["brier"] for k, v in base.items()},
                                        "model_mae_pp": m["mae_pp"], "baseline_mae_pp": {k: v["mae_pp"] for k, v in base.items()}}},
        "independent": {"applicable": True, "passed": l1["selected_checks"]["passed"],
                        "what": "held-out ENNS 2019 provinces, FNRI-published HFIAS values", "n": m["n"]},
        "calibration": {"interval_nominal": 0.90, "interval_coverage": m["coverage90"], "ece": m["ece"]},
        "geographic": {"passed_at_served_resolution": bool(l1["selected_checks"]["checks"]["mae"]),
                       "island_cv_pooled_mae_pp": l1["secondary_island_cv"]["pooled_mae_pp"]},
        "horizon": {"validated_leads": passed_leads,
                    "note": "Lead k = issue k quarters before Q1 of the survey year; the outcome is a survey round, not a quarter."},
        "group_contribution": contrib,
        "documents": ["docs/hfias/METHODOLOGY_AND_RESULTS.md"],
    }
