"""E173: the frozen SIMPLE rule is exactly E172's SIMPLE subset, LightGBM only, and its config hash is reproducible."""
from app.e172 import lgbm_only as E
from app.e173 import freeze as F


def test_simple_menu_is_e172_simple_subset_and_low_complexity_only():
    m = F.simple_menu("OH")
    assert len(m) == 24 and m == [c for c in E.stage2("OH") if E.SUBSETS["SIMPLE"](c)]
    assert {l[:3] for _, l, _ in m} == {"GR1", "GR2", "GR3", "GR4"} and all(issubclass(E.VARIANTS[l], E.LGB) for _, l, _ in m)


def test_config_hash_is_reproducible_and_covers_the_code():
    a, b = F.config(), F.config()
    assert a["config_sha256"] == b["config_sha256"] and "app/e172/lgbm_only.py" in a["code_sha256"]
    assert a["settings"]["R1"]["num_leaves"] == 2 and a["settings"]["R4"]["colsample_bytree"] == 0.5
