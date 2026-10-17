"""E51 step 1 (no E32 guard): export the CPI-based labels (T43, PS) with their as-of persistence values, so the guarded
E38 code can use them without reading the production data tree.

    backend/venv/Scripts/python.exe -B runner/e51_export.py  -> data/labels_cpi.csv, data/persistence_cpi.csv
"""
import sys
from pathlib import Path

E51 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(E51.parent / "E43_Five_Trigger_Risk" / "runner"))
import e43_lib as K  # noqa: E402

L, pd = K.L, K.pd
d = L.load()
th = L.e40_spec()
F, HL = L.quarter_F(d), L.quarter_F(d, "all_items").rename(columns={"F": "HL"})
Y = F.merge(HL, on=["province_code", "q"])
Y["PS"] = ((Y["F"] > Y["province_code"].map(th["food"])) | ((Y["F"] - Y["HL"]) > Y["province_code"].map(th["gap"]))).astype(int)
t43 = K.label_frame(d)[["province_code", "q", "y"]].rename(columns={"y": "T43"})
lab = Y[["province_code", "q", "PS"]].merge(t43, on=["province_code", "q"], how="left")
lab.assign(quarter=lab["q"].map(L.qs)).to_csv(E51 / "data" / "labels_cpi.csv", index=False)
rows = []
for t in range(L.qi("2021-Q3"), L.qi("2026-Q3") + 1):
    a = K.available_labels(d, t)                                 # T43: SWS posted before O(t), q <= t-1
    c = L.quarter_F(d.cut(t))                                    # PS: CPI quarters complete before O(t)
    cq = set(zip(c["province_code"], c["q"]))
    for p in L.PROVS:
        g = a[a["province_code"] == p].sort_values("q")
        ps = Y[(Y["province_code"] == p) & (Y["q"] <= t - 1)].sort_values("q")
        ps = ps[[(p, q) in cq for q in ps["q"]]]
        rows.append({"t": t, "province_code": p,
                     "T43_last": int(g["y"].iloc[-1]) if len(g) else None,
                     "PS_last": int(ps["PS"].iloc[-1]) if len(ps) else None,
                     "PS_last_quarter": L.qs(int(ps["q"].iloc[-1])) if len(ps) else None})
pd.DataFrame(rows).to_csv(E51 / "data" / "persistence_cpi.csv", index=False)
print(len(lab), "label rows;", len(rows), "persistence rows")
