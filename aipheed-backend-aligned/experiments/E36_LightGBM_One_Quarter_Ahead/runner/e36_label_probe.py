import sys
sys.path.insert(0, r"C:\Users\admin\aipheed\aipheed-backend-aligned\experiments\E32_New_Model\runner")
import e32_common as C, e32_lib as L
d = L.Data()
print("S1 quarters", sorted(d.S1["quarter"].unique()))
for target in range(C.qk("2021-Q3"), C.qk("2026-Q3")+1):
    t = target-1
    try:
        tau = d.tau(t)
        labs = [d.label(p, target, t) for p in C.PROVS]
        tr = d.training_pairs(t, 1)
        print(C.qs(target), "origin", L.origin(t).date(), "tau %.2f"%tau, labs, "train", len(tr), "HIGHshare", round(tr['y'].mean(),2) if len(tr) else None, "posted", [C.qs(q) for q in d.posted_quarters(L.origin(t))][-3:])
    except Exception as e:
        print(C.qs(target), "ERR", type(e).__name__, e)
