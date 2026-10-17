"""E49 step 1 (no E32 guard): export the T43 labels and the as-of T43 persistence values so the guarded E38 code can
use them without reading the production data tree.

    backend/venv/Scripts/python.exe -B runner/e49_export_t43.py  -> data/t43_labels.csv, data/t43_persistence.csv
"""
import sys
from pathlib import Path

E49 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(E49.parent / "E43_Five_Trigger_Risk" / "runner"))
import e43_lib as K  # noqa: E402

L, pd = K.L, K.pd
d = L.load()
lab = K.label_frame(d)[["province_code", "q", "y"]]
(E49 / "data").mkdir(exist_ok=True)
lab.assign(quarter=lab["q"].map(L.qs)).to_csv(E49 / "data" / "t43_labels.csv", index=False)
rows = []
for t in range(L.qi("2021-Q3"), L.qi("2026-Q3") + 1):
    a = K.available_labels(d, t)
    for p in L.PROVS:
        g = a[a["province_code"] == p].sort_values("q")
        rows.append({"t": t, "origin_quarter": L.qs(t), "province_code": p,
                     "y_last_t43": int(g["y"].iloc[-1]) if len(g) else None,
                     "last_label_quarter": L.qs(int(g["q"].iloc[-1])) if len(g) else None})
pd.DataFrame(rows).to_csv(E49 / "data" / "t43_persistence.csv", index=False)
print(len(lab), "labels;", len(rows), "persistence rows")
