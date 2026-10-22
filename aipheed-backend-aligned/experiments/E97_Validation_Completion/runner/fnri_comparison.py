"""E97 Q7 (PROTOCOL.md): DOST-FNRI FIES figures against the system's evidence, descriptive / construct level only.
Run from backend/."""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pandas as pd

import common as C

FNRI = C.EXP / "E87_Outcome_Gap" / "data_acquired" / "fnri_fies_observations.csv"


def overlap(a, b) -> bool:
    return not (a[1] < b[0] or b[1] < a[0])


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    o = C.E97 / "runs" / f"{stamp}_fnri"
    o.mkdir(parents=True, exist_ok=True)
    f = pd.read_csv(FNRI)
    ms = f[f["indicator"] == "moderate_or_severe_FI"]
    v = pd.read_csv("data/inputs/lgu_vulnerability.csv")
    pov = v.assign(w=v["poverty_value_used"] * v["population_2024"]).groupby("province")[["w", "population_2024"]].sum()
    pov = (pov["w"] / pov["population_2024"]).round(2).to_dict()
    from app.ml.inference import firi as FI
    v1 = {FI.PROVINCES[k]: round(x, 3) for k, x in FI.vulnerability().items()}
    p21 = ms[ms["year"] == 2021].set_index("geography")
    b, c = p21.loc["Batangas"], p21.loc["Cavite"]
    s = pd.read_csv("data/inputs/sws_rounds.csv")
    s = s[s["definition_A"].astype(str) == "True"]
    sws = s.groupby("quarter")["H"].mean()
    h = pd.read_csv("data/thesis/firi2_history.csv")
    reg = h.groupby("target")["FIRI"].mean().dropna()
    year = lambda ser, y: ser[[q for q in ser.index if q.startswith(str(y))]]  # noqa: E731
    r = ms[ms["level"] == "region"].set_index("year")
    res = {
        "stamp": stamp, "protocol_sha256": (C.E97 / "PROTOCOL.sha256").read_text().split()[0],
        "construct_note": ("FIES moderate-or-severe food insecurity (12-month recall, household or population basis) is "
                           "not SWS involuntary hunger (3-month recall, Balance Luzon) and not the FIRI index; only "
                           "direction and ordering can be compared, not levels."),
        "nns_2019_calabarzon": "not published (ENNS 2019 covered 2 CALABARZON provinces; no regional estimate, E22)",
        "c1_2021_provinces": {
            "fies": {g: {"value": float(p21.loc[g, "value_pct"]), "ci90": [float(p21.loc[g, "ci_low"]), float(p21.loc[g, "ci_high"])]}
                     for g in p21.index},
            "batangas_vs_cavite_ci_overlap": overlap((b["ci_low"], b["ci_high"]), (c["ci_low"], c["ci_high"])),
            "psa_2021_poverty_pop_weighted": {g: pov.get(g) for g in ("Batangas", "Cavite", "Quezon")},
            "served_V1_profile": {g: v1.get(g) for g in ("Batangas", "Cavite")},
            "reading": "FIES 2021 cannot order Batangas and Cavite (90% CIs overlap), so no ordering check of V1 or of the poverty weights is possible.",
        },
        "c2_regional_2023_2025": {
            "fies": {int(y): {"value": float(r.loc[y, "value_pct"]), "basis": r.loc[y, "basis"]} for y in r.index},
            "sws_annual_mean_definition_A": {y: {"mean": round(float(year(sws, y).mean()), 2), "quarters": list(year(sws, y).index)} for y in (2023, 2025)},
            "firi_v2_regional_mean_lead2_targets": {y: {"mean": round(float(year(reg, y).mean()), 4), "quarters": list(year(reg, y).index)} for y in (2023, 2025)},
        },
    }
    d = res["c2_regional_2023_2025"]
    up = lambda x23, x25: x25 > x23  # noqa: E731
    d["direction_agreement"] = {
        "fies_up": up(d["fies"][2023]["value"], d["fies"][2025]["value"]),
        "sws_up": up(d["sws_annual_mean_definition_A"][2023]["mean"], d["sws_annual_mean_definition_A"][2025]["mean"]),
        "firi_up": up(d["firi_v2_regional_mean_lead2_targets"][2023]["mean"], d["firi_v2_regional_mean_lead2_targets"][2025]["mean"]),
        "caveat": "one pair of years, and the 2023 (households) and 2025 (population) FIES bases differ: a face-validity "
                  "direction check, not validation",
    }
    (o / "fnri_comparison.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main()
