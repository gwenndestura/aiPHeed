"""E36 diagnostics for the report (descriptive; no selection, no tuning): what the served model relies on and whether
its development score depends on a few quarters.

    python -B runner/e36_diagnostics.py runs/<primary run>   -> runs/e36_diagnostics.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e36_lib as L  # noqa: E402

C, np, pd = L.C, L.np, L.pd


def main(run_dir: str):
    run = Path(run_dir).resolve()
    b = json.loads((L.E36 / "frozen" / "E36_SERVING_BUNDLE.json").read_text(encoding="utf-8"))
    Pr = pd.read_csv(run / "predictions.csv", dtype={"province_code": str})
    out = {}

    def shares(rows):
        tot = {"government": 0.0, "news": 0.0}
        feat = {}
        for v in rows:
            for d in v["drivers"]:
                a = abs(d["contribution"])
                tot[d["source"]] += a
                feat[d["key"]] = feat.get(d["key"], 0.0) + a
        s = sum(tot.values())
        return {"by_source": {k: round(x / s, 4) for k, x in tot.items()},
                "by_feature": {k: round(x / s, 4) for k, x in sorted(feat.items(), key=lambda kv: -kv[1])}}

    out["shap_share_forecast_2026Q4"] = shares(b["forecast"]["provinces"].values())
    out["shap_share_all_backtests"] = shares([v for q in b["backtests"] for v in q["provinces"].values()])
    out["gain_importance_operational"] = b["model"]["gain_importance"]

    e = Pr[Pr["arm"] == "E36-LGBM"].copy()
    e["tq"] = e["target_quarter"].map(C.qk)
    e["ok"] = ((e["p"] >= .5).astype(int) == e["y"])
    out["time_trend"] = {
        "spearman_p_vs_date": float(e["p"].rank().corr(e["tq"].rank())),
        "spearman_y_vs_date": float(e["y"].rank().corr(e["tq"].rank())),
        "note": "p rising with time together with the label base rate; read with the y trend, not alone"}
    per_q = e.groupby("target_quarter").agg(correct=("ok", "sum"), n=("ok", "size"), HIGH=("y", "sum"))
    out["per_quarter_correct"] = per_q.astype(int).to_dict(orient="index")
    # leave-one-quarter-out sensitivity of the accuracy (how much any single quarter moves it)
    acc = {q: float(e[e["target_quarter"] != q]["ok"].mean()) for q in per_q.index}
    out["leave_one_quarter_out_accuracy"] = {"min": min(acc.values()), "max": max(acc.values()), "by_quarter": acc}
    # does the model only repeat the last label? agreement with persistence
    pers = Pr[Pr["arm"] == "B1_PERSISTENCE"].set_index(["target_quarter", "province_code"])["p"]
    e2 = e.set_index(["target_quarter", "province_code"])
    agree = ((e2["p"] >= .5).astype(int) == pers.loc[e2.index].astype(int))
    out["agreement_with_persistence"] = {"share": float(agree.mean()), "n": int(len(agree)),
                                         "model_right_when_disagree": int(((~agree) & e2["ok"]).sum()),
                                         "persistence_right_when_disagree": int(((~agree) & ~e2["ok"]).sum())}
    out["selection_path"] = {q: s["chosen"] for q, s in json.loads((run / "results.json").read_text(
        encoding="utf-8"))["selections"]["E36-LGBM"].items()}
    C.write_json(L.E36 / "runs" / "e36_diagnostics.json", C.clean(out))
    print(json.dumps({k: out[k] for k in ("shap_share_forecast_2026Q4", "shap_share_all_backtests", "time_trend",
                                          "agreement_with_persistence")}, indent=1)[:2500])
    print("LOQO accuracy range", out["leave_one_quarter_out_accuracy"]["min"], out["leave_one_quarter_out_accuracy"]["max"])


if __name__ == "__main__":
    main(sys.argv[1])
