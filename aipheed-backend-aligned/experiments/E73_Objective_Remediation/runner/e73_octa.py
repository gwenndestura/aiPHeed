"""E73 WS2b (PROTOCOL section 2b): the OCTA Research Tugon ng Masa Balance Luzon involuntary-hunger series (O2), never used
before in this project, as an independent outcome for the served FIRI v2 Lead-2 estimates, FIRI v2 without its
regional-hunger domain, the latest SWS reading, the E56 price model and always-elevated. Run with cwd = backend.

O2 rounds come only from inputs/provenance.csv (each value traced to its source text). Quarter = the quarter holding
the majority of fieldwork days (DEVIATIONS 1); rounds in one quarter are averaged; a round known only as a later
article's "from X" uses the month named there.
"""
import csv
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("AIPHEED_LEAD2_MODEL", "thesis")
sys.path.insert(0, ".")
HERE = Path(__file__).resolve().parent
E73 = HERE.parent
sys.path.insert(0, str(E73.parent / "E70_Objectives_Completion" / "runner"))
import e70_metrics as MT  # noqa: E402
from scipy.stats import spearmanr  # noqa: E402

from app.ml.inference import dimensions as D  # noqa: E402
from app.ml.inference import e41_lead2 as LEAD2  # noqa: E402
from app.ml.inference import thesis_system as T  # noqa: E402

np, pd = MT.np, MT.pd
RNG = np.random.default_rng(73)
# fieldwork -> quarter, fixed from the provenance text (majority of fieldwork days)
ROUND_QUARTER = {"2023-09-30/2023-10-04": "2023-Q4", "2023-12-10/2023-12-14": "2023-Q4", "2024-03-11/2024-03-14": "2024-Q1",
                 "2024-06 (previous round, June)": "2024-Q2", "2024-08-28/2024-09-02": "2024-Q3",
                 "2024-11-10/2024-11-16": "2024-Q4", "2025-04-10/2025-04-16": "2025-Q2",
                 "2026-03 (previous round, March)": "2026-Q1", "2026-07-04/2026-07-11": "2026-Q3"}
DERIVED_SENSITIVITY = {"2025-Q3": 13.0}      # 2025-04 value 7 + "increased by six percentage points" (GMA 2025-08-12)


def o2_series():
    rounds = {}
    for r in csv.DictReader((E73 / "inputs" / "provenance.csv").open(encoding="utf-8")):
        fw = r["fieldwork"].split(" (previous round, November 2024")[0] if "November 2024" in r["fieldwork"] else r["fieldwork"]
        if fw.startswith("2024-11-10/2024-11-16"):
            fw = "2024-11-10/2024-11-16"
        rounds[fw] = float(r["value"])          # a round confirmed twice keeps one value (they agree)
    q = defaultdict(list)
    for fw, v in rounds.items():
        q[ROUND_QUARTER[fw]].append(v)
    series = {k: sum(v) / len(v) for k, v in sorted(q.items())}
    order = sorted(rounds, key=lambda fw: fw[:10])
    early = [rounds[fw] for fw in order if fw[:4] <= "2023"]
    base = early if len(early) >= 3 else [rounds[fw] for fw in order[:4]]
    return series, rounds, float(np.median(base)), ("2021-2023 rounds" if len(early) >= 3 else "first 4 rounds")


def boot_rho(a, b, B=4000):
    a, b = np.asarray(a, float), np.asarray(b, float)
    out = []
    for _ in range(B):
        i = RNG.integers(0, len(a), len(a))
        if len(set(a[i])) > 1 and len(set(b[i])) > 1:
            out.append(spearmanr(a[i], b[i])[0])
    return float(spearmanr(a, b)[0]), [float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))]


def main():
    series, rounds, thr, thr_basis = o2_series()
    rec = LEAD2.record()
    hist = list(csv.DictReader(open(T.FIRI_HISTORY, encoding="utf-8")))
    reg = {}
    for q in series:
        vals, wos, issue = [], [], None
        for code in rec["provinces"]:
            f = T.firi_for(rec, q, code)
            if f and f["firi"] is not None:
                vals.append(f["firi"])
                wos.append(D.without_outcome(f))
                issue = f.get("issueDate")
        if len(vals) == 5:
            reg[q] = {"firi": sum(vals) / 5, "firi_noH": (sum(wos) / 5) if all(w is not None for w in wos) else None,
                      "issue": issue}
    # latest SWS reading published before the FIRI issue date (approved rounds and supplementary, as served)
    sws = pd.read_csv("data/inputs/sws_rounds.csv")
    sws["published"] = pd.to_datetime(sws["published"])
    sq = sws.groupby("quarter").agg(H=("H", "mean"), pub=("published", "max"))
    e63 = pd.read_csv("../aipheed-backend-aligned/experiments/E63_Lead_Time_Study/sealed/predictions.csv")
    e56 = e63[e63["lead"] == 2].groupby("target")["E56_p"].mean().to_dict()
    rows = []
    for q, v in series.items():
        if q not in reg:
            continue
        iss = pd.Timestamp(reg[q]["issue"])
        known = sq[sq["pub"] < iss]
        h_last = float(known.loc[known.index.max(), "H"]) if len(known) else None
        rows.append({"target": q, "issue_date": reg[q]["issue"], "octa_BL": v, "y": int(v > thr),
                     "FIRI_regional": reg[q]["firi"], "FIRI_p": float(reg[q]["firi"] >= 0.5),
                     "FIRI_noH_regional": reg[q]["firi_noH"],
                     "FIRI_noH_p": None if reg[q]["firi_noH"] is None else float(reg[q]["firi_noH"] >= 0.5),
                     "SWS_last": h_last, "SWS_p": None if h_last is None else float(h_last > 11.3),
                     "E56_regional": e56.get(q), "ALWAYS_p": 1.0,
                     "SWS_concurrent": float(sq.loc[q, "H"]) if q in sq.index else None})
    R = pd.DataFrame(rows)
    out = {"threshold": thr, "threshold_basis": thr_basis, "rounds": rounds, "quarters": series, "rows": rows}
    res = {}
    for arm in ("FIRI", "FIRI_noH", "SWS", "ALWAYS"):
        g = R.dropna(subset=[f"{arm}_p"])
        m = MT.metrics(g["y"], g[f"{arm}_p"])
        b = MT.binomtest
        a_ok = (g[f"{arm}_p"] >= .5).astype(int) == g["y"]
        al_ok = g["y"] == 1
        n10, n01 = int((a_ok & ~al_ok).sum()), int((~a_ok & al_ok).sum())
        m["mcnemar_vs_always"] = {"a_only": n10, "always_only": n01,
                                  "p": float(b(n10, n10 + n01, .5).pvalue) if n10 + n01 else 1.0}
        res[arm] = {k: m[k] for k in ("n", "correct", "accuracy", "acc_wilson95", "TP", "FP", "FN", "TN", "recall_HIGH",
                                      "recall_LOW", "balanced_accuracy")} | {"mcnemar_vs_always": m["mcnemar_vs_always"]}
    out["classification"] = res
    cor = {}
    for col in ("FIRI_regional", "FIRI_noH_regional", "SWS_last", "E56_regional", "SWS_concurrent"):
        g = R.dropna(subset=[col])
        if len(g) >= 5:
            rho, ci = boot_rho(g[col], g["octa_BL"])
            cor[col] = {"n": int(len(g)), "rho": rho, "ci95": ci}
    out["spearman_vs_octa_level"] = cor
    m = res["FIRI"]
    out["goal80_independent"] = {"accuracy": m["accuracy"], "balanced": m["balanced_accuracy"],
                                 "rho_ci_lower": cor["FIRI_regional"]["ci95"][0],
                                 "supported": bool(m["accuracy"] >= 0.80 and (m["balanced_accuracy"] or 0) >= 0.70
                                                   and cor["FIRI_regional"]["ci95"][0] > 0)}
    # sensitivity: add the derived 2025-Q3 value
    out["sensitivity_derived_2025Q3"] = DERIVED_SENSITIVITY
    (E73 / "out").mkdir(exist_ok=True)
    (E73 / "out" / "octa_validation.json").write_text(json.dumps(out, indent=1, default=float))
    print(R[["target", "issue_date", "octa_BL", "y", "FIRI_regional", "FIRI_noH_regional", "SWS_last", "SWS_concurrent", "E56_regional"]].round(3).to_string())
    print("threshold", thr, thr_basis)
    for k, v in res.items():
        print(k, v["correct"], "/", v["n"], round(v["accuracy"], 3), "bal", v["balanced_accuracy"], "McNemar vs always", v["mcnemar_vs_always"])
    print(json.dumps(cor, indent=1))
    print(out["goal80_independent"])


if __name__ == "__main__":
    main()
