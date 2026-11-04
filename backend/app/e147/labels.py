"""
Split the Heat Map export: development labels (2011 to 2019) versus the sealed 2021 round, and reconcile development rounds with
the E141 panel. 2021 percentages are never printed or returned by `prepare`; only area names and the file hash are reported.

    python -m app.e147.labels prepare
"""
from __future__ import annotations

import hashlib
import json

import pandas as pd

from app.e141 import panel as P
from app.e147 import OUT, RAW
from app.hfias.panel import norm as key

CAT = {"Food Insecure Households": "insecure", "Mildly Food Insecure Households": "mild", "Moderately Food Insecure Households": "moderate",
       "Severely Food Insecure Households": "severe"}
ALIAS = {"compostella valley": "compostela valley", "davao de oro": "compostela valley", "cotabato": "north cotabato", "mountain province": "mountain",
         "tawi-tawi": "tawi tawi", "western samar": "western samar", "samar": "western samar"}
SEALED = RAW / "sealed_2021_labels.csv"
DEV = RAW / "dev_labels_2011_2019.csv"


def _load() -> pd.DataFrame:
    d = pd.DataFrame([json.loads(x) for x in open(RAW / "heatmap_provincial.jsonl", encoding="utf-8", newline="\n")])
    d["key"] = d["province_name"].str.lower().map(lambda s: ALIAS.get(s, key(s)))
    d["pct"] = pd.to_numeric(d["fs_percentage"], errors="coerce")
    return d


def prepare() -> dict:
    d = _load()
    h = d[d["fs_survey_category"] == "Food Insecure Households"]
    OUT.mkdir(parents=True, exist_ok=True)
    s = d[d["actual_year"] == "2021"]
    s[["province_name", "key", "fs_survey_category", "actual_year", "pct"]].to_csv(SEALED, index=False, lineterminator="\n")
    dv = d[~d["actual_year"].isin(["2021", "2018-2021"])]
    dv[["province_name", "key", "fs_survey_category", "actual_year", "pct"]].to_csv(DEV, index=False, lineterminator="\n")
    panel = P.outcomes()
    pk = set(panel["key"])
    a21 = sorted(s["province_name"].unique())
    in_panel = sorted(s.loc[s["key"].isin(pk), "province_name"].unique())
    # reconciliation of rounds already read: Heat Map any-level against the panel's published sources
    hd = dv[dv["fs_survey_category"] == "Food Insecure Households"]
    rec = {}
    src = {"2018": "ENNS2018", "2019": "ENNS2019", "2015": "FNRI2015", "2013": "NNS2013"}
    enns = pd.read_csv(P.DATA.parent / "hfias" / "clean" / "enns_hfias.csv")
    enns["key"] = enns["area"].map(key)
    fn15 = pd.read_csv(P.DATA.parent / "hfias" / "clean" / "fnri2015_hfias.csv")
    fn15["key"] = fn15["name"].map(key)
    fn15["insecure_pct"] = 100 - fn15["food_secure_pct"]
    for y, sv in src.items():
        g = hd[hd["actual_year"] == y]
        if y in ("2018", "2019"):
            r = enns[enns["year"] == int(y)][["key", "insecure_pct"]]
        elif y == "2015":
            r = fn15[["key", "insecure_pct"]]
        else:
            t = pd.read_csv(P.DATA / "clean" / "nns2013_hfias.csv")
            r = pd.DataFrame({"key": t["province"].map(key), "insecure_pct": t["insecure_pct"]}) if "insecure_pct" in t else None
        if r is None:
            rec[y] = {"heatmap_rows": int(len(g)), "note": "no any-level column in the local source"}
            continue
        m = g.merge(r.dropna(), on="key")
        dif = (m["pct"] - m["insecure_pct"]).abs()
        rec[y] = {"heatmap_rows": int(len(g)), "matched": int(len(m)), "exact_within_0_2": int((dif <= 0.2).sum()), "max_abs_diff": float(dif.max()) if len(m) else None,
                  "mismatches": m.loc[dif > 0.2, ["province_name", "pct", "insecure_pct"]].to_dict(orient="records")[:12]}
    dup = d.groupby(["province_name", "actual_year", "fs_survey_category"]).size()
    cal = dv[dv["key"].isin(["batangas", "cavite", "laguna", "quezon", "rizal"]) & (dv["fs_survey_category"] == "Food Insecure Households")]
    out = {"sealed_sha256": hashlib.sha256(SEALED.read_bytes()).hexdigest(), "areas_2021": a21, "areas_2021_with_panel_features": in_panel,
           "reconciliation": rec, "duplicate_category_rows": int((dup > 1).sum()), "duplicates_by_year": {str(k): int(v) for k, v in dup[dup > 1].groupby(level=1).size().items()},
           "dev_any_level_rows_by_year": hd.groupby("actual_year").size().to_dict(),
           "dev_high_share_ge60_by_year": {y: round(float((g["pct"] >= 60).mean()), 3) for y, g in hd[hd["actual_year"] != "2011"].groupby("actual_year")},
           "calabarzon_dev_any_level": cal.pivot_table(index="key", columns="actual_year", values="pct").round(1).to_dict(orient="index")}
    (OUT / "label_audit.json").write_text(json.dumps(out, indent=1, default=str), newline="\n")
    print(json.dumps(out, indent=1, default=str))
    return out


if __name__ == "__main__":
    prepare()
