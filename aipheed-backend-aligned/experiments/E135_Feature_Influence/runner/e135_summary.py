"""
E135 deliverable tables and headline numbers from the run outputs:
  E135_FEATURE_AUDIT.csv, E135_FEATURE_INFLUENCE_EXPERIMENTS.csv, E135_TRIGGER_GROUP_ABLATION.csv,
  E135_LEAD_COMPARISON.csv, out/e135_summary.json

    python -I runner/e135_summary.py      (after e135_run.py)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e135_run as S  # noqa: E402

L, OUT, ROOT, EXP = S.L, S.OUT, S.ROOT, S.EXP
CONFIG = {"HFM-X": "A,C,E,N,V; prior SD 1 (full influence)", "SEAS-LLM": "no drivers (E132)",
          "FULL7": "A,C,E,N,V,aR,aP; prior SD 1 (full influence, = E134-AREA-T)",
          "X-RED": "HFM-X groups; prior SD 0.5 (reduced influence)",
          "X-NSD": "HFM-X groups; prior SD chosen in-fold from {0.25,0.5,1,2} (regularized, nested)",
          "X-SEL": "FULL7 groups kept in-fold only if they lowered past MSE (selective, lead-specific, nested)",
          "X-GREG": "FULL7 groups; groups X-SEL would drop shrunk to prior SD 0.25 (group regularization, nested)",
          "X-STACK": "w*HFM-X + (1-w)*SEAS-LLM, w chosen in-fold (regime-aware combination, nested)",
          "X-COMB": "w*X-SEL + (1-w)*SEAS-LLM, w chosen in-fold (combined, nested)",
          "X-EXCL": "HFM-X minus C typhoons (exclusion, POST-HOC reference, not selectable)",
          "PERSIST": "latest SWS", "CLIM": "area mean", "LLM": "local level (E131)"}
META = [  # family, feature, source, meaning, geography, frequency, publication delay used, in E135 pool
    ("A1-A3 market", "A: rice CPI q/q %", "PSA CPI (E131)", "rice price acceleration", "18 regions -> 4 areas", "monthly", "quarter end + 10 d", "A"),
    ("A1-A3 market", "bottom-30% food CPI q/q", "PSA B30 CPI (E133)", "price faced by poor households", "regions -> areas", "monthly", "quarter end + 10 d", "tested E133 (HFM-X-B30)"),
    ("A1-A3 market", "food YoY, rice YoY, relative food price", "PSA CPI (E131)", "food inflation", "regions -> areas", "monthly", "quarter end + 10 d", "tested E131/E132 (learned models)"),
    ("A1-A3 market", "farmgate palay YoY", "PSA (E119)", "producer price", "IV-A", "monthly", "one quarter back", "screen only"),
    ("C1-C2 climate", "C: typhoons in PAR", "PAGASA/IBTrACS (E119)", "storm exposure", "PAR", "quarterly", "one quarter back", "C"),
    ("C1-C2 climate", "ONI", "NOAA (E119)", "ENSO state", "global", "monthly", "one quarter back", "tested E133 PH2 / E134-ONI"),
    ("C1-C2 climate", "aR: area rainfall deficit", "NASA POWER (E134)", "drought exposure", "18 regional points -> areas", "daily", "quarter end + 10 d", "aR"),
    ("C1-C2 climate", "rainfall/temperature anomaly (IV-A)", "E119", "local climate", "IV-A", "quarterly", "one quarter back", "screen only"),
    ("C3-C4 production", "aP: area palay drop", "PSA palay (E134)", "food availability", "regions -> areas", "quarterly", "quarter end + 75 d", "aP"),
    ("C3-C4 production", "C3 palay/corn drop, C4 fisheries drop", "PSA (E119)", "food availability", "IV-A", "quarterly", "one quarter back", "screen only"),
    ("E1-E2 employment/OFW", "E: unemployment change pp", "PSA LFS (E119)", "labour-market deterioration", "national", "quarterly", "one quarter back", "E"),
    ("E1-E2 employment/OFW", "remittance decline %", "BSP (E119)", "OFW income", "national", "monthly", "one quarter back", "tested E131/E132"),
    ("E1-E2 employment/OFW", "real daily pay growth, regional unemployment", "PSA SDG (E132)", "income", "regions", "annual", "30 June next year", "tested E132"),
    ("N1 news", "N: GDELT shortage share", "GDELT (E119)", "food-shortage news intensity", "national", "quarterly", "one quarter back", "N"),
    ("N1 news", "GDELT agri supply, jobs/income, assistance shares", "GDELT (E119)", "other news topics", "national", "quarterly", "one quarter back", "screen only"),
    ("N1 news", "FSSI v2", "aiPHeed NLP", "province food-stress news", "5 CALABARZON provinces", "quarterly", "end of quarter", "diagnostic E134 (no signal)"),
    ("V1 poverty", "V: poverty x market (area interaction)", "PSA poverty (E131)", "vulnerability scaling of price shocks", "regions -> areas", "triennial", "release dates", "V"),
    ("H1 history", "SWS state (level, design effect)", "SWS (E110)", "measured hunger", "4 areas", "quarterly", "publication date", "always (state)"),
]


def main():
    Mt = pd.read_csv(OUT / "e135_metrics.csv")
    rules = json.loads((OUT / "e135_rules.json").read_text())
    loo = pd.read_csv(OUT / "e135_loo_audit.csv")
    scr = pd.read_csv(EXP / "E133_Forecasting_Breakthrough" / "out" / "d2_leading_indicator_screen.csv")
    pool_screen = {"A": "driver_A_rice", "C": "driver_C_rice", "E": "driver_E_rice", "N": "driver_N_rice"}
    rows = []
    for fam, feat, src, mean, geo, freq, delay, pool in META:
        rec = {"family": fam, "feature": feat, "source": src, "meaning": mean, "geography": geo, "frequency": freq,
               "publication_delay_rule": delay, "e135_role": pool}
        if pool in pool_screen:
            for k in (1, 2):
                s = scr[(scr.lead == k) & (scr.feature == pool_screen[pool])]
                if len(s):
                    rec[f"d2_spearman_lead{k}"], rec[f"d2_p_holm_lead{k}"] = float(s["spearman"].iloc[0]), float(s["p_holm"].iloc[0])
        if pool in S.POOL:
            for k in L.LEADS:
                r = loo[(loo.group == pool) & (loo.lead == k) & (loo.test == "removed from FULL7")].iloc[0]
                rec[f"lead{k}_dmae_when_removed"] = r["delta_mae_variant_minus_full7"]
                rec[f"lead{k}_dwithin_when_removed"] = r["delta_within_variant_minus_full7"]
                rec[f"lead{k}_p_with_better"] = r["p_full7_better_sq_error"]
                rec[f"lead{k}_status"] = "demonstrated" if r["demonstrated_contribution"] else ("harmful" if r["harmful"] else "weak/none")
            r2 = loo[(loo.group == pool) & (loo.lead == 2) & (loo.test == "removed from FULL7")].iloc[0]
            rec["lead2_bias_change_when_removed"] = r2["bias_variant"] - r2["bias_full7"]
            rec["lead2_high_tercile_bias_change_when_removed"] = r2["high_bias_variant"] - r2["high_bias_full7"]
            for c in ("dmae_surge 2024", "dmae_post-break 2025+", "dmae_metro_manila", "dmae_balance_luzon", "dmae_visayas", "dmae_mindanao"):
                rec[f"lead2_{c}"] = r2[c]
        rows.append(rec)
    pd.DataFrame(rows).to_csv(ROOT / "E135_FEATURE_AUDIT.csv", index=False)

    ex = Mt.copy()
    ex["configuration"] = ex["model"].map(CONFIG)
    ex["selectable"] = ex["model"].isin(S.SELECTABLE)
    ex.to_csv(ROOT / "E135_FEATURE_INFLUENCE_EXPERIMENTS.csv", index=False)
    e133 = pd.read_csv(EXP / "E133_Forecasting_Breakthrough" / "out" / "e133_ablation.csv")
    e133 = e133[e133.policy == "P-DASH"].assign(base="HFM-X (E133, reproduced)")
    tg = pd.concat([loo.assign(base="FULL7 (E135)"), e133.rename(columns={"variant": "test"})], ignore_index=True)
    tg.to_csv(ROOT / "E135_TRIGGER_GROUP_ABLATION.csv", index=False)

    lc = []
    for k, v in rules.items():
        st, pol, lead, m = k.split("|")
        if pol != "P-DASH":
            continue
        lc.append({"set": st, "lead": int(lead), "model": m, "rows": v["n_rows"], "quarters": v["n_quarters"],
                   "within": v["within"], "mae": v["mae"], "rmse": v["rmse"], "coverage80": v["coverage80"],
                   "p_vs_persistence": v["p_vs_persistence"], "failed_rules": ";".join(n for n, o in v["rules"].items() if not o),
                   "passed_all": v["passed"]})
    lc = pd.DataFrame(lc).merge(Mt[["set", "policy", "lead", "model", "bias", "bias_high", "sharp_n", "sharp_within"]]
                                [Mt.policy == "P-DASH"].drop(columns="policy"), on=["set", "lead", "model"], how="left")
    lc.sort_values(["set", "lead", "model"]).to_csv(ROOT / "E135_LEAD_COMPARISON.csv", index=False)

    g = Mt[(Mt.set == "S-U") & (Mt.policy == "P-DASH") & (Mt.lead == 2) & Mt.model.isin(S.SELECTABLE)]
    g = g.sort_values(["within_tolerance", "mae"], ascending=[False, True])
    cand = g["model"].iloc[0]
    passed = {k: rules[f"S-U|P-DASH|{k}|{cand}"]["passed"] and rules[f"S-E132|P-DASH|{k}|{cand}"]["rules"]["N2_within_tolerance_75"]
              for k in L.LEADS}
    ch = pd.read_csv(OUT / "e135_nested_choices.csv")
    stab = {}
    for (p, k), c in ch[ch.policy == "P-DASH"].groupby(["procedure", "lead"]):
        c = c[c.past_rows >= S.MIN_PAST]
        stab[f"{p}|{k}"] = float(c["choice"].astype(str).value_counts(normalize=True).iloc[0]) if len(c) else None
    s = {"selection": {"candidate": cand, "table": g[["model", "n", "n_quarters", "within_tolerance", "mae", "rmse", "bias_high"]].round(4).to_dict("records")},
         "maximum_reliable_lead": L.maximum_reliable_lead(passed), "any_rule_set_passed": [k for k, v in rules.items() if v["passed"]],
         "any_model_any_lead_75": bool((Mt.loc[Mt.set.isin(["S-U", "S-E132"]), "within_tolerance"] >= 0.75).any()),
         "nested_choice_modal_share": stab,
         "x_comb_recommendable": False}
    L.dump(s, OUT / "e135_summary.json")
    print(json.dumps(s, indent=1, default=str)[:3500])


if __name__ == "__main__":
    main()
