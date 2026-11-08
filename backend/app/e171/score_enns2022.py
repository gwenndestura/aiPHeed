"""
Score every sealed ENNS 2022 forecast (E158, E166, E168, E170, E171) the moment provincial outcomes exist, under the
locked E171 evaluation rule (docs/e171/PROTOCOL.md section 3): C1/C2/C3/C5/C6 on pooled retrospective + new rows,
C4 on new rows only once n >= 40 (pending adviser confirmation; the original pooled C4 is always reported beside it).

Input CSV (every qualifying province; none may be dropped):
    province,moderate_pct,severe_pct[,se_pct][,source]
  provincial HFIAS from DOST-FNRI ENNS 2022; se_pct = SE of moderate+severe in points (default 3.0, as for 2021).

    python -m app.e171.score_enns2022 OUTCOMES.csv [--out DIR]
Default DIR = data/e171/prospective (the file app.e171.model.evaluate reads). Use --out for dry runs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

from app.e147 import features as Fe
from app.e150 import model as M
from app.e151 import prov as Pv
from app.e156 import leads as LD
from app.e166.enns2022 import ORIGIN, T22, targets
from app.paths import BACKEND_DIR

D = BACKEND_DIR / "data"
SEALS = {"E158": ("e166/out/sealed_enns2022.json", "49e514d2"), "E166": ("e166/out/sealed_enns2022.json", "49e514d2"), "E168": ("e168/out/sealed_enns2022.json", "f8228fae"),
         "E170": ("e170/out/sealed_enns2022.json", "af0180af"), "E171": ("e171/out/sealed_enns2022.json", "a929929a")}
lg = lambda p: np.log(np.asarray(p, float) / (1 - np.asarray(p, float)))
pct = lambda y: 100 / (1 + np.exp(-np.asarray(y, float)))


def outcomes(path):
    o = pd.read_csv(path)
    o["key"] = o["province"].str.lower().str.strip()
    o["pct"] = o["moderate_pct"] + o["severe_pct"]
    se = o["se_pct"] if "se_pct" in o else pd.Series(3.0, index=o.index)
    p = o["pct"] / 100
    o["y_true"] = lg(p)
    o["se_true"] = (se / 100) / (p * (1 - p))
    o["q_true"] = norm.cdf(o["y_true"] / o["se_true"])
    o["y_high"] = (o["y_true"] >= 0).astype(int)
    return o[["key", "province", "pct", "y_true", "se_true", "q_true", "y_high"]]


def persistence(lead):
    """PERS exactly as app.e151.prov (anchor logit; scale from training-row changes at the same origin)."""
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    S = Pv.Store2(None)
    i = T22 - lead
    P = M.Pipeline(S, i, Pv.ROUNDS, ORIGIN)
    te = M.rows_for(S, targets(S), [lead], ORIGIN)
    dy = (P.tr["y_true"] - P.tr["y_anchor"]).values
    s = float(np.sqrt(np.mean(dy ** 2)))
    return te[["key"]].assign(lead=lead, mu_PERS=te["y_anchor"].values, PERS=norm.cdf(te["y_anchor"].values / s), half_PERS=float(np.quantile(np.abs(dy), 0.9)), region=te["region"].values)


def sealed(model):
    path, prefix = SEALS[model]
    raw = (D / path).read_bytes()
    assert hashlib.sha256(raw).hexdigest().startswith(prefix), f"{model} seal changed"
    f = pd.DataFrame(json.loads(raw)["forecasts"])
    if model in ("E158", "E166", "E168"):
        mu, p, lo = f[f"mu_{model}"], f[f"{model}_p_high"], f[f"{model}_low90"]
    else:
        mu, p, lo = f["mu"], f["p_high"], f["low90"]
    return pd.DataFrame({"key": f["key"], "lead": f["lead"], f"mu_{model}": mu, model: p, f"half_{model}": mu - lg(lo / 100)})


def retro(model, lead):
    G = pd.read_csv(D / "e158" / "out" / "oof.csv")
    G = G[G["lead"] == lead]
    if model == "E158":
        return G
    src = {"E166": "e166/out/all_rows.csv", "E168": "e168/out/all_rows.csv", "E170": "e170/out/all_rows.csv", "E171": "e171/out/all_rows.csv"}[model]
    A = pd.read_csv(D / src)
    A = A[(A["lead"] == lead) & (A["mode"] == "main")][["key", "survey", "lead", "mu", "p", "half"]]
    return G.drop(columns=[c for c in (model, f"mu_{model}", f"half_{model}") if c in G]).merge(A.rename(columns={"mu": f"mu_{model}", "p": model, "half": f"half_{model}"}), on=["key", "survey", "lead"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outcomes")
    ap.add_argument("--out", default=str(D / "e171" / "prospective"))
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    O = outcomes(a.outcomes)
    S = {m: sealed(m) for m in SEALS}
    unknown = sorted(set(O["key"]) - set(S["E171"]["key"]))
    assert not unknown, f"provinces not in the sealed panel: {unknown}"
    rng = np.random.default_rng(2022)
    report, new_e171 = {"outcome_file_sha256": hashlib.sha256(Path(a.outcomes).read_bytes()).hexdigest(), "provinces": int(len(O)), "models": {}}, []
    for lead in (1, 2):
        P = persistence(lead)
        base = O.merge(P, on="key").assign(survey="ENNS2022", lead=lead)
        allm = base.copy()
        for m in SEALS:
            allm = allm.merge(S[m][S[m]["lead"] == lead].drop(columns="lead"), on="key")
        new_e171.append(allm)
        for m in SEALS:
            R = retro(m, lead)
            cols = ["key", "survey", "lead", "region", "y_true", "se_true", "q_true", "y_high", "PERS", "mu_PERS", "half_PERS", m, f"mu_{m}", f"half_{m}"]
            pooled = pd.concat([R[cols].assign(src="R"), allm[cols].assign(src="N")], ignore_index=True)
            ev = LD.evaluate(pooled, m, m)["leads"][0]
            nw = allm
            c4_new = None
            if len(nw) >= 40:
                sc = Pv.scale_test(nw.reset_index(drop=True), m, rng, n=2000)
                c4_new = bool(sc["slope_ci95"][0] <= 1 <= sc["slope_ci95"][1])
            crit_new = {**ev["criteria"], "C4": c4_new}
            report["models"].setdefault(m, {})[f"lead{lead}"] = {
                "new_rows": int(len(nw)), "new_correct": int(((nw[m] >= .5) == (nw["y_high"] == 1)).sum()), "new_accuracy": round(float(((nw[m] >= .5) == (nw["y_high"] == 1)).mean()), 3),
                "new_brier": round(float(np.mean((nw[m] - nw["q_true"]) ** 2)), 4), "new_brier_persistence": round(float(np.mean((nw["PERS"] - nw["q_true"]) ** 2)), 4),
                "new_mean_error_pts": round(float(np.mean(pct(nw[f"mu_{m}"]) - nw["pct"])), 2),
                "pooled_rows": int(len(pooled)), "pooled_accuracy": ev["accuracy"], "pooled_accuracy_low": ev["accuracy_95_low_effective_n"], "pooled_majority": ev["majority_rule"],
                "criteria_original_E156": ev["criteria"], "pass_original": bool(ev["reliable"]), "criteria_new_rule": crit_new, "pass_new_rule": bool(all(v is True for v in crit_new.values()))}
    N = pd.concat(new_e171, ignore_index=True)
    keep = ["key", "survey", "lead", "region", "y_true", "se_true", "q_true", "y_high", "PERS", "mu_PERS", "half_PERS", "E158", "mu_E158", "half_E158", "E171", "mu_E171", "half_E171"]
    N[keep].assign(cfg="sealed a929929a", level=np.nan).to_csv(out / "scored_rows.csv", index=False, lineterminator="\n")
    for m in SEALS:
        ml = 0
        for lead in (1, 2):
            if report["models"][m][f"lead{lead}"]["pass_new_rule"] and lead == ml + 1:
                ml = lead
            else:
                break
        report["models"][m]["maximum_reliable_lead_new_rule_leads_1_2"] = ml
    (out / "enns2022_score.json").write_text(json.dumps(report, indent=1, default=str), newline="\n")
    for m, r in report["models"].items():
        l1 = r["lead1"]
        print(f"{m}: new {l1['new_correct']}/{l1['new_rows']} ({l1['new_accuracy']}), pooled {l1['pooled_accuracy']} low {l1['pooled_accuracy_low']} vs {l1['pooled_majority']}, "
              f"orig {''.join(str(int(v)) for v in l1['criteria_original_E156'].values())}, new-rule C4 {l1['criteria_new_rule']['C4']}, max lead (new rule) {r['maximum_reliable_lead_new_rule_leads_1_2']}")


if __name__ == "__main__":
    main()
