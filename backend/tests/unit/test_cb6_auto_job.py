"""The automatic C-B6 update: served-row layout, source parsers, and the quarterly job on a simulated clock."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.cb6_auto import config as C
from app.cb6_auto import features as F
from app.cb6_auto import frozen as Z

SEED = C.SEED


@pytest.fixture(scope="module")
def data():
    return F.load(SEED)


# ================================================================================================ served-row layout
def test_served_row_matches_the_export_at_the_frozen_origin(data):
    """The job's row writer, on the frozen origin, gives the export's 2027-Q1 rows: probability, score, SHAP, drivers."""
    from app.cb6_auto import job as J

    t = F.qi("2026-Q3")
    rows = F.rows_origin(data, t)
    x = next(r for r in rows if r["lead"] == 2)
    s = Z.score([x])[0]
    export = C.BACKEND / "data" / "foodinsecurity_engine_cb6"
    ev = json.loads((export / "evaluation.json").read_text(encoding="utf-8"))
    hist = pd.read_csv(SEED / "shap_history.csv")
    new = J.served_rows(x, s, ev["province_poverty"], hist, "2026-08", {}, "abc")
    old = pd.read_csv(export / "rows.csv", dtype={"province_code": str})
    old = old[old["quarter"] == "2027-Q1"].set_index("province_code")
    assert len(new) == 5
    head = list(pd.read_csv(export / "rows.csv", nrows=0).columns)
    for r in new:
        assert set(head) <= set(r), set(head) - set(r)
        o = old.loc[r["province_code"]]
        assert (r["quarter"], r["issue_date"], r["lead"], r["origin"], r["class"]) == (
            o["quarter"], o["issue_date"], o["lead"], o["origin"], o["class"])
        for c in ("probability", "score", "pov_weight", "h_last", "shap_market", "shap_climate", "shap_fish_kill", "shap_hunger",
                  "shap_news", "shap_lead", "shap_supply", "avg8_shap_market", "avg8_shap_climate", "avg8_shap_fish_kill",
                  "avg8_n", "val_R_food_yoy", "val_R_rice_yoy", "val_ONI_last", "val_tc_mean", "val_R_C3", "val_R_C4",
                  "val_W_rice_yoy"):
            assert abs(float(r[c]) - float(o[c])) < 2e-6, (c, r[c], o[c])


def test_news_n1r_port_equals_history():
    """N1R from the store and score files equals the stored table's value."""
    from app.cb6_auto import news as NW

    class Empty:
        articles: dict = {}

        def read(self, _):
            return []
    h = pd.read_csv(SEED / "n1r_history.csv").set_index("t")["N1R"]
    checked = 0
    for t in h.index[h.index >= F.qi("2021-Q1")]:
        got = NW.n1r_asof(int(t), Empty(), require_complete=False)["n1r"]
        assert (np.isnan(got) and np.isnan(h[t])) or abs(got - h[t]) < 1e-9, (F.qs(int(t)), got, h[t])
        checked += int(not np.isnan(got))
    assert checked >= 15


def test_partial_quarter_news_gives_a_missing_input():
    """Stored scores stop at 2026-10-14, so 2026-Q4 has a mean of 5+ articles but is not a whole quarter: missing, with why."""
    from app.cb6_auto import news as NW

    class Empty:
        articles: dict = {}

        def read(self, _):
            return []
    t = F.qi("2026-Q4")
    assert not np.isnan(NW.n1r_asof(t, Empty(), require_complete=False)["n1r"])
    r = NW.n1r_asof(t, Empty())
    assert np.isnan(r["n1r"]) and "days before the issue date" in r["incomplete"]


# ================================================================================================ source parsers
PX_CSV = ("Geolocation,Commodity Description,2026 Jan,2026 Feb\n"
          "..Region IV-A (CALABARZON),0 - ALL ITEMS,130.1,..\n"
          "..Region IV-A (CALABARZON),01.1 - FOOD,140.2,141.3\n")


def test_px_tidy_keeps_missing_cells_missing():
    from app.cb6_auto import fetchers as K

    t = K.tidy_px(PX_CSV, "month")
    assert len(t) == 4
    a = t[t["item"] == "0 - ALL ITEMS"].sort_values("ym")
    assert a["value"].iloc[0] == 130.1 and np.isnan(a["value"].iloc[1])
    assert a["ym"].iloc[0] == 2026 * 12


def test_blank_cell_never_erases_and_short_reply_is_refused():
    from app.cb6_auto import fetchers as K

    old = pd.DataFrame({"item": ["x"] * 4, "ym": [1, 2, 3, 4], "value": [1.0, 2.0, 3.0, 4.0]})
    new = pd.DataFrame({"item": ["x"] * 5, "ym": [1, 2, 3, 4, 5], "value": [1.0, 2.5, 3.0, np.nan, 5.0]})
    out = K._keep_history(old, new, ["item", "ym"], "t").set_index("ym")["value"]
    assert out[2] == 2.5 and out[4] == 4.0 and out[5] == 5.0
    broken = pd.DataFrame({"item": ["x"] * 4, "ym": [1, 2, 3, 4], "value": [np.nan, np.nan, np.nan, 4.0]})
    with pytest.raises(K.SourceRefused):
        K._keep_history(old, broken, ["item", "ym"], "t")


def test_oni_ndj_season_ends_in_the_next_year():
    from app.cb6_auto import fetchers as K

    text = "SEAS YR TOTAL ANOM\n" + "\n".join(f" NDJ {y} 26.0 {0.1:.2f}" for y in range(1000, 1801))
    r = K.parse_oni(text).iloc[0]
    assert (r["end_year"], r["end_month"], r["YR"]) == (1001, 1, 1000)
    with pytest.raises(K.SourceRefused):
        K.parse_oni("garbage")


def test_typhoon_counts_only_completed_quarters():
    from app.cb6_auto import fetchers as K

    cen = {"PH040100000": (14.3, 120.9)}
    csv = ("SID,ISO_TIME,LAT,LON\n,,,\n"
           "A,2026-07-01 00:00:00,10,170\n"
           "B,2026-10-05 00:00:00,14.5,121.0\nB,2026-10-05 03:00:00,14.6,121.1\nC,2026-11-05 00:00:00,14.5,121.0\n"
           "D,2027-01-02 00:00:00,14.5,121.0\n")
    out = K.typhoon_counts(csv.encode(), cen, pd.Timestamp("2027-01-03", tz="UTC"))
    assert out["quarter"].tolist() == ["2026-Q4"]              # the first quarter may be partial; the running one has no row
    assert out["tc_count"].tolist() == [2]


RELEASE = ("<p>The national Social Weather Survey of March 3-9, 2027, found that 20.0% of Filipino families experienced hunger.</p>"
           "<p>As of March 2027, hunger was highest in Metro Manila at 25.0%, followed by Balance Luzon (or Luzon outside Metro "
           "Manila) at 21.0%, Mindanao and the Visayas, both at 18.0% [ Chart 3, Table 2 ].</p>"
           "<p>In Balance Luzon, Moderate Hunger rose by 1.0 point from 13.0% to 14.0%, while Severe Hunger rose by 1.0 point "
           "from 6.0% to 7.0% [Chart 5].</p><p>face-to-face interviews of 1,200 adults: 300 each in Metro Manila, Balance Luzon, "
           "the Visayas, and Mindanao.</p>")


def test_sws_release_parser():
    from app.cb6_auto import fetchers as K

    r = K.parse_sws_release("SOCIAL WEATHER REPORT | Hunger at 20.0%", RELEASE, "2027-04-02T10:00:00", "https://sws.org.ph/x")
    assert (r["quarter"], r["fieldwork"], r["published"]) == ("2027-Q1", "2027-03-03/2027-03-09", "2027-04-02")
    assert (r["national"], r["metro_manila"], r["balance_luzon"], r["visayas"], r["mindanao"]) == (20.0, 25.0, 21.0, 18.0, 18.0)
    assert r["bl_n"] == 300.0


def test_sws_inconsistent_or_changed_release_is_refused_not_guessed():
    from app.cb6_auto import fetchers as K

    with pytest.raises(K.SwsParseError):
        K.parse_sws_release("t", RELEASE.replace("to 14.0%", "to 19.0%"), "2027-04-02", "u")   # breakdown disagrees
    with pytest.raises(K.SwsParseError):
        K.parse_sws_release("t", RELEASE.replace("Balance Luzon (or Luzon outside Metro Manila) at 21.0%", "Luzon 21.0%"),
                            "2027-04-02", "u")
    assert not K.is_hunger_release("SOCIAL WEATHER REPORT | Stratbase-SWS March Survey: Hunger rises")
    assert not K.is_hunger_release("SOCIAL WEATHER REPORT | Net satisfaction")


def test_fetch_sws_adds_a_new_round_and_reports_an_unparsable_one(tmp_path):
    from app.cb6_auto import fetchers as K

    (tmp_path / "sws_area_rounds_full.csv").write_bytes((SEED / "sws_area_rounds_full.csv").read_bytes())
    posts = [{"title": {"rendered": "SOCIAL WEATHER REPORT | Hunger at 20.0%"}, "content": {"rendered": RELEASE},
              "date": "2027-04-02T10:00:00", "link": "https://sws.org.ph/new"},
             {"title": {"rendered": "SOCIAL WEATHER REPORT | Hunger changed layout"}, "content": {"rendered": "<p>nothing</p>"},
              "date": "2027-04-03T10:00:00", "link": "https://sws.org.ph/odd"},
             {"title": {"rendered": "SOCIAL WEATHER REPORT | Hunger old"}, "content": {"rendered": "<p>nothing</p>"},
              "date": "2024-01-01T10:00:00", "link": "https://sws.org.ph/old"}]
    r = K.fetch_sws(tmp_path, get=lambda url, *a, **k: json.dumps(posts).encode())
    assert [x["quarter"] for x in r["added"]] == ["2027-Q1"]
    assert [x["link"] for x in r["needs_human"]] == ["https://sws.org.ph/odd"]
    d = F.load(tmp_path_sources(tmp_path))
    assert (d.sws[(d.sws["q"] == F.qi("2027-Q1")) & (d.sws["area"] == "BL")]["H"] == 21.0).all()


def tmp_path_sources(tmp_path: Path) -> Path:
    for p in SEED.glob("*.csv"):
        if not (tmp_path / p.name).exists():
            (tmp_path / p.name).write_bytes(p.read_bytes())
    return tmp_path


# ================================================================================================ the quarterly job
def _extend_sources(src: Path) -> None:
    """Stand-in fetch: extends each stored file to what the rules allow on 2027-01-01, with clearly synthetic values."""
    months = range(2026 * 12 + 9, 2026 * 12 + 11)              # Oct, Nov 2026
    d = pd.read_csv(src / "cpi_ACP22.csv", dtype={"geo_code": str})
    d = d[d["ym"] < 2026 * 12 + 9]
    new = [{"geo_code": F.REGION, "item": i, "year": 2026, "month": m % 12 + 1, "ym": m, "value": v}
           for m in months for i, v in (("0 - ALL ITEMS", 135.0), ("01.1 - FOOD", 145.0))]
    pd.concat([d, pd.DataFrame(new)]).to_csv(src / "cpi_ACP22.csv", index=False)
    r = pd.read_csv(src / "cpi_rice_region.csv")
    pd.concat([r[r["ym"] < 2026 * 12 + 9],
               pd.DataFrame([{"year": 2026, "month": m % 12 + 1, "ym": m, "value": 125.0} for m in months])]
              ).to_csv(src / "cpi_rice_region.csv", index=False)
    o = pd.read_csv(src / "cov_oni.csv")
    pd.concat([o, pd.DataFrame([{"end_year": 2026, "end_month": m, "SEAS": "X", "YR": 2026, "oni": 2.0} for m in (10, 11)])]
              ).to_csv(src / "cov_oni.csv", index=False)
    p = pd.read_csv(src / "pinksheet_monthly_1960.csv")
    last = p.iloc[-1].to_dict()
    pd.concat([p, pd.DataFrame([{**last, "ym": m, "month": f"2026-{m % 12 + 1:02d}"} for m in months])]
              ).to_csv(src / "pinksheet_monthly_1960.csv", index=False)
    q3, q4 = F.qi("2026-Q3"), F.qi("2026-Q4")
    pc = pd.read_csv(src / "fisheries_GVFP1.csv", dtype={"geo_code": str})
    pc = pc[~((pc["q"] == q3) & pc["value"].isna())]
    pd.concat([pc, pd.DataFrame([{"geo_code": F.REGION, "item": "FISHERIES", "year": 2026, "quarter": 3, "q": q3, "value": 50000.0}])]
              ).to_csv(src / "fisheries_GVFP1.csv", index=False)
    t = pd.read_csv(src / "typhoons_province_quarter.csv", dtype={"province_code": str})
    pd.concat([t, pd.DataFrame([{"province_code": c, "q": q4, "quarter": "2026-Q4", "tc_count": 2} for c in F.PROVS])]
              ).to_csv(src / "typhoons_province_quarter.csv", index=False)


def _fetchers(calls: list) -> dict:
    def extend(src):
        calls.append("extend")
        if not (src / "extended.flag").exists():
            _extend_sources(src)
            (src / "extended.flag").write_text("x")
        return {}
    return {"extend": extend, "sws_hunger": lambda src: {"added": [], "needs_human": []}}


def no_news(t):
    return {"quarter": F.qs(t), "admitted": 0, "scored": 0, "n1r": float("nan")}


@pytest.fixture()
def state(tmp_path, monkeypatch):
    from app.cb6_auto import job as J

    monkeypatch.setenv("AIPHEED_CB6_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("AIPHEED_FI_DATA_DIR", str(tmp_path / "served"))
    monkeypatch.delenv("AIPHEED_CB6_NEWS_SCORING", raising=False)
    monkeypatch.setattr(J, "stage", lambda q: {"staged_quarter": q})
    return tmp_path


def _no_training(monkeypatch):
    """Any attempt to fit a model fails the test."""
    import lightgbm as lgb

    def refuse(*a, **k):
        raise AssertionError("a model was trained")
    monkeypatch.setattr(lgb, "train", refuse)
    monkeypatch.setattr(lgb.LGBMClassifier, "fit", refuse)
    monkeypatch.setattr(lgb.LGBMRegressor, "fit", refuse)
    monkeypatch.setattr(lgb.Booster, "update", refuse)


def test_simulated_2027_01_01_issue_scores_frozen_model_and_never_trains(state, monkeypatch):
    from app.cb6_auto import job as J

    _no_training(monkeypatch)
    model_before = (C.FROZEN / "model.txt").read_bytes()
    export = C.BACKEND / "data" / "foodinsecurity_engine_cb6" / "rows.csv"
    export_before = export.read_bytes()
    calls: list = []
    r = J.run_due("2027-01-01T05:00:00+08:00", fetchers=_fetchers(calls), news_fn=no_news)
    assert r["status"] == "FORECAST_RELEASED", r
    assert r["target_quarter"] == "2027-Q2" and set(r["p_high"]) == {"2027-Q1", "2027-Q2"}
    assert r["stale"] == ["news_n1r_quarter_t"]
    assert calls                                                # the sources really were collected
    rows = pd.read_csv(state / "served" / "rows.csv", dtype={"province_code": str})
    new = rows[rows["quarter"] == "2027-Q2"]
    assert len(new) == 5 and set(new["province_code"]) == set(F.PROVS)
    assert set(new["issue_date"]) == {"2027-01-01"} and set(new["lead"]) == {2} and set(new["origin"]) == {"2026-Q4"}
    assert new["cfg"].iloc[0].startswith("frozen:") and (new["avail_news"] == 0).all()
    e = J.ledger()[0]
    f2 = next(f for f in e["forecasts"] if f["lead"] == 2)
    assert f2["inputs"]["z_N1R"] is None                        # no scored news: missing, not invented
    assert e["cutoffs"]["cpi_food_month"] == "2026-11" and e["cutoffs"]["sws_newest_quarter"] == "2026-Q3"
    assert f2["inputs"]["true_h"] == 3.0                        # 2027-Q2 minus 2026-Q3
    assert abs(f2["p_high"] - new["probability"].iloc[0]) < 1e-6
    assert (C.FROZEN / "model.txt").read_bytes() == model_before and export.read_bytes() == export_before
    old = pd.read_csv(export, dtype={"province_code": str})
    pd.testing.assert_frame_equal(rows[rows["quarter"] != "2027-Q2"].reset_index(drop=True), old, check_dtype=False)
    assert J.verify_ledger()


def test_second_run_same_quarter_changes_nothing(state):
    from app.cb6_auto import job as J

    r = J.run_due("2027-01-01T05:00:00+08:00", fetchers=_fetchers([]), news_fn=no_news)
    assert r["status"] == "FORECAST_RELEASED"
    a = (state / "served" / "rows.csv").read_bytes()
    r2 = J.run_due("2027-01-02T05:00:00+08:00", fetchers=_fetchers([]))
    assert r2["status"] == "NOTHING_DUE" and (state / "served" / "rows.csv").read_bytes() == a and len(J.ledger()) == 1


def test_source_down_waits_then_issues_with_it_recorded_stale(state):
    from app.cb6_auto import job as J

    only_sws = {"sws_hunger": lambda src: {"added": [], "needs_human": []}}
    r = J.run_due("2027-01-02T05:00:00+08:00", fetchers=only_sws, news_fn=no_news)
    assert r["status"] == "WAITING" and "cpi_food_month2" in r["blocking"]
    assert not J.ledger()
    r = J.run_due("2027-01-09T05:00:00+08:00", fetchers=only_sws, news_fn=no_news)
    assert r["status"] == "FORECAST_RELEASED" and "cpi_food_month2" in r["stale"]
    f = next(x for x in J.ledger()[0]["forecasts"] if x["lead"] == 2)
    assert f["inputs"]["R_food_yoy"] is None and f["inputs"]["ONI_last"] is None        # missing stays missing


def test_fetch_failure_is_recorded_and_leaves_the_file_alone(state):
    from app.cb6_auto import job as J

    J.ensure_state()
    before = (C.sources_dir() / "cov_oni.csv").read_bytes()

    def boom(src):
        raise RuntimeError("source down")
    r = J.run_due("2027-01-02T05:00:00+08:00", fetchers={"noaa_oni": boom}, news_fn=no_news)
    assert r["sources"]["noaa_oni"]["ok"] is False and "source down" in r["sources"]["noaa_oni"]["error"]
    assert (C.sources_dir() / "cov_oni.csv").read_bytes() == before


def test_unparsable_sws_release_waits_then_goes_out_flagged(state):
    from app.cb6_auto import job as J

    odd = [{"title": "x", "link": "u", "published": "2026-12-15", "reason": "layout"}]
    calls: list = []
    fs = {**_fetchers(calls), "sws_hunger": lambda src: {"added": [], "needs_human": odd}}
    r = J.run_due("2027-01-02T05:00:00+08:00", fetchers=fs, news_fn=no_news)
    assert r["status"] == "WAITING" and r["needs_human"] == odd
    r = J.run_due("2027-01-08T05:00:00+08:00", fetchers=fs, news_fn=no_news)
    assert r["status"] == "FORECAST_RELEASED" and r["needs_human"] == odd


def test_missed_window_is_recorded_and_never_backfilled(state):
    from app.cb6_auto import job as J

    r = J.run_due("2027-01-20T05:00:00+08:00", fetchers=_fetchers([]))
    assert r["status"] == "MISSED" and not J.ledger()
    r = J.run_due("2027-04-01T05:00:00+08:00", fetchers=_fetchers([]), news_fn=no_news)
    assert r["status"] in ("WAITING", "FORECAST_RELEASED")
    assert all(e["issue_date"] != "2027-01-01" for e in J.ledger())


def test_before_first_issue_and_without_config_nothing_happens(state, monkeypatch):
    from app.cb6_auto import job as J

    assert J.run_due("2026-11-04T05:00:00+08:00")["status"] == "NOTHING_DUE"
    monkeypatch.delenv("AIPHEED_FI_DATA_DIR")
    assert J.run_due("2027-01-01T05:00:00+08:00")["status"] == "NOT_CONFIGURED"


def test_existing_forecast_cannot_be_overwritten(state):
    from app.cb6_auto import job as J

    J.ensure_state()
    rows = pd.read_csv(state / "served" / "rows.csv", dtype=str)
    clash = rows[rows["quarter"] == "2027-Q1"].fillna("").to_dict("records")
    with pytest.raises(ValueError):
        J.append_served(state / "served" / "rows.csv", clash)


def test_restart_keeps_stored_forecasts(state):
    from app.cb6_auto import job as J

    r = J.run_due("2027-01-01T05:00:00+08:00", fetchers=_fetchers([]), news_fn=no_news)
    assert r["status"] == "FORECAST_RELEASED"
    a = (state / "served" / "rows.csv").read_bytes()
    J.ensure_state()
    assert (state / "served" / "rows.csv").read_bytes() == a


def test_crash_after_ledger_write_is_finished_from_the_ledger(state, monkeypatch):
    from app.cb6_auto import job as J

    real = J.append_served
    monkeypatch.setattr(J, "append_served", lambda *a: (_ for _ in ()).throw(OSError("disk")))
    with pytest.raises(OSError):
        J.run_due("2027-01-01T05:00:00+08:00", fetchers=_fetchers([]), news_fn=no_news)
    monkeypatch.setattr(J, "append_served", real)
    r = J.run_due("2027-01-02T05:00:00+08:00", fetchers=_fetchers([]))
    assert r["status"] == "NOTHING_DUE"
    rows = pd.read_csv(state / "served" / "rows.csv", dtype={"province_code": str})
    assert (rows["quarter"] == "2027-Q2").sum() == 5


def test_package_has_no_training_calls():
    src = "\n".join(p.read_text(encoding="utf-8") for p in (C.BACKEND / "app" / "cb6_auto").glob("*.py"))
    for needle in (".fit(", "lgb.train", "lightgbm.train", "LGBMClassifier", "lgbm_select", "GridSearch", "save_model"):
        assert needle not in src, needle


def test_scheduler_registers_only_the_auto_update(monkeypatch):
    from app.tasks import scheduler as S

    monkeypatch.setattr(S, "ENABLED", True)
    monkeypatch.setattr(S, "_scheduler", None)
    sch = S.start_scheduler()
    try:
        jobs = sch.get_jobs()
        assert [j.id for j in jobs] == [S.AUTO_JOB_ID]
        assert jobs[0].misfire_grace_time == 86400 and jobs[0].next_run_time is not None
    finally:
        S.shutdown_scheduler()
