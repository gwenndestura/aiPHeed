"""Regression for the patched pcf_engine (two layers): the E25 quarterly transition with SYNTHETIC complete inputs,
run through E26's backend_dev, still reaches READY, stays indicative, ranks 142 LGUs and now carries the layers."""
import numpy as np
import pandas as pd

import _paths  # noqa: F401
from _paths import EXP
from app.quarterly.config import ForecastPeriod
from app.quarterly.periods import Quarter
from app.quarterly.registry import Registry
from app.quarterly.update import run_update

PROVS = ["PH040100000", "PH040200000", "PH040300000", "PH040400000", "PH040500000"]


def test_quarterly_transition_with_synthetic_inputs_carries_layers(tmp_path):
    from app.quarterly.forecaster_v2 import make_pcf_forecaster
    rng = np.random.default_rng(0)
    qs = [str(Quarter.parse("2021-Q1").shift(i)) for i in range(24)]          # 2021-Q1 .. 2026-Q4
    rounds = pd.DataFrame([{"quarter": q, "round": q, "H": 12 + rng.normal(),
                            "published": str(Quarter.parse(q).next().start().date()),
                            "published_eff": str(Quarter.parse(q).next().start().date()), "date_type": "verified",
                            "definition_A": True, "source": "production"} for q in qs[1:-1]])
    D = pd.DataFrame([{"province_code": p, "quarter": q, "D": rng.normal(), "F": 3.0} for q in qs[:-1] for p in PROVS])
    D["D"] -= D.groupby("quarter")["D"].transform("mean")
    S1 = D.merge(rounds[["quarter", "H"]], on="quarter").assign(S1=lambda x: x["H"] + 2 * x["D"])[["province_code", "quarter", "S1"]]
    N = D[D["quarter"] >= "2022-Q1"].assign(Dnow=lambda x: x["D"])[["province_code", "quarter", "Dnow"]]
    N = pd.concat([N, pd.DataFrame([{"province_code": p, "quarter": "2026-Q4", "Dnow": 0.1} for p in PROVS])])
    lg = pd.read_csv(_paths.BD / "data" / "inputs" / "lgu_vulnerability.csv", dtype={"lgu_code": str})
    files = {"sws_rounds": rounds, "s1_labels": S1, "d_quarterly_panel": D, "dnow_panel": N, "lgu_vulnerability": lg}
    reg = Registry(tmp_path / "reg.json")
    for sid, df in files.items():
        f = tmp_path / f"{sid}.csv"
        df.to_csv(f, index=False)
        kind = {"sws_rounds": "label", "s1_labels": "label", "lgu_vulnerability": "static"}.get(sid, "indicator")
        end = {"sws_rounds": "2026-Q3", "s1_labels": "2026-Q3", "d_quarterly_panel": "2026-Q3", "dnow_panel": "2026-Q4"}.get(sid)
        reg.register(sid, kind, str(f), observation_start="2021-Q1", observation_end=end,
                     available_at="2026-12-01T00:00:00+08:00", authorized=True)
    card = tmp_path / "card.json"
    card.write_text('{"name": "synthetic"}')
    reg.register("pcf_model_card", "model", str(card), authorized=True)
    reqs = [{"id": "sws", "kind": "label", "quarter": "2026-Q3", "source_ids": ["sws_rounds"]},
            {"id": "lab", "kind": "label", "quarter": "2026-Q3", "source_ids": ["s1_labels"]},
            {"id": "d", "kind": "indicator", "quarter": "2026-Q3", "source_ids": ["d_quarterly_panel"]},
            {"id": "n", "kind": "indicator", "quarter": "2026-Q4", "source_ids": ["dnow_panel"]},
            {"id": "m", "kind": "model", "source_ids": ["pcf_model_card"]},
            {"id": "l", "kind": "static", "source_ids": ["lgu_vulnerability"]}]
    p = ForecastPeriod(Quarter.parse("2026-Q4"), pd.Timestamp("2026-12-31T23:59:59", tz="Asia/Manila"), requirements=reqs)
    early = run_update(p, reg, tmp_path / "out", forecaster=make_pcf_forecaster({}),
                       now=pd.Timestamp("2026-12-15", tz="Asia/Manila"))
    assert early["status"] == "INSUFFICIENT_DATA"
    rec = run_update(p, reg, tmp_path / "out", forecaster=make_pcf_forecaster({}),
                     now=pd.Timestamp("2027-01-02", tz="Asia/Manila"))
    assert rec["status"] == "READY"
    lead = rec["forecast"]["leads"]["1"]
    assert all(v["risk"]["indicative_only"] for v in lead["provinces"].values())
    assert set(lead["layers"]) == {"regional_risk", "provincial_differential", "composite"}
    assert "not a verified food-insecurity outcome" in lead["layers"]["provincial_differential"]["kind"]
    assert len(rec["forecast"]["lgu_ranking"]) == 142
