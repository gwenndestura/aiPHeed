"""E31 step 3: extend the quarterly pipeline inputs with the data authorized on 2026-10-14 (vintage 2).

* Vintage 1 (the E29 inputs, ending 2026-Q2) is kept byte-identical in backend_dev/data/inputs_vintage1_e29/ so the
  frozen 2026-Q3 records stay reproducible.
* Vintage 2 adds, with the SAME constructions as E25 (load_components / load_monthly / Target):
    sws_rounds        verified posting dates for the March and June 2026 rounds (replacing the 2026-09-10 upper
                      bound) and the September 2026 round (posted 2026-10-14);
    d_quarterly_panel 2026-Q3: F = mean Jul-Sep food YoY, D = F - five-province mean;
    dnow_panel        2026-Q3: mean over Jul-Aug of (monthly YoY - five-province mean);
    s1_labels         2026-Q3: S1 = H + 2D.
  Every row is 2021-Q1..2026-Q3; nothing before 2021 is read.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

sys.dont_write_bytecode = True
EXP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXP / "runner"))
sys.path.insert(0, str(EXP / "backend_dev"))
import guard31  # noqa: E402

guard31.install()
import pandas as pd  # noqa: E402

BD = EXP / "backend_dev"
INP = BD / "data" / "inputs"
V1 = BD / "data" / "inputs_vintage1_e29"
CPI = EXP / "data_acquired" / "cpi" / "provincial_food_cpi_yoy_2026_raw.csv"
SWS = EXP / "data_acquired" / "sws" / "sws_rounds_2026_verified.csv"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write(df: pd.DataFrame, p: Path):
    p.write_bytes(df.to_csv(index=False, lineterminator="\n").encode("utf-8"))


def main():
    if not V1.exists():
        shutil.copytree(INP, V1)
    rounds = pd.read_csv(V1 / "sws_rounds.csv", dtype=str)
    S1 = pd.read_csv(V1 / "s1_labels.csv", dtype={"province_code": str})
    dq = pd.read_csv(V1 / "d_quarterly_panel.csv", dtype={"province_code": str})
    dn = pd.read_csv(V1 / "dnow_panel.csv", dtype={"province_code": str})
    v = pd.read_csv(SWS, dtype=str)
    # --- SWS: verified dates for 2026-Q1/Q2, new 2026-Q3 round
    for r in v.itertuples():
        m = (rounds["quarter"] == r.quarter) & (rounds["round"] == r.round)
        if m.any():
            assert abs(float(rounds.loc[m, "H"].iloc[0]) - float(r.H)) < 1e-9, (r.quarter, "stored H differs")
            rounds.loc[m, ["published", "published_eff", "date_type", "source"]] = [
                r.published, f"{r.published}T00:00:00", "verified (SWS release posted date, E31)", "sws_release_2026_E31"]
        else:
            rounds = pd.concat([rounds, pd.DataFrame([{
                "quarter": r.quarter, "round": r.round, "H": r.H, "published": r.published,
                "published_eff": f"{r.published}T00:00:00", "date_type": "verified (SWS release posted date, E31)",
                "definition_A": r.definition_A, "source": "sws_release_2026_E31"}])], ignore_index=True)
    # --- CPI: quarterly D and monthly Dnow for 2026-Q3
    c = pd.read_csv(CPI, dtype={"province_code": str})
    c["m"] = c["reference_month"].str[5:7].astype(int)
    q3 = c[c["m"].between(7, 9)]
    assert len(q3) == 15
    F = q3.groupby("province_code")["food_cpi_yoy_pct_raw"].mean()
    D = F - F.mean()
    dq = pd.concat([dq, pd.DataFrame({"province_code": F.index, "quarter": "2026-Q3", "D": D.values, "F": F.values})],
                   ignore_index=True)
    mm = c[c["m"].isin([7, 8])].copy()
    mm["d"] = mm["food_cpi_yoy_pct_raw"] - mm.groupby("m")["food_cpi_yoy_pct_raw"].transform("mean")
    dnow = mm.groupby("province_code")["d"].mean()
    dn = pd.concat([dn, pd.DataFrame({"province_code": dnow.index, "quarter": "2026-Q3", "Dnow": dnow.values})],
                   ignore_index=True)
    # sanity: the E25 construction reproduces the stored 2026-Q1/Q2 D and Dnow from the same raw file
    for q, months in (("2026-Q1", (1, 2, 3)), ("2026-Q2", (4, 5, 6))):
        g = c[c["m"].isin(months)].groupby("province_code")["food_cpi_yoy_pct_raw"].mean()
        old = dq[dq["quarter"] == q].set_index("province_code")["D"]
        assert ((g - g.mean()) - old).abs().max() < 1e-9, f"D construction mismatch {q}"
        mm2 = c[c["m"].isin(months[:2])].copy()
        mm2["d"] = mm2["food_cpi_yoy_pct_raw"] - mm2.groupby("m")["food_cpi_yoy_pct_raw"].transform("mean")
        oldn = dn[dn["quarter"] == q].set_index("province_code")["Dnow"]
        assert (mm2.groupby("province_code")["d"].mean() - oldn).abs().max() < 1e-9, f"Dnow mismatch {q}"
    # --- label
    H = float(v[(v["quarter"] == "2026-Q3") & (v["definition_A"] == "True")]["H"].astype(float).mean())
    S1 = pd.concat([S1, pd.DataFrame({"province_code": D.index, "quarter": "2026-Q3", "S1": H + 2 * D.values})],
                   ignore_index=True)
    for name, df in (("sws_rounds.csv", rounds), ("s1_labels.csv", S1), ("d_quarterly_panel.csv", dq),
                     ("dnow_panel.csv", dn)):
        assert df["quarter"].min() >= "2021-Q1" and df["quarter"].max() <= "2026-Q3", name
        write(df, INP / name)
    # --- registry: new vintage of each changed source
    from app.quarterly.registry import Registry

    reg = Registry(BD / "config" / "quarterly_sources.json")
    common = dict(authorized=True, authorized_by="researcher 2026-10-14 (E31): data released up to 2026-10-14",
                  revision_note="E31 vintage 2: + 2026-Q3; 2026 SWS posting dates verified")
    reg.register("sws_rounds", "label", str(INP / "sws_rounds.csv"), observation_start="2021-Q2",
                 observation_end="2026-Q3", available_at="2026-10-14T00:00:00+08:00",
                 authorization_ref=str(SWS.relative_to(EXP)), granularity="region-round", **common)
    reg.register("s1_labels", "label", str(INP / "s1_labels.csv"), observation_start="2021-Q2",
                 observation_end="2026-Q3", available_at="2026-10-14T00:00:00+08:00",
                 authorization_ref="derived: H (SWS Sept 2026) + 2D (PSA Jul-Sep 2026)", granularity="province-quarter",
                 **common)
    reg.register("d_quarterly_panel", "indicator", str(INP / "d_quarterly_panel.csv"), observation_start="2021-Q1",
                 observation_end="2026-Q3", available_at="2026-10-14T15:40:00Z",
                 authorization_ref=str(CPI.relative_to(EXP)), granularity="province-quarter", **common)
    reg.register("dnow_panel", "indicator", str(INP / "dnow_panel.csv"), observation_start="2022-Q1",
                 observation_end="2026-Q3", available_at="2026-10-14T15:40:00Z",
                 authorization_ref=str(CPI.relative_to(EXP)), granularity="province-quarter", **common)
    reg.save()
    out = {"vintage": 2, "files_sha256": {n: sha(INP / n) for n in
                                          ("sws_rounds.csv", "s1_labels.csv", "d_quarterly_panel.csv", "dnow_panel.csv")},
           "vintage1_kept_at": str(V1.relative_to(EXP)), "S1_2026Q3": dict(zip(D.index, (H + 2 * D.values).round(4)))}
    (EXP / "runs" / "e31_inputs_vintage2.json").write_bytes(json.dumps(out, indent=1).encode())
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
