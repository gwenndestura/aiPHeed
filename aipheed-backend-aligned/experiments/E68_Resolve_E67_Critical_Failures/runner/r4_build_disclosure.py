"""E68 r4 (PROTOCOL 7): build backend/data/e68/e68_disclosure.json for the e68 serving mode from the E68 outputs and the
model's own feature table at the two issued origins (2026-07-01 -> 2026-Q4, 2026-10-01 -> 2027-Q1).

Each input is classified at its issue date: observed | observed_zero | missing | stale | substituted |
too_few_articles | not_collected, with its period and data age. Nothing here changes a forecast.

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E68_Resolve_E67_Critical_Failures/runner/r4_build_disclosure.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e68_lib as R  # noqa: E402

H, L, E, np, pd = R.H, R.L, R.E, R.np, R.pd
DEST = H.BACKEND / "data" / "e68" / "e68_disclosure.json"
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def _f(v):
    return None if v is None or (isinstance(v, float) and not np.isfinite(v)) else round(float(v), 2)


def statuses(row: pd.Series, t: int) -> list[dict]:
    q, q1 = L.qs(t), L.qs(t - 1)
    cpi_month = f"{q[:4]}-{int(q[-1]) * 3 - 1:02d}"           # month 2 of the origin quarter
    h_age = row["H_age"]
    sws_q = L.qs(int(t - h_age)) if np.isfinite(h_age) else None
    out = []

    def add(key, label, group, value, period, status, note, age=None):
        out.append({"key": key, "label": label, "group": group, "value": _f(value), "period": period, "status": status,
                    "ageQuarters": age, "note": note})

    add("food_cpi", "Food inflation (PSA CPI, province)", "market", row["F_now"], f"latest two months to {cpi_month}",
        "observed", "Months published after the issue date are not used.")
    add("headline_cpi", "Headline inflation (PSA CPI, province)", "market", row["F_now"] - row["gap_now"],
        f"latest two months to {cpi_month}", "observed", "Used through the food-minus-headline gap.")
    rice = row["rice_whsl_yoy"]
    add("rice_wholesale", "Wholesale rice price (PSA, province)", "market", rice, q1,
        "missing" if not np.isfinite(rice) else "observed", "Year-on-year change.")
    add("sws_hunger", "Hunger (SWS, Balance Luzon region)", "hunger", row["H_last"], sws_q,
        "missing" if not np.isfinite(row["H_last"]) else ("stale" if h_age >= 2 else "observed"),
        "Regional figure, the same for all five provinces; the next round was posted after the issue date.",
        None if not np.isfinite(h_age) else int(h_age))
    tc = row["tc_count"]
    if q in R.INCOMPLETE_TC_QUARTERS:
        add("typhoons", "Typhoons within 300 km (IBTrACS)", "climate", tc, q, "substituted",
            "The quarter was still in progress when the data were fetched (2026-09-09); the served model stores the "
            "count so far as a number. E67 showed this changes the score by less than 0.2 percentage points.")
    else:
        add("typhoons", "Typhoons within 300 km (IBTrACS)", "climate", tc, q, "observed_zero" if tc == 0 else "observed",
            "0 means no storm passed within 300 km." if tc == 0 else "Count of storms.")
    add("enso", "ENSO phase (NOAA ONI, observed)", "climate", row["enso"], q1, "observed",
        "+1 El Nino, 0 neutral, -1 La Nina; observed only, without its strength.")
    add("enso_outlook", "PAGASA El Nino outlook", "climate", None, "issue date", "not_collected",
        "Shown in the climate watch, not a model input: one El Nino episode in 2021-2026 cannot teach its effect.")
    add("rainfall_drought", "Rainfall, dry spell and drought", "climate", None, "-", "not_collected",
        "No dated 2021-2026 PAGASA dry-spell/drought archive is available; not in the model.")
    for k, lab in (("palay_yoy", "Palay production (PSA, province)"), ("corn_yoy", "Corn production (PSA, province)")):
        v = row[k]
        add(k, lab, "climate", v, q1, "missing" if not np.isfinite(v) else "observed", "Year-on-year change.")
    for k, lab in (("fish_yoy", "Fisheries production (PSA, province)"), ("aqua_yoy", "Aquaculture production (PSA, province)")):
        v = row[k]
        add(k, lab, "fish_kill", v, q1, "missing" if not np.isfinite(v) else "observed",
            "Production, not fish-kill events.")
    add("fish_kill_events", "Fish-kill events", "fish_kill", None, "-", "not_collected",
        "No official fish-kill event series exists for 2021-2026.")
    for k, lab in (("ur_yoy", "Unemployment rate (PSA LFS)"), ("under_yoy", "Underemployment rate (PSA LFS)")):
        add(k, lab, "employment", row[k], q1, "observed", "National figure, the same for all five provinces.")
    for k, lab in (("remit_usd_yoy", "OFW cash remittances in US dollars (BSP)"), ("remit_php_yoy", "OFW cash remittances in pesos (BSP)")):
        v = row[k]
        add(k, lab, "ofw_remittance", v, q1, "missing" if not np.isfinite(v) else "observed",
            "National. The BSP file in the system ends at 2025-Q4; missing values are treated as unknown, not as no change.")
    add("fx_yoy", "USD/PHP exchange rate", "ofw_remittance", row["fx_yoy"], q1, "observed", "National.")
    n = row["news_n"]
    for k in R.NEWS_SHARES:
        v = row[k]
        st = "too_few_articles" if n < R.NEWS_MIN else ("observed_zero" if v == 0 else "observed")
        add(k, f"News titles on {k.replace('news_', '').replace('_', ' ')}", "news", v, q,
            st, f"Share of {int(n)} titles about the province this quarter.")
    return out


def main():
    R.verify_protocol()
    d, X, B = E.load()
    r3 = json.loads((R.OUT / "r3_score.json").read_text())
    T = pd.read_csv(R.TABLES / "r3_t43_arms.csv").set_index("reading")
    P = pd.read_csv(R.TABLES / "r3_t43_paired_vs_A0.csv").set_index("arm")
    kin = pd.read_csv(R.TABLES / "r1_elnino_shift.csv")
    fv = pd.read_csv(R.TABLES / "r2_face_validity_subsistence.csv")
    inputs, afford = {}, {}
    for t in R.FORWARD_ORIGINS:
        q = L.qs(t + 2)
        inputs[q], afford[q] = {}, {}
        for p in L.PROVS:
            row = X[(X["t"] == t) & (X["province_code"] == p)].iloc[0]
            name = L.NAMES[p]
            inputs[q][name] = {"issueDate": R.issue_date(t), "inputs": statuses(row, t)}
            hl = float(row["F_now"] - row["gap_now"])
            afford[q][name] = {"headline": round(hl, 2), "headlineUsual": round(R.HEADLINE_P60[p], 2),
                               "food": round(float(row["F_now"]), 2), "foodUsual": round(L.e40_spec()["food"][p], 2),
                               "headlineAbove": bool(hl > R.HEADLINE_P60[p])}
    k = kin[(kin["arm"] == "K1") & (kin["origin_quarter"] == "2023-Q4")].iloc[0]
    shift23 = json.loads(k["shift_food_m1"])
    a0, n1 = T.loc["A0"], P.loc["N1_p"]
    body = {
        "schema": "aipheed.e68.disclosure/1", "experiment": "E68_Resolve_E67_Critical_Failures",
        "protocolSha256": R.verify_protocol(), "prospectiveSealSha256": r3["sealed_sha256"],
        "targetWording": ("an exploratory food-stress score: high regional hunger (SWS) together with provincial food-price "
                          "pressure (PSA); on every evaluated quarter it reduced to food-price pressure; it is not a measure "
                          "of household food insecurity"),
        "evaluation": (f"Lead-2 back-test, 50 province-quarters in 10 quarters (2024-Q2 to 2026-Q3), all examined before "
                       f"E68: accuracy {a0['accuracy']:.2f} ({int(a0['correct'])}/50), balanced {a0['balanced_accuracy']:.2f}. "
                       "No E68 correction beats it by the pre-registered rule; the 75% goal is not met on valid evidence. "
                       "The forecasts of every E68 variant for 2026-Q4 and 2027-Q1 are sealed for scoring when the outcomes "
                       "are published."),
        "elNinoFinding": ("The only El Nino in 2021-2026 (2023-24) came while inflation was falling: food inflation ended "
                          f"{abs(max(shift23.values())):.1f} to {abs(min(shift23.values())):.1f} percentage points below the projections made "
                          "during it. The data therefore cannot estimate how much an El Nino raises CALABARZON food prices, "
                          "and the score cannot include it (E68)."),
        "faceValidity": ("PSA subsistence incidence (2021, 2023) is the only independent provincial measure in the system; "
                         f"with five provinces per year and sampling errors up to {fv['max_cv_pct'].max():.0f}% it cannot "
                         "confirm or reject the province ordering."),
        "nationalInputsNote": (f"Removing the national employment and OFW inputs improved the back-test probability score "
                               f"(Brier {n1['mean_brier_diff']:+.3f}, 95% CI {n1['ci95_lo']:+.3f} to {n1['ci95_hi']:+.3f}) "
                               "but not by the pre-registered rule; it is a candidate for the next model build."),
        "inputStatus": inputs, "affordability": afford,
    }
    body["content_sha256"] = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_bytes(json.dumps(body, indent=1, sort_keys=True).encode("utf-8"))
    print(json.dumps({k: v for k, v in body.items() if k not in ("inputStatus",)}, indent=1))
    print(json.dumps(inputs["2027-Q1"]["Quezon"], indent=1)[:3000])


if __name__ == "__main__":
    main()
