"""Diagnostic after ADDENDUM_1 (reported as such): Bayes accuracy of ELEVATED for Balance Luzon as the survey margin
shrinks, with the level process estimated in ADDENDUM_1 A1.1 (random walk). Writes out/ceiling_by_margin_BL.json."""
import json
import sys

sys.argv = ["ceiling_by_margin.py"]
import run_final as RF  # noqa: E402

np = RF.np
res = json.loads((RF.OUT / "results_addendum1.json").read_text())
rng = np.random.default_rng(2026)
s = res["simulation"]["BL"]
out = {}
for moe in (6, 4, 3, 2, 1, 0.01):
    r = RF._bayes_accuracy(s["Q"], (moe / 1.959964) ** 2, 1.0, s["mu"], rng, n_series=600)
    out[str(moe)] = {k: round(v["bayes_accuracy"], 3) for k, v in r.items()}
    print("BL margin", moe, out[str(moe)])
(RF.OUT / "ceiling_by_margin_BL.json").write_text(json.dumps(out, indent=1))
