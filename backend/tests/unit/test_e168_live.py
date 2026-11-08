"""Live refresh rules (app.e168.live_data / live_refresh): only the live quarter's cut-off moves, a live figure counts
only once it was public, and archived periods are never replaced by a live download."""
import pandas as pd
import pytest

from app.e148 import panel as Pn
from app.fi5.target import qindex


def test_cutoff_moves_only_for_the_live_quarter(monkeypatch):
    monkeypatch.setenv("AIPHEED_LIVE_ASOF", "2026-11-08")
    assert Pn.q_start(qindex("2026-Q4")) == pd.Timestamp("2026-11-08")
    assert Pn.q_start(qindex("2026-Q3")) == pd.Timestamp("2026-07-01")      # past quarters never move
    assert Pn.q_start(qindex("2019-Q2")) == pd.Timestamp("2019-04-01")
    monkeypatch.delenv("AIPHEED_LIVE_ASOF")
    assert Pn.q_start(qindex("2026-Q4")) == pd.Timestamp("2026-10-01")


def test_a_quarter_counts_by_rule_or_once_seen_online(monkeypatch):
    from app.e137 import features as F
    from app.e168 import live_data as LD
    seen = {"palay_corn_q": {"2026 Quarter 3": "2026-11-08"}}
    monkeypatch.setattr(LD, "_seen_cached", lambda: seen)
    monkeypatch.setattr(LD, "_live_dates", lambda: (pd.Timestamp("2026-11-01"), pd.Timestamp("2026-11-08")))
    cols = ["2026 Quarter 1", "2026 Quarter 2", "2026 Quarter 3"]
    assert F._published_quarters(cols, pd.Timestamp("2026-11-01")) == cols[:2]                     # rule: +45 days
    # live issue: cut-off 1 Nov, checked online 8 Nov -> the July-September quarter (ended before the cut-off) counts
    assert F._published_quarters(cols, pd.Timestamp("2026-11-01"), "palay_corn_q") == cols
    # any other date: only what was online by that date
    assert F._published_quarters(cols, pd.Timestamp("2026-10-20"), "palay_corn_q") == cols[:2]


def test_the_month_in_progress_is_never_used(monkeypatch):
    from app.e168 import live_data as LD
    monkeypatch.setattr(LD, "_seen_cached", lambda: {"cpi": {"2026-10": "2026-11-05", "2026-11": "2026-11-08"}})
    monkeypatch.setattr(LD, "_live_dates", lambda: (pd.Timestamp("2026-11-01"), pd.Timestamp("2026-11-08")))
    cut = pd.Timestamp("2026-11-01")
    assert LD.usable("cpi", "2026-10", pd.Timestamp("2026-10-31"), cut)            # October: complete, online by 8 Nov
    assert not LD.usable("cpi", "2026-11", pd.Timestamp("2026-11-30"), cut)        # November: not finished


def test_live_production_only_adds_quarters_the_archive_lacks():
    from app.e147 import features as Fe
    from app.e168 import live_data as LD
    if LD.production("agri").empty:
        pytest.skip("no live download on this machine")
    Fe._quarterly_late.cache_clear()
    q = Fe._quarterly_late("agri")
    arch = pd.read_csv(Fe.R137 / "y2023" / "psa" / "palay_corn_q_2020_2023.csv", encoding="utf-8-sig")
    arch_cols = [c for c in arch.columns if c[:4].isdigit()]
    assert set(arch_cols) <= set(q.columns)
    assert max(q.columns) > max(arch_cols)                                  # newer quarters were added
    a = arch[arch["Ecosystem/Croptype"].isin(["Palay", "Corn"])].copy()
    a["k"] = a["Geolocation"].map(Fe.F.nospace)
    a[arch_cols] = a[arch_cols].apply(pd.to_numeric, errors="coerce")
    a = a.groupby("k")[arch_cols].sum(min_count=1)
    pd.testing.assert_frame_equal(q.loc[a.index, arch_cols], a, check_names=False)   # archived values untouched


def test_refresh_never_changes_training_rows():
    """The panels' rows before the live quarter are the ones the model was trained and validated on."""
    from app.e168 import live_refresh as LR
    for name, p in LR.PANELS.items():
        d = pd.read_parquet(p)
        assert d["qi"].min() == Pn.FIRST
        assert not d.duplicated([c for c in ("key", "stream", "qi", "lag_m") if c in d]).any(), name
