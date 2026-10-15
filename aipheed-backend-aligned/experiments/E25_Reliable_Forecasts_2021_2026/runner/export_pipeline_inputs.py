"""E25: rebuild the isolated quarterly pipeline's inputs (backend_dev/) from in-window data only, replacing the
E24v2 inputs that carried 1995-2020 values, and write the evidence status from the E25 frozen run.

Writes backend_dev/data/inputs/{sws_rounds.csv, s1_labels.csv, d_quarterly_panel.csv, dnow_panel.csv,
lgu_vulnerability.csv, model_card_pcf21.json}, backend_dev/config/{evidence_status.json, quarterly_sources.json,
forecast_period.json}. Every file is registered with its SHA-256 computed from the bytes.
Usage: python -B runner/export_pipeline_inputs.py <run_id>"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard  # noqa: E402

guard.install()
import pandas as pd  # noqa: E402

import e25lib as E  # noqa: E402

EXP = guard.EXP
BD = EXP / "backend_dev"
sys.path.insert(0, str(BD))
from app.quarterly.registry import Registry  # noqa: E402

RETRIEVED_2026 = "2026-10-09T14:40:00Z"     # retrieval time of the authorized Jan-Jun 2026 CPI file (upper bound)


def main(run_id: str):
    res = json.loads((EXP / "runs" / run_id / "results.json").read_text(encoding="utf-8"))
    rounds = E.load_rounds()
    comp, c26, D = E.load_components()
    mon, Dnow, _ = E.load_monthly(c26, comp)
    T = E.Target("T1", "A", rounds, D)
    inp = BD / "data" / "inputs"
    inp.mkdir(parents=True, exist_ok=True)
    for old in inp.glob("*"):
        old.unlink()
    r = rounds.copy()
    r["published"] = r["published"].dt.date.astype(str).replace("NaT", "")
    r["published_eff"] = r["published_eff"].dt.strftime("%Y-%m-%dT%H:%M:%S")
    r[["quarter", "round", "H", "published", "published_eff", "date_type", "definition_A", "source"]].to_csv(
        inp / "sws_rounds.csv", index=False, lineterminator="\n")
    T.V.rename(columns={"v": "S1"})[["province_code", "quarter", "S1"]].to_csv(inp / "s1_labels.csv", index=False,
                                                                                lineterminator="\n")
    D[["province_code", "quarter", "D", "F"]].to_csv(inp / "d_quarterly_panel.csv", index=False, lineterminator="\n")
    Dnow.to_csv(inp / "dnow_panel.csv", index=False, lineterminator="\n")
    lg = pd.read_csv(EXP / "LGU_RANKING_VALIDATION.csv", dtype={"lgu_code": str})
    lg[["lgu_code", "lgu_name", "lgu_type", "province", "population_2020", "land_area_km2", "poverty_lgu_estimate",
        "poverty_source", "poverty_value_used"]].to_csv(inp / "lgu_vulnerability.csv", index=False, lineterminator="\n")
    proto = (EXP / "runner" / "PROTOCOL_SHA256.txt").read_text(encoding="utf-8").split()[0]
    card = {"name": "PCF21 (FINAL_T1, E25)", "protocol_sha256": proto, "run_id": run_id,
            "H_part": "local level (random walk + SWS sampling noise, n = 600) on production rounds usable at the origin",
            "D_part_T1": "OLS without intercept of D(t'+k) on D(t'-1), pairs 2021-Q2 onward (lead-specific)",
            "D_part_T2": "M4_21: OLS without intercept on [Dnow(t'), D(t'-1)], pairs 2022-Q1 onward",
            "window": "2021-Q1 to 2026-Q2 (authorized)", "status": "development evidence only; not adviser-approved",
            "trained_through": "re-fitted at each origin on the labels published before it"}
    (inp / "model_card_pcf21.json").write_text(json.dumps(card, indent=2), encoding="utf-8")
    # ---- evidence status per lead from the frozen run (T1 FINAL = PCF21; T2 FINAL = M4_21)
    ev = {"T1": {}, "T2": {}, "run_id": run_id}
    for tg, key in (("T1", "T1_A"), ("T2", "T2")):
        rl = res[key]["R_A"]["by_lead"]
        crit = res[key]["criteria_C1_C9"]
        for k in map(str, range(1, 9)):
            if k not in rl:
                ev[tg][k] = {"status": "NOT_ESTABLISHED", "basis": "no evaluable development dates at this lead"}
                continue
            v = rl[k]
            if tg == "T2" and k == "1" and all(crit[c] is True for c in crit if c.startswith("C") and c[1] in "1234567"):
                st = "DEVELOPMENT_EVIDENCE_ONLY"
                basis = (f"exploratory target; C1-C7 met on {v['n_dates']} examined quarters "
                         f"({v['HIGH']} HIGH / {v['LOW']} LOW); C9 not assessable; not a food-insecurity outcome")
            else:
                st = "NOT_ESTABLISHED"
                basis = (f"development quarters only; {v['n_dates']} dates, {v['HIGH']} HIGH / {v['LOW']} LOW; "
                         f"evaluable = {v['evaluable']}; sealed forecasts await outcome authorization")
            ev[tg][k] = {"status": st, "basis": basis}
    (BD / "config" / "evidence_status.json").write_text(json.dumps(ev, indent=2), encoding="utf-8")
    # ---- registry (hash computed from bytes)
    regp = BD / "config" / "quarterly_sources.json"
    if regp.exists():
        regp.unlink()
    reg = Registry(regp)
    ub = rounds["published_eff"].max().strftime("%Y-%m-%dT%H:%M:%S+08:00")
    reg.register("sws_rounds", "label", str(inp / "sws_rounds.csv"), observation_start="2021-Q2",
                 observation_end="2026-Q2", available_at=ub, authorized=True,
                 authorized_by="E17/E18 allowlist (2021-2025) + researcher 2026-10-13 (Jan-Jun 2026)",
                 authorization_ref="E12 details.json; E18 DATA_AUTHORIZATION_RECORD.md; 2026 dates = fetch upper bound",
                 granularity="region-round")
    reg.register("s1_labels", "label", str(inp / "s1_labels.csv"), observation_start="2021-Q2",
                 observation_end="2026-Q2", available_at=ub, authorized=True,
                 authorized_by="derived from authorized H and D", authorization_ref="reading A (production rounds)",
                 granularity="province-quarter")
    reg.register("d_quarterly_panel", "indicator", str(inp / "d_quarterly_panel.csv"), observation_start="2021-Q1",
                 observation_end="2026-Q2", available_at=RETRIEVED_2026, authorized=True,
                 authorized_by="E12 (2021-2025) + researcher 2026-10-13 (Jan-Jun 2026)",
                 authorization_ref="no pre-2021 row (E24v2 panel from 1995 replaced)", granularity="province-quarter")
    reg.register("dnow_panel", "indicator", str(inp / "dnow_panel.csv"), observation_start="2022-Q1",
                 observation_end="2026-Q2", available_at=RETRIEVED_2026, authorized=True,
                 authorized_by="public PSA indices 2021-2025 (owner confirmation A6 pending) + researcher (Jan-Jun 2026)",
                 authorization_ref="months 1-2 of each quarter; no pre-2021 value", granularity="province-quarter")
    reg.register("lgu_vulnerability", "static", str(inp / "lgu_vulnerability.csv"), authorized=True,
                 authorized_by="E17 allowlist (2020 census, 2021 SAE)", authorization_ref="E25 LGU_RANKING_VALIDATION.csv",
                 granularity="lgu")
    reg.register("pcf_model_card", "model", str(inp / "model_card_pcf21.json"), authorized=True,
                 authorized_by="E25 frozen protocol", authorization_ref=proto, granularity="model")
    reg.save()
    period = {"reference_quarter": "2026-Q4", "target_quarter": "2027-Q1", "cutoff": "2026-12-31T23:59:59+08:00",
              "timezone": "Asia/Manila", "model_version": f"PCF21 (E25 frozen protocol {proto[:12]})",
              "feature_version": "E25: SWS rounds usable at the origin (verified date or documented upper bound); "
                                 "D through reference-1; Dnow months 1-2 of the reference quarter; 2021+ only",
              "requirements": [
                  {"id": "news_reference_quarter", "kind": "news", "quarter": "2026-Q4", "source_ids": ["news_2026Q4"],
                   "blocking": False, "note": "Supporting news (display only; PCF21 does not use news)."},
                  {"id": "sws_rounds", "kind": "label", "quarter": "2026-Q3", "source_ids": ["sws_rounds"],
                   "note": "SWS Balance Luzon rounds; the September 2026 round (with its publication date) is needed"},
                  {"id": "label_history", "kind": "label", "quarter": "2026-Q3", "source_ids": ["s1_labels"],
                   "note": "Published S1 labels through 2026-Q3 (threshold rule and persistence)"},
                  {"id": "provincial_D_quarterly", "kind": "indicator", "quarter": "2026-Q3",
                   "source_ids": ["d_quarterly_panel"], "note": "D through 2026-Q3 (July-September 2026 provincial CPI)"},
                  {"id": "provincial_D_now", "kind": "indicator", "quarter": "2026-Q4", "source_ids": ["dnow_panel"],
                   "note": "October-November 2026 provincial CPI (M4_21 price-pressure part)"},
                  {"id": "forecasting_model", "kind": "model", "source_ids": ["pcf_model_card"],
                   "note": "PCF21 (E25 FINAL_T1); development evidence only"},
                  {"id": "lgu_vulnerability", "kind": "static", "source_ids": ["lgu_vulnerability"],
                   "note": "142 LGUs; 126 carry a labelled province-mean poverty substitute"}]}
    (BD / "config" / "forecast_period.json").write_text(json.dumps(period, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({e.source_id: e.sha256 for e in reg.entries}, indent=1))
    print(json.dumps(ev, indent=1)[:1200])


if __name__ == "__main__":
    main(sys.argv[1])
