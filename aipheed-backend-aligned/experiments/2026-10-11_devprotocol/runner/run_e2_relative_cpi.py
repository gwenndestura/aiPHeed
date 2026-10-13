"""
E2: relative food-price stress (research alternative; protocol ../E2_PROTOCOL.md).

Target d(p,q) = provincial food CPI YoY - five-province mean of the same quarter.
NOT a food-insecurity forecast; no SWS is used.

DRY RUN BY DEFAULT (prints target checks and fold eligibility, writes nothing).
    PYTHONPATH=. python experiments/2026-10-11_devprotocol/runner/run_e2_relative_cpi.py
    PYTHONPATH=. python experiments/2026-10-11_devprotocol/runner/run_e2_relative_cpi.py --execute --authorized-by "<name>"

Reuses the E1 runner's safety helpers (fresh run folder, protected-file hashing,
production-module guard). Tests: tests/unit/test_e2_relative_cpi.py
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import scripts.supplementary.devprotocol_rule_l as D
import scripts.supplementary.timing_audit as T
import scripts.supplementary.window2021_study as W

_spec = importlib.util.spec_from_file_location("run_exploratory", Path(__file__).with_name("run_exploratory.py"))
E1 = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("run_exploratory", E1)
_spec.loader.exec_module(E1)

EXP = Path("experiments/2026-10-11_devprotocol")
RUNS = EXP / "runs"
PROTOCOL = EXP / "E2_PROTOCOL.md"
RUNNER = Path(__file__)
SOURCE = Path("data/processed/psa_indicators.parquet")

SEED = 42
MIN_TRAIN_QUARTERS = 8
FIRST_Q, LAST_Q = "2021-Q1", "2025-Q4"
PROVINCES = ["PH040100000", "PH040200000", "PH040300000", "PH040400000", "PH040500000"]
TEST_QUARTERS = ["2023-Q4", "2024-Q1", "2024-Q2", "2024-Q3", "2024-Q4",
                 "2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4"]
LESS_EXPOSED = ["2025-Q2", "2025-Q3"]
REUSED = [q for q in TEST_QUARTERS if q not in LESS_EXPOSED]
MODELS = ("MODEL-B2-reg", "Carry-forward", "Province-mean", "Zero")
BOOTSTRAP_DRAWS = 10_000
TARGET_COLUMNS = {"d", "food_cpi_yoy_target", "regional_mean_target"}
PROTECTED_GLOBS = E1.PROTECTED_GLOBS + (
    "experiments/2026-10-11_devprotocol/runs/20261011T111651Z/*",
    "experiments/2026-10-11_devprotocol/diagnosis_20261011T111651Z/*",
    "experiments/2026-10-11_devprotocol/runner/*.py",
)


# ---------------------------------------------------------------- target
def target_table(src: Path = SOURCE) -> pd.DataFrame:
    ind = pd.read_parquet(src)[["province_code", "quarter", "food_cpi_yoy"]].copy()
    ind = ind[ind["province_code"].isin(PROVINCES) & (ind["quarter"] >= FIRST_Q) & (ind["quarter"] <= LAST_Q)]
    ind["food_cpi_yoy"] = pd.to_numeric(ind["food_cpi_yoy"], errors="coerce")
    if ind["food_cpi_yoy"].isna().any():
        raise RuntimeError("missing provincial food CPI YoY; target cannot be computed consistently")
    if ind.duplicated(["province_code", "quarter"]).any():
        raise RuntimeError("duplicate province-quarter rows")
    if not (ind.groupby("quarter").size() == 5).all():
        raise RuntimeError("a quarter lacks one of the five provinces")
    ind["regional_mean_target"] = ind.groupby("quarter")["food_cpi_yoy"].transform("mean")
    ind["d"] = ind["food_cpi_yoy"] - ind["regional_mean_target"]
    return ind.rename(columns={"food_cpi_yoy": "food_cpi_yoy_target"}).sort_values(["quarter", "province_code"])


def published(q: str) -> tuple[pd.Timestamp, str]:
    return D.cpi_published(q, provincial=True)


def eligible_quarters(target: str, quarters: list[str]) -> list[str]:
    o = T.qstart(target)
    return [q for q in quarters if q < target and published(q)[0] < o]


class TargetVault:
    """Training access only to eligible quarters before the target; the target quarter's d
    is revealed only after that fold's predictions were written and registered."""

    def __init__(self, table: pd.DataFrame):
        if (table["quarter"] > LAST_Q).any() or set(table["quarter"]) & D.PROTECTED:
            raise RuntimeError("a 2026 target is present")
        self._t = table[["quarter", "province_code", "d"]].copy()
        self._registered: dict[str, str] = {}
        self.revealed: list[str] = []

    def quarters(self) -> list[str]:
        return sorted(self._t["quarter"].unique())

    def training(self, quarters: list[str], target: str) -> pd.DataFrame:
        if any(q >= target for q in quarters):
            raise PermissionError(f"training access to a quarter not before {target}")
        return self._t[self._t["quarter"].isin(quarters)].copy()

    def register_predictions(self, key: str, path: Path) -> None:
        self._registered[key] = E1.sha256(path)

    def reveal(self, key: str, target: str) -> pd.DataFrame:
        if key not in self._registered:
            raise PermissionError(f"target {target} requested before predictions {key} were written")
        self.revealed.append(key)
        return self._t[self._t["quarter"] == target].copy()


@dataclass
class Fold:
    target: str
    train_quarters: list[str]
    eligible: bool


def fold_plan(vault: TargetVault, targets=TEST_QUARTERS) -> list[Fold]:
    out = []
    for t in targets:
        if t > LAST_Q:
            raise ValueError(f"{t} is outside the E2 window")
        e = eligible_quarters(t, vault.quarters())
        out.append(Fold(t, e, len(e) >= MIN_TRAIN_QUARTERS))
    return out


def feature_cols(usable: list[str]) -> list[str]:
    cols = W.feature_sets(usable)["gov_c"]
    if len(cols) != 44:
        raise RuntimeError(f"MODEL-B2 input set has {len(cols)} columns, expected 44")
    return cols


# ---------------------------------------------------------------- prediction
def fit_reg(X, y):
    from lightgbm import LGBMRegressor
    return LGBMRegressor(objective="regression", random_state=SEED, verbosity=-1).fit(X, y)


def predict_fold(frame, vault, fold, cols, fitter=fit_reg, check_determinism=True) -> pd.DataFrame:
    tr_t = vault.training(fold.train_quarters, fold.target)
    tr = frame[frame["target_quarter"].isin(fold.train_quarters)].merge(
        tr_t, left_on=["target_quarter", "province_code"], right_on=["quarter", "province_code"],
        how="inner", suffixes=("", "_t"))
    if len(tr) != 5 * len(fold.train_quarters):
        raise RuntimeError(f"{fold.target}: {len(tr)} training rows for {len(fold.train_quarters)} quarters")
    te = frame[frame["target_quarter"] == fold.target].sort_values("province_code")
    if TARGET_COLUMNS & set(te.columns) or len(te) != 5:
        raise RuntimeError(f"{fold.target}: test matrix invalid")
    prov = te["province_code"].values

    m = fitter(tr[cols], tr["d"].values)
    p = m.predict(te[cols])
    if check_determinism and not np.array_equal(p, fitter(tr[cols], tr["d"].values).predict(te[cols])):
        raise RuntimeError(f"{fold.target}: MODEL-B2-reg not reproducible")
    last = max(fold.train_quarters)
    cf = tr_t[tr_t["quarter"] == last].set_index("province_code")["d"].reindex(prov).values
    pm = tr_t.groupby("province_code")["d"].mean().reindex(prov).values
    rows = []
    for name, pred in (("MODEL-B2-reg", p), ("Carry-forward", cf), ("Province-mean", pm), ("Zero", np.zeros(5))):
        rows.append(pd.DataFrame({"target_quarter": fold.target, "province_code": prov, "model": name,
                                  "pred": pred, "n_train_quarters": len(fold.train_quarters),
                                  "carry_forward_source_quarter": last}))
    return pd.concat(rows, ignore_index=True)


# ---------------------------------------------------------------- metrics
def per_quarter(r: pd.DataFrame) -> pd.DataFrame:
    from scipy.stats import spearmanr
    out = []
    for (q, m), g in r.groupby(["target_quarter", "model"]):
        pred, act = g["pred"].values, g["d"].values
        rho = spearmanr(pred, act).correlation if np.ptp(pred) > 0 and np.ptp(act) > 0 else np.nan
        tied = (pred == pred.max()).sum() > 1
        hit = np.nan if tied else float(np.argmax(pred) == np.argmax(act))
        out.append({"target_quarter": q, "model": m, "spearman": rho, "top_hit": hit,
                    "mae": float(np.mean(np.abs(pred - act))),
                    "top_actual": g["province_code"].values[np.argmax(act)],
                    "top_predicted": None if tied else g["province_code"].values[np.argmax(pred)]})
    return pd.DataFrame(out)


def summarize(r: pd.DataFrame, pq: pd.DataFrame, quarters: list[str]) -> dict:
    from sklearn.metrics import balanced_accuracy_score, confusion_matrix
    res = {}
    for m in MODELS:
        g, s = r[(r["model"] == m) & r["target_quarter"].isin(quarters)], pq[(pq["model"] == m) & pq["target_quarter"].isin(quarters)]
        rho, hit = s["spearman"].dropna(), s["top_hit"].dropna()
        y, yh = (g["d"] > 0).astype(int).values, (g["pred"] > 0).astype(int).values
        sign = {"actual_above_mean": int(y.sum()), "actual_below_or_equal": int(len(y) - y.sum()),
                "predicted_above_mean": int(yh.sum()),
                "confusion_[[TN,FP],[FN,TP]]": confusion_matrix(y, yh, labels=[0, 1]).tolist(),
                "balanced_accuracy": (round(float(balanced_accuracy_score(y, yh)), 4)
                                      if len(set(y)) > 1 and m != "Zero" else None),
                "per_quarter_accuracy": {q: round(float(((gg["d"] > 0) == (gg["pred"] > 0)).mean()), 2)
                                         for q, gg in g.groupby("target_quarter")}}
        if m == "Zero":
            sign["note"] = "undefined: Zero predicts no province above the mean"
        res[m] = {"quarters": len(s), "mae": round(float(g["pred"].sub(g["d"]).abs().mean()), 4),
                  "mean_spearman": round(float(rho.mean()), 4) if len(rho) else None,
                  "spearman_defined_quarters": int(len(rho)),
                  "top_hit_rate": round(float(hit.mean()), 4) if len(hit) else None,
                  "top_hits": f"{int(hit.sum())}/{len(hit)}" if len(hit) else "undefined",
                  "sign_secondary": sign}
    return res


def paired_bootstrap(pq: pd.DataFrame, quarters: list[str], metric: str, a="MODEL-B2-reg", b="Carry-forward"):
    x = pq[pq["model"] == a].set_index("target_quarter")[metric].reindex(quarters)
    y = pq[pq["model"] == b].set_index("target_quarter")[metric].reindex(quarters)
    diff = (x - y).dropna().values
    if len(diff) < 2:
        return {"mean_diff": None, "ci95": None, "n_quarters": int(len(diff))}
    rng = np.random.default_rng(SEED)
    boots = [diff[rng.integers(0, len(diff), len(diff))].mean() for _ in range(BOOTSTRAP_DRAWS)]
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return {"mean_diff": round(float(diff.mean()), 4), "ci95": [round(float(lo), 4), round(float(hi), 4)],
            "n_quarters": int(len(diff)), "per_quarter_diff": dict(zip([q for q in quarters if not np.isnan(x[q] - y[q])],
                                                                        np.round(diff, 3).tolist()))}


def decision(summary9: dict, boot_rho: dict) -> dict:
    b2, cf = summary9["MODEL-B2-reg"], summary9["Carry-forward"]
    c1 = b2["mean_spearman"] is not None and cf["mean_spearman"] is not None and \
        b2["mean_spearman"] - cf["mean_spearman"] >= 0.20
    c2 = boot_rho["ci95"] is not None and boot_rho["ci95"][0] > 0          # interval entirely above 0
    c3 = b2["mae"] <= cf["mae"]
    return {"rule_1_rho_gain_ge_0.20": bool(c1), "rule_2_ci_excludes_0_positive": bool(c2),
            "rule_3_mae_not_worse": bool(c3),
            "verdict": "demonstrates value" if (c1 and c2 and c3) else "no demonstrated value beyond carry-forward"}


# ---------------------------------------------------------------- run
def plan(vault: TargetVault, table: pd.DataFrame) -> dict:
    return {"target_rows": len(table), "quarters": f"{table['quarter'].min()}..{table['quarter'].max()}",
            "max_abs_quarter_sum_of_d": float(table.groupby("quarter")["d"].sum().abs().max()),
            "folds": {f.target: {"eligible_train_quarters": len(f.train_quarters), "fold_eligible": f.eligible,
                                 "first": f.train_quarters[0] if f.train_quarters else None,
                                 "last": f.train_quarters[-1] if f.train_quarters else None}
                      for f in fold_plan(vault)}}


def execute(authorized_by: str, runs_root: Path = RUNS) -> Path:
    E1.assert_no_forbidden_modules()
    if not PROTOCOL.exists():
        raise FileNotFoundError(PROTOCOL)
    before = E1.snapshot_hashes(PROTECTED_GLOBS)
    table = target_table()
    vault = TargetVault(table)
    frame, usable = D.development_frame()
    cols = feature_cols(usable)
    folds = fold_plan(vault)

    run = E1.RunDir(runs_root / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_E2"))
    import lightgbm, sklearn, scipy
    run.write_json("config.json", {
        "experiment": "E2 relative food-price stress (research alternative; not a food-insecurity forecast)",
        "authorized_by": authorized_by, "started_utc": datetime.now(timezone.utc).isoformat(),
        "protocol": {"path": PROTOCOL.as_posix(), "sha256": E1.sha256(PROTOCOL)},
        "runner_sha256": E1.sha256(RUNNER), "e1_helpers_sha256": E1.sha256(Path(E1.__file__)),
        "devprotocol_sha256": E1.sha256(Path(D.__file__)),
        "target": {"definition": "food_cpi_yoy(p,q) - mean over 5 provinces of food_cpi_yoy(q)",
                   "source": SOURCE.as_posix(), "source_sha256": E1.sha256(SOURCE), "units": "percentage points",
                   "rows": len(table), "quarters": [FIRST_Q, LAST_Q], "uses_sws": False,
                   "publication": "devprotocol_rule_l.cpi_published(q, provincial=True): WD1 proxy "
                                  "(national + 14 d), verified 2024-Q4 only, not before 2022-02-04"},
        "seed": SEED, "min_train_quarters": MIN_TRAIN_QUARTERS, "test_quarters": TEST_QUARTERS,
        "reused_quarters": REUSED, "less_exposed_quarters": LESS_EXPOSED,
        "fold_eligibility": {f.target: {"eligible": f.eligible, "train_quarters": f.train_quarters,
                                        "publication": {q: [str(published(q)[0].date()), published(q)[1]]
                                                        for q in f.train_quarters}} for f in folds},
        "feature_set_MODEL-B2": cols,
        "models": {"MODEL-B2-reg": "LGBMRegressor(objective=regression, random_state=42, verbosity=-1), defaults",
                   "Carry-forward": "d of the latest eligible quarter", "Province-mean": "mean d over eligible quarters",
                   "Zero": "0"},
        "versions": {"numpy": np.__version__, "pandas": pd.__version__, "lightgbm": lightgbm.__version__,
                     "sklearn": sklearn.__version__, "scipy": scipy.__version__},
        "input_provenance_sha256": {k: v for k, v in before.items()
                                    if k.startswith(("data/processed", "evidence/2026-10"))},
    })

    scored = []
    for f in folds:
        if not f.eligible:
            continue
        key = f"E2__{f.target}"
        preds = predict_fold(frame, vault, f, cols)
        path = run.write_csv(f"pred_{key}.csv", preds)              # target-free, written first
        vault.register_predictions(key, path)
        actual = vault.reveal(key, f.target)
        scored.append(preds.merge(actual[["province_code", "d"]], on="province_code"))
    r = pd.concat(scored, ignore_index=True)
    r["abs_error"] = (r["pred"] - r["d"]).abs()
    run.write_csv("scored_rows.csv", r)
    pq = per_quarter(r)
    run.write_csv("per_quarter_metrics.csv", pq)
    # full target construction, written only after every fold's predictions were written and revealed
    run.write_csv("target_table_construction.csv", table.assign(
        published=table["quarter"].map(lambda q: published(q)[0].date()),
        date_type=table["quarter"].map(lambda q: published(q)[1])))

    evaluated = [f.target for f in folds if f.eligible]
    sets = {"all_9": evaluated, "reused_7": [q for q in REUSED if q in evaluated],
            "less_exposed_2": [q for q in LESS_EXPOSED if q in evaluated]}
    summaries = {k: summarize(r, pq, v) for k, v in sets.items()}
    boots = {k: {"spearman": paired_bootstrap(pq, v, "spearman"), "mae": paired_bootstrap(pq, v, "mae")}
             for k, v in sets.items()}
    run.write_json("metrics.json", {
        "label": "E2 research alternative: relative food-price stress. Exploratory (7 reused + 2 less-exposed "
                 "quarters). Not a food-insecurity forecast; no bearing on the 75% requirement.",
        "ineligible_folds": [f.target for f in folds if not f.eligible],
        "summaries": summaries, "paired_bootstrap_B2_minus_CF": boots,
        "decision_rule_all_9": decision(summaries["all_9"], boots["all_9"]["spearman"])})

    after = E1.snapshot_hashes(PROTECTED_GLOBS)
    E1.assert_unchanged(before, after)
    E1.assert_no_forbidden_modules()
    run.write_json("manifest.json", {"finished_utc": datetime.now(timezone.utc).isoformat(),
                                     "protected_files_checked": len(before), "protected_files_unchanged": True,
                                     "targets_revealed_after_predictions": vault.revealed,
                                     "outputs_sha256": dict(run.written)})
    return run.path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="E2 relative food-price stress experiment")
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--authorized-by", default="")
    a = ap.parse_args(argv)
    if not Path("app/ml").is_dir():
        ap.error("run from aipheed-backend-aligned/ with PYTHONPATH=.")
    if a.execute and not a.authorized_by.strip():
        ap.error("--execute requires --authorized-by")
    E1.assert_no_forbidden_modules()
    if not a.execute:
        t = target_table()
        print(json.dumps(plan(TargetVault(t), t), indent=2, default=str))
        print("DRY RUN: nothing fitted, nothing written.")
        return 0
    print(f"run written to {execute(a.authorized_by)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
