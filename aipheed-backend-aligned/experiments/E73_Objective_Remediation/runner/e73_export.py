"""Condense the E73 results into backend/data/thesis/e73_summary.json (read by the thesis text fields)."""
import json
from pathlib import Path

E73 = Path(__file__).resolve().parents[1]
o = json.loads((E73 / "out" / "octa_validation.json").read_text())
n = json.loads((E73 / "out" / "news_validation.json").read_text())
w = json.loads((E73 / "out" / "lgu_weight_sensitivity.json").read_text())
c = o["classification"]
out = {"date": "2026-10-20", "experiment": "E73_Objective_Remediation",
       "octa": {"quarters": c["FIRI"]["n"], "firi_correct": c["FIRI"]["correct"], "firi_accuracy": c["FIRI"]["accuracy"],
                "firi_balanced": c["FIRI"]["balanced_accuracy"], "sws_correct": c["SWS"]["correct"],
                "always_correct": c["ALWAYS"]["correct"], "firi_noH_correct": c["FIRI_noH"]["correct"],
                "rho_firi": o["spearman_vs_octa_level"]["FIRI_regional"]["rho"],
                "rho_firi_ci": o["spearman_vs_octa_level"]["FIRI_regional"]["ci95"],
                "rho_firi_noH": o["spearman_vs_octa_level"]["FIRI_noH_regional"]["rho"],
                "threshold": o["threshold"], "goal80_supported": o["goal80_independent"]["supported"]},
       "news": {"climate_rho": n["1a"]["climate_vs_typhoons"]["rho"], "climate_ci": n["1a"]["climate_vs_typhoons"]["ci95"],
                "market_rho": n["1a"]["market_vs_food_cpi"]["rho"], "fish_rho": n["1a"]["fish_kill_vs_fish_drop"]["rho"],
                "bias_correction_validated": n["1b"]["served_validated"], "regional_news_pass": n["1e"]["pass"]},
       "lgu_weights": {"robust": w["robust"], "min_rho": {k: v["min_spearman"] for k, v in w["alternatives"].items()}}}
p = E73.parents[2] / "backend" / "data" / "thesis" / "e73_summary.json"
p.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
print(json.dumps(out["octa"]))
