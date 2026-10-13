"""E24 additions: NLP stage, validation, PSA SAE ingestion, deterministic LGU ranking, leakage guards.
All fixtures are SYNTHETIC and live only in pytest's tmp_path; nothing here enters study data or results."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

E24 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(E24 / "backend_dev"))
sys.path.insert(0, str(E24 / "runner"))

from app.quarterly.config import ForecastPeriod  # noqa: E402
from app.quarterly.eligibility import classify_news  # noqa: E402
from app.quarterly.lgu_poverty import legacy_psgc, parse_sae_table, rank_lgus, validate_against_census  # noqa: E402
from app.quarterly.nlp_stage import build_news_features  # noqa: E402
from app.quarterly.periods import Quarter  # noqa: E402
from app.quarterly.validation import check_table, model_version_record  # noqa: E402

PROV = ["PH040100000", "PH040200000", "PH040300000", "PH040400000", "PH040500000"]


def period():
    r = Quarter.parse("2026-Q4")
    return ForecastPeriod(r, r.end().floor("s"))


# ------------------------------------------------------------------ NLP stage
def test_nlp_stage_uses_only_eligible_articles_and_flags_limited_signal():
    arts = pd.DataFrame([
        {"link": f"https://n.ph/{i}", "title": "Rice price hike in Cavite market", "summary": "",
         "published": "2026-11-0%dT10:00:00+08:00" % (i % 9 + 1), "province_code": PROV[0]} for i in range(6)] + [
        {"link": "https://n.ph/x", "title": "Typhoon floods Quezon farms", "summary": "",
         "published": "2026-12-05T10:00:00+08:00", "province_code": PROV[2]},
        {"link": "https://n.ph/late", "title": "Future article", "summary": "",
         "published": "2027-01-02T10:00:00+08:00", "province_code": PROV[2]}])
    c = classify_news(arts, period())
    el = c[c["eligibility"] == "ELIGIBLE"]
    out = build_news_features(el, period(), lambda df: pd.Series(0.8, index=df.index), PROV)
    rows = {r["province_code"]: r for r in out["rows"]}
    assert out["scored_articles"] == 7                               # the 2027 article never reaches scoring
    assert rows[PROV[0]]["article_count"] == 6 and rows[PROV[0]]["data_sufficiency"] == "OK"
    assert rows[PROV[2]]["article_count"] == 1 and rows[PROV[2]]["data_sufficiency"] == "LIMITED_SIGNAL"
    assert rows[PROV[1]]["article_count"] == 0 and rows[PROV[1]]["FSSI"] is None   # missing, not zero
    assert rows[PROV[0]]["trigger_market"] == 1.0 and rows[PROV[2]]["trigger_climate"] == 1.0


def test_nlp_stage_relevance_gate():
    arts = pd.DataFrame([{"link": f"https://n.ph/{i}", "title": "x", "summary": "", "province_code": PROV[0],
                          "published": "2026-11-10T10:00:00+08:00"} for i in range(3)])
    el = classify_news(arts, period())
    out = build_news_features(el, period(), lambda df: pd.Series([0.1, 0.2, 0.9], index=df.index), PROV)
    f = {r["province_code"]: r["FSSI"] for r in out["rows"]}
    assert f[PROV[0]] == pytest.approx(0.9)                         # 0.30 gate drops the two weak articles


# ------------------------------------------------------------------ validation
def test_check_table_flags_duplicates_conflicts_and_gaps():
    df = pd.DataFrame({"province_code": [PROV[0], PROV[0], PROV[1]], "quarter": ["2026-Q1"] * 3, "v": [1, 2, 3]})
    r = check_table(df, ["province_code", "quarter", "v"], key=["province_code", "quarter"], value_col="v",
                    provinces=PROV[:2], quarters=("2026-Q1", "2026-Q2"))
    assert r["duplicate_keys"] == 1 and r["conflicting_keys"] == 1 and not r["passes"]
    assert any(c["status"] == "MISSING" for c in r["non_present_cells"])
    assert check_table(df, ["nope"])["missing_columns"] == ["nope"]


def test_model_version_record(tmp_path):
    p = tmp_path / "m.bin"
    p.write_bytes(b"abc")
    r = model_version_record(p, ["a", "b"], "2026-Q2", "f" * 64, "persistence-gated")
    assert len(r["model_sha256"]) == 64 and r["features"] == ["a", "b"]


# ------------------------------------------------------------------ PSA SAE ingestion (synthetic workbook)
def census():
    return pd.DataFrame({"lgu_code": ["041001000", "041002000", "042103000", "042106000"],
                         "lgu_name": ["Agoncillo", "Alitagtag", "Bacoor", "Dasmariñas"],
                         "province_code": ["PH040500000", "PH040500000", "PH040100000", "PH040100000"],
                         "lgu_type": "municipality", "population_2020": [100, 200, 900, 800],
                         "land_area_km2": [10.0, 10.0, 10.0, 10.0]})


def test_legacy_psgc():
    assert legacy_psgc("0401001000") == "041001000" and legacy_psgc(41001000) == "041001000"
    assert legacy_psgc("1381300000") is None and legacy_psgc(None) is None
    assert legacy_psgc(401001000) == "041001000"          # 10-digit code read back from Excel as a number


def test_sae_workbook_ingestion_and_validation(tmp_path):
    wb = pd.DataFrame({"PSGC": ["0401001000", "0402103000", "1381300000", "0401002000"],
                       "City/Municipality": ["Agoncillo", "Bacoor", "Elsewhere", "Alitagtag"],
                       "2021 Poverty Incidence (%)": [12.5, 3.1, 9.9, 140.0],
                       "2021 Standard Error": [1.0, 0.5, 1.0, 2.0]})
    f = tmp_path / "sae.xlsx"
    wb.to_excel(f, index=False)
    sae = parse_sae_table(pd.read_excel(f), 2021)          # numeric codes (leading zero lost)
    sae_txt = parse_sae_table(pd.read_excel(f, dtype=str), 2021)
    assert sae["lgu_code"].tolist() == sae_txt["lgu_code"].tolist()
    m, rep = validate_against_census(sae, census())
    assert rep["matched"] == 3 and rep["census_lgus_without_estimate"] == ["Dasmariñas"]
    assert rep["out_of_range_values"] == ["041002000"] and not rep["passes"]      # 140% is rejected


# ------------------------------------------------------------------ ranking
def test_ranking_labels_substitutes_and_is_deterministic():
    pov = pd.DataFrame({"lgu_code": census()["lgu_code"], "poverty_lgu_estimate": [12.0, None, 3.0, None],
                        "poverty_province_value": [10.0, 10.0, 4.0, 4.0], "poverty_source": "test"})
    r1 = rank_lgus(census(), pov, {"PH040500000": 0.5, "PH040100000": 0.5})
    r2 = rank_lgus(census().sample(frac=1, random_state=1), pov.sample(frac=1, random_state=2),
                   {"PH040500000": 0.5, "PH040100000": 0.5})
    assert r1["lgu_code"].tolist() == r2["lgu_code"].tolist()                    # input order does not matter
    sub = r1.set_index("lgu_code")
    assert sub.loc["041002000", "poverty_value_kind"].startswith("province-mean substitute")
    assert sub.loc["041002000", "poverty_lgu_estimate"] != sub.loc["041002000", "poverty_lgu_estimate"]   # NaN
    assert "density only" in sub.loc["042106000", "limitation"]
    none = rank_lgus(census(), pov, {"PH040500000": 0.5})                        # Cavite has no forecast
    assert none.set_index("lgu_code").loc["042103000", "risk_index"] != none.set_index("lgu_code").loc["042103000", "risk_index"]
    assert none.tail(2)["province_code"].eq("PH040100000").all()


def test_tie_rule_competition_rank():
    c = census().assign(population_2020=[100, 100, 100, 100])
    pov = pd.DataFrame({"lgu_code": c["lgu_code"], "poverty_lgu_estimate": [5.0, 5.0, 5.0, 5.0],
                        "poverty_province_value": 5.0, "poverty_source": "t"})
    r = rank_lgus(c, pov, {"PH040500000": 0.5, "PH040100000": 0.5})
    assert r["rank_region"].tolist() == [1, 1, 1, 1] and r["lgu_code"].tolist() == sorted(c["lgu_code"])


# ------------------------------------------------------------------ leakage guards in the E24 runner
def test_pblock_uses_only_published_labels():
    import run_e24 as RE
    V = pd.DataFrame({"province_code": ["A"] * 4, "quarter": ["2024-Q1", "2024-Q2", "2024-Q3", "2024-Q4"],
                      "v": [1.0, 2.0, 30.0, 40.0]})
    V["tq"] = V["quarter"].map(RE.qk)
    pub = lambda q, t: RE.qk(q) <= t - 1                                         # T2 rule
    rows = pd.DataFrame({"t": [RE.qk("2024-Q3")], "province_code": ["A"]})
    out = RE.pblock(V, pub, rows, 5.0, {})
    assert out["v_last"].iloc[0] == 2.0 and out["y_last"].iloc[0] == 0.0          # 2024-Q3/Q4 never visible


def test_prospective_sealing_refuses_without_authorized_2026_features(capsys):
    import seal_prospective as SP
    assert SP.main(["--origin-quarter", "2026-Q3"]) == 2
    assert "REFUSED" in capsys.readouterr().out
