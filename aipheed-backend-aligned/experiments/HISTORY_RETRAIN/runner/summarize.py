"""Tables for RESULTS.md from out/results.json (no new computation of forecasts; seed aggregation per Amendment 1).

    python summarize.py > ../out/summary.md
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import json
import re

import numpy as np

import hr_lib as H

R = json.loads((H.OUT / "results.json").read_text())
MET = [("accuracy", "acc"), ("balanced", "bal"), ("precision", "prec"), ("recall", "rec"), ("auc", "AUC"),
       ("brier", "Brier")]
RULES = ["R1", "R2", "R3", "R4", "R5", "R6", "R7"]


def f(x, n=3):
    return "–" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.{n}f}"


def rules_str(r):
    return " ".join(f"{k}{'✓' if r[[x for x in r if x.startswith(k)][0]]['pass'] else '✗'}" for k in RULES)


def classic_rows(w):
    out = []
    for n in ("PERSIST", "LOGIT_b", "LGBM_b", "LOGIT_c", "LGBM_c", "CLIM", "ALWAYS-HIGH_p", "ALWAYS-LOW_p"):
        r = w["models"].get(n)
        if r is None or "metrics" not in r:
            continue
        m = r["metrics"]
        bv = r.get("brierVs", {})
        out.append(f"| {n.replace('_p', '')} | " + " | ".join(f(m.get(k)) for k, _ in MET) +
                   f" | {m['TP']}/{m['FP']}/{m['FN']}/{m['TN']} | " + (rules_str(r["rules"]) if "rules" in r else "") +
                   " | " + " / ".join(f"{f(v['brierDiff'], 4)} (p {f(v['p_one_sided'], 3)})" for v in bv.values()) +
                   f" | **{'RELIABLE' if r.get('reliable') else 'no'}** |")
    return out


def dl_groups(w):
    g = {}
    for n, r in w["models"].items():
        mm = re.match(r"^(MLP|GRU)_s(\d+)_(b|c)$", n)
        if mm and "metrics" in r:
            g.setdefault(f"{mm.group(1)}_{mm.group(3)}", []).append(r)
    return g


def dl_rows(w):
    out = []
    for name, rs in sorted(dl_groups(w).items()):
        cells = []
        for k, _ in MET:
            v = np.array([r["metrics"].get(k) if r["metrics"].get(k) is not None else np.nan for r in rs], float)
            cells.append(f"{f(np.nanmean(v))} ± {f(np.nanstd(v), 3)} [{f(np.nanmin(v))}, {f(np.nanmax(v))}]")
        rp = " ".join(f"{k}:{sum(r['rules'][[x for x in r['rules'] if x.startswith(k)][0]]['pass'] for r in rs)}"
                      for k in RULES)
        nrel = sum(r["reliable"] for r in rs)
        verdict = "RELIABLE" if nrel == len(rs) == 10 else (f"unstable {nrel}/10" if nrel else "no")
        out.append(f"| {name} (n seeds {len(rs)}) | " + " | ".join(cells) + f" | {rp} | {nrel}/{len(rs)} | **{verdict}** |")
    return out


def beats(w):
    """Amendment 1 section 3: DL beats X iff seed-mean Brier < X Brier and >= 8/10 seeds have lower Brier."""
    out = []
    for name, rs in sorted(dl_groups(w).items()):
        kind, opt = name.split("_")
        b = np.array([r["metrics"]["brier"] for r in rs])
        a = np.array([r["metrics"]["accuracy"] for r in rs])
        for x in (f"LGBM_{opt}", f"LOGIT_{opt}", "PERSIST"):
            if x not in w["models"] or "metrics" not in w["models"][x]:
                continue
            xb, xa = w["models"][x]["metrics"]["brier"], w["models"][x]["metrics"]["accuracy"]
            k = int((b < xb).sum())
            out.append(f"| {name} vs {x} | {f(b.mean(), 4)} vs {f(xb, 4)} | {f(a.mean())} vs {f(xa)} | {k}/{len(rs)} | "
                       f"**{'beats' if b.mean() < xb and k >= 8 else 'does not beat'}** |")
    return out


def main():
    hdr = ("| model | acc | bal | prec | rec | AUC | Brier | TP/FP/FN/TN | R1–R7 | Brier diff vs ALWAYS-HIGH / "
           "persistence (p) | verdict |\n|---|---|---|---|---|---|---|---|---|---|---|")
    dhdr = ("| model | acc mean ± sd [min, max] | bal | prec | rec | AUC | Brier | seeds passing each rule | reliable "
            "seeds | verdict |\n|---|---|---|---|---|---|---|---|---|---|")
    for key, w in R["windows"].items():
        print(f"\n### {key}  ({w['period']}, {w['n_rows']} rows, {w['n_quarters']} quarters, HIGH share "
              f"{f(w['high_share'])})\n")
        if "verdict_" in key:
            print("| model | acc | Brier | all R1–R7 | reliable |\n|---|---|---|---|---|")
            for n, r in w["models"].items():
                if "metrics" in r and not re.match(r"^(MLP|GRU)_s", n):
                    print(f"| {n} | {f(r['metrics']['accuracy'])} | {f(r['metrics']['brier'], 4)} | {r['allR1R7']} | "
                          f"{r['reliable']} |")
            for name, rs in sorted(dl_groups(w).items()):
                print(f"| {name} (10 seeds) | {f(np.mean([r['metrics']['accuracy'] for r in rs]))} | "
                      f"{f(np.mean([r['metrics']['brier'] for r in rs]), 4)} | "
                      f"{sum(r['allR1R7'] for r in rs)}/10 | {sum(r['reliable'] for r in rs)}/10 |")
            continue
        print(hdr)
        print("\n".join(classic_rows(w)))
        if dl_groups(w):
            print("\n" + dhdr)
            print("\n".join(dl_rows(w)))
            print("\n| comparison | Brier (DL seed mean vs X) | accuracy | seeds with lower Brier | Amendment-1 rule |"
                  "\n|---|---|---|---|---|")
            print("\n".join(beats(w)))
    print("\nfallbacks:", json.dumps(R["fallbacks"]))


if __name__ == "__main__":
    main()
