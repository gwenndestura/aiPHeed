"""FOOD_INSECURITY_SYSTEM Step 4: export the served food-insecurity rows (AIPHEED_MAP_MODEL=foodinsecurity).

    python fetch_psa.py      # once: the PSA poverty tables (backend/data/foodinsecurity_engine/psa/)
    python export_fi.py      # -> backend/data/foodinsecurity_engine/rows.csv, evaluation.json, lgu_vulnerability.csv

Design: ../PLAN.md (revision 2; its SHA-256 is checked first).
- Model: IMPROVE_V2 arm REF+news (OPTION_1 re-run), P(Balance Luzon SWS hunger > 11.3%), HIGH at 0.50. Leads 1-2 only
  (Algorithm 3: Maximum Reliable Lead Time 2; R1-R7: 0).
- Province score = P_reg x pov_p / max pov (PSA 2023 poverty incidence among families, Table 1). The class, colour and
  rank basis stay regional; the weighting never changes the class.
- Context only (never changes score, class, colour or rank): the P0H4 food-price pressure band (official row of the
  same issue date), PSA 2023 food poverty among families with its CV, the E112 regional news sentence and the E85
  provincial news sentence and early-warning flag (rule fixed in PLAN section 4).
- LGUs: lgu_vulnerability.csv copied with Lucena's own PSA Table 2a 2021 value (Quezon Table 2 value only as fallback).
Inputs are read only. Nothing is refitted.
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[1]
EXP = HERE.parent
ROOT = EXP.parents[1]
PLAN = HERE / "PLAN.md"
IV2 = EXP / "IMPROVE_V2"
OPT = EXP / "OPTION_1"
CB = EXP / "NEW_MODEL" / "NEWS_V2"                  # PLAN section 9 (revision 4): the served model is C-b
E85 = EXP / "E85_GDELT_Events" / "runs" / "20261021T101520Z" / "gdelt_features_k1.csv"
E112 = EXP / "E112_Food_Insecurity_Forecasting" / "out" / "news_quarterly_corpus.csv"
FOODPOV = (EXP / "LEAD2_RELIABILITY_RESEARCH" / "y14_food_insecurity_forecast" / "data_acquired"
           / "subsistence_families_2018_2023.csv")
CH1_ROWS = ROOT / "backend" / "data" / "ch1_engine" / "rows.csv"
LGU_VUL = ROOT / "backend" / "data" / "inputs" / "lgu_vulnerability.csv"
OUT = ROOT / "backend" / "data" / "foodinsecurity_engine"
PSA = OUT / "psa" / "psa_poverty.csv"
sys.path.insert(0, str(EXP / "HISTORY_RETRAIN" / "runner"))
sys.path.insert(0, str(EXP / "E41_Lead2_Audit" / "runner"))
import hr_lib as H  # noqa: E402
import e41_lib as E41  # noqa: E402   (E85's O(t), via e83_lib.L)

NAME = "C-b"
MODEL = "NEWS_V2-CB"
MAX_LEAD = 2
FIRST_Q, LAST_RETRO_ORIGIN = H.qi("2023-Q1"), H.qi("2026-Q2")       # the span of the ch1 export (pi_price exists)
FORECAST_ORIGIN = H.qi("2026-Q3")                                   # issued 2026-10-01: 2026-Q4 (L1), 2027-Q1 (L2)
BAND_CUTS = (0.33, 0.67)
LOW_PRECISION_CV = 30.0
PROVS = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal",
         "PH040500000": "Batangas"}
LUCENA = "045624000"
NEWS_COLS = ["N1R", "G_pri_yoy", "price_share", "shortage_share", "disaster_share", "agri_supply_share",
             "jobs_income_share", "assistance_share"]
GROUPS = {"market": ["R_food_yoy", "R_head_yoy", "R_food_mom", "R_rice_yoy"] + H.WORLD,
          "climate": ["ONI_last", "ONI_max12", "tc_mean", "R_C3"], "fish_kill": ["R_C4"],
          "hunger": ["h_last", "h_change", "h_mean4", "true_h", "pi_H4L"], "news": NEWS_COLS + ["z_N1R"],
          "lead": ["lead"]}
VALUES = ["R_food_yoy", "R_head_yoy", "R_rice_yoy", "ONI_last", "tc_mean", "R_C3", "R_C4", "W_rice_yoy"]
FNRI = {"source": "DOST-FNRI 2023 National Nutrition Survey", "region": "CALABARZON",
        "moderate_or_severe_food_insecure_pct": 19.1, "ci95": [17.0, 21.1], "national_pct": 31.4,
        "use": "face validity only: a different measure from SWS hunger, never a label"}

# PLAN section 4: the early-warning flag rule, fixed before any flag was computed
FLAG_FAMILIES = ("PRICE", "FOODSEC", "DISASTER", "AGRI", "LIVELIHOOD")
ALL_FAMILIES = FLAG_FAMILIES + ("RESPONSE",)
WINDOW, MIN_HISTORY, Z_MIN, RISE_MIN, MIN_ARTICLES = 8, 6, 1.5, 0.05, 20
SERVED_RULE = {"z_min": Z_MIN, "rise_min": RISE_MIN, "min_articles": MIN_ARTICLES}
STRICT_RULE = {"z_min": 2.0, "rise_min": 0.10, "min_articles": 30}      # PLAN section 8.2 (exploratory, report only)
FAMILY_WORDS = {"PRICE": "food-price", "FOODSEC": "hunger and food-security", "DISASTER": "disaster",
                "AGRI": "farm and fisheries", "LIVELIHOOD": "jobs and poverty", "RESPONSE": "relief and aid"}
E112_WORDS = {"price": "food-price", "shortage": "food-shortage", "disaster": "disaster", "agri_supply": "farm-supply",
              "jobs_income": "jobs and income", "assistance": "assistance"}
REGIONAL_RISE_MIN = 0.05


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def check_plan() -> str:
    b = PLAN.read_bytes()
    body, last = b.rstrip(b"\n").rsplit(b"\n", 1)
    assert last.startswith(b"PLAN-SHA256: "), "PLAN.md has no hash line"
    h = hashlib.sha256(body + b"\n").hexdigest()
    assert last.split()[1].decode() == h, "PLAN.md changed after it was hashed"
    return h


def band(p: float) -> str:
    return "Low" if p < BAND_CUTS[0] else "Medium" if p < BAND_CUTS[1] else "High"


# ---------------------------------------------------------------------------------------------- PSA inputs
def psa() -> pd.DataFrame:
    assert PSA.exists(), "run fetch_psa.py first"
    return pd.read_csv(PSA, dtype={"place_code": str})


def _psa_value(P: pd.DataFrame, table: str, place: str, year: int, item: str) -> float | None:
    m = P[(P["table"] == table) & (P["place_code"] == place) & (P["year"] == year) & P["item"].str.startswith(item)]
    return None if m.empty or pd.isna(m.iloc[0]["value"]) else float(m.iloc[0]["value"])


def province_poverty(P: pd.DataFrame) -> pd.DataFrame:
    """PLAN section 2: PSA 2023 poverty incidence among families (Table 1) and the weight pov / max pov."""
    rows = [{"province_code": c, "province": n,
             "pov_families_2023": _psa_value(P, "T1", c, 2023, "Poverty Incidence"),
             "pov_families_2023_cv": _psa_value(P, "T1", c, 2023, "Coefficient")} for c, n in PROVS.items()]
    d = pd.DataFrame(rows)
    assert d["pov_families_2023"].notna().all(), "Table 1 has no 2023 value for a province"
    d["pov_weight"] = d["pov_families_2023"] / d["pov_families_2023"].max()
    return d


def food_poverty() -> pd.DataFrame:
    f = pd.read_csv(FOODPOV)
    out = []
    for c, n in PROVS.items():
        r = f[f["Geolocation"].str.strip(". ").str.startswith(n)].iloc[0]
        out.append({"province_code": c, "food_pov_2023": float(r["Subsistence Incidence among Families (%) 2023"]),
                    "food_pov_2023_cv": float(r["Coefficient of Variation 2023"])})
    return pd.DataFrame(out)


def lucena(P: pd.DataFrame) -> dict:
    """PLAN section 3: Lucena's own Table 2a value (2021, population basis); the Quezon Table 2 value only if none."""
    v = _psa_value(P, "T2a", LUCENA, 2021, "Poverty Incidence")
    if v is not None:
        return {"value": v, "cv": _psa_value(P, "T2a", LUCENA, 2021, "Coefficient"), "own": True,
                "source": ("PSA 2021 Full-Year Official Poverty Statistics, Table 2a (City of Lucena), poverty incidence "
                           "among population; published to the whole per cent"),
                "url": P[P["table"] == "T2a"].iloc[0]["url"]}
    return {"value": _psa_value(P, "T2", "PH040300000", 2021, "Poverty Incidence"),
            "cv": _psa_value(P, "T2", "PH040300000", 2021, "Coefficient"), "own": False,
            "source": "PSA 2021 Full-Year Official Poverty Statistics, Table 2 (Quezon province value, not a Lucena "
                      "estimate)", "url": P[P["table"] == "T2"].iloc[0]["url"]}


def lgu_copy(L: dict) -> pd.DataFrame:
    v = pd.read_csv(LGU_VUL, dtype={"lgu_code": str})
    i = v.index[v["lgu_code"] == LUCENA]
    assert len(i) == 1 and pd.isna(v.loc[i[0], "poverty_lgu_estimate"])
    v.loc[i, "poverty_lgu_estimate"] = L["value"] if L["own"] else np.nan
    v.loc[i, "poverty_cv"] = L["cv"] if L["own"] else np.nan
    v.loc[i, "poverty_value_used"] = L["value"]
    v.loc[i, "poverty_source"] = L["source"]
    return v


# ---------------------------------------------------------------------------------------------- news
def regional_news(E: pd.DataFrame, t: int) -> dict:
    """PLAN section 4: the E112 category with the largest positive year-on-year share change, quarter t, usable only if
    last_published < O(t) (the timing REF+news uses)."""
    r = E[E["q"] == t]
    issue = pd.Timestamp(H.issue(t))
    if r.empty or not pd.Timestamp(r.iloc[0]["last_published"]) < issue:
        return {"regional_news_text": "Regional news: no corpus value before the issue date.", "regional_news_n": ""}
    r = r.iloc[0]
    yoy = {k: r[f"{k}_yoy"] for k in E112_WORDS if pd.notna(r[f"{k}_yoy"])}
    head = f"Regional news (project corpus, {H.qs(t)}, {int(r['n']):,} articles)"
    if not yoy:
        return {"regional_news_text": f"{head}: no year-earlier quarter to compare.", "regional_news_n": int(r["n"])}
    k, v = max(yoy.items(), key=lambda kv: kv[1])
    text = (f"{head}: {E112_WORDS[k]} coverage rose most, {100 * v:+.1f} points year on year"
            if v >= REGIONAL_RISE_MIN else f"{head}: no news category rose 5 points or more year on year")
    return {"regional_news_text": text, "regional_news_n": int(r["n"])}


def province_news(G: pd.DataFrame, code: str, t: int, rule: dict = SERVED_RULE) -> dict:
    """PLAN section 4: E85 province shares at quarter t against the 8 quarters before it (min 6); a family flags when it
    is >= 1.5 sd and >= 5 points above its usual level and the province has >= 20 own articles (rule = SERVED_RULE;
    STRICT_RULE is section 8.2). RESPONSE never flags. The text describes coverage only: a flag is never named in it
    (PLAN section 8.1); it lives in news_flag and in the staged alert candidates."""
    g = G[G["province_code"] == code].set_index("t")
    if t not in g.index:
        return {"news_flag": "", "news_flag_family": "", "province_news_n": "",
                "province_news_text": f"Province news: no provincial GDELT data after {H.qs(int(G['t'].max()))}."}
    cut = E41.origin(t) - pd.Timedelta(days=1)
    assert cut <= pd.Timestamp(H.issue(t)), "E85 cut is after the issue date"
    n = int(round(math.expm1(float(g.loc[t, "gp_logn"]))))
    hist = g.loc[[x for x in range(t - WINDOW, t) if x in g.index]]
    head = f"Province news (GDELT, {H.qs(t)}, {n} articles)"
    if len(hist) < MIN_HISTORY:
        return {"news_flag": False, "news_flag_family": "", "province_news_n": n,
                "province_news_text": f"{head}: not enough news history for an early-warning check."}
    if n < rule["min_articles"]:
        return {"news_flag": False, "news_flag_family": "", "province_news_n": n,
                "province_news_text": f"{head}: too few province articles for an early-warning check."}
    hits = []
    for f in FLAG_FAMILIES:
        x, h = float(g.loc[t, f"gp_share_{f}"]), hist[f"gp_share_{f}"].astype(float)
        mu, sd = float(h.mean()), float(h.std(ddof=1))
        if x - mu >= rule["rise_min"] and sd > 0 and x - mu >= rule["z_min"] * sd:
            hits.append((x - mu, f, x, mu))
    if not hits:
        return {"news_flag": False, "news_flag_family": "", "province_news_n": n,
                "province_news_text": f"{head}: no news category above its usual level."}
    _, f, x, mu = max(hits)
    return {"news_flag": True, "news_flag_family": ";".join(h[1] for h in sorted(hits, reverse=True)),
            "province_news_n": n,
            "province_news_text": (f"{head}: {FAMILY_WORDS[f]} coverage {100 * x:.0f}% against a usual "
                                   f"{100 * mu:.0f}% ({len(hist)}-quarter mean)")}


# ---------------------------------------------------------------------------------------------- main
def main():
    plan_sha = check_plan()
    d = H.load()
    F = pd.read_csv(CB / "out" / "forecasts.csv")
    F = F[(F["name"] == NAME) & (F["lead"] <= MAX_LEAD)]
    S = pd.read_csv(CB / "out" / "shap_cb.csv")
    S = S[S["lead"] <= MAX_LEAD]
    T = pd.read_csv(IV2 / "out" / "table_pooled.csv", dtype={"area": str})
    T = T[T["area"] == "BL"].merge(pd.read_csv(CB / "out" / "news_anomalies.csv")[["t", "z_N1R"]], on="t", how="left")
    lab = pd.read_csv(IV2 / "out" / "labels_areas.csv")
    lab = lab[lab["area"] == "BL"].set_index("q")
    ch1 = pd.read_csv(CH1_ROWS, dtype={"province_code": str})
    G = pd.read_csv(E85, dtype={"province_code": str})
    E = pd.read_csv(E112)
    P = psa()
    PV = province_poverty(P).merge(food_poverty(), on="province_code")
    LU = lucena(P)
    seal = CB / "sealed_prospective_CB.csv"
    seal_sha = sha(seal)
    sealed = pd.read_csv(seal)

    keys = [(t, 1) for t in range(FIRST_Q - 1, LAST_RETRO_ORIGIN + 1)] + \
           [(FORECAST_ORIGIN, k) for k in range(1, MAX_LEAD + 1)]
    out = []
    for t, k in keys:
        f = F[(F["t"] == t) & (F["lead"] == k)]
        s = S[(S["t"] == t) & (S["lead"] == k)]
        x = T[(T["t"] == t) & (T["lead"] == k)]
        assert len(f) == len(s) == len(x) == 1, (t, k)
        f, s, x = f.iloc[0], s.iloc[0], x.iloc[0]
        q = t + k
        qs, issue = H.qs(q), H.issue(t)
        kn = H.known(d, t, "BL")
        assert abs(kn[-1][1] - x["h_last"]) < 1e-9          # C-b's forecast file carries no h_last: the table does
        p = float(f["p"])
        obs = ("HIGH" if lab.loc[q, "y"] == 1 else "LOW") if q in lab.index and q < H.qi("2026-Q4") else ""
        sh = {g: float(sum(s.get(f"shap_{c}", 0.0) or 0.0 for c in cs if pd.notna(s.get(f"shap_{c}"))))
              for g, cs in GROUPS.items()}
        av = {g: int(any(pd.notna(x.get(c)) for c in cs)) for g, cs in GROUPS.items() if g != "lead"}
        rn = regional_news(E, t)
        for v in PV.itertuples():
            c = ch1[(ch1["province_code"] == v.province_code) & (ch1["quarter"] == qs) & (ch1["lead"] == k)
                    & (ch1["issue_date"] == issue)]
            assert len(c) <= 1, (v.province, qs, k)
            c = c.iloc[0] if len(c) else None
            pp = None if c is None else float(c["pi_price"])
            score = p * float(v.pov_weight)
            r = {"province_code": v.province_code, "province": v.province, "quarter": qs, "issue_date": issue,
                 "lead": k, "origin": H.qs(t), "probability": round(p, 6), "pi_hunger": round(p, 6),
                 "score": round(score, 6), "class": "HIGH" if p >= 0.5 else "LOW", "observed": obs,
                 "observed_hunger": round(float(lab.loc[q, "H"]), 2) if obs else "",
                 "pov_families_2023": v.pov_families_2023, "pov_families_2023_cv": v.pov_families_2023_cv,
                 "pov_weight": round(float(v.pov_weight), 6),
                 "food_pov_2023": v.food_pov_2023, "food_pov_2023_cv": v.food_pov_2023_cv,
                 "pi_price": "" if pp is None else round(pp, 6), "price_band": "" if pp is None else band(pp),
                 "sws_newest_q": H.qs(kn[-1][0]), "sws_newest_published": x["sws_newest_published"],
                 "h_last": round(float(x["h_last"]), 2),
                 "psa_newest_month": "" if c is None else c["psa_newest_month"],
                 "cfg": f["cfg"], "fallback": bool(str(f["fallback"]).lower() == "true"),
                 **{f"shap_{g}": round(v_, 6) for g, v_ in sh.items()},
                 **{f"avail_{g}": a for g, a in av.items()},
                 "avail_employment": 0, "avail_ofw_remittance": 0,
                 **{f"val_{c_}": (round(float(x[c_]), 4) if pd.notna(x.get(c_)) else "") for c_ in VALUES},
                 **rn, **province_news(G, v.province_code, t),
                 "model": MODEL, "seal_sha256": ""}
            if t == FORECAST_ORIGIN:
                m = sealed[(sealed["target_quarter"] == qs) & (sealed["lead"] == k)
                           & sealed["model"].str.startswith(NAME)]
                if len(m):
                    assert abs(float(m.iloc[0]["p_high"]) - p) <= 5e-7, "sealed forecast differs from the export"
                    r["seal_sha256"] = seal_sha
            out.append(r)
    R = pd.DataFrame(out)
    assert (R.loc[R["quarter"] == "2027-Q1", "seal_sha256"] == seal_sha).all(), "2027-Q1 is not the sealed forecast"
    OUT.mkdir(parents=True, exist_ok=True)
    R.to_csv(OUT / "rows.csv", index=False)
    lgu_copy(LU).to_csv(OUT / "lgu_vulnerability.csv", index=False)

    res = json.loads((CB / "out" / "results_cb.json").read_text(encoding="utf-8"))
    chk = json.loads((CB / "out" / "checks.json").read_text(encoding="utf-8"))
    leads = {}
    for k in (1, 2, 3):                                  # Algorithm 3 advances to the first failing lead (Lead 3)
        L = res["leads"][f"L{k}"]
        m = L["metrics"]
        leads[str(k)] = {"n": sum(m[x] for x in ("TP", "FP", "FN", "TN")), "n_quarters": L["n_quarters"],
                         "period": L["period"], "metrics": {x: m[x] for x in ("accuracy", "balanced", "precision",
                                                                             "recall", "f1", "auc", "brier", "TP",
                                                                             "FP", "FN", "TN")},
                         "persistence_accuracy": L["persistence_accuracy"], "alg3_pass": L["alg3_pass"],
                         "reliable": bool(L["alg3_pass"] and k <= res["max_reliable_lead_alg3"]),
                         "rules": {x: {"pass": v.get("pass")} for x, v in L["rules"].items()},
                         "failed": L["failed"], "shap_shares": (L.get("shap") or {}).get("shares"),
                         "vs_REF": L.get("vs_REF")}
    o4 = {c: {"p_holm": v.get("p_holm"), "diff": v.get("diff")} for c, v in res["leads"]["L1"]["objective4"].items()}
    news_share = res["leads"]["L1"]["shap"]["shares"]
    flags = R[R["news_flag"] == True]  # noqa: E712
    ev = {"model": MODEL,
          "target": "SWS Balance Luzon involuntary hunger > 11.3% (quarter mean of non-commissioned rounds)",
          "decision_rule": "HIGH when P >= 0.50 (the regional probability; the province score never sets the class)",
          "design": ("FOOD_INSECURITY_SYSTEM/PLAN.md revision 4: regional C-b forecast (REF inputs + FSSI anomaly); "
                     "province score = P x PSA 2023 poverty among families / max; class and colour regional; P0H4 "
                     "price band, PSA 2023 food poverty and news are context only"),
          "chosen": "C-b chosen by the team on 2026-11-03, pending adviser confirmation (not a test result)",
          "max_reliable_lead": res["max_reliable_lead_alg3"], "max_reliable_lead_r1_r7": res["max_reliable_lead_R1_R7"],
          "served_leads": list(range(1, MAX_LEAD + 1)), "algorithm3": res["rule"], "leads": leads,
          "objective4_lead1": o4, "news_shap_share_lead1": news_share,
          "evidence_status": "development evidence (every scored quarter was examined during development)",
          "price_band_cuts": list(BAND_CUTS),
          "price_part_reliability": {"source": "P0H4_LEAD12_REVIEW/out/price_warning.json",
                                     "lead1_accuracy": 0.614, "lead2_accuracy": 0.600, "verdict": "not reliable"},
          "province_poverty": PV.round(4).to_dict("records"), "low_precision_cv": LOW_PRECISION_CV,
          "lucena": LU,
          "news_flag_rule": {"families": list(FLAG_FAMILIES), "window": WINDOW, "min_history": MIN_HISTORY,
                             "z_min": Z_MIN, "rise_min": RISE_MIN, "min_articles": MIN_ARTICLES,
                             "regional_rise_min": REGIONAL_RISE_MIN},
          "news_flags": {"rows": int(len(flags)), "by_province": flags.groupby("province").size().to_dict(),
                         "quarters": sorted(flags["quarter"].unique().tolist())},
          "fnri_2023": FNRI,
          "seal_sha256": seal_sha, "seal_issue_date": "2026-10-01", "seal_file": "NEW_MODEL/NEWS_V2/sealed_prospective_CB.csv",
          "plan_sha256": plan_sha,
          "news_effect": {k: res["leads"][f"L{k}"]["vs_REF"] for k in (1, 2)},
          "sources": {"forecasts": sha(CB / "out" / "forecasts.csv"), "shap": sha(CB / "out" / "shap_cb.csv"),
                      "results": sha(CB / "out" / "results_cb.json"), "table_pooled": sha(IV2 / "out" / "table_pooled.csv"),
                      "ch1_rows": sha(CH1_ROWS), "e85_features": sha(E85), "e112_corpus": sha(E112),
                      "food_poverty": sha(FOODPOV), "psa_poverty": sha(PSA), "lgu_vulnerability_input": sha(LGU_VUL),
                      "reproduced": chk["reproduced"]}}
    (OUT / "evaluation.json").write_text(json.dumps(ev, indent=1, default=str), encoding="utf-8")
    print(f"rows {len(R)} ({R['quarter'].nunique()} quarters, leads {sorted(R['lead'].unique())}); "
          f"max reliable lead {ev['max_reliable_lead']}; seal {seal_sha[:8]}; plan {plan_sha[:8]}")
    print("province weights:", PV.set_index("province")["pov_weight"].round(3).to_dict())
    print("Lucena:", {k: LU[k] for k in ("value", "cv", "own")})
    print("news flags:", ev["news_flags"])


if __name__ == "__main__":
    main()
