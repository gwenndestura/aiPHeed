"""E39 Phase 0: inventory and hand-check of label v1 (S1 = H + 2D > trailing-median tau). Read-only; independent of
the served code (no app.* import). Writes runs/phase0_v1_check.json and docs/PHASE0_TABLES.md.

    <backend venv python> -B runner/e39_phase0_v1_check.py

Raw sources (all 2021-2026; nothing before 2021 is loaded):
  * SWS rounds:  backend/data/inputs/sws_rounds.csv (quarter, round, H, published, definition_A); 2026 rounds
                 cross-checked against E31 data_acquired/sws/sws_rounds_2026_verified.csv (SWS release pages).
  * Food CPI:    PSA ACP22 index table 2021-2025 (01.1 FOOD) -> YoY for 2022-01..2025-12 (needs t-12, so 2021 YoY
                 cannot be formed in-window); PSA OpenStat 0012M4ACP23 published YoY for 2026-01..09; 2021 F taken
                 from the E12 realized-components table (PSA-published YoY, the only in-window 2021 source).
"""
from __future__ import annotations

import hashlib
import json
import statistics
from pathlib import Path

import pandas as pd

E39 = Path(__file__).resolve().parents[1]
ROOT = E39.parents[2]
EXP = E39.parent
INP = ROOT / "backend" / "data" / "inputs"
RAW_IDX = EXP / "E25_Reliable_Forecasts_2021_2026" / "inputs" / "e24v2" / "cpi_index_2021_2025_ACP22.csv"
RAW_2026 = EXP / "E31_Chapter1_Completion" / "data_acquired" / "cpi" / "provincial_food_cpi_yoy_2026_raw.csv"
SWS_2026 = EXP / "E31_Chapter1_Completion" / "data_acquired" / "sws" / "sws_rounds_2026_verified.csv"
E12 = EXP / "E25_Reliable_Forecasts_2021_2026" / "inputs" / "e12" / "realized_components_2021_2025.csv"
PROVS = ["PH040100000", "PH040200000", "PH040300000", "PH040400000", "PH040500000"]
NAMES = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal",
         "PH040500000": "Batangas"}
IDX_GEO = {"33": "PH040500000", "34": "PH040100000", "35": "PH040200000", "36": "PH040300000", "37": "PH040400000"}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def qi(q):
    return int(q[:4]) * 4 + int(q[-1]) - 1


def qn(i):
    return f"{i // 4}-Q{i % 4 + 1}"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def monthly_food_yoy() -> pd.DataFrame:
    d = pd.read_csv(RAW_IDX, dtype=str)
    d = d[d["Commodity Description"].str.startswith("01.1 - FOOD")]
    idx = {(IDX_GEO[r.Geolocation_code], int(r.Year), MONTHS.index(r.Period) + 1): float(r.value) for r in d.itertuples()}
    assert min(k[1] for k in idx) >= 2021
    rows = [(p, y, m, 100 * (v / idx[(p, y - 1, m)] - 1)) for (p, y, m), v in idx.items() if (p, y - 1, m) in idx]
    c = pd.read_csv(RAW_2026, dtype={"province_code": str})
    rows += [(r.province_code, int(r.reference_month[:4]), int(r.reference_month[5:7]), float(r.food_cpi_yoy_pct_raw))
             for r in c.itertuples()]
    y = pd.DataFrame(rows, columns=["province_code", "year", "month", "yoy"])
    y["quarter"] = y["year"].astype(str) + "-Q" + ((y["month"] - 1) // 3 + 1).astype(str)
    return y


def main():
    out = {"inputs_sha256": {p.name: sha(p) for p in (INP / "sws_rounds.csv", INP / "s1_labels.csv",
                                                       INP / "d_quarterly_panel.csv", RAW_IDX, RAW_2026, SWS_2026, E12)}}
    # ---------------- 2. H by round
    r = pd.read_csv(INP / "sws_rounds.csv")
    r["defA"] = r["definition_A"].astype(str) == "True"
    r["usable"] = pd.to_datetime(r["published"], format="ISO8601")
    out["rounds"] = r[["quarter", "round", "H", "published", "date_type", "defA"]].to_dict(orient="records")
    v26 = pd.read_csv(SWS_2026)
    out["rounds_2026_match_verified_file"] = all(
        float(r.loc[r["quarter"] == x.quarter, "H"].iloc[0]) == float(x.H) and
        str(r.loc[r["quarter"] == x.quarter, "published"].iloc[0]) == x.published for x in v26.itertuples())
    H = r[r["defA"]].groupby("quarter")["H"].mean()
    all_q = [qn(i) for i in range(qi("2021-Q1"), qi("2026-Q3") + 1)]
    out["quarters_without_approved_round"] = [q for q in all_q if q not in H.index]
    # ---------------- 3. F, D, S1 from raw
    y = monthly_food_yoy()
    g = y.groupby(["province_code", "quarter"]).agg(F=("yoy", "mean"), n=("yoy", "size")).reset_index()
    g = g[g["n"] == 3]
    e12 = pd.read_csv(E12, dtype={"province_code": str})
    f21 = e12[e12["quarter"].str.startswith("2021")][["province_code", "quarter", "F"]]
    F = pd.concat([f21.assign(src="E12 published YoY (2021)"), g[["province_code", "quarter", "F"]].assign(src="raw")])
    F["mean5"] = F.groupby("quarter")["F"].transform("mean")
    F["D"] = F["F"] - F["mean5"]
    F["H"] = F["quarter"].map(H)
    F["S1"] = F["H"] + 2 * F["D"]
    s1 = pd.read_csv(INP / "s1_labels.csv", dtype={"province_code": str})
    dq = pd.read_csv(INP / "d_quarterly_panel.csv", dtype={"province_code": str})
    m = F.merge(s1, on=["province_code", "quarter"], suffixes=("", "_served"), how="inner").merge(
        dq, on=["province_code", "quarter"], suffixes=("", "_served"))
    m["dS1"] = (m["S1"] - m["S1_served"]).abs()
    m["dD"] = (m["D"] - m["D_served"]).abs()
    out["recompute"] = {"rows_compared": int(len(m)), "max_abs_diff_S1": float(m["dS1"].max()),
                        "max_abs_diff_D": float(m["dD"].max()),
                        "rows_diff_S1_gt_1e-9": int((m["dS1"] > 1e-9).sum()),
                        "rows_diff_S1_gt_0.05": int((m["dS1"] > 0.05).sum()),
                        "sign_check_D_equals_F_minus_mean": bool((m["D_served"] - (m["F"] - m["mean5"])).abs().max() < 0.05),
                        "per_date_mean_D_max_abs": float(m.groupby("quarter")["D_served"].mean().abs().max()),
                        "units": "H: percent of families (SWS); D: percentage points of food YoY; S1 = H + 2D mixes the two"}
    hand = m[m["quarter"].isin(["2021-Q2", "2023-Q3", "2024-Q4", "2025-Q4", "2026-Q3"])].sort_values(["quarter", "province_code"])
    out["hand_cases"] = [{"quarter": x.quarter, "province": NAMES[x.province_code], "H": round(x.H, 4), "F": round(x.F, 4),
                          "mean5": round(x.mean5, 4), "D": round(x.D, 6), "S1_recomputed": round(x.S1, 6),
                          "S1_served": round(x.S1_served, 6), "abs_diff": float(x.dS1), "F_source": x.src}
                         for x in hand.itertuples()]
    # ---------------- 4. tau per origin (lead 1), posted rounds only
    posted_at = r[r["defA"]].groupby("quarter")["usable"].max()        # a quarter is labelled once ALL its rounds are posted
    rows = []
    for tg in range(qi("2021-Q3"), qi("2026-Q3") + 1):
        t = tg - 1
        o = pd.Timestamp(f"{(t + 1) // 4}-{3 * ((t + 1) % 4) + 1:02d}-01")
        ok = [q for q in posted_at.index if qi(q) <= t - 1 and posted_at[q] < o]
        vals = s1[s1["quarter"].isin(ok)]["S1"]
        tau = float(statistics.median(vals)) if len(vals) else None
        q = qn(tg)
        lab = s1[s1["quarter"] == q]
        rows.append({"target": q, "origin": str(o.date()), "H_target": None if q not in H.index else round(float(H[q]), 3),
                     "mean_D": None if lab.empty else round(float(dq[dq["quarter"] == q]["D"].mean()), 6),
                     "S1_spread": None if lab.empty else round(float(lab["S1"].max() - lab["S1"].min()), 3),
                     "HIGH_count": None if (lab.empty or tau is None) else int((lab["S1"] > tau).sum()),
                     "tau": None if tau is None else round(tau, 3), "labelled_quarters_in_tau": len(ok),
                     "H_minus_tau": None if (q not in H.index or tau is None) else round(float(H[q]) - tau, 3)})
    out["per_date"] = rows
    lab_rows = [x for x in rows if x["HIGH_count"] is not None]
    out["summary"] = {"dates_labelled": len(lab_rows), "HIGH_rows": sum(x["HIGH_count"] for x in lab_rows),
                      "rows": 5 * len(lab_rows), "dates_all_five_HIGH": sum(x["HIGH_count"] == 5 for x in lab_rows),
                      "dates_H_above_tau": sum(1 for x in lab_rows if x["H_minus_tau"] > 0)}
    (E39 / "runs").mkdir(exist_ok=True)
    (E39 / "runs" / "phase0_v1_check.json").write_bytes(json.dumps(out, indent=1, default=str).encode())
    md = ["# Phase 0 tables (generated by runner/e39_phase0_v1_check.py)\n", "## SWS rounds (backend/data/inputs/sws_rounds.csv)\n",
          "| Quarter | Round | H % | Posted | Date type | Approved (definition_A) |", "|---|---|---|---|---|---|"]
    md += [f"| {x['quarter']} | {x['round']} | {x['H']} | {x['published']} | {x['date_type']} | {x['defA']} |" for x in out["rounds"]]
    md += ["\n## Hand-recomputed S1 (raw files; independent code)\n",
           "| Quarter | Province | H | F (food YoY) | five-province mean | D | S1 recomputed | S1 served | abs diff | F source |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    md += [f"| {x['quarter']} | {x['province']} | {x['H']} | {x['F']} | {x['mean5']} | {x['D']} | {x['S1_recomputed']} | "
           f"{x['S1_served']} | {x['abs_diff']:.2e} | {x['F_source']} |" for x in out["hand_cases"]]
    md += ["\n## Per date (lead-1 origin; tau from labels posted before the origin)\n",
           "| Target | Origin | H | tau | H - tau | mean D | S1 spread | HIGH of 5 | labelled quarters in tau |",
           "|---|---|---|---|---|---|---|---|---|"]
    md += [f"| {x['target']} | {x['origin']} | {x['H_target']} | {x['tau']} | {x['H_minus_tau']} | {x['mean_D']} | "
           f"{x['S1_spread']} | {x['HIGH_count']} | {x['labelled_quarters_in_tau']} |" for x in rows]
    (E39 / "docs").mkdir(exist_ok=True)
    (E39 / "docs" / "PHASE0_TABLES.md").write_bytes(("\n".join(md) + "\n").encode())
    print(json.dumps({k: out[k] for k in ("rounds_2026_match_verified_file", "quarters_without_approved_round",
                                          "recompute", "summary")}, indent=1))
    for x in out["hand_cases"][:8]:
        print(x)
    for x in rows:
        print(x)


if __name__ == "__main__":
    main()
