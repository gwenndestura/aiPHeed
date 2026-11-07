"""E175 target-transformation study: source data untouched, leakage correctly flagged, logit equals original classes."""
import hashlib
import json

import pytest

from app.paths import BACKEND_DIR

OUT = BACKEND_DIR / "data" / "e175" / "out" / "results.json"
pytestmark = pytest.mark.skipif(not OUT.exists(), reason="E175 not run")


def test_fnri_source_file_is_unchanged():
    # sha256 of the FNRI provincial HFIAS file as committed before the study
    import subprocess
    p = BACKEND_DIR / "data" / "hfias" / "clean" / "enns_hfias.csv"
    head = subprocess.run(["git", "show", "HEAD:backend/data/hfias/clean/enns_hfias.csv"], cwd=BACKEND_DIR.parent,
                          capture_output=True).stdout
    assert head and hashlib.sha256(p.read_bytes()).hexdigest() == hashlib.sha256(head).hexdigest()


def test_target_round_methods_are_flagged_as_leaking_and_asof_ones_are_not():
    r = json.loads(OUT.read_text())
    for lead in ("1", "2", "3"):
        for name, v in r["leads"][lead].items():
            assert v["leakage_free"] is (not name.endswith("_target_round")), name


def test_logit_transform_gives_the_original_classes():
    r = json.loads(OUT.read_text())
    for lead in ("1", "2", "3"):
        assert r["leads"][lead]["F_logit_0"]["E168"] == r["leads"][lead]["A_original_50"]["E168"]


def test_original_definition_ranks_provinces_best_among_leakage_free_methods():
    r = json.loads(OUT.read_text())
    for lead in ("1", "2", "3"):
        free = {n: v["E168"]["auc"] for n, v in r["leads"][lead].items() if v["leakage_free"]}
        assert free["A_original_50"] == max(free.values())
