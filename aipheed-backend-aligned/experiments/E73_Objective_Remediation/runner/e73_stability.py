"""E73 WS4: do the model-vs-baseline comparisons hold in both sub-periods (targets <= 2024-Q4 vs >= 2025-Q1)?
FIRI v2 vs always-elevated and the hunger reading on the regional SWS outcome (E72 rows); E56 vs persistence and
majority on T43 (E70 rows and labels). Per province for E56."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP = HERE.parents[1]
sys.path.insert(0, str(EXP / "E70_Objectives_Completion" / "runner"))
import e70_metrics as MT  # noqa: E402

np, pd = MT.np, MT.pd
out = {}
R = pd.read_csv(EXP / "E72_Final_Thesis_System" / "inputs" / "firi2_regional.csv")
R = R[R["lead"] == 2].dropna(subset=["C3", "y"])
for name, g in (("<=2024-Q4", R[R["target"] <= "2024-Q4"]), (">=2025-Q1", R[R["target"] >= "2025-Q1"])):
    out[f"FIRI_regional_{name}"] = {a: {k: MT.metrics(g["y"], g[a])[k] for k in ("n", "correct", "accuracy", "balanced_accuracy", "brier")}
                                    for a in ("C3", "H1", "ALWAYS")}
P = pd.read_csv(EXP / "E70_Objectives_Completion" / "sealed" / "predictions.csv", dtype={"province_code": str})
S = json.loads((EXP / "E70_Objectives_Completion" / "out" / "score.json").read_text(encoding="utf-8"))
E63 = pd.read_csv(EXP / "E63_Lead_Time_Study" / "sealed" / "predictions.csv", dtype={"province_code": str})
lab = pd.read_csv(EXP / "E71_Food_Insecurity_Dimensions" / "out" / "labels.csv", dtype={"province_code": str})
spec = json.loads((EXP / "E40_SWS_CPI_Tiers" / "label_spec.json").read_text())["thresholds"]
lab["PS"] = ((lab["a1"] > lab["province_code"].map(spec["food"])) | (lab["gap"] > lab["province_code"].map(spec["gap"]))).astype(int)
P2 = P[P["lead"] == 2].merge(E63[E63["lead"] == 2][["origin_quarter", "province_code", "PERSIST_p", "MAJORITY_p"]],
                             on=["origin_quarter", "province_code"]).merge(lab[["province_code", "quarter", "PS"]].rename(columns={"quarter": "target"}),
                                                                           on=["province_code", "target"], how="left")
P2 = P2.dropna(subset=["PS"])          # T43 == PS on every evaluated row (E70); 2026-Q3 has no E71 label row -> dropped here
P2["y"] = P2["PS"].astype(int)
for name, g in (("<=2024-Q4", P2[P2["target"] <= "2024-Q4"]), (">=2025-Q1", P2[P2["target"] >= "2025-Q1"])):
    out[f"E56_T43_{name}"] = {a: {k: MT.metrics(g["y"], g[f"{a}_p"])[k] for k in ("n", "pos", "correct", "accuracy", "balanced_accuracy", "brier")}
                              for a in ("R0", "PERSIST", "MAJORITY")}
out["E56_by_province"] = {p: {k: MT.metrics(g["y"], g["R0_p"])[k] for k in ("n", "pos", "correct", "accuracy")} for p, g in P2.groupby("province")}
(HERE.parent / "out" / "stability.json").write_text(json.dumps(out, indent=1, default=float))
for k, v in out.items():
    print(k, {a: (m.get("correct"), m.get("n"), round(m.get("accuracy") or 0, 3), None if m.get("brier") is None else round(m["brier"], 3)) for a, m in v.items()})
