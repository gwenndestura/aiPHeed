"""Condense the E72 audit and the E71 validation into backend/data/thesis/e72_summary.json (read by the thesis text)."""
import json
from pathlib import Path

E72 = Path(__file__).resolve().parents[1]
EXP = E72.parent
reg = json.loads((E72 / "out" / "regional_outcome.json").read_text())["2"]
dim = json.loads((E72 / "out" / "firi_dimensions.json").read_text())["summary"]
e71 = json.loads((EXP / "E71_Food_Insecurity_Dimensions" / "out" / "score.json").read_text(encoding="utf-8"))
m = reg["metrics"]
out = {"date": "2026-10-20", "experiment": "E72_Final_Thesis_System",
       "regional_lead2": {"correct": m["C3"]["correct"], "n": m["C3"]["n"], "accuracy": m["C3"]["accuracy"],
                          "wilson": m["C3"]["acc_wilson95"], "always_correct": m["ALWAYS"]["correct"],
                          "h1_correct": m["H1"]["correct"], "mcnemar_p_always": reg["C3_vs"]["ALWAYS"]["mcnemar_p"],
                          "mcnemar_p_h1": reg["C3_vs"]["H1"]["mcnemar_p"], "brier_diff_vs_h1": reg["C3_vs"]["H1"]["brier_diff"],
                          "brier_ci_vs_h1": reg["C3_vs"]["H1"]["ci95"], "targets": reg["targets"],
                          "evidence": "development quarters; regional (one value per quarter); not unseen"},
       "firi_dimensions": dim["mean_abs_share"], "firi_HIGH_rows": dim["HIGH"], "firi_rows": dim["rows"],
       "firi_HIGH_low_without_outcome": dim["HIGH_rows_low_without_outcome"],
       "firi_reconstruction_error": dim["max_reconstruction_error"],
       "e71_rho": e71["V1"]["rho_FIR71_H"], "e71_ci": e71["V1"]["ci95"], "e71_supported": e71["V1"]["supported"]}
p = E72.parents[2] / "backend" / "data" / "thesis" / "e72_summary.json"
p.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
print(p, json.dumps(out["regional_lead2"]))
