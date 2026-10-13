"""E15 runner: build the two-layer prototype output from eligible 2021-2025 data, run the runtime checks, write
runs/<utc>/ (JSON + 3 CSVs + checks + manifest). Refuses to run if the prospective protocol hash has changed."""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "21")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard  # noqa: E402

guard.install()
import hashlib  # noqa: E402
import json  # noqa: E402
import platform  # noqa: E402
from datetime import datetime, timezone  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import loaders  # noqa: E402
import two_layer as TL  # noqa: E402

EXP = guard.EXP


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    frozen = (EXP / "PROSPECTIVE_VALIDATION_PROTOCOL.sha256").read_text(encoding="utf-8").split()[0]
    if sha(EXP / "PROSPECTIVE_VALIDATION_PROTOCOL.md") != frozen:
        raise SystemExit("E15: prospective protocol differs from its frozen hash; stop.")
    started = datetime.now(timezone.utc)
    out = EXP / "runs" / started.strftime("%Y%m%dT%H%M%SZ")
    out.mkdir(parents=True)
    allow_start = guard.verify_allowlist()

    comp = loaders.load_components()
    rounds = loaders.load_rounds()
    quarters = sorted(comp["quarter"].unique(), key=loaders.qkey)
    loaders.assert_quarters(quarters, "output quarters")
    if abs(rounds.attrs["tau0_recorded"] - TL.TAU0) > 1e-12:
        raise SystemExit("E15: tau0 mismatch")

    res = TL.build_two_layer(comp[["quarter", "province_code", "F"]], rounds, quarters, data_through=loaders.MAXQ)

    # ------------------------------------------------------------------ runtime checks
    checks = {}
    import jsonschema
    schema = json.loads((EXP / "TWO_LAYER_SCHEMA.json").read_text(encoding="utf-8"))
    jsonschema.validate(json.loads(json.dumps(res)), schema)
    checks["schema_valid"] = True
    checks["wording_violations"] = TL.wording_violations(res)
    tables = TL.to_tables(res)
    checks["wording_violations_tables"] = sum(
        (TL.wording_violations(list(t.columns)) + TL.wording_violations(t.astype(str).to_numpy().ravel().tolist())
         for t in tables.values()), [])
    pv = tables["provincial_layer"].merge(comp[["quarter", "province_code", "D"]], on=["quarter", "province_code"])
    checks["max_abs_D_vs_E12"] = float((pv["relative_pressure_D_pp"] - pv["D"]).abs().max())
    lg = tables["legacy_layer"].merge(comp[["quarter", "province_code", "S1"]], on=["quarter", "province_code"],
                                      suffixes=("", "_E12"))
    both = lg[lg["S1"].notna() | lg["S1_E12"].notna()]
    checks["legacy_rows_with_S1"] = int(lg["S1"].notna().sum())
    checks["E12_rows_with_S1"] = int(comp["S1"].notna().sum())
    checks["S1_null_pattern_matches_E12"] = bool((lg["S1"].isna() == lg["S1_E12"].isna()).all())
    checks["max_abs_S1_vs_E12"] = float((both["S1"] - both["S1_E12"]).abs().max())
    s1 = comp["S1"].dropna().to_numpy()
    labels = {t: (s1 > t) for t in (10.843, rounds.attrs["tau0_full_precision"], TL.TAU0)}
    checks["threshold_equivalence"] = {
        "thresholds": [10.843, rounds.attrs["tau0_full_precision"], TL.TAU0],
        "identical_labels": bool(all((v == labels[TL.TAU0]).all() for v in labels.values())),
        "S1_values_between_10.843_and_10.84335": int(((s1 > 10.843) & (s1 <= TL.TAU0)).sum()),
        "HIGH_count": int(labels[TL.TAU0].sum()), "rows": int(len(s1))}
    reg = tables["regional_layer"]
    checks["regional_rows"] = int(len(reg))
    checks["regional_quarters_unique"] = bool(reg["quarter"].is_unique)
    checks["provincial_quarters_complete"] = int((res and sum(q["provincial_layer"]["status"] == "COMPLETE"
                                                              for q in res["quarters"])))
    checks["D_sum_max_abs"] = float(tables["provincial_layer"].groupby("quarter")["relative_pressure_D_pp"]
                                    .sum().abs().max())
    checks["max_output_quarter"] = max(quarters, key=loaders.qkey)
    ok = (checks["schema_valid"] and not checks["wording_violations"] and not checks["wording_violations_tables"]
          and checks["max_abs_D_vs_E12"] <= 1e-9 and checks["max_abs_S1_vs_E12"] <= 1e-9
          and checks["S1_null_pattern_matches_E12"] and checks["threshold_equivalence"]["identical_labels"]
          and checks["regional_quarters_unique"] and checks["D_sum_max_abs"] <= 1e-9)
    checks["all_passed"] = bool(ok)

    # ------------------------------------------------------------------ write
    (out / "two_layer_output.json").write_text(json.dumps(res, indent=1), encoding="utf-8", newline="\n")
    for name, t in tables.items():
        t.to_csv(out / f"{name}.csv", index=False, lineterminator="\n", float_format="%.10g")
    (out / "runtime_checks.json").write_text(json.dumps(checks, indent=1), encoding="utf-8", newline="\n")
    manifest = {"started_utc": started.isoformat(), "finished_utc": datetime.now(timezone.utc).isoformat(),
                "prospective_protocol_sha256": frozen, "allowlist_sha256_start": allow_start,
                "allowlist_sha256_end": guard.verify_allowlist(),
                "code_sha256": {p.name: sha(p) for p in sorted((EXP / "runner").glob("*.py"))},
                "schema_sha256": sha(EXP / "TWO_LAYER_SCHEMA.json"),
                "outputs_sha256": {p.name: sha(p) for p in sorted(out.glob("*")) if p.name != "manifest.json"},
                "environment": {"python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__,
                                "jsonschema": jsonschema.__version__},
                "access_log": guard.ACCESS_LOG}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8", newline="\n")
    print(out)
    print(json.dumps(checks, indent=1))
    if not ok:
        raise SystemExit("E15: a runtime check failed")


if __name__ == "__main__":
    main()
