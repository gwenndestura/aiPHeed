"""E13 step 1: describe the allowlisted inputs (structure, coverage, outcome-audit values).
No model, baseline or comparison is computed here. Output: runs/inspect_<utc>/input_inventory.json"""
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

import pandas as pd  # noqa: E402

import loaders  # noqa: E402


def main():
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = guard.EXP / "runs" / f"inspect_{ts}"
    out.mkdir(parents=True)
    hashes = guard.verify_allowlist()
    comp = loaders.load_components()
    det = loaders.load_details()
    rounds = loaders.load_rounds(det)
    ext = loaders.load_external()

    inv = {"utc": ts, "allowlist_sha256": hashes}
    inv["components"] = {
        "rows": int(len(comp)), "columns": list(comp.columns),
        "quarters": [comp["quarter"].min(), comp["quarter"].max()], "n_quarters": int(comp["quarter"].nunique()),
        "provinces": sorted(comp["province"].unique().tolist()),
        "non_missing": {c: int(comp[c].notna().sum()) for c in ["F", "mean5", "D", "H", "S1"]},
        "quarters_with_H": sorted(comp.loc[comp["H"].notna(), "quarter"].unique().tolist()),
        "quarters_complete_five_F": int(comp.groupby("quarter")["F"].apply(lambda s: s.notna().sum() == 5).sum()),
    }
    inv["regional_rounds"] = {
        "rows": int(len(rounds)), "quarters": sorted(rounds["quarter"].unique().tolist()),
        "first_published": str(rounds["published"].min().date()), "last_published": str(rounds["published"].max().date()),
        "date_type_counts": rounds["date_type"].value_counts().to_dict(),
        "definition_A_counts": rounds["definition_A"].value_counts().to_dict(),
        "source_counts": rounds["source"].value_counts().to_dict(),
        "regional_scope": det["two_layer"]["regional_scope"],
    }
    inv["details_keys_used"] = ["two_layer.regional_layer_rounds", "two_layer.regional_scope", "tau0_recorded",
                                "tau0_full_precision", "tau0_quarters"]
    inv["tau0"] = {"recorded": det["tau0_recorded"], "full_precision": det["tau0_full_precision"],
                   "quarters": det["tau0_quarters"]}
    f = ext["fies"]
    inv["nns_fies"] = {"rows": int(len(f)), "records": f.astype(object).where(f.notna(), None).to_dict("records")}
    s = ext["subsistence"]
    inv["psa_subsistence_2021_2023"] = {"rows": int(len(s)),
                                        "records": s.astype(object).where(s.notna(), None).to_dict("records")}
    lg = ext["lgu_poverty"]
    inv["lgu_poverty"] = {"rows": int(len(lg)), "years": sorted(lg["year"].unique().tolist()),
                          "per_province": lg.groupby("province_name")["poverty_incidence_pct"].agg(
                              ["count", "median", "min", "max"]).round(2).reset_index().to_dict("records"),
                          "distinct_values_per_province": lg.groupby("province_name")["poverty_incidence_pct"].nunique().to_dict(),
                          "source_note_examples": lg["source_note"].dropna().unique().tolist()[:3]}
    inv["access_log"] = guard.ACCESS_LOG
    with open(out / "input_inventory.json", "w", encoding="utf-8") as fh:
        json.dump(inv, fh, indent=1, default=str)
    print(out)


if __name__ == "__main__":
    main()
