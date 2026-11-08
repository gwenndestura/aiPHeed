"""PROTOCOL sections 10-11: prospective seal and the backend export of FINAL (served only with AIPHEED_CH1_ENGINE=fr2).

FINAL (chosen by the frozen DEV rule) = Z0-U: the flat base-effect projection of PSA food and headline CPI as the price
part (no learned model), times the served hunger term; Lead 1 issued at the quarter start, Leads 2-4 re-issued the day
after the SWS release (the P0H4-U schedule). Rows start from the P0H4-U export, so the hunger part, issue dates and
input values are identical; only the price part, the probability, the class and the attribution change.

    python export_ii.py         # backend/data/ch1_engine_fr2/{rows.csv, evaluation.json}, out/PROSPECTIVE_SEAL.json
"""
from __future__ import annotations

import copy
import json

import numpy as np
import pandas as pd

import ii_lib as L
from score_ii import ARMS

F, M, KEY = L.F, L.M, L.KEY
BACK = L.EXP.parents[1] / "backend" / "data"
SRC, TARGET = BACK / "ch1_engine_fr", BACK / "ch1_engine_fr2"
SERVED_SEAL = "a498b5ef3fd9143348737a3a4464ba71c3c728fff48efa5f11d4c544644fbee1"
FR_SEAL = "bd6572e1"
MODEL = "Z0-U"


def logit(p):
    p = np.clip(np.asarray(p, float), 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def price_clim(t: int, k: int) -> float:
    S = F.stack()
    tr = S[(S["t"] < t) & (S["target_q"] <= t - 1) & (S["lead"] == k) & S["F"].notna()]
    y = (((tr["F"] - tr["province_code"].map(F.TH_F)) > 0) | ((tr["F"] - tr["HL"] - tr["province_code"].map(F.TH_G)) > 0))
    return float(y.mean()) if len(tr) else 0.5


def f1(m):
    p, r = m["precision"], m["recall"]
    return float(2 * p * r / (p + r)) if p == p and r == r and p + r > 0 else 0.0


def lead_entry(d: dict, g: pd.DataFrame) -> dict:
    m = dict(d["metrics"])
    m["f1"] = f1(m)
    return {"n": m["n"], "n_quarters": int(g["q"].nunique()), "metrics": m, "accuracy_ci90": d["acc_ci90"],
            "baseline_accuracy": d["baseline_accuracy"], "criteria": d["criteria"], "failed": d["failed"],
            "reliable": d["reliable"], "loqo_min": d["loqo_min"], "acc_thirds": d["acc_thirds"],
            "brier_vs_persist_si": d["brier_vs_persist"], "brier_vs_clim": d["brier_vs_clim"],
            "confusion": {k: m[k] for k in ("tp", "fp", "fn", "tn")}}


def onl_pick(E: pd.DataFrame, t: int) -> str:
    hist = E[(E["t"] < t) & (E["q"] <= t - 1)]
    if hist["q"].nunique() < 4:
        return "P0"
    sc = {a: float(np.mean((hist[f"{a}_price"] - hist["price"]) ** 2)) for a in ARMS}
    return min(ARMS, key=lambda a: (round(sc[a], 10), ARMS.index(a)))


def main():
    L.check_protocol()
    res = json.loads((L.OUT / "results_ii.json").read_text())
    final = res["selection"]["chosen_FINAL"]
    assert final == "Z0", f"export written for FINAL = Z0 (got {final})"
    E = pd.read_csv(L.OUT / "predictions_ii.csv", dtype={"province_code": str})
    Z = pd.read_csv(F.OUT / "price_arms_all_origins.csv", dtype={"province_code": str})
    Z = Z[Z["arm"] == "Z0"].set_index(["t", "lead", "province_code"])["pi_P"]
    ev_src = json.loads((SRC / "evaluation.json").read_text(encoding="utf-8"))
    assert ev_src["seal_sha256"] == SERVED_SEAL and ev_src["sws_update"]["seal_sha256"].startswith(FR_SEAL)
    R = pd.read_csv(SRC / "rows.csv", dtype=str, keep_default_na=False)
    t_new = max(F.stack()["t"])
    clim_cache = {}
    for i in R.index:
        q = R.at[i, "quarter"]
        tq = int(q[:4]) * 4 + int(q[-1]) - 1
        k = int(R.at[i, "lead"])
        t = tq - k
        pp = float(Z[(t, k, R.at[i, "province_code"])])
        ph = float(R.at[i, "pi_hunger"])
        p = ph * pp
        if (t, k) not in clim_cache:
            clim_cache[(t, k)] = price_clim(t, k)
        R.at[i, "pi_price"] = f"{pp:.6g}"
        R.at[i, "probability"] = f"{p:.6g}"
        R.at[i, "class"] = "HIGH" if p >= 0.5 else "LOW"
        # the price part uses only PSA food and headline CPI (family A1): its whole push away from the price
        # climatology of that lead is Market / Prices; every other family has no effect on this model
        for f in ("A1", "A2", "A3", "V1", "C1", "C2", "C3", "C4", "E1", "E2", "N1", "H1"):
            R.at[i, f"shap_{f}"] = "0"
        R.at[i, "shap_A1"] = f"{float(logit(pp) - logit(clim_cache[(t, k)])):.6g}"
        R.at[i, "model"] = MODEL
    new = R["issue_date"] >= "2026-10-01"
    assert set(R.loc[new, "issue_date"]) == {"2026-10-01", "2026-10-15"}
    # ---------------------------------------------------------------- prospective seal
    seal_rows = R[new].copy()
    seal_path = L.OUT / "sealed_prospective_Z0U.csv"
    seal_rows.to_csv(seal_path, index=False, lineterminator="\n")
    seal = L.sha256(seal_path)
    R.loc[new, "seal_sha256"] = seal
    pick = onl_pick(E, int(t_new))
    J2S = pd.read_csv(L.OUT / "j2s_rows.csv", dtype={"province_code": str})
    A = pd.read_csv(L.OUT / "price_arms_ii.csv", dtype={"province_code": str})
    ex = []
    for _, r in seal_rows.iterrows():
        q = r["quarter"]
        tq = int(q[:4]) * 4 + int(q[-1]) - 1
        k = int(r["lead"])
        key = (int(t_new), k, r["province_code"])
        j2s = float(J2S.set_index(KEY).loc[key, "J2S_price"])
        if pick == "P0":
            onl = float(pd.read_csv(SRC / "rows.csv", dtype=str).set_index(["province_code", "quarter"]).loc[(r["province_code"], q), "pi_price"])
        elif pick == "Z0":
            onl = float(Z[key])
        else:
            onl = float(A[(A["arm"] == pick)].set_index(KEY).loc[key, "pi_P"])
        ph = float(r["pi_hunger"])
        ex.append({"province_code": r["province_code"], "target_quarter": q, "lead": k, "issue_date": r["issue_date"],
                   "pi_hunger": ph, "ONL_arm": pick, "ONL_price": onl, "ONL_probability": ph * onl,
                   "J2S_price_POSTHOC": j2s, "J2S_probability_POSTHOC": ph * j2s})
    ex_path = L.OUT / "sealed_prospective_exploratory.csv"
    pd.DataFrame(ex).to_csv(ex_path, index=False, lineterminator="\n", float_format="%.6g")
    seal_doc = {"protocol_sha256": res["protocol_sha256"], "origin": F.qs(int(t_new)),
                "FINAL": {"model": MODEL, "file": seal_path.name, "sha256": seal},
                "exploratory": {"file": ex_path.name, "sha256": L.sha256(ex_path),
                                "contents": f"ONL (pre-registered online selection; picks {pick} at this origin) and J2S "
                                            "(POST-HOC anchored-drift arm, recorded for prospective testing only)"},
                "served_seal_unchanged": SERVED_SEAL, "p0h4u_seal_unchanged": ev_src["sws_update"]["seal_sha256"],
                "note": "Score only after SWS publishes 2026-Q4 and later quarters; never edit these files."}
    L.dump("PROSPECTIVE_SEAL.json", seal_doc)
    # ---------------------------------------------------------------- evaluation.json
    ev = copy.deepcopy(ev_src)
    arm = res["arms"]["Z0"]["leads"]
    leads = {}
    for k in F.LEADS:
        leads[str(k)] = lead_entry(arm[str(k)] if str(k) in arm else arm[k], E[E["lead"] == k])
    ev["leads"] = leads
    mr = res["arms"]["Z0"]["max_reliable_lead"]
    ev.update({"model": MODEL, "protocol_name": "FORECAST_RESEARCH_II", "protocol_sha256": res["protocol_sha256"],
               "max_reliable_lead": mr, "max_reliable_lead_strict": mr, "seal_sha256": seal, "seal_issue_date": "2026-10-01",
               "previous_seal_sha256": ev_src["sws_update"]["seal_sha256"],
               "price_part": {"kind": "structural", "name": "Z0",
                              "description": ("the flat base-effect projection of PSA food and headline CPI (the latest "
                                              "index held flat to the target quarter), with its uncertainty from past "
                                              "projection errors at the same lead; no learned model"),
                              "selection": res["selection"]},
               "serve_note": ("Research candidate Z0-U (AIPHEED_CH1_ENGINE=fr2), chosen by the frozen FORECAST_RESEARCH_II "
                              "DEV rule: the price part is the flat CPI projection (no LightGBM; LightGBM added no "
                              "development value). Not significantly different from P0H4 or P0H4-U at any lead. Lead 2 "
                              f"still not reliable (fails {', '.join(arm['2']['failed'] if '2' in arm else arm[2]['failed'])}).")})
    ev["horizon"] = {"leads_evaluated": list(F.LEADS), "testable_horizon_R1": max(k for k in F.LEADS if leads[str(k)]["criteria"]["R1"]),
                     "max_reliable_lead": mr, "individually_passing_leads": [k for k in F.LEADS if leads[str(k)]["reliable"]],
                     "generated_up_to": 4,
                     "why_not_longer": ("Lead 2 (re-issued after the SWS release) fails only R5: its Brier score is not "
                                        "significantly better than climatology. Leads 3-4 fail most criteria: the food-price "
                                        "condition two or more quarters ahead is not predictable from 2021-2026 data, and the "
                                        "hunger reading is older."),
                     "leads": {str(k): {**{x: ev_src["horizon"]["leads"].get(str(k), {}).get(x) for x in ("quarters_after_issue", "quarters_after_newest_sws")},
                                        "n": leads[str(k)]["n"], "accuracy": leads[str(k)]["metrics"]["accuracy"],
                                        "reliable": leads[str(k)]["reliable"], "criteria": leads[str(k)]["criteria"]} for k in F.LEADS}}
    u = ev["sws_update"]
    l2a = res["arms_A"]["Z0"]
    u["lead2"] = {"n": leads["2"]["n"], "metrics": leads["2"]["metrics"], "failed": leads["2"]["failed"],
                  "reliable": leads["2"]["reliable"], "acc_ci90": leads["2"]["accuracy_ci90"],
                  "warning_days_median": float(E.loc[E["lead"] == 2, "warn_days_B"].median()),
                  "quarter_start_issue": {"metrics": {"accuracy": l2a["acc"]["2"] if "2" in l2a["acc"] else l2a["acc"][2],
                                                      "recall": M.cls(E.loc[E["lead"] == 2, "y"], E.loc[E["lead"] == 2, "Z0A_p"])["recall"]}}}
    u["seal_sha256"], u["protocol_sha256"] = seal, res["protocol_sha256"]
    u["research"] = "aipheed-backend-aligned/experiments/FORECAST_RESEARCH_II/FORECAST_RESEARCH_II_REPORT.md"
    for k in ("one_model_candidate", "post_hoc_improved", "calibration_lead1"):
        ev.pop(k, None)
    TARGET.mkdir(exist_ok=True)
    R.to_csv(TARGET / "rows.csv", index=False, lineterminator="\n")
    (TARGET / "evaluation.json").write_text(json.dumps(ev, indent=1, default=float), encoding="utf-8")
    print(json.dumps(seal_doc, indent=1))
    print(R[new][["province", "quarter", "lead", "issue_date", "pi_hunger", "pi_price", "probability", "class"]].to_string())
    print(pd.DataFrame(ex)[["province_code", "target_quarter", "ONL_arm", "ONL_probability", "J2S_probability_POSTHOC"]].to_string())


if __name__ == "__main__":
    main()
