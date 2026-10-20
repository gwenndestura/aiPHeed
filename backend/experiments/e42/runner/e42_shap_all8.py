"""Supplement: mean |SHAP| per driver over the evaluation set for the two arms that carry all 8 driver features
(E42-fixed, E42-nested), from the configurations the run chose (E42_results.json). Adds `mean_abs_shap_eval_all8`."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e42_lib as L  # noqa: E402
import e42_run as R  # noqa: E402

L.register_pools()
res_path = L.E42 / "E42_results.json"
res = json.loads(res_path.read_text(encoding="utf-8"))
d = L.Data()
out = {}
for arm in ("E42-fixed", "E42-nested"):
    rows = []
    for q, chosen in res["selection_path"][arm].items():
        fs, g = chosen.split("x")
        _, c, _ = R.shap_rows(d, L.qk(q) - 1, fs, g)
        if c is not None:
            rows.append(R.group_abs(c))
    a = L.pd.concat(rows)
    out[arm] = {"rows": int(len(a)), **{k: float(a[k].mean()) for k in a.columns},
                "share_pct": {k: float(a[k].sum() / a.to_numpy().sum() * 100) for k in a.columns}}
res["mean_abs_shap_eval_all8"] = out
L.C.write_json(res_path, L.C.clean(res))
for k, v in out.items():
    print(k, {g: round(x, 4) for g, x in v.items() if g not in ("rows", "share_pct")}, {g: round(x, 1) for g, x in v["share_pct"].items()})
