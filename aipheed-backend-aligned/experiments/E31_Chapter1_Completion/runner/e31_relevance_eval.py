"""E31 relevance validation: metrics for each candidate gate on a reviewed sample.

    python -B runner/e31_relevance_eval.py dev       # the 355-title development sample (validation/)
    python -B runner/e31_relevance_eval.py holdout   # the fresh holdout (validation/holdout/), scored ONCE

Truth: annotator label DIRECT or INDIRECT = food-insecurity related ("relevant"); DIRECT alone is also reported.
Population: province-attributed articles (strata S1-S3). Estimates are weighted by stratum (N_s / n_s) so that they
describe the whole province-attributed corpus, not the over-sampled strata; 95% intervals by a stratified bootstrap
(2,000 resamples, seed 31). Unweighted counts are reported beside them.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
EXP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXP / "runner"))
sys.path.insert(0, str(EXP / "backend_dev"))
import guard31  # noqa: E402

guard31.install()
import numpy as np  # noqa: E402

from app.news.relevance import VERSION, classify  # noqa: E402

GEO = ("S1_IN_FSSI", "S2_BELOW_THR", "S3_NO_NEXUS")


def load(folder: Path):
    key = {k["id"]: k for k in json.loads((folder / "sample_key.json").read_text())}
    sheet = {s["id"]: s for s in json.loads((folder / "annotation_sheet_blind.json").read_text(encoding="utf-8"))}
    lab = {}
    for line in (folder / "labels_annotator_claude.txt").read_text().splitlines():
        if line.strip():
            i, f, g = line.split()[:3]
            lab[i] = {"fi": f, "geo": g}
    meta = json.loads((folder / "sample_meta.json").read_text())
    nli_p = folder / "nli_relevance_scores.json"
    nli = json.loads(nli_p.read_text(encoding="utf-8"))["scores"] if nli_p.exists() else {}
    return key, sheet, lab, meta, nli


def metrics(rows, pred, truth, weights, rng=None, B=2000):
    def calc(idx):
        w = np.array([weights[rows[i]["stratum"]] for i in idx])
        p = np.array([pred(rows[i]) for i in idx], bool)
        y = np.array([truth(rows[i]) for i in idx], bool)
        tp, fp, fn = (w * (p & y)).sum(), (w * (p & ~y)).sum(), (w * (~p & y)).sum()
        prec = tp / (tp + fp) if tp + fp else float("nan")
        rec = tp / (tp + fn) if tp + fn else float("nan")
        f1 = 2 * prec * rec / (prec + rec) if prec == prec and rec == rec and prec + rec else float("nan")
        return prec, rec, f1, int((p & y).sum()), int((p & ~y).sum()), int((~p & y).sum()), int((~p & ~y).sum())
    idx = list(range(len(rows)))
    est = calc(idx)
    out = {"precision": est[0], "recall": est[1], "f1": est[2], "TP": est[3], "FP": est[4], "FN": est[5], "TN": est[6]}
    if rng is not None:
        by = {}
        for i in idx:
            by.setdefault(rows[i]["stratum"], []).append(i)
        bs = []
        for _ in range(B):
            s = [j for v in by.values() for j in rng.choice(v, len(v), replace=True)]
            bs.append(calc(s)[:3])
        bs = np.array(bs, float)
        for k, col in (("precision", 0), ("recall", 1), ("f1", 2)):
            v = bs[:, col][~np.isnan(bs[:, col])]
            out[k + "_95ci"] = [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))] if len(v) else None
    return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in out.items()}


def main(which: str):
    folder = EXP / "validation" / ("holdout" if which == "holdout" else "")
    key, sheet, lab, meta, nli = load(folder)
    pop = meta["population_by_stratum"]
    smp = meta["sample_by_stratum"]
    weights = {s: pop[s] / smp[s] for s in GEO if smp.get(s)}
    rows = []
    for i, k in key.items():
        if k["stratum"] not in GEO:
            continue
        rows.append({**k, "title": sheet[i]["title"], "fi": lab[i]["fi"], "geo": lab[i]["geo"],
                     "nli": nli.get(i), "r1": classify(sheet[i]["title"])})
    rel = lambda r: r["fi"] in ("D", "I")
    direct = lambda r: r["fi"] == "D"
    rng = np.random.default_rng(31)
    gates = {
        "E28 gate (food-nexus guard + XLM-R 10-hypothesis max >= 0.30)": lambda r: r["stratum"] == "S1_IN_FSSI",
        f"R1 rule ({VERSION})": lambda r: r["r1"] != "NONE",
    }
    if nli:
        for t in (0.5, 0.7, 0.8, 0.9, 0.95):
            gates[f"R-NLI relevance hypothesis >= {t}"] = (lambda tt: (lambda r: r["nli"] is not None and r["nli"] >= tt))(t)
    for s in (0.5, 0.7, 0.9):
        gates[f"E28 guard + XLM-R >= {s}"] = (lambda ss: (lambda r: r["stratum"] in ("S1_IN_FSSI", "S2_BELOW_THR")
                                                        and r["score"] is not None and r["score"] >= ss))(s)
    res = {"sample": which, "rule_version": VERSION, "population_by_stratum": pop, "sample_by_stratum": smp,
           "n_rows_province_attributed": len(rows), "n_relevant": sum(map(rel, rows)),
           "n_direct": sum(map(direct, rows)),
           "geography": {"YES": sum(r["geo"] == "Y" for r in rows), "NO": sum(r["geo"] == "N" for r in rows),
                         "UNCLEAR": sum(r["geo"] == "U" for r in rows)},
           "gates": {}}
    for name, g in gates.items():
        res["gates"][name] = {"relevant": metrics(rows, g, rel, weights, rng),
                              "direct_recall": metrics(rows, g, direct, weights)["recall"]}
    if which == "dev":
        for half in ("DEV", "TEST"):
            sub = [r for r in rows if r["split"] == half]
            res[f"half_{half}"] = {n: metrics(sub, g, rel, weights)["f1"] for n, g in gates.items()}
    errs = {"R1_false_positive": [r["title"] for r in rows if r["r1"] != "NONE" and not rel(r)],
            "R1_false_negative": [r["title"] for r in rows if r["r1"] == "NONE" and rel(r)]}
    out = folder / f"relevance_metrics_{which}.json"
    out.write_bytes(json.dumps({**res, "errors": errs}, indent=1, ensure_ascii=False).encode("utf-8"))
    for n, v in res["gates"].items():
        m = v["relevant"]
        print(f"{n[:62]:62s} P {m['precision']:.3f} R {m['recall']:.3f} F1 {m['f1']:.3f} "
              f"TP{m['TP']} FP{m['FP']} FN{m['FN']} directR {v['direct_recall']}")
    print(json.dumps({k: res[k] for k in ("n_rows_province_attributed", "n_relevant", "n_direct", "geography")}))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "dev")
