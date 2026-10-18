"""E56 step 0 (score-free): latest observation, release rule and availability of every dataset used by the
two-quarter food-insecurity forecast, at the 2027-Q1 issue date O(2026-Q3) = 2026-10-01 and at the authorized data
limit (2026-10-14). Distinguishes target-data freshness from predictor-data freshness.

    backend/venv/Scripts/python.exe -B runner/e56_data_freshness.py   -> tables/data_freshness.csv, tables/horizon.json
"""
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
E56 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(E56.parent / "E55_Food_Insecurity_LightGBM" / "runner"))
import e55_lib as F  # noqa: E402

L, K, M, np, pd = F.L, F.K, F.M, F.np, F.pd
OPER = L.qi("2026-Q3")
O = L.origin(OPER)
AUTH = pd.Timestamp("2026-10-14")


def ym(v):
    return L.ym_s(int(v))


def main():
    d = L.load()
    x = K.load_extra()
    ev = M.load_events()
    c = d.cut(OPER)
    sws_all = pd.read_csv(L.SWS_FILE)
    sws_all["published"] = pd.to_datetime(sws_all["published"])
    rows = []

    def add(name, role, geo, freq, latest_in_data, used_at_issue, rule, note=""):
        rows.append({"dataset": name, "role": role, "geography": geo, "frequency": freq,
                     "latest_observation_in_dataset": latest_in_data,
                     "latest_used_for_2027Q1_forecast": used_at_issue, "availability_rule": rule, "note": note})

    idx = d.idx
    add("PSA CPI food and all-items index (OpenSTAT 0012M4ACP22)", "target (price part) + predictor", "province", "monthly",
        ym(idx["ym"].max()), ym(c.idx["ym"].max()),
        "months through month 2 of quarter t (published before O(t))",
        "September 2026 CPI was released after the 2026-10-01 issue date and is not used in the 2027-Q1 forecast")
    add("PSA CPI YoY, food and headline (0012M4ACP23)", "target (price part) + predictor", "province", "monthly",
        ym(d.yoy["ym"].max()), ym(c.yoy["ym"].max()), "as above")
    add("SWS hunger, Balance Luzon (sws_rounds.csv)", "target (hunger part) + hunger gate", "region (Balance Luzon)",
        "quarterly (rounds)", f"{sws_all['quarter'].iloc[-1]} (posted {sws_all['published'].max().date()})",
        f"{L.qs(int(c.sws['q'].max()))} (posted {c.sws['published'].max().date()})",
        "rounds posted before O(t); approved (definition A) rounds for the gate; all rounds for labels",
        "2026-Q3 round posted 2026-10-14, after the issue date: it labels 2026-Q3 but is not a 2027-Q1 predictor")
    add("PSA palay/corn production (0012E4EVCP0)", "predictor (climate group)", "province", "quarterly",
        L.qs(int(d.prod[d.prod["series"].isin(["palay", "corn"])]["q"].max())),
        L.qs(int(c.prod[c.prod["series"].isin(["palay", "corn"])]["q"].max())), "quarter t-1")
    add("PSA fisheries/aquaculture production (0132E4GVFP1)", "predictor (fish-kill group)", "province", "quarterly",
        L.qs(int(d.prod[d.prod["series"].isin(["fish", "aqua"])]["q"].max())),
        L.qs(int(c.prod[c.prod["series"].isin(["fish", "aqua"])]["q"].max())), "quarter t-1",
        "no official fish-kill event series exists")
    add("PSA LFS unemployment/underemployment (national)", "predictor (employment group)", "national", "monthly",
        ym(d.lfs["ym"].max()), ym(c.lfs["ym"].max()), "months of quarter t-1")
    cl = x["climate"]
    add("IBTrACS typhoon tracks + NOAA ONI (pagasa_climate.parquet)", "predictor (climate group)", "province / national",
        "quarterly", L.qs(int(cl["q"].max())), f"typhoons {L.qs(OPER)}; ENSO {L.qs(OPER - 1)}",
        "typhoons quarter t; ENSO quarter t-1")
    add("BSP OF cash remittances + ECB USD/PHP (bsp_macro.parquet)", "predictor (OFW group)", "national", "quarterly",
        L.qs(int(x["ofw"].dropna(subset=["ofw_cash_remit_usd_bn"])["q"].max())),
        L.qs(int(x["ofw"][x["ofw"]["q"] <= OPER - 1].dropna(subset=["ofw_cash_remit_usd_bn"])["q"].max())),
        "quarter t-1", "remittances end 2025-Q4 in the dataset: missing at the 2026 issue dates (data refresh needs authorization)")
    add("PSA wholesale rice prices", "predictor (market group)", "province", "quarterly",
        L.qs(int(x["rice"]["q"].max())), L.qs(int(x["rice"][x["rice"]["q"] <= OPER - 1]["q"].max())), "quarter t-1")
    add("News corpus trigger shares (E40 composition)", "predictor (NLP)", "province", "quarterly",
        L.qs(int(d.news["q"].max())), L.qs(int(c.news["q"].max())), "quarter t")
    add("FSSI v2 panel", "NLP index (not an E55/E56 tree input)", "province", "quarterly",
        L.qs(int(x["fssi"]["q"].max())), L.qs(int(x["fssi"][x["fssi"]["q"] <= OPER]["q"].max())), "quarter t")
    add("Rice-policy orders (EO 62, import suspensions, MSRP, food security emergency)", "predictor (market group)",
        "national", "events", str(ev["announcement_date"].max().date()),
        str(ev[ev["announcement_date"] < O]["announcement_date"].max().date()), "announced before O(t)")
    add("PSA 2021 municipal SAE poverty incidence", "candidate predictor (E54/E55: no gain); Objective 3 weight",
        "city/municipality (141 LGUs)", "one-off (2021)", "2021", "2021 (POV-AS arm only)",
        "published 2024; known from O(t) >= 2025-01-01")
    add("PSA subsistence incidence (food poverty)", "direct measure, not a target (2 points)", "province", "triennial",
        "2023", "not used", "published 2024-08-15")
    add("DOST-FNRI NNS FIES (moderate or severe household food insecurity)", "direct measure; face-validity anchor (Obj 5)",
        "region", "survey years", "2023 (CALABARZON 19.1%)", "not used", "survey publication",
        "regional only; annual/triennial; cannot be a quarterly provincial target")
    out = E56 / "tables"
    out.mkdir(exist_ok=True)
    pd.DataFrame(rows).to_csv(out / "data_freshness.csv", index=False)
    lab = F.t43_labels(d)
    lab = lab[lab["T43"].notna()]
    horizon = {
        "issue_date": str(O.date()), "origin_quarter_t": L.qs(OPER), "intermediate_quarter": L.qs(OPER + 1),
        "target_quarter": L.qs(OPER + 2), "horizon_quarters": 2,
        "rule": "issued 00:00 day 1 of quarter t+1 with data published before then; target t+2 (two quarters after the "
                "latest predictor quarter t)",
        "latest_target_label_quarter_in_data": L.qs(int(lab["q"].max())),
        "latest_target_label_known_at_issue": L.qs(int(F.t43_last(d, OPER)[L.PROVS[0]][1])),
        "latest_cpi_month_used": ym(c.idx["ym"].max()), "latest_sws_round_used": L.qs(int(c.sws["q"].max())),
        "authorized_data_limit": str(AUTH.date()),
        "note": ("The target T43 is observed through 2026-Q3 (SWS round posted 2026-10-14, September CPI). At the "
                 "2026-10-01 issue date the latest complete target quarter known was " +
                 L.qs(int(F.t43_last(d, OPER)[L.PROVS[0]][1])) + "; direct food-insecurity surveys (FIES, subsistence) "
                 "end in 2023 and are not targets.")}
    (out / "horizon.json").write_text(json.dumps(horizon, indent=1))
    print(pd.DataFrame(rows)[["dataset", "latest_observation_in_dataset", "latest_used_for_2027Q1_forecast"]].to_string())
    print(json.dumps(horizon, indent=1))


if __name__ == "__main__":
    main()
