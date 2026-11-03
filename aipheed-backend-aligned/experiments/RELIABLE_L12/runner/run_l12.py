"""RELIABLE_L12 (EXPLORATORY): exactly two candidates with a per-origin decision threshold (PLAN.md).

    python run_l12.py check   # PLAN hash; input hashes; C1/C2 Leads 1-2 equal the stored IMPROVE_V2 forecasts
    python run_l12.py leak    # thresholds tau(t, k) and leakage tests (a)-(c) -> out/thresholds.csv, out/leakage.json
    python run_l12.py score   # R1-R7 at Leads 1-2 in two passes, the selection rule -> out/results.json
    python run_l12.py seal    # only if a candidate was chosen -> ../sealed_prospective_L12.csv + ../SEAL_LEDGER.md

C1 = REF (IMPROVE_V2_LEADS), C2 = REF+news (OPTION_1): stored walk-forward forecasts, nothing refitted. The only change
is the call: HIGH when p >= tau(t, k), tau chosen on the candidate's own earlier forecasts at the same lead whose labels
were published before the issue date O(t) (max balanced accuracy on the grid 0.01..0.99; ties -> closest to 0.50, then
lower; 0.50 with < 20 such forecasts or one class only). The frozen rules() is used unedited: R1-R4, R6, R7 from the
0/1 decision column, R5 / Brier / AUC from the probabilities. Other folders are read only.
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[1]
EXP = HERE.parent
PLAN = HERE / "PLAN.md"
OUT = HERE / "out"
sys.path.insert(0, str(EXP / "IMPROVE_V2" / "runner"))
import iv2_lib as V  # noqa: E402
import run_iv2 as R  # noqa: E402

H = V.H
FILES = {"C1": EXP / "IMPROVE_V2_LEADS" / "out" / "forecasts_leads.csv",
         "C2": EXP / "OPTION_1" / "out" / "forecasts_refnews.csv"}
NAMES = {"C1": "REF", "C2": "REF+news"}
IV2_FORECASTS = EXP / "IMPROVE_V2" / "out" / "forecasts.csv"
LEADS = (1, 2)
GRID = np.round(np.arange(1, 100) / 100, 2)
MIN_TRAIN, DEFAULT = 20, 0.50
SEAL_ORIGIN = H.qi("2026-Q3")                    # issued 2026-10-01
SEED, REPS = 2036, 20


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def check_plan() -> str:
    b = PLAN.read_bytes()
    body, last = b.rstrip(b"\n").rsplit(b"\n", 1)
    assert last.startswith(b"PLAN-SHA256: "), "PLAN.md has no hash line"
    h = hashlib.sha256(body + b"\n").hexdigest()
    assert last.split()[1].decode() == h, "PLAN.md changed after it was hashed"
    return h


def load_forecasts() -> dict[str, pd.DataFrame]:
    out = {}
    for c, p in FILES.items():
        f = pd.read_csv(p)
        out[c] = f
    return out


# ================================================================================================ check
def check():
    plan = check_plan()
    F = load_forecasts()
    iv2 = pd.read_csv(IV2_FORECASTS)
    rep = {}
    for c, f in F.items():
        a = f[(f["name"] == NAMES[c]) & f["lead"].isin(LEADS)][["t", "lead", "q", "p"]]
        b = iv2[(iv2["name"] == NAMES[c]) & iv2["lead"].isin(LEADS)][["t", "lead", "q", "p"]]
        m = a.merge(b, on=["t", "lead"], how="inner", suffixes=("", "_iv2"))
        rep[c] = {"rows_iv2": int(len(b)), "matched": int(len(m)), "same_q": bool((m["q"] == m["q_iv2"]).all()),
                  "max_abs_diff": float((m["p"] - m["p_iv2"]).abs().max())}
    ok = all(v["matched"] == v["rows_iv2"] and v["same_q"] and v["max_abs_diff"] <= 1e-12 for v in rep.values())
    res = {"plan_sha256": plan, "inputs": {k: sha(p) for k, p in {**FILES, "iv2_forecasts": IV2_FORECASTS}.items()},
           "reproduction": rep, "reproduced": ok}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "checks.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps(res, indent=1))
    if not ok:
        raise SystemExit("C1/C2 do not reproduce IMPROVE_V2: nothing is scored")


# ================================================================================================ thresholds
def known_q(d, origins) -> dict[int, set]:
    """BL quarters whose every non-commissioned round was published before O(t) (iv2_lib.complete_area)."""
    out = {}
    for t in origins:
        c = V.complete_area(d, t)
        out[t] = set(c.loc[c["area"] == "BL", "q"].astype(int))
    return out


def balanced(y: np.ndarray, call: np.ndarray) -> float:
    return 0.5 * (float(call[y == 1].mean()) + float((1 - call[y == 0]).mean()))


def choose(p: np.ndarray, y: np.ndarray) -> float:
    if len(p) < MIN_TRAIN or y.min() == y.max():
        return DEFAULT
    best, best_key = DEFAULT, None
    for tau in GRID:
        ba = balanced(y, (p >= tau).astype(int))
        key = (round(ba, 12), -abs(tau - 0.5), -tau)
        if best_key is None or key > best_key:
            best, best_key = float(tau), key
    return best


def thresholds(f: pd.DataFrame, k: int, ylab: dict[int, int], known: dict[int, set], origins) -> pd.DataFrame:
    """tau(t, k) at each origin from the candidate's forecasts at lead k from earlier origins whose target label was
    published before O(t). ylab: the label table to use (the leakage test passes perturbed ones)."""
    g = f[f["lead"] == k][["t", "q", "p"]].sort_values("t")
    rows = []
    for t in origins:
        tr = g[(g["t"] < t) & g["q"].isin(known[t])]
        y = tr["q"].map(ylab).to_numpy(int)
        rows.append({"t": t, "lead": k, "tau": choose(tr["p"].to_numpy(float), y), "n_train": int(len(tr)),
                     "n_high": int(y.sum()), "max_train_origin": int(tr["t"].max()) if len(tr) else None,
                     "max_train_target": int(tr["q"].max()) if len(tr) else None})
    return pd.DataFrame(rows)


def leak():
    check_plan()
    assert json.loads((OUT / "checks.json").read_text(encoding="utf-8"))["reproduced"]
    d = H.load()
    lab = V.area_labels(d)
    lab_bl = lab[lab["area"] == "BL"]
    ylab = dict(zip(lab_bl["q"].astype(int), lab_bl["y"].astype(int)))
    F = load_forecasts()
    origins = sorted(set(range(R.VERDICT[0] - max(LEADS), SEAL_ORIGIN + 1)))
    known = known_q(d, origins)
    rng = np.random.default_rng(SEED)
    allT, leakres = [], {}
    for c, f in F.items():
        f = f[f["name"] == NAMES[c]]
        for k in LEADS:
            T = thresholds(f, k, ylab, known, origins)
            # (a) every training forecast: origin < t and target label published before O(t)
            a_ok = bool(all((r.max_train_origin is None or r.max_train_origin < r.t) for r in T.itertuples()))
            for t in origins:
                g = f[(f["lead"] == k) & (f["t"] < t) & f["q"].isin(known[t])]
                assert set(g["q"]) <= known[t] and (g["t"] < t).all()
                assert all(q <= t - 1 for q in g["q"]), "a training target is not before the origin quarter"
            # (b) perturb every label NOT published before O(t): tau must not move
            b_ok = True
            for _ in range(REPS):
                for t in origins:
                    pert = {q: (int(rng.integers(0, 2)) if q not in known[t] else y) for q, y in ylab.items()}
                    tt = thresholds(f, k, pert, known, [t])["tau"].iloc[0]
                    if tt != float(T.loc[T["t"] == t, "tau"].iloc[0]):
                        b_ok = False
            # (c) the 2026-10-01 issue uses no label of 2026-Q3 or later unless published before 2026-10-01
            used = set(f[(f["lead"] == k) & (f["t"] < SEAL_ORIGIN) & f["q"].isin(known[SEAL_ORIGIN])]["q"])
            c_ok = all(q < SEAL_ORIGIN or q in known[SEAL_ORIGIN] for q in used) and max(used) <= SEAL_ORIGIN - 1
            leakres[f"{c}_L{k}"] = {"a_inputs_past_only": a_ok, "b_perturbation_invariant": b_ok,
                                    "c_seal_issue_timing": bool(c_ok), "latest_label_used_at_seal": H.qs(max(used))}
            T.insert(0, "candidate", c)
            allT.append(T)
    T = pd.concat(allT, ignore_index=True)
    T["origin"] = T["t"].map(H.qs)
    T.to_csv(OUT / "thresholds.csv", index=False)
    ok = all(all(v[x] for x in ("a_inputs_past_only", "b_perturbation_invariant", "c_seal_issue_timing"))
             for v in leakres.values())
    res = {"tests": leakres, "passed": ok, "reps": REPS, "seed": SEED, "plan_sha256": check_plan()}
    (OUT / "leakage.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))
    if not ok:
        raise SystemExit("leakage test failed: nothing is scored")


# ================================================================================================ score
def _rules_out(r: dict) -> dict:
    return {k.split()[0]: {"pass": v["pass"], "value": v["value"], "rule": k} for k, v in r["rules"].items()}


def score():
    plan = check_plan()
    assert json.loads((OUT / "leakage.json").read_text(encoding="utf-8"))["passed"], "leakage test not passed"
    d = H.load()
    lab = V.area_labels(d)
    lab_bl = lab[lab["area"] == "BL"]
    F = load_forecasts()
    T = pd.read_csv(OUT / "thresholds.csv")
    res = {"plan_sha256": plan, "inputs": json.loads((OUT / "checks.json").read_text(encoding="utf-8"))["inputs"],
           "label": "EXPLORATORY; development evidence; 2 candidates tried", "candidates": {}}
    for c, f in F.items():
        name = NAMES[c]
        res["candidates"][c] = {"model": name, "leads": {}}
        for k in LEADS:
            W = R.frame(f, k, lab_bl)
            g = W[W[name].notna()].copy()
            tau = T[(T["candidate"] == c) & (T["lead"] == k)].set_index("t")["tau"]
            g["tau"] = g["t"].map(tau)
            assert g["tau"].notna().all()
            g["DECISION"] = (g[name] >= g["tau"]).astype(float)
            dec = H.evaluate(g, "DECISION")                     # R1-R4, R6, R7 and the confusion metrics
            prob = H.evaluate(g, name)                          # R5, Brier, AUC
            ref05 = prob                                        # the same model at 0.50
            rd, rp_ = _rules_out(dec), _rules_out(prob)
            rules = {x: (rp_[x] if x == "R5" else rd[x]) for x in rd}
            m = dec["metrics"]
            L = {"n_quarters": int(g["q"].nunique()), "period": f"{H.qs(int(g['q'].min()))}..{H.qs(int(g['q'].max()))}",
                 "metrics": {"accuracy": m["accuracy"], "balanced": m["balanced"], "precision": m["precision"],
                             "recall": m["recall"], "f1": m.get("f1"), "auc": prob["metrics"]["auc"],
                             "brier": prob["metrics"]["brier"], **{x: m[x] for x in ("TP", "FP", "FN", "TN")}},
                 "rules": rules, "failed": [x for x, v in rules.items() if not v["pass"]],
                 "all_R1_R7": all(v["pass"] for v in rules.values()),
                 "tau": {"min": float(g["tau"].min()), "median": float(g["tau"].median()), "max": float(g["tau"].max()),
                         "share_default_050": float((g["tau"] == DEFAULT).mean())},
                 "at_050": {"metrics": {x: ref05["metrics"].get(x) for x in ("accuracy", "balanced", "precision",
                                                                             "recall", "f1", "auc", "brier")},
                            "failed": [x.split()[0] for x, v in ref05["rules"].items() if not v["pass"]]}}
            res["candidates"][c]["leads"][str(k)] = L
        Ls = res["candidates"][c]["leads"]
        res["candidates"][c]["passes_L1_and_L2"] = bool(Ls["1"]["all_R1_R7"] and Ls["2"]["all_R1_R7"])
        res["candidates"][c]["mean_brier"] = float(np.mean([Ls["1"]["metrics"]["brier"], Ls["2"]["metrics"]["brier"]]))
    passing = [c for c in ("C1", "C2") if res["candidates"][c]["passes_L1_and_L2"]]
    if not passing:
        chosen, why = None, "no candidate passes all of R1-R7 at both Lead 1 and Lead 2: REF+news stays the main model " \
                            "under the paper's 75% rule (Maximum Reliable Lead Time 2)"
    elif len(passing) == 1:
        chosen, why = passing[0], f"{passing[0]} is the only candidate passing all of R1-R7 at Leads 1 and 2"
    else:
        b = {c: res["candidates"][c]["mean_brier"] for c in passing}
        chosen = "C2" if b["C2"] <= b["C1"] else "C1"
        why = f"both pass; lower mean Brier (ties to C2): {b}"
    res["decision"] = {"chosen": chosen, "model": NAMES.get(chosen), "reason": why}
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    for c, v in res["candidates"].items():
        for k, L in v["leads"].items():
            m = L["metrics"]
            print(f"{c} {v['model']} L{k}: acc {m['accuracy']:.3f} bal {m['balanced']:.3f} P {m['precision']:.3f} "
                  f"R {m['recall']:.3f} F1 {m['f1']:.3f} AUC {m['auc']:.3f} Brier {m['brier']:.4f} failed {L['failed']} "
                  f"tau {L['tau']}")
    print("DECISION:", res["decision"])


# ================================================================================================ seal
def seal():
    plan = check_plan()
    res = json.loads((OUT / "results.json").read_text(encoding="utf-8"))
    c = res["decision"]["chosen"]
    if c is None:
        print("no candidate chosen: nothing is sealed (PLAN section 5)")
        return
    d = H.load()
    f = load_forecasts()[c]
    f = f[f["name"] == NAMES[c]]
    T = pd.read_csv(OUT / "thresholds.csv")
    rows = []
    for k in LEADS:
        r = f[(f["t"] == SEAL_ORIGIN) & (f["lead"] == k)].iloc[0]
        tau = float(T[(T["candidate"] == c) & (T["lead"] == k) & (T["t"] == SEAL_ORIGIN)]["tau"].iloc[0])
        kn = H.known(d, SEAL_ORIGIN, "BL")
        rows.append({"issue_date": H.issue(SEAL_ORIGIN), "origin": H.qs(SEAL_ORIGIN), "lead": k,
                     "target_quarter": H.qs(SEAL_ORIGIN + k), "candidate": c, "model": NAMES[c],
                     "p_high": round(float(r["p"]), 6), "tau": tau, "class": "HIGH" if r["p"] >= tau else "LOW",
                     "newest_sws_q": H.qs(kn[-1][0]), "newest_sws_reading": kn[-1][1],
                     "newest_sws_published": r["sws_newest_published"], "threshold_line": 11.3,
                     "plan_sha256": plan, "sealed_on": "2026-11-03",
                     "label": ("SEALED AFTER THE DEVELOPMENT RESULTS WERE KNOWN; prospective, not an independent test "
                               "of them")})
    p = HERE / "sealed_prospective_L12.csv"
    assert not p.exists(), "a sealed file is never overwritten"
    pd.DataFrame(rows).to_csv(p, index=False)
    h = sha(p)
    led = HERE / "SEAL_LEDGER.md"
    lines = ["# RELIABLE_L12 seal ledger", "",
             "Sealed on 2026-11-03, **after the development results of RELIABLE_L12 were known**. Prospective: the target "
             "quarters have no published SWS round yet. Not an independent test of the development results.", "",
             "Sealed files are never edited; later forecasts go into new files, each appended below with its SHA-256.", "",
             "| File | SHA-256 | Issue date | Leads | Targets | Candidate | Sealed on |", "|---|---|---|---|---|---|---|",
             f"| `{p.name}` | `{h}` | {rows[0]['issue_date']} | 1, 2 | {rows[0]['target_quarter']}, "
             f"{rows[1]['target_quarter']} | {c} ({NAMES[c]}) | 2026-11-03 |", ""]
    led.write_text("\n".join(lines), encoding="utf-8")
    print(pd.DataFrame(rows).to_string(), "\nSHA-256", h)


if __name__ == "__main__":
    {"check": check, "leak": leak, "score": score, "seal": seal}[sys.argv[1]]()
