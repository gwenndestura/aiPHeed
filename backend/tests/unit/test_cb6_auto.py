"""The automatic C-B6 operation: frozen model, feature parity, fetch parsers, the quarterly job."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.cb6_auto import config as C
from app.cb6_auto import features as F
from app.cb6_auto import frozen as Z

SEED = C.SEED
INPUTS = ["h_last", "h_change", "h_mean4", "true_h", "pi_H4L", "R_food_yoy", "R_head_yoy", "R_rice_yoy", "R_food_mom",
          "ONI_last", "ONI_max12", "tc_mean", "R_C3", "R_C4", "W_rice_yoy", "W_rice_mom", "W_cereal_yoy", "W_crude_yoy",
          "W_urea_yoy", "z_N1R", "lead", "ST1", "ST2"]


@pytest.fixture(scope="module")
def data():
    return F.load(SEED)


def test_frozen_manifest_and_hash():
    m = Z.manifest()
    assert m["model_sha256"] == hashlib.sha256((C.FROZEN / "model.txt").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    assert m["columns"] == INPUTS and m["origin"] == "2026-Q3"


def test_frozen_model_reproduces_the_served_forecast():
    m = Z.manifest()
    rows = [{**m["reference_inputs_origin"][k]} for k in ("1", "2")]
    rows = [{c: (np.nan if r[c] is None else r[c]) for c in INPUTS} for r in rows]
    out = Z.score(rows)
    assert abs(out[0]["p"] - m["reproduction"]["stored_p_by_lead"]["1"]) < 1e-12
    assert abs(out[1]["p"] - m["reproduction"]["stored_p_by_lead"]["2"]) < 1e-12
    assert round(out[1]["p"], 6) == 0.955803


def test_tampered_model_is_refused(tmp_path, monkeypatch):
    for f in ("model.txt", "manifest.json"):
        (tmp_path / f).write_bytes((C.FROZEN / f).read_bytes())
    with open(tmp_path / "model.txt", "ab") as fh:
        fh.write(b"\n")
    monkeypatch.setattr(Z, "FROZEN", tmp_path)
    with pytest.raises(Z.FrozenModelError):
        Z.load()


def test_feature_parity_every_origin(data):
    """The port equals the stored development table at every origin and input (leads 1 and 2)."""
    ref = pd.read_csv(SEED / "parity_reference.csv")
    worst, bad = 0.0, []
    for t, g in ref.groupby("t"):
        built = {r["lead"]: r for r in F.rows_origin(data, int(t))}
        for _, x in g.iterrows():
            r = built[int(x["lead"])]
            for c in INPUTS:
                a, b = float(r[c]), float(x[c])
                if np.isnan(a) != np.isnan(b):
                    bad.append((int(t), int(x["lead"]), c, a, b))
                elif not np.isnan(a):
                    worst = max(worst, abs(a - b))
                    if abs(a - b) > 1e-6:
                        bad.append((int(t), int(x["lead"]), c, a, b))
    assert not bad, bad[:20]
    assert worst < 1e-6


def test_future_values_cannot_reach_an_origin(data):
    """Randomising everything after the as-of limits of origin 2024-Q2 leaves its row unchanged."""
    t = F.qi("2024-Q2")
    before = F.rows_origin(data, t)
    d = F.load(SEED)
    rng = np.random.default_rng(1)
    m0 = F.m0_of(t)
    for k, s in d.idx.items():
        s = s.copy(); s[s.index > m0] = rng.uniform(1, 500, int((s.index > m0).sum())); d.idx[k] = s
    d.oni = d.oni.copy(); d.oni[d.oni.index > m0] = 9.0
    d.pink = d.pink.copy()
    for c in d.pink.columns:
        if c != "month":
            d.pink.loc[d.pink.index > m0, c] = 777.0
    for k, s in d.prod.items():
        s = s.copy(); s[s.index > t - 1] = 1.0; d.prod[k] = s
    for k, s in d.tc.items():
        s = s.copy(); s[s.index > t] = 99.0; d.tc[k] = s
    d.sws = d.sws.copy(); d.sws.loc[d.sws["published"] >= F.issue(t), "H"] = 99.0
    d.stocks = d.stocks.copy()
    stock_m = t // 4 * 12 + (t % 4) * 3 + 3 - F.STOCK_LAG_MONTHS
    d.stocks.loc[d.stocks.index > stock_m, ["total", "nfa"]] = 5.0
    d.n1r = d.n1r.copy(); d.n1r[d.n1r.index > t] = 99.0
    after = F.rows_origin(d, t)
    for a, b in zip(before, after):
        for c in INPUTS:
            assert (np.isnan(a[c]) and np.isnan(b[c])) or a[c] == b[c], c
