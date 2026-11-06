"""
Maximum reliable lead for every model, by the fixed E156 rule (docs/e156/LEAD_RELIABILITY_CRITERIA.md):
a lead counts only if it and every shorter lead pass C1-C6. Reads saved out-of-sample forecasts; fits nothing.
If a model passes every lead it was evaluated at, its maximum is reported as "at least" that lead and the
longer leads must be run before a maximum can be stated.

    python -m app.e156.max_lead_all -> data/e156/out/max_lead_all.json
"""
from __future__ import annotations

import json
import warnings

import pandas as pd

from app.e156 import leads as LD
from app.paths import BACKEND_DIR

warnings.filterwarnings("ignore")
D = BACKEND_DIR / "data"
K = ["key", "survey", "lead"]


def frames():
    e158 = pd.read_csv(D / "e158" / "out" / "oof.csv")
    e164 = pd.read_csv(D / "e164" / "out" / "oof.csv")
    out = {"E158": (e158, "E158"), "E164_AUTO (withdrawn)": (e164, "AUTO")}
    for name, path, arm in (("E165_AUTO_FINAL", D / "e165" / "out" / "all_rows.csv", "FINAL"), ("E166", D / "e166" / "out" / "all_rows.csv", "E166"), ("E167", D / "e167" / "out" / "all_rows.csv", "E167")):
        if not path.exists():
            continue
        a = pd.read_csv(path)
        a = a[a["mode"] == "main"][K + ["mu", "p", "half"]].rename(columns={"mu": f"mu_{arm}", "p": arm, "half": f"half_{arm}"})
        out[name] = (e164.merge(a, on=K), arm)
    return out


def main():
    res = {}
    for name, (F, arm) in frames().items():
        F = F[F[arm].notna()]
        r = LD.evaluate(F, arm, name)
        leads = [x["lead"] for x in r["leads"]]
        passed_all = all(x["reliable"] for x in r["leads"])
        res[name] = {"leads_evaluated": leads, "maximum_reliable_lead": r["maximum_reliable_lead"], "first_failing_lead": r["first_failing_lead"],
                     "statement": (f"at least {max(leads)}; evaluate longer leads" if passed_all else f"{r['maximum_reliable_lead']}"),
                     "per_lead": {x["lead"]: {"accuracy": x["accuracy"], "failed": [c for c, v in x["criteria"].items() if not v]} for x in r["leads"]}}
    (D / "e156" / "out" / "max_lead_all.json").write_text(json.dumps(res, indent=1, default=str), newline="\n")
    for k, v in res.items():
        print(k, "| max reliable lead:", v["statement"], "| first failing:", v["first_failing_lead"])
        print("   ", {l: (p["accuracy"], p["failed"]) for l, p in v["per_lead"].items()})


if __name__ == "__main__":
    main()
