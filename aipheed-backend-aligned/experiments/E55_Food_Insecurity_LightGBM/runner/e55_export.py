"""E55 step 1 (no E32 guard): export the T43 labels (all SWS rounds; approved-only variant; PS) and the as-of T43
persistence values, so the guarded E38 baseline code can use them without reading the production data tree.

    backend/venv/Scripts/python.exe -B runner/e55_export.py  -> data/labels_t43.csv, data/persistence_t43.csv
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e55_lib as F  # noqa: E402

L, pd = F.L, F.pd
d = F.L.load()
Y = F.t43_labels(d)
assert Y["q"].min() >= L.FIRST_Q
cols = ["province_code", "q", "quarter", "F", "HL", "H_all", "H_app", "PS", "T43", "T43_approved"]
Y[cols].sort_values(["q", "province_code"]).to_csv(F.E55 / "data" / "labels_t43.csv", index=False)
rows = []
for t in range(L.qi("2021-Q3"), L.qi("2026-Q3") + 1):
    last = F.t43_last(d, t)
    for p in L.PROVS:
        v, q = last[p]
        rows.append({"t": t, "province_code": p, "T43_last": v, "T43_last_quarter": None if q is None else L.qs(q)})
pd.DataFrame(rows).to_csv(F.E55 / "data" / "persistence_t43.csv", index=False)
print(len(Y), "label rows;", len(rows), "persistence rows")
