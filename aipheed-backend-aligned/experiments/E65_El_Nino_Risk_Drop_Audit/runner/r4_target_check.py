"""E65 r4 (PROTOCOL section 5): can the T43 label be LOW while climate-related food stress worsens?

Uses E62's independently recomputed labels (raw PSA CPI + SWS rounds; 0 mismatches with E58/E61), the climate parquet,
the PAGASA status at each quarter's start, and provincial palay/corn production YoY (from the E56 feature table, where
the row of origin t holds production of quarter t-1). Labels and thresholds are not changed.

Also computes, descriptively, a separately named EXPLORATORY indicator (CRFS-X, PROTOCOL 5) - not a target, not validated.

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E65_El_Nino_Risk_Drop_Audit/runner/r4_target_check.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e65_lib as H  # noqa: E402

L, np, pd = H.L, H.np, H.pd
LAB = H.EXP / "E62_Final_System_Audit" / "tables" / "r1_labels_independent.csv"
H_LINE = 11.3


def main():
    H.verify_protocol()
    lab = pd.read_csv(LAB, dtype={"province_code": str})
    lab["q"] = lab["quarter"].map(L.qi)
    lab = lab[lab["T43"].notna()].copy()
    c = H.climate_raw().drop_duplicates("q").set_index("q")
    lab["enso_phase_q"] = lab["q"].map(c["enso_phase"])
    lab["enso_intensity_q"] = lab["q"].map(c["enso_intensity"])
    lab["enso_phase_q_minus1"] = lab["q"].map(lambda q: c["enso_phase"].get(q - 1))
    lab["el_nino_q_or_prev"] = (lab["enso_phase_q"] == "EL_NINO") | (lab["enso_phase_q_minus1"] == "EL_NINO")
    # PAGASA status in force at the start of the quarter = issue date O(q-1)
    lab["pagasa_status_at_quarter_start"] = lab["q"].map(
        lambda q: H.PAGASA_STATUS.get(str(L.origin(q - 1).date()), (np.nan, ""))[0])
    lab["pagasa_el_nino_alert_or_advisory"] = lab["pagasa_status_at_quarter_start"] >= 1
    d, X, B = H.E.load()
    prod = X[["t", "province_code", "palay_yoy", "corn_yoy"]].assign(q=lambda f: f["t"] - 1).drop(columns="t")
    lab = lab.merge(prod, on=["province_code", "q"], how="left")
    lab["production_drop_10pct"] = (lab["palay_yoy"] <= -10) | (lab["corn_yoy"] <= -10)
    lab["hunger_high"] = lab["H_all"] > H_LINE
    lab["T43"] = lab["T43"].astype(int)
    lab["PS"] = lab["PS"].astype(int)

    def low_when(mask, name):
        s = lab[mask]
        return {"condition": name, "rows": int(len(s)), "T43_LOW": int((s["T43"] == 0).sum()),
                "share_LOW": float((s["T43"] == 0).mean()) if len(s) else None,
                "quarters": int(s["q"].nunique())}
    checks = [low_when(lab.index == lab.index, "all labelled rows"),
              low_when(lab["hunger_high"], "regional hunger > 11.3%"),
              low_when(lab["H_all"] >= 20, "regional hunger >= 20%"),
              low_when(lab["el_nino_q_or_prev"], "ENSO El Nino in the quarter or the previous one (ONI)"),
              low_when(lab["pagasa_el_nino_alert_or_advisory"], "PAGASA El Nino Alert/Advisory at quarter start"),
              low_when(lab["production_drop_10pct"], "provincial palay or corn production YoY <= -10%"),
              low_when(lab["hunger_high"] & lab["production_drop_10pct"], "hunger > 11.3% AND production drop"),
              low_when(lab["hunger_high"] & (lab["HL"] > 4), "hunger > 11.3% AND headline inflation > 4%"),
              low_when(lab["hunger_high"] & (lab["F"] >= 4) & (lab["PS"] == 0),
                       "hunger > 11.3% AND food YoY >= 4% but below the province threshold and gap rule")]
    hh = lab[lab["hunger_high"]]
    identity = {"rows_hunger_high": int(len(hh)), "T43_equals_PS_when_hunger_high": int((hh["T43"] == hh["PS"]).sum()),
                "share_rows_hunger_high": float(lab["hunger_high"].mean()),
                "share_rows_hunger_high_2024_2026": float(lab[lab["q"] >= L.qi("2024-Q1")]["hunger_high"].mean())}
    # does the hunger level carry any information into the label once above the line?
    from scipy.stats import mannwhitneyu
    if hh["T43"].nunique() == 2:
        u = mannwhitneyu(hh[hh["T43"] == 1]["H_all"], hh[hh["T43"] == 0]["H_all"])
        identity["hunger_level_HIGH_vs_LOW_mannwhitney_p"] = float(u.pvalue)
        identity["mean_H_HIGH"], identity["mean_H_LOW"] = float(hh[hh["T43"] == 1]["H_all"].mean()), float(hh[hh["T43"] == 0]["H_all"].mean())
    el = lab[lab["q"].between(L.qi("2023-Q2"), L.qi("2024-Q3"))][
        ["province", "quarter", "enso_phase_q", "enso_intensity_q", "pagasa_status_at_quarter_start", "H_all", "F", "HL",
         "G", "thr_food", "thr_gap", "PS", "T43", "palay_yoy", "corn_yoy"]]
    recent = lab[lab["q"] >= L.qi("2025-Q4")][["province", "quarter", "enso_phase_q", "enso_intensity_q", "H_all", "F",
                                               "HL", "G", "thr_food", "thr_gap", "PS", "T43", "palay_yoy", "corn_yoy"]]
    # CRFS-X (exploratory, PROTOCOL 5): hazard = PAGASA El Nino Advisory in force at the issue date; household stress =
    # latest posted regional hunger > 11.3%; local exposure = latest provincial palay or corn production YoY <= -10%.
    cr = []
    for t in H.EVAL_ORIGINS + H.FORWARD_ORIGINS:
        hs = H.P2.h_series(d, t, False)
        h_last = float(hs[hs.index <= t].iloc[-1])
        haz = H.official_status(t) >= 2
        for p in L.PROVS:
            r = X[(X["t"] == t) & (X["province_code"] == p)].iloc[0]
            expo = bool((r["palay_yoy"] <= -10) or (r["corn_yoy"] <= -10))
            level = "CLIMATE WATCH (hazard + hunger + local production drop)" if haz and h_last > H_LINE and expo else (
                "CLIMATE WATCH (hazard + hunger)" if haz and h_last > H_LINE else "none")
            cr.append({"issue_date": str(L.origin(t).date()), "target": L.qs(t + 2), "province": L.NAMES[p],
                       "pagasa_el_nino_advisory": haz, "latest_hunger": h_last, "palay_yoy_prevq": float(r["palay_yoy"]),
                       "corn_yoy_prevq": float(r["corn_yoy"]), "local_production_drop": expo, "CRFS_X": level})
    CR = pd.DataFrame(cr)
    H.write_csv(lab, H.TABLES / "r4_labels_with_climate.csv")
    H.write_csv(pd.DataFrame(checks), H.TABLES / "r4_low_label_checks.csv")
    H.write_csv(el, H.TABLES / "r4_el_nino_2023_24_rows.csv")
    H.write_csv(recent, H.TABLES / "r4_recent_rows.csv")
    H.write_csv(CR, H.TABLES / "r4_crfs_x_exploratory.csv")
    H.dump({"protocol_sha256": H.verify_protocol(), "checks": checks, "identity": identity}, H.OUT / "r4_target_check.json")
    pd.set_option("display.width", 250)
    print(pd.DataFrame(checks).to_string(index=False))
    print(identity)
    print(el.round(2).to_string(index=False))
    print(recent.round(2).to_string(index=False))
    print(CR[CR["target"].isin(["2024-Q2", "2024-Q3", "2026-Q4", "2027-Q1"])].to_string(index=False))


if __name__ == "__main__":
    main()
