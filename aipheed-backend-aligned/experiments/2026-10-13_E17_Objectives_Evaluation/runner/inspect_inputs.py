"""E17 step 1: input inventory (structure, coverage, label class balance, feasible test origins by horizon).
No model is fitted and nothing is compared. Output: runs/inspect_<utc>/input_inventory.json"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "21")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard  # noqa: E402

guard.install()
import json  # noqa: E402

import numpy as np  # noqa: E402

import loaders as Ld  # noqa: E402


def main():
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = guard.EXP / "runs" / f"inspect_{ts}"
    out.mkdir(parents=True)
    hashes = guard.verify_allowlist()
    gov = Ld.load_governing()
    f = Ld.load_features(gov)
    comp = Ld.load_components()
    rounds = Ld.load_rounds()
    top = Ld.load_topics()
    pov, cen = Ld.load_lgu()
    fies = Ld.load_fies()
    feats = [c for c in f.columns if c not in ("province_code", "quarter")]
    inv = {"utc": ts, "allowlist_sha256": hashes,
           "governing": {k: gov[k] for k in ("name", "status", "target", "horizon", "timing", "decision_threshold",
                                             "algorithm", "lightgbm_params", "class_weighting")},
           "governing_model_inputs": gov["feature_set"]["model_inputs"],
           "features_fused": {"rows": int(len(f)), "quarters": [f["quarter"].min(), f["quarter"].max()],
                              "provinces": int(f["province_code"].nunique()),
                              "per_column": {c: {"nan": int(f[c].isna().sum()), "exact_zero": int((f[c] == 0).sum()),
                                                 "distinct": int(f[c].nunique())} for c in feats}}}
    # poverty: does it change only at release quarters?
    p = f.sort_values(["province_code", "quarter"])
    chg = p.groupby("province_code")["poverty_incidence"].apply(
        lambda s: [q for q, a, b in zip(p.loc[s.index, "quarter"], s.shift(1), s) if a == a and a != b])
    inv["poverty_change_quarters_by_province"] = chg.to_dict()
    # labels
    lab = comp[comp["S1"].notna()]
    inv["labels"] = {"rows": int(len(lab)), "quarters": sorted(lab["quarter"].unique().tolist(), key=Ld.qkey),
                     "median_S1_eligible": float(lab["S1"].median()),
                     "HIGH_at_14.6": int((lab["S1"] > 14.6).sum()), "HIGH_at_10.84335": int((lab["S1"] > 10.84335).sum()),
                     "S1_within_1e-3_of_14.6": int(((lab["S1"] - 14.6).abs() < 1e-3).sum()),
                     "HIGH_at_14.6_by_year": lab.assign(y=lab["quarter"].str[:4]).groupby("y")["S1"].apply(
                         lambda s: f"{int((s > 14.6).sum())}/{len(s)}").to_dict()}
    inv["sws_rounds"] = {"rows": int(len(rounds)), "definition_A": int(rounds["definition_A"].sum())}
    inv["topics"] = {"rows": int(len(top)), "quarters": [top["quarter"].min(), top["quarter"].max()],
                     "province_quarters": int(top[["province_code", "quarter"]].drop_duplicates().shape[0])}
    inv["lgu"] = {"poverty_rows": int(len(pov)), "census_rows": int(len(cen)),
                  "poverty_fallback_rows": int(pov["source_note"].str.contains("fallback", case=False, na=False).sum()),
                  "population_source": cen["population_source"].value_counts().to_dict()}
    inv["fies"] = fies.astype(object).where(fies.notna(), None).to_dict("records")
    inv["access_log"] = guard.ACCESS_LOG
    (out / "input_inventory.json").write_text(json.dumps(inv, indent=1, default=lambda o: o.item()
                                                         if isinstance(o, np.generic) else str(o)), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
