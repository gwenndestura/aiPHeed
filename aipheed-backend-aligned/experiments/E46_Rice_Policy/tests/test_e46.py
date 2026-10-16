"""E46 tests: protocol frozen, policy-event timing (announced before the origin only), five triggers, leakage."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np
import pytest

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "runner"))
sys.path.insert(0, str(HERE.parents[1] / "E41_Lead2_Audit" / "tests"))
sys.path.insert(0, str(HERE.parents[1] / "E43_Five_Trigger_Risk" / "tests"))
import e46_lib as M  # noqa: E402
from test_e41 import perturb  # noqa: E402
from test_e43 import perturb_extra  # noqa: E402

L, K, P2 = M.L, M.K, M.P2
EV = M.load_events()
FIVE = {"market", "climate", "fish_kill", "employment", "ofw_remittance"}


def test_protocol_frozen():
    want = (HERE.parent / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]
    assert hashlib.sha256((HERE.parent / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest() == want


def test_events_are_sourced_and_in_window():
    assert EV["source_primary"].str.startswith("https://").all()
    assert (EV["announcement_date"] >= "2021-01-01").all()


def test_policy_enters_only_after_announcement():
    # EO 62 announced 2024-06-20: the origin 2024-04-01 (t = 2024-Q1, target 2024-Q3) must not see it
    assert M.policy_features(EV, L.qi("2024-Q1"))["tariff_yoy_regime"] == 0.0
    # origin 2024-07-01 (t = 2024-Q2, target 2024-Q4): announced before, target months after the cut -> regime on
    assert M.policy_features(EV, L.qi("2024-Q2"))["tariff_yoy_regime"] == 1.0
    # EO 93 announced 2025-08-29: origin 2025-07-01 (target 2025-Q4) must not see the suspension
    assert M.policy_features(EV, L.qi("2025-Q2"))["import_suspension_share"] == 0.0
    # origin 2025-10-01 (t = 2025-Q3, target 2026-Q1): EO 102's extension was announced 2025-10-30 -> not known
    assert M.policy_features(EV, L.qi("2025-Q3"))["import_suspension_share"] == 0.0


def test_policy_features_ignore_events_announced_later():
    t = L.qi("2025-Q1")
    late = EV.copy()
    late.loc[len(late)] = late.iloc[0].copy()
    late.loc[len(late) - 1, ["announcement_date", "effective_start", "effective_end", "feature"]] = [
        np.datetime64("2026-01-05"), np.datetime64("2026-01-05"), np.datetime64("2026-12-31"), "price_ceiling_share"]
    assert M.policy_features(late, t) == M.policy_features(EV, t)


@pytest.mark.parametrize("hg", [P2.ALL_GROUPS, [g for g in P2.ALL_GROUPS if g not in ("employment", "ofw_remittance")]])
def test_i6_ignores_post_origin_data_and_keeps_five_triggers(hg):
    t = L.qi("2025-Q1")
    o = list(range(L.qi("2021-Q3"), t + 1))
    outs = []
    for d, x in ((L.load(), K.load_extra()), (perturb(L.load(), t), perturb_extra(K.load_extra(), t))):
        X = M.features(d, x, o, EV)
        f = M.forecast(d, X, P2.bases(d, o), t, hunger_groups=hg, n_jobs=1)
        outs.append((list(np.round(f["p"], 12)), f["threshold"], f["price_cfg"]))
        assert FIVE <= {g for g in P2.ALL_GROUPS for c in P2.PRICE_GROUPS[g] if c in f["price_model"].cols}
        assert set(M.POLICY) <= set(f["price_model"].cols)
    assert outs[0] == outs[1]
