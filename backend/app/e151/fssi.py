"""
Objective 1 outputs from the E151 two-tier news pipeline. Reads no food-insecurity outcome.

Tier 1 (event and sentiment reading): XLM-RoBERTa zero-shot, combined with embedding similarity and seed phrases (deviation D3), problem against response.
Tier 2 (latent patterns): BERTopic fitted only on stories published before each origin.
Bias correction: each outlet centred on its own earlier mean, shrinkage toward the outlet norm when a province has few stories, and one count per story.

FSSI, Food Stress Sentiment Index, province-quarter: 50 + 10 z, where z standardises bias-corrected problem stress (the five trigger groups, weighted by how strongly a story reports a current problem) against all province-quarters issued before 2016.
Above 50 means more food-stress reporting than the province's outlets usually carry. Response reporting (aid, price caps, recovery) is a separate index, RSI: subtracting it hid the 2018 and 2023 rice shocks, because aid coverage rises in the same quarters. That change was made by checking known events and prices, with no food-insecurity outcome.

    python -m app.e151.fssi -> data/e151/out/fssi/{fssi_province_quarter.csv, topic_patterns_province_quarter.csv, fssi_audit.json}
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from app.e147 import features as Fe
from app.e150 import response as R150
from app.e151 import OUT, RAW
from app.e151.topics import ORIGINS
from app.fi5.target import qindex, qlabel

DIR = OUT / "fssi"
REF_END = qindex("2016-Q1")
GROUPS = ["market", "climate", "employment", "remittance", "poverty", "response"]


def fssi() -> pd.DataFrame:
    P = pd.read_parquet(OUT / "news_panel.parquet")
    P = P[P["lag_m"] == 0]
    base = Fe.base_rows().drop_duplicates("key").set_index("key")
    prov = P[P["stream"].str.startswith("prov:")].copy()
    prov["key"] = prov["stream"].str[5:]
    area = P[P["stream"].str.startswith("area:")].copy()
    area["sws_area"] = area["stream"].str[5:]
    nat = P[P["stream"] == "nat"].set_index("qi")
    rows = []
    for key in base.index:
        g = prov[prov["key"] == key].set_index("qi")
        a = area[area["sws_area"] == base.at[key, "sws_area"]].set_index("qi")
        for i in range(qindex("2013-Q1"), qindex("2026-Q4") + 1):
            if i in g.index:
                r, src = g.loc[i], "province"
            elif i in a.index:
                r, src = a.loc[i], "area fallback"
            elif i in nat.index:
                r, src = nat.loc[i], "national fallback"
            else:
                continue
            o = {"key": key, "province": base.at[key, "province"], "region": base.at[key, "region"], "quarter": qlabel(i), "qi": i, "source_level": src, "stories": int(r["n"]), "net_stress": float(r["e_net"]), "hunger": float(r["e_hunger"])}
            for c in GROUPS:
                o["stress_" + c] = float(r["e_" + c])
            rows.append(o)
    F = pd.DataFrame(rows)
    F["problem_stress"] = F["net_stress"] + F["stress_response"]
    ref = F[(F["qi"] < REF_END) & (F["source_level"] == "province")]
    F["fssi"] = (50 + 10 * (F["problem_stress"] - ref["problem_stress"].mean()) / ref["problem_stress"].std()).round(1)
    F["rsi"] = (50 + 10 * (F["stress_response"] - ref["stress_response"].mean()) / ref["stress_response"].std()).round(1)
    F["note"] = "issued on the quarter's first day from stories before it; not a survey measure"
    return F


def topics() -> pd.DataFrame:
    st = pd.read_parquet(RAW / "stories.parquet", columns=["id", "story", "published", "provinces", "geo_level"]).drop_duplicates("story")
    st = st[st["geo_level"].isin(["province", "lgu"]) & (st["provinces"] != "")]
    rep = pd.read_csv(OUT / "topic_report.csv")
    st["qi"] = [qindex(f"{d.year}-Q{(d.month - 1) // 3 + 1}") + 1 for d in st["published"]]
    rows = []
    for o_i, o in enumerate(ORIGINS):
        nxt = ORIGINS[o_i + 1] if o_i + 1 < len(ORIGINS) else "2027-01-01"
        a = pd.read_parquet(RAW / f"topic_assign_{o}.parquet")
        r = rep[(rep["origin"] == o) & ~rep["irrelevant"] & ~rep["off_topic"]].set_index("topic")
        # a quarter's patterns come from the fit at the latest origin on or before its first day
        lo, hi = qindex(f"{o[:4]}-Q{(int(o[5:7]) - 1) // 3 + 1}"), qindex(f"{nxt[:4]}-Q{(int(nxt[5:7]) - 1) // 3 + 1}")
        s = st[(st["qi"] >= lo) & (st["qi"] < hi)].merge(a, on="id")
        s = s[s["topic"].isin(r.index)]
        s = s.assign(key=s["provinces"].str.split("|")).explode("key")
        for (k, i), g in s.groupby(["key", "qi"]):
            vc = g["topic"].value_counts()
            top = [{"topic": int(t), "stories": int(n), "group": r.at[t, "group"], "keywords": r.at[t, "keywords"]} for t, n in vc.head(3).items()]
            rows.append({"key": k, "quarter": qlabel(int(i)), "stories_with_topic": int(len(g)), "top_patterns": json.dumps(top), "share_by_group": json.dumps({gr: round(float((g["t_group"] == gr).mean()), 3) for gr in GROUPS})})
    return pd.DataFrame(rows)


def validate(F: pd.DataFrame) -> dict:
    G = R150.province_inputs()
    m = F.merge(G[["key", "qi", "cpi_food_yoy", "c_tc_4q", "unemp_rate"]], on=["key", "qi"])
    m = m[m["source_level"] == "province"]
    out = {}
    for a, b in (("stress_market", "cpi_food_yoy"), ("stress_climate", "c_tc_4q"), ("stress_employment", "unemp_rate"), ("fssi", "cpi_food_yoy")):
        z = m[["key", a, b]].dropna().copy()
        z[a] -= z.groupby("key")[a].transform("mean")
        z[b] -= z.groupby("key")[b].transform("mean")
        out[f"{a}~{b}"] = {"n": int(len(z)), "within_province_spearman": float(spearmanr(z[a], z[b]).statistic)}
    ev = {"2018-Q4 rice surge": "2018-Q4", "2020-Q2 COVID": "2020-Q2", "2022-Q1 after Odette": "2022-Q1", "2023-Q4 rice crisis": "2023-Q4", "2025-Q1 Kristine": "2025-Q1"}
    for c in ("fssi", "rsi", "stress_market", "stress_climate"):
        nat = F.groupby("quarter")[c].mean()
        z = (nat - nat.mean()) / nat.std()
        out[f"event_z_{c}"] = {k: round(float(z.get(q, np.nan)), 2) for k, q in ev.items()}
    return out


def main():
    DIR.mkdir(parents=True, exist_ok=True)
    F = fssi()
    F.to_csv(DIR / "fssi_province_quarter.csv", index=False, lineterminator="\n")
    T = topics()
    T.to_csv(DIR / "topic_patterns_province_quarter.csv", index=False, lineterminator="\n")
    cal = F[F["province"].isin(["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"])]
    a = {"province_quarters": int(len(F)), "provinces": int(F["key"].nunique()), "source_level_share": F["source_level"].value_counts(normalize=True).round(3).to_dict(), "calabarzon_source_level_share": cal["source_level"].value_counts(normalize=True).round(3).to_dict(), "topic_rows": int(len(T)), "calabarzon_topic_rows": int(T["key"].isin(["batangas", "cavite", "laguna", "quezon", "rizal"]).sum()),
         "validation": validate(F), "label_check": "fresh sample, 69 % top-event agreement (Wilson 58 to 78 %), 84 % on relevant stories, 80 % problem agreement; reader is the system author", "forecast_value": "no measurable gain one quarter ahead (docs/e151/FINAL_REPORT.md section 4, 8; docs/e154 news_l0.json)"}
    (DIR / "fssi_audit.json").write_text(json.dumps(a, indent=1, default=float), newline="\n")
    print(json.dumps(a, indent=1, default=float))
    print(cal[cal["qi"] >= qindex("2025-Q1")].pivot_table(index="quarter", columns="province", values="fssi").to_string())


if __name__ == "__main__":
    main()
