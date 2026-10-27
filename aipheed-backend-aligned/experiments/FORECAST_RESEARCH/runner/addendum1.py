"""Addendum 1 (ADDENDUM_1_LGBM_FROM_PROJECTION.md): P4 (unified LightGBM boosted from the structural projection) x
the hunger term of schedules A and B.   python addendum1.py   -> out/results_addendum1.json"""
import json

import numpy as np
import pandas as pd

import fr_lib as F
import metrics as M

KEY = ["t", "lead", "province_code"]


def main():
    F.check_protocol()
    assert F.sha256(F.FR / "ADDENDUM_1_LGBM_FROM_PROJECTION.md") == (F.HERE / "ADDENDUM_1_SHA256.txt").read_text().strip()
    E = pd.read_csv(F.OUT / "predictions.csv", dtype={"province_code": str})
    A = pd.read_csv(F.EXP / "FINAL_ARCHITECTURE" / "out" / "predictions.csv", dtype={"province_code": str})
    E = E.merge(A[KEY + ["P4_price"]], on=KEY, how="left")
    assert E["P4_price"].notna().all()
    base = json.loads((F.OUT / "results.json").read_text())
    res = {"addendum_sha256": F.sha256(F.FR / "ADDENDUM_1_LGBM_FROM_PROJECTION.md"), "arms": {}, "decision": {}}
    for sch in ("A", "B"):
        E[f"P4{sch}_p"] = E[f"pi_H_{sch}"] * E["P4_price"]
        chosen = base["selection"][sch]["chosen"]
        dec = {}
        for k, g in E.groupby("lead"):
            d = F.evaluate(g, f"P4{sch}_p", f"PERSIST_{sch}")
            d["dev"] = M.cls(g.loc[g["q"] <= F.DEV_LAST, "y"], g.loc[g["q"] <= F.DEV_LAST, f"P4{sch}_p"])
            d["conf"] = M.cls(g.loc[g["q"] > F.DEV_LAST, "y"], g.loc[g["q"] > F.DEV_LAST, f"P4{sch}_p"])
            d["price_term"] = M.cls(g["price"], g["P4_price"])
            d["vs_selected"] = M.boot_diff(g["q"], (g[f"P4{sch}_p"] - g["y"]) ** 2, (g[f"{chosen}{sch}_p"] - g["y"]) ** 2)
            d["vs_served_P0H4"] = M.boot_diff(g["q"], (g[f"P4{sch}_p"] - g["y"]) ** 2, (g["P0H4_p3"] - g["y"]) ** 2)
            d["calibration"] = M.calibration(g["y"], g[f"P4{sch}_p"])
            dec[int(k)] = d
        dev = float(np.mean([dec[k]["dev"]["brier"] for k in (1, 2, 3)]))
        sel_dev = base["arms"][f"{chosen}{sch}"]["dev_brier_L1_3"]
        ok = dev - sel_dev <= 0.002 and not (dec[1]["vs_selected"]["diff"] > 0 and dec[1]["vs_selected"]["p_two"] < 0.10)
        res["arms"][f"P4{sch}"] = {"leads": dec, "dev_brier_L1_3": dev, "max_reliable_lead": F.max_reliable(dec)}
        res["decision"][sch] = {"selected_structural": chosen, "selected_dev": sel_dev, "P4_dev": dev,
                                "P4_is_thesis_candidate": bool(ok)}
        print(f"P4{sch} dev {dev:.4f} (selected {chosen} {sel_dev:.4f}) candidate {ok} maxrel {F.max_reliable(dec)} |",
              " | ".join(f"L{k} acc {d['metrics']['accuracy']:.3f} bal {d['metrics']['balanced_accuracy']:.3f} "
                         f"P {d['metrics']['precision']:.2f} R {d['metrics']['recall']:.2f} Br {d['metrics']['brier']:.3f} "
                         f"vsSel {d['vs_selected']['diff']:+.3f} p{d['vs_selected']['p_two']:.2f} fail {d['failed']}"
                         for k, d in dec.items()))
    E.to_csv(F.OUT / "predictions_addendum1.csv", index=False, lineterminator="\n", float_format="%.6g")
    (F.OUT / "results_addendum1.json").write_text(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main()
