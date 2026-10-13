"""
E9 allowlist-only input frame and S1 targets.

Import AFTER guard.install(). Reads data ONLY through guard.read_allowed_parquet() and the hash-pinned
CSVs used by the timing helpers. Never calls devprotocol_rule_l.development_frame(),
eligible_training_quarters() or window2021_study (those load sws_hunger.parquet and news carriers).

Timing rules reused unchanged from scripts/supplementary/devprotocol_rule_l.py (development protocol):
  SWS: latest round with a recorded publication date strictly before the origin (sws_known).
  Provincial CPI: final-month release of the reference quarter, national date + 14 d (WD1 proxy)
                  except 2024-Q4 (verified); reference quarter = target - 2.
  Regional CPI (headline, food-minus-headline): national release date of the reference quarter.
  LFS unemployment: documented schedule, reference-quarter end + 45 d (SCHEDULE_DAYS).
  Poverty: survey vintages released 2022-08-15 (2021 survey) and 2024-08-15 (2023 survey).
  Labels: Rule L1 (label_published): both the definition-A SWS round(s) and the provincial CPI
          final month published before the origin.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

QMIN, QMAX = "2021-Q1", "2025-Q4"          # eligible window: nothing after 2025-Q4 is read or built
POVERTY_RELEASES = [(pd.Timestamp("2024-08-15"), 2023), (pd.Timestamp("2022-08-15"), 2021)]  # else 2018 survey (stored as 2020)
UNEMP_DAYS = 45
IMPOSSIBLE_ZERO = ["unemployment_rate", "headline_cpi", "poverty_incidence"]  # exact 0.0 cannot be a real value


# ------------------------------------------------------------------ quarter helpers (pure)
def qi(q: str) -> int:
    y, k = q.split("-Q")
    return int(y) * 4 + int(k) - 1


def qs(i: int) -> str:
    return f"{i // 4}-Q{i % 4 + 1}"


def qadd(q: str, n: int) -> str:
    return qs(qi(q) + n)


def qstart(q: str) -> pd.Timestamp:
    y, k = q.split("-Q")
    return pd.Timestamp(year=int(y), month=3 * (int(k) - 1) + 1, day=1)


def quarter_range(a: str, b: str) -> list[str]:
    return [qs(i) for i in range(qi(a), qi(b) + 1)]


# ------------------------------------------------------------------ feature construction (pure)
def grid(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """quarter x province matrix; duplicates are an error; missing stays NaN."""
    if df.duplicated(["province_code", "quarter"]).any():
        raise ValueError(f"duplicate province-quarter rows for {col}")
    return df.pivot(index="quarter", columns="province_code", values=col)


def _val(g: pd.DataFrame, q: str, p: str) -> float:
    try:
        v = g.at[q, p]
    except KeyError:
        return np.nan
    return float(v) if pd.notna(v) else np.nan


def provincial_cpi_features(yoy: pd.DataFrame, ref: str, provinces: tuple[str, ...]) -> dict[str, dict[str, float]]:
    """Features for reference quarter `ref` (already T-2). cpi_rel needs all five provinces."""
    ref1 = qadd(ref, -1)
    out = {}

    def rel(q):
        vals = [_val(yoy, q, p) for p in provinces]
        if any(np.isnan(v) for v in vals):
            return {p: np.nan for p in provinces}
        m = float(np.mean(vals))
        return {p: v - m for p, v in zip(provinces, vals)}

    r0, r1 = rel(ref), rel(ref1)
    for p in provinces:
        x0, x1 = _val(yoy, ref, p), _val(yoy, ref1, p)
        hist = [_val(yoy, qadd(ref, -k), p) for k in range(1, 5)]
        hist = [h for h in hist if not np.isnan(h)]
        out[p] = {"food_cpi_yoy": x0, "food_cpi_yoy_lag1": x1, "food_cpi_yoy_accel": x0 - x1,
                  "cpi_rel": r0[p], "cpi_rel_lag1": r1[p],
                  "cpi_dev": (x0 - float(np.mean(hist))) if len(hist) >= 2 and not np.isnan(x0) else np.nan}
    return out


def poverty_survey_year(origin: pd.Timestamp) -> int:
    for released, year in POVERTY_RELEASES:
        if released < origin:
            return year
    return 2020


def last_published(stress: pd.DataFrame, target: str, published) -> tuple[str | None, dict[str, float]]:
    """Latest COMPLETE labelled quarter q < target whose label was published before the target's origin."""
    origin = qstart(target)
    cands = [q for q in sorted(stress["quarter"].unique(), key=qi)
             if qi(q) < qi(target) and (published(q) is not None and published(q) < origin)]
    if not cands:
        return None, {}
    a = cands[-1]
    s = stress[stress["quarter"] == a].set_index("province_code")["stress"]
    return a, s.to_dict()


def eligible_training_quarters(stress: pd.DataFrame, target: str, published) -> list[str]:
    origin = qstart(target)
    return [q for q in sorted(stress["quarter"].unique(), key=qi)
            if qi(q) < qi(target) and published(q) is not None and published(q) < origin]


# ------------------------------------------------------------------ loading (guarded)
def load_sources(guard) -> dict:
    psa = guard.read_allowed_parquet("data/processed/psa_indicators.parquet",
                                     ["province_code", "quarter", "food_cpi_yoy"])
    ff = guard.read_allowed_parquet("data/processed/features_fused.parquet",
                                    ["province_code", "quarter", "unemployment_rate", "poverty_incidence",
                                     "headline_cpi", "food_minus_headline_yoy"])
    lab = guard.read_allowed_parquet("data/processed/labels.parquet",
                                     ["province_code", "quarter", "sws_hunger_pct", "stress_score"])
    for d in (psa, ff, lab):
        d.drop(d[(d["quarter"] < QMIN) | (d["quarter"] > QMAX)].index, inplace=True)
    zero_counts = {c: int((ff[c] == 0.0).sum()) for c in IMPOSSIBLE_ZERO}
    for c in IMPOSSIBLE_ZERO:
        ff.loc[ff[c] == 0.0, c] = np.nan
    return {"psa": psa, "ff": ff, "lab": lab, "impossible_zero_set_missing": zero_counts}


def s1_targets(D, R, psa: pd.DataFrame) -> tuple[pd.DataFrame, list]:
    """S1 stress from its components: definition-A SWS rounds (quarter <= 2025-Q4) and provincial food CPI YoY."""
    rounds = [r for r in D.sws_rounds() if qi(r.quarter) <= qi(QMAX)]
    sws = pd.DataFrame([{"quarter": r.quarter, "sws_hunger_pct": r.value}
                        for r in rounds if r.in_label_definition_A])
    st = R.compute_stress(sws, psa[["province_code", "quarter", "food_cpi_yoy"]])
    complete = st.dropna(subset=["stress"]).groupby("quarter").filter(lambda g: len(g) == len(R.PROVINCES))
    return complete.reset_index(drop=True), rounds


def build_frame(D, R, src: dict, stress: pd.DataFrame, rounds: list, targets: list[str]) -> pd.DataFrame:
    provinces = R.PROVINCES
    yoy = grid(src["psa"], "food_cpi_yoy")
    ff = src["ff"]
    g_unemp, g_head, g_fmh = grid(ff, "unemployment_rate"), grid(ff, "headline_cpi"), grid(ff, "food_minus_headline_yoy")
    pov = ff.assign(year=ff["quarter"].str[:4].astype(int)).dropna(subset=["poverty_incidence"]) \
            .groupby(["province_code", "year"])["poverty_incidence"].first()
    published = lambda q: D.label_published(q, "development")[0]
    rows = []
    for t in targets:
        origin = qstart(t)
        ref, ref1 = qadd(t, -2), qadd(t, -3)
        sw = D.sws_known(origin, rounds)
        pc_pub, pc_type = D.cpi_published(ref, provincial=True)
        rc_pub, rc_type = D.cpi_published(ref, provincial=False)
        un_pub = qstart(qadd(ref, 1)) + pd.Timedelta(days=UNEMP_DAYS)
        pv_year = poverty_survey_year(origin)
        anchor, lps = last_published(stress, t, published)
        anchor_pub = D.label_published(anchor, "development") if anchor else (None, None)
        pcf = provincial_cpi_features(yoy, ref, provinces)
        for p in provinces:
            r = {"province_code": p, "target_quarter": t, "origin": origin.date().isoformat(),
                 "sws_hunger": sw["sws_hunger"], "sws_change": sw["sws_change"],
                 "sws_round": sw["sws_round"], "sws_round_quarter": sw["sws_round_quarter"],
                 "sws_published": None if sw["sws_published"] is None else pd.Timestamp(sw["sws_published"]).date().isoformat(),
                 "sws_date_type": sw["sws_date_type"],
                 "sws_age": (qi(t) - qi(sw["sws_round_quarter"])) if sw["sws_round_quarter"] else np.nan,
                 "anchor_quarter": anchor, "last_published_stress": lps.get(p, np.nan),
                 "anchor_published": None if anchor_pub[0] is None else anchor_pub[0].date().isoformat(),
                 "anchor_date_type": anchor_pub[1],
                 "cpi_reference_quarter": ref, "prov_cpi_published": pc_pub.date().isoformat(), "prov_cpi_date_type": pc_type,
                 "reg_cpi_published": rc_pub.date().isoformat(), "reg_cpi_date_type": rc_type,
                 "unemp_available": un_pub.date().isoformat(), "unemp_date_type": "schedule",
                 "poverty_survey": pv_year, "poverty_date_type": "documented-release"}
            prov_ok = pc_pub < origin
            for k, v in pcf[p].items():
                r[k] = v if prov_ok else np.nan
            reg_ok = rc_pub < origin
            r["headline_cpi"] = _val(g_head, ref, p) if reg_ok else np.nan
            r["food_minus_headline_yoy"] = _val(g_fmh, ref, p) if reg_ok else np.nan
            r["food_minus_headline_yoy_lag1"] = _val(g_fmh, ref1, p) if reg_ok else np.nan
            r["unemployment_rate"] = _val(g_unemp, ref, p) if un_pub < origin else np.nan
            r["poverty_incidence"] = float(pov.get((p, pv_year), np.nan))
            rows.append(r)
    return pd.DataFrame(rows)
