"""FIRI v2 at Lead 2 against the observed regional food-insecurity outcome R (PROTOCOL.md). Read-only on every input;
writes out/firi_l2_results.json and out/firi_l2_rows.csv. Refuses to run if PROTOCOL.md differs from its frozen hash.

    python score_firi_l2.py
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import hashlib  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import binomtest, norm  # noqa: E402
from sklearn.metrics import roc_auc_score  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
DATA = ROOT / "backend" / "data"
OUT = HERE.parent / "out"
H_LINE, THR, B, SEED = 11.3, 0.5, 5000, 2036


def frozen_ok() -> None:
    want = (HERE / "PROTOCOL_SHA256.txt").read_text().split()[0]
    assert hashlib.sha256((HERE.parent / "PROTOCOL.md").read_bytes()).hexdigest() == want, "PROTOCOL.md changed"


def qi(q: str) -> int:
    return int(q[:4]) * 4 + int(q[-1]) - 1


def qs(i: int) -> str:
    return f"{i // 4}-Q{i % 4 + 1}"


def wilson(k: int, n: int, z: float = 1.959964) -> list[float] | None:
    if not n:
        return None
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(c - h, 4), round(c + h, 4)]


def scores(y: np.ndarray, p: np.ndarray) -> dict:
    yh = (p >= THR).astype(int)
    tp, fp = int(((yh == 1) & (y == 1)).sum()), int(((yh == 1) & (y == 0)).sum())
    fn, tn = int(((yh == 0) & (y == 1)).sum()), int(((yh == 0) & (y == 0)).sum())
    rec = tp / (tp + fn) if tp + fn else None
    spec = tn / (tn + fp) if tn + fp else None
    prec = tp / (tp + fp) if tp + fp else None
    return {"n": int(len(y)), "positives": int(y.sum()), "TP": tp, "FP": fp, "FN": fn, "TN": tn,
            "accuracy": (tp + tn) / len(y), "accuracyWilson95": wilson(tp + tn, len(y)),
            "balanced": None if rec is None or spec is None else (rec + spec) / 2,
            "precision": prec, "recall": rec, "specificity": spec, "specificityWilson95": wilson(tn, tn + fp),
            "f1": 2 * prec * rec / (prec + rec) if prec and rec else 0.0,
            "auc": float(roc_auc_score(y, p)) if len(set(y)) == 2 and len(set(p)) > 1 else None,
            "brier": float(np.mean((np.clip(p, 0, 1) - y) ** 2))}


# ------------------------------------------------------------------------------------------------ inputs
def outcomes() -> tuple[pd.DataFrame, dict]:
    s = pd.read_csv(DATA / "inputs" / "sws_rounds.csv")
    s["published"] = pd.to_datetime(s["published"])
    g = s.groupby("quarter")["H"].agg(["mean", "min", "max", "size"])
    single_round_flips = [q for q, r in g.iterrows() if (r["min"] > H_LINE) != (r["max"] > H_LINE)]
    return s, {"y": {q: int(r["mean"] > H_LINE) for q, r in g.iterrows()}, "H": g["mean"].to_dict(),
               "rounds": g["size"].to_dict(), "singleRoundChoiceChangesLabel": single_round_flips}


def posted(s: pd.DataFrame, iss: str) -> dict[str, float]:
    k = s[s["published"] < pd.Timestamp(iss)]
    return k.groupby("quarter")["H"].mean().to_dict()


def history() -> pd.DataFrame:
    h = pd.read_csv(DATA / "thesis" / "firi2_history.csv", dtype={"province_code": str})
    h = h[h["kind"] == "backtest"].copy()
    h["lead"] = h["target"].map(qi) - h["origin_quarter"].map(qi)
    assert (h["lead"] == 2).all(), "firi2_history backtest rows are not all Lead 2"
    h["H1"] = [json.loads(j)["H1"]["x"] for j in h["indicators_json"]]
    return h


# ------------------------------------------------------------------------------------------------ rules
def boot(rows: pd.DataFrame, stat) -> np.ndarray:
    rng = np.random.default_rng(SEED)
    n = len(rows)
    return np.array([stat(rows.iloc[rng.integers(0, n, n)]) for _ in range(B)])


def rules(d: pd.DataFrame) -> dict:
    y, p = d["y"].to_numpy(int), d["F2"].to_numpy(float)
    s = scores(y, p)
    acc = lambda h: float(((h["F2"] >= THR).astype(int) == h["y"]).mean())  # noqa: E731
    base_acc = {b: float(((d[b] >= THR).astype(int) == d["y"]).mean()) for b in ("ALWAYS-LOW", "ALWAYS-HIGH", "PERSIST")}
    r5 = {}
    for b in ("H1", "CLIM"):
        diff = float(np.mean((d["F2"] - d["y"]) ** 2 - (d[b] - d["y"]) ** 2))
        bs = boot(d, lambda h, b=b: float(np.mean((h["F2"] - h["y"]) ** 2 - (h[b] - h["y"]) ** 2)))
        r5[b] = {"brierDiff": round(diff, 4), "p_one_sided": float(np.mean(bs >= 0))}
    q = sorted(d["q"].tolist())
    thirds = [list(t) for t in np.array_split(np.array(q), 3)]
    third_acc = [acc(d[d["q"].isin(t)]) for t in thirds]
    loqo = min(acc(d[d["q"] != x]) for x in q)
    res = {
        "R1 >=10 quarters and >=40 rows (as written)": (len(q) >= 10 and len(d) >= 40, f"{len(q)} q, {len(d)} rows"),
        "R2 accuracy >= 0.75": (s["accuracy"] >= .75, round(s["accuracy"], 4)),
        "R3 balanced accuracy >= 0.70": ((s["balanced"] or 0) >= .70, s["balanced"]),
        "R4 accuracy > always-LOW and > PERSIST (as written)": (
            s["accuracy"] > base_acc["ALWAYS-LOW"] and s["accuracy"] > base_acc["PERSIST"],
            f"{s['accuracy']:.4f} vs {base_acc['ALWAYS-LOW']:.4f} / {base_acc['PERSIST']:.4f}"),
        "R5 Brier < H1 and < CLIM, one-sided cluster p < 0.10": (
            all(v["brierDiff"] < 0 and v["p_one_sided"] < .10 for v in r5.values()), r5),
        "R6 precision >= 0.60 and recall >= 0.60": ((s["precision"] or 0) >= .6 and (s["recall"] or 0) >= .6,
                                                   f"P {s['precision']}, R {s['recall']}"),
        "R7 each third >= 0.60 and LOQO min >= 0.70": (
            min(third_acc) >= .6 and loqo >= .7,
            f"thirds {[round(x, 3) for x in third_acc]} ({[qs(t[0]) + '..' + qs(t[-1]) for t in thirds]}), "
            f"LOQO min {loqo:.3f}"),
    }
    adapted = {
        "R1-q >=10 independent quarters (adaptation)": (len(q) >= 10, f"{len(q)} q"),
        "R4-maj accuracy > ALWAYS-HIGH and > PERSIST (adaptation)": (
            s["accuracy"] > base_acc["ALWAYS-HIGH"] and s["accuracy"] > base_acc["PERSIST"],
            f"{s['accuracy']:.4f} vs {base_acc['ALWAYS-HIGH']:.4f} / {base_acc['PERSIST']:.4f}"),
    }
    fmt = lambda r: {k: {"pass": bool(v[0]), "value": v[1]} for k, v in r.items()}  # noqa: E731
    return {"scores": s, "baselineAccuracy": base_acc, "rules": fmt(res), "adapted": fmt(adapted),
            "thirds": {f"{qs(t[0])}..{qs(t[-1])}": round(a, 4) for t, a in zip(thirds, third_acc)}}


def sufficiency(d: pd.DataFrame) -> dict:
    y = d.sort_values("q")["y"].to_numpy(int)
    f = (d.sort_values("q")["F2"].to_numpy(float) >= THR).astype(int)
    pe = (d.sort_values("q")["PERSIST"].to_numpy(float) >= THR).astype(int)
    changes = int((np.diff(y) != 0).sum())
    onset_idx = [i for i in range(1, len(y)) if y[i] == 1 and y[i - 1] == 0]
    offset_idx = [i for i in range(1, len(y)) if y[i] == 0 and y[i - 1] == 1]
    b_, c_ = int(((f == y) & (pe != y)).sum()), int(((f != y) & (pe == y)).sum())
    mc = binomtest(b_, b_ + c_, 0.5, alternative="greater").pvalue if b_ + c_ else 1.0
    qq = d.sort_values("q")["q"].map(qs).tolist()
    return {
        "S1 >=3 class changes in the outcome": {"pass": changes >= 3, "value": changes},
        "S2 >=5 quarters of each class": {"pass": int(y.sum()) >= 5 and int((1 - y).sum()) >= 5,
                                          "value": f"HIGH {int(y.sum())}, LOW {int((1 - y).sum())}"},
        "S3 beats PERSIST, McNemar exact one-sided p < 0.10": {
            "pass": bool(mc < .10), "value": f"F2 right & PERSIST wrong {b_}, reverse {c_}, p {mc:.4f}"},
        "onsets (LOW->HIGH)": [{"quarter": qq[i], "F2": int(f[i]), "PERSIST": int(pe[i])} for i in onset_idx],
        "offsets (HIGH->LOW)": [{"quarter": qq[i], "F2": int(f[i]), "PERSIST": int(pe[i])} for i in offset_idx],
    }


def main():
    frozen_ok()
    s, oc = outcomes()
    h = history()
    reg = h.dropna(subset=["FIRI"]).groupby(["target", "origin_quarter", "issue_date"]).agg(
        F2=("FIRI", "mean"), provinces=("FIRI", "size"), H1=("H1", "mean"), H1_sd=("H1", "std"),
        prov_min=("FIRI", "min"), prov_max=("FIRI", "max")).reset_index()
    dropped = reg[reg["provinces"] < 5]["target"].tolist() + sorted(set(h["target"]) - set(reg["target"]))
    reg = reg[reg["provinces"] == 5].copy()
    assert (reg["H1_sd"].fillna(0) < 1e-12).all(), "H1 differs across provinces"
    reg["y"] = reg["target"].map(oc["y"])
    reg["H_obs"] = reg["target"].map(oc["H"])
    no_outcome = reg[reg["y"].isna()]["target"].tolist()
    reg = reg.dropna(subset=["y"]).copy()
    reg["q"] = reg["target"].map(qi)
    pers, clim, pers_src = [], [], []
    for iss in reg["issue_date"]:
        k = posted(s, iss)
        newest = max(k, key=qi) if k else None
        pers.append(float(k[newest] > H_LINE) if newest else np.nan)
        pers_src.append(newest)
        ys = [int(v > H_LINE) for q, v in k.items() if q >= "2021-Q1"]
        clim.append(float(np.mean(ys)) if ys else 0.5)
    reg["PERSIST"], reg["PERSIST_from"], reg["CLIM"] = pers, pers_src, clim
    reg["ALWAYS-HIGH"], reg["ALWAYS-LOW"] = 1.0, 0.0
    reg = reg.sort_values("q").reset_index(drop=True)

    ev = json.loads((DATA / "thesis" / "firi2_evaluation.json").read_text(encoding="utf-8"))
    art = ev["regional"]["2"]["candidates"][ev["selected"]]
    mine = scores(reg["y"].to_numpy(int), reg["F2"].to_numpy(float))
    repro = {"artifact": {k: art[k] for k in ("n", "positives", "accuracy", "brier", "auc_roc", "confusion")},
             "recomputed": {k: mine[k] for k in ("n", "positives", "accuracy", "brier", "auc", "TP", "FP", "FN", "TN")}}
    repro["matches"] = (art["n"] == mine["n"] and art["confusion"] == {k: mine[k] for k in ("TP", "FP", "FN", "TN")}
                        and abs(art["brier"] - mine["brier"]) < 1e-6)

    y = reg["y"].to_numpy(int)
    res = {
        "protocolSha256": (HERE / "PROTOCOL_SHA256.txt").read_text().split()[0],
        "protocolFrozenAt": (HERE / "PROTOCOL_FROZEN_AT.txt").read_text().strip(),
        "evidence": "development: these R outcomes were examined before this protocol (PROTOCOL.md section 3)",
        "outcome": {"series": "backend/data/inputs/sws_rounds.csv, mean of rounds per quarter, > 11.3",
                    "singleRoundChoiceChangesLabel": oc["singleRoundChoiceChangesLabel"]},
        "rows": {"quarters": int(len(reg)), "period": f"{reg['target'].iloc[0]}..{reg['target'].iloc[-1]}",
                 "droppedFewerThan5Provinces": dropped, "noOutcome": no_outcome,
                 "classBalance": {"HIGH": int(y.sum()), "LOW": int((1 - y).sum())}},
        "baselineReproduction": repro,
        "F2": rules(reg),
        "baselines": {b: scores(y, reg[b].to_numpy(float)) for b in ("ALWAYS-HIGH", "ALWAYS-LOW", "PERSIST", "H1", "CLIM")},
        "sufficiency": sufficiency(reg),
        "provincialSpread": {"note": "descriptive only: no provincial outcome exists",
                             "meanRange": round(float((reg["prov_max"] - reg["prov_min"]).mean()), 4),
                             "quartersWhereProvincesSplitAcross0.5": int(((reg["prov_min"] < THR) & (reg["prov_max"] >= THR)).sum())},
    }
    res["decision"] = decide(res)
    OUT.mkdir(exist_ok=True)
    (OUT / "firi_l2_results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    reg[["target", "origin_quarter", "issue_date", "F2", "prov_min", "prov_max", "H1", "PERSIST", "PERSIST_from", "CLIM",
         "H_obs", "y"]].to_csv(OUT / "firi_l2_rows.csv", index=False, lineterminator="\n", float_format="%.4f")
    report(res, reg)


def decide(res: dict) -> str:
    r = res["F2"]["rules"]
    core = all(v["pass"] for k, v in r.items() if not k.startswith("R1"))
    adapted = res["F2"]["adapted"]["R1-q >=10 independent quarters (adaptation)"]["pass"]
    suff = all(v["pass"] for k, v in res["sufficiency"].items() if k.startswith("S"))
    if core and adapted and suff:
        return "Outcome A: meets the adapted criteria on development evidence (prospective confirmation required)"
    return "Outcome C: insufficient evidence for a defensible Lead-2 forecast of overall food insecurity"


def report(res: dict, reg: pd.DataFrame) -> None:
    print("reproduction:", json.dumps(res["baselineReproduction"]))
    print(reg[["target", "issue_date", "F2", "prov_min", "prov_max", "H1", "PERSIST", "PERSIST_from", "CLIM", "H_obs",
               "y"]].round(3).to_string(index=False))
    s = res["F2"]["scores"]
    print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in s.items()})
    for name, b in res["baselines"].items():
        print(f"  {name:12s} acc {b['accuracy']:.3f} bal {b['balanced']} brier {b['brier']:.4f} "
              f"CM {b['TP']}/{b['FP']}/{b['FN']}/{b['TN']}")
    for grp in ("rules", "adapted"):
        for k, v in res["F2"][grp].items():
            print(f"  {'PASS' if v['pass'] else 'FAIL'}  {k}: {v['value']}")
    print("  thirds:", res["F2"]["thirds"])
    for k, v in res["sufficiency"].items():
        print(f"  {k}: {v}")
    print("provincial spread:", res["provincialSpread"])
    print(res["decision"])


if __name__ == "__main__":
    main()
