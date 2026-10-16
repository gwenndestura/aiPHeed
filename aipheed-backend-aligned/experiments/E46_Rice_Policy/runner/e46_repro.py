"""E46 step 1: reproduce E44 I2 predictions at three origins from the code (no new model)."""
import sys
from pathlib import Path
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
E44 = HERE.parents[1] / "E44_Five_Trigger_Optimization"
sys.path.insert(0, str(E44 / "runner"))
import e44_components as P2  # noqa: E402
L, K, np, pd = P2.L, P2.K, P2.np, P2.pd
d, x = L.load(), K.load_extra()
origins = list(range(L.qi("2021-Q3"), L.qi("2026-Q3") + 1))
X, B = P2.features(d, x, origins), P2.bases(d, origins)
P = pd.read_csv(E44 / "runs" / "20261015T150213Z" / "predictions.csv", dtype={"province_code": str})
for q in ("2024-Q2", "2025-Q2", "2026-Q3"):
    t = L.qi(q)
    f = P2.forecast(d, X, B, t, n_jobs=8)
    ref = P[P["t"] == t].set_index("province_code").loc[L.PROVS, "I2_p"].to_numpy()
    print(q, "max abs diff vs E44 run 1:", float(np.max(np.abs(f["p"] - ref))))
