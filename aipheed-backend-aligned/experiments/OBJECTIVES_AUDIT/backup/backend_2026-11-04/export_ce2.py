"""LOCAL DEMO export of C-E2 (CE2_PREREGISTRATION.md) for the food-insecurity dashboard mode.

Writes backend/data/foodinsecurity_engine_ce2/ (rows.csv, evaluation.json, lgu_vulnerability.csv) with the same layout as
FOOD_INSECURITY_SYSTEM/runner/export_fi.py, which is reused read-only. C-b's export (backend/data/foodinsecurity_engine/)
and its seal are not touched. Served only when the backend runs with AIPHEED_FI_DATA_DIR pointing at the new folder.

C-E2 did not pass the pre-registered adoption rule (out/ce2_results.json); this export is a team-requested demonstration.

Every quarter is served at Lead 2 (one forecast per quarter, as the main repo serves FIRI v2).

Driver bars ("relative" view): each quarter's own C-E2 SHAP per group, divided by that group's typical size (mean
|group SHAP| over this lead's forecasts issued up to this one; no later data), then shared to 100%. A bar says how
strongly the driver pushes this quarter compared with its own usual push, not its share of the raw log-odds.

    python export_ce2.py
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[1]
EXP = HERE.parent
ROOT = EXP.parents[1]
OUT = ROOT / "backend" / "data" / "foodinsecurity_engine_ce2"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ce_model as CE  # noqa: E402
import ce2_model as CE2  # noqa: E402   (pre-registration check)

PC, H, V, R = CE.PC, CE.H, CE.V, CE.R
spec = importlib.util.spec_from_file_location("export_fi_ro", EXP / "FOOD_INSECURITY_SYSTEM" / "runner" / "export_fi.py")
E = importlib.util.module_from_spec(spec)
spec.loader.exec_module(E)

NAME, MODEL = "C-E2", "ALLBASE-CE2"
GROUPS = {**E.GROUPS, "employment": ["E1"], "ofw_remittance": ["E2"]}
SHARE_GROUPS = {"H1 Hunger (SWS)": E.GROUPS["hunger"], "A1-A2 Food and headline prices": ["R_food_yoy", "R_head_yoy",
                                                                                          "R_food_mom"],
                "A3 Rice": ["R_rice_yoy"], "C1 Climate (ONI)": ["ONI_last", "ONI_max12"], "C2 Typhoons": ["tc_mean"],
                "C3 Crops": ["R_C3"], "C4 Fisheries": ["R_C4"], "World prices": H.WORLD, "N1 News": ["z_N1R"],
                "E1 Employment": ["E1"], "E2 OFW remittances": ["E2"]}


def shares(s: pd.DataFrame) -> dict:
    a = {g: s[[f"shap_{c}" for c in cs if f"shap_{c}" in s]].abs().sum(axis=1) for g, cs in SHARE_GROUPS.items()}
    tot = sum(a.values())
    return {g: round(float(100 * (v / tot).mean()), 1) for g, v in a.items()}


def main():
    pre = CE2.check()
    res = json.loads((HERE / "out" / "ce2_results.json").read_text(encoding="utf-8"))
    d = H.load()
    Fa = pd.read_csv(HERE / "out" / "ce2_fits.csv")
    Fa = Fa[Fa["name"] == NAME]
    F = Fa[Fa["lead"] <= E.MAX_LEAD].assign(cfg="")
    T = pd.read_csv(E.IV2 / "out" / "table_pooled.csv", dtype={"area": str})
    T = T[T["area"] == "BL"].merge(pd.read_csv(E.CB / "out" / "news_anomalies.csv")[["t", "z_N1R"]], on="t", how="left")
    T = T.merge(pd.read_csv(HERE / "out" / "ce_features.csv"), on="t", how="left")
    lab = pd.read_csv(E.IV2 / "out" / "labels_areas.csv")
    lab = lab[lab["area"] == "BL"].set_index("q")
    ch1 = pd.read_csv(E.CH1_ROWS, dtype={"province_code": str})
    G = pd.read_csv(E.E85, dtype={"province_code": str})
    Ec = pd.read_csv(E.E112)
    P = E.psa()
    PV = E.province_poverty(P).merge(E.food_poverty(), on="province_code")
    LU = E.lucena(P)
    # As the main repo serves FIRI v2: one forecast per quarter, always Lead 2 (issued two quarters before it), so
    # 2026-Q4 is the forecast issued 2026-07-01 and 2027-Q1 the one issued 2026-10-01.
    keys = [(q - 2, 2) for q in range(E.FIRST_Q, E.FORECAST_ORIGIN + 3)]
    out = []
    for t, k in keys:
        f = F[(F["t"] == t) & (F["lead"] == k)]
        x = T[(T["t"] == t) & (T["lead"] == k)]
        assert len(f) == len(x) == 1, (t, k)
        f, x = f.iloc[0], x.iloc[0]
        q = t + k
        qs, issue = H.qs(q), H.issue(t)
        kn = H.known(d, t, "BL")
        p = float(f["p"])
        obs = ("HIGH" if lab.loc[q, "y"] == 1 else "LOW") if q in lab.index and q < H.qi("2026-Q4") else ""
        sh = {g: float(sum(f.get(f"shap_{c}", 0.0) or 0.0 for c in cs if pd.notna(f.get(f"shap_{c}"))))
              for g, cs in GROUPS.items()}
        av = {g: int(any(pd.notna(x.get(c)) for c in cs)) for g, cs in GROUPS.items() if g != "lead"}
        rn = E.regional_news(Ec, t)
        # Relative driver influence: this forecast's group SHAP / the group's mean |SHAP| over this lead's forecasts
        # issued at origins <= t (no later data); the sign is this forecast's.
        win = Fa[(Fa["lead"] == k) & (Fa["t"] <= t) & ~Fa["fallback"].astype(str).str.lower().eq("true")]
        avg8 = {}
        for g_ in ("market", "climate", "fish_kill", "employment", "ofw_remittance"):
            v_ = sum(win[f"shap_{c}"].fillna(0) for c in GROUPS[g_] if f"shap_{c}" in win)
            typ = float(v_.abs().mean()) if len(v_) else 0.0
            avg8[f"avg8_shap_{g_}"] = round(sh[g_] / typ, 6) if typ > 0 else 0.0
        for v in PV.itertuples():
            c = ch1[(ch1["province_code"] == v.province_code) & (ch1["quarter"] == qs) & (ch1["lead"] == k)
                    & (ch1["issue_date"] == issue)]
            c = c.iloc[0] if len(c) else None
            pp = None if c is None else float(c["pi_price"])
            out.append({"province_code": v.province_code, "province": v.province, "quarter": qs, "issue_date": issue,
                        "lead": k, "origin": H.qs(t), "probability": round(p, 6), "pi_hunger": round(p, 6),
                        "score": round(p * float(v.pov_weight), 6), "class": "HIGH" if p >= 0.5 else "LOW",
                        "observed": obs, "observed_hunger": round(float(lab.loc[q, "H"]), 2) if obs else "",
                        "pov_families_2023": v.pov_families_2023, "pov_families_2023_cv": v.pov_families_2023_cv,
                        "pov_weight": round(float(v.pov_weight), 6), "food_pov_2023": v.food_pov_2023,
                        "food_pov_2023_cv": v.food_pov_2023_cv,
                        "pi_price": "" if pp is None else round(pp, 6), "price_band": "" if pp is None else E.band(pp),
                        "sws_newest_q": H.qs(kn[-1][0]), "sws_newest_published": x["sws_newest_published"],
                        "h_last": round(float(x["h_last"]), 2),
                        "psa_newest_month": "" if c is None else c["psa_newest_month"], "cfg": "",
                        "fallback": bool(str(f["fallback"]).lower() == "true"),
                        **{f"shap_{g}": round(v_, 6) for g, v_ in sh.items()},
                        **{f"avail_{g}": a for g, a in av.items()},
                        **{f"val_{c_}": (round(float(x[c_]), 4) if pd.notna(x.get(c_)) else "") for c_ in E.VALUES},
                        **avg8, "avg8_n": int(len(win)),
                        **rn, **E.province_news(G, v.province_code, t), "model": MODEL, "seal_sha256": ""})
    Rr = pd.DataFrame(out)
    OUT.mkdir(parents=True, exist_ok=True)
    Rr.to_csv(OUT / "rows.csv", index=False)
    E.lgu_copy(LU).to_csv(OUT / "lgu_vulnerability.csv", index=False)

    # evaluation (C-E's own walk-forward results; Lead 3 computed here for Algorithm 3's stopping lead)
    lab_all = V.area_labels(d)
    lab_bl = lab_all[lab_all["area"] == "BL"]
    Lp = pd.read_csv(E.CB.parent.parent / "IMPROVE_V2_LEADS" / "out" / "forecasts_leads.csv")
    comp = pd.concat([Lp[Lp["name"].isin(["PERSIST", "CLIM"])][["name", "t", "lead", "q", "p"]],
                      Fa[["t", "lead", "q", "p"]].assign(name=NAME)], ignore_index=True)
    leads = {}
    for k in (1, 2, 3):
        W = R.frame(comp, k, lab_bl).dropna(subset=[NAME])
        s = PC._summ(W, NAME)
        m = s["metrics"]
        leads[str(k)] = {"n": int(len(W)), "n_quarters": int(W["q"].nunique()),
                         "period": f"{H.qs(int(W['q'].min()))}..{H.qs(int(W['q'].max()))}",
                         "metrics": {x: m[x] for x in ("accuracy", "balanced", "precision", "recall", "f1", "auc", "brier",
                                                        "TP", "FP", "FN", "TN")},
                         "persistence_accuracy": PC._acc(W, "PERSIST"), "alg3_pass": bool(m["accuracy"] >= .75),
                         "reliable": bool(m["accuracy"] >= .75 and k <= res["algorithm3"][NAME]),
                         "rules": {x: {"pass": v["pass"]} for x, v in s["rules"].items()}, "failed": s["failed"],
                         "shap_shares": shares(Fa[(Fa["lead"] == k) & Fa["q"].isin(W["q"])]) if k <= 2 else None,
                         "vs_REF": None}
    o4 = {f["comparator"]: {"p_holm": f["p_holm_14"], "diff": f["diff"]} for f in res["holm_family_14"]
          if f["lead"] == 1 and f["comparator"] in ("PERSIST", "PSA-only", "NLP-only", "LOGIT", "ALWAYS-HIGH")}
    # Average driver influence (team request: every dashboard driver shows its share): mean |group SHAP| over C-E's
    # evaluated forecasts (Leads 1-2, 2010-Q1..2026-Q3), signed by the mean signed SHAP; the same for every quarter.
    ev_rows = Fa[Fa["lead"].isin([1, 2]) & Fa["q"].between(H.qi("2010-Q1"), H.qi("2026-Q3"))]
    shown = ("market", "climate", "fish_kill", "employment", "ofw_remittance")
    avg = {}
    for g in shown:
        v = sum(ev_rows[f"shap_{c}"].fillna(0) for c in GROUPS[g] if f"shap_{c}" in ev_rows)
        avg[g] = round(float(np.sign(v.mean()) * v.abs().mean()), 6)
    news = leads["1"]["shap_shares"]["N1 News"]
    m1, m2 = leads["1"]["metrics"], leads["2"]["metrics"]
    ev = {"model": MODEL,
          "target": "SWS Balance Luzon involuntary hunger > 11.3% (quarter mean of non-commissioned rounds)",
          "decision_rule": "HIGH when P >= 0.50 (the regional probability; the province score never sets the class)",
          "design": ("LOCAL DEMO: C-E2 = C-E with the 8 LightGBM settings averaged; C-E = C-b + national unemployment change (PSA LFS) + OFW remittance decline (IMF BOP), "
                     "OBJECTIVES_AUDIT/CE2_PREREGISTRATION.md; province score = P x PSA 2023 poverty among families / max"),
          "chosen": "C-E2 served at the team's request for a local demonstration; it did NOT pass the pre-registered "
                    "adoption rule (out/ce2_results.json); C-b remains the sealed main model",
          "max_reliable_lead": res["algorithm3"][NAME], "max_reliable_lead_r1_r7": 0, "served_leads": [2],
          "algorithm3": "Algorithm 3: mean fold accuracy >= 0.75 (one quarter per fold), k = 1..8, halt at the first failing lead",
          "leads": leads, "objective4_lead1": o4, "news_shap_share_lead1": leads["1"]["shap_shares"],
          "evidence_status": "development evidence (every scored quarter was examined during development)",
          "price_band_cuts": list(E.BAND_CUTS),
          "price_part_reliability": {"source": "P0H4_LEAD12_REVIEW/out/price_warning.json", "lead1_accuracy": 0.614,
                                     "lead2_accuracy": 0.600, "verdict": "not reliable"},
          "province_poverty": PV.round(4).to_dict("records"), "low_precision_cv": E.LOW_PRECISION_CV, "lucena": LU,
          "news_flag_rule": {"families": list(E.FLAG_FAMILIES), "window": E.WINDOW, "min_history": E.MIN_HISTORY,
                             "z_min": E.Z_MIN, "rise_min": E.RISE_MIN, "min_articles": E.MIN_ARTICLES,
                             "regional_rise_min": E.REGIONAL_RISE_MIN},
          "news_flags": {"rows": int(Rr["news_flag"].sum())}, "fnri_2023": E.FNRI,
          "seal_sha256": "", "seal_issue_date": "", "seal_file": "none (C-E2 has no sealed forecast; C-b's seal is 67baec66)",
          "plan_sha256": pre,
          "news_effect": {},
          "not_input_groups": [],
          "driver_view": "relative",
          "news_effect_text": (f"the NLP input (FSSI anomaly) is included and carries {news:.1f}% of SHAP influence on "
                               "average"),
          "model_line": (f"C-E2 (local demo): the mean of 8 LightGBM settings (stacked leads, walk-forward from 1998; C-b's inputs plus "
                         f"national unemployment change and OFW remittances) forecasting P(Balance Luzon SWS hunger > "
                         f"11.3%). Maximum Reliable Lead Time {res['algorithm3'][NAME]} quarters under the paper's 75% rule "
                         f"(development accuracy Lead 1 {m1['accuracy']:.3f}, Lead 2 {m2['accuracy']:.3f}, Lead 3 "
                         f"{leads['3']['metrics']['accuracy']:.3f}); 0 under the stricter rules R1-R7. Not adopted by the "
                         "pre-registered rule; C-b remains the main model."),
          "sources": {"ce2_fits": E.sha(HERE / "out" / "ce2_fits.csv"), "ce2_results": E.sha(HERE / "out" / "ce2_results.json"),
                      "table_pooled": E.sha(E.IV2 / "out" / "table_pooled.csv"), "reproduced": res.get("checks", {}).get("Cb_reproduced")}}
    (OUT / "evaluation.json").write_text(json.dumps(ev, indent=1, default=str), encoding="utf-8")
    print(f"rows {len(Rr)} -> {OUT}; Lead 1 acc {m1['accuracy']:.3f}, Lead 2 {m2['accuracy']:.3f}; MRLT {ev['max_reliable_lead']}")
    last = Rr[Rr["quarter"] == "2027-Q1"].iloc[0]
    print("2027-Q1 P", last["probability"], {g: last[f"shap_{g}"] for g in GROUPS},
          {g: last[f"avg8_shap_{g}"] for g in ("market", "climate", "fish_kill", "employment", "ofw_remittance")})


if __name__ == "__main__":
    main()
