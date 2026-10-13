"""
Exploratory development run for aiPHeed (protocol: ../EXPLORATORY_PROTOCOL_v4.md).

DRY RUN BY DEFAULT. Without --execute it prints the fold plan, feature counts and
thresholds and writes nothing. With --execute --authorized-by "<name>" it fits the
fixed configurations, writes every output to a NEW folder under runs/, and checks
that no protected file changed.

Run from the aipheed-backend-aligned/ directory:
    PYTHONPATH=. python experiments/2026-10-11_devprotocol/runner/run_exploratory.py           # dry run
    PYTHONPATH=. python experiments/2026-10-11_devprotocol/runner/run_exploratory.py --execute --authorized-by "<name>"

Safety rules enforced here (tests: tests/unit/test_exploratory_runner.py):
  * never imports the production pipeline, scheduler, API or training code;
  * training labels come only from quarters eligible under Rule L at the fold's origin;
  * the fold threshold tau_T is the median of those training rows only;
  * test labels are revealed only after the fold's label-free predictions are written;
  * no 2026 label exists anywhere in the run;
  * outputs go to a fresh run folder; nothing is overwritten;
  * protected files are hashed before and after; any change aborts the run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import scripts.supplementary.devprotocol_rule_l as D
import scripts.supplementary.timing_audit as T
import scripts.supplementary.window2021_study as W
from app.ml.features.feature_selector import EQUATION5_FEATURES

EXP = Path("experiments/2026-10-11_devprotocol")
RUNS = EXP / "runs"
PROTOCOL = EXP / "EXPLORATORY_PROTOCOL_v4.md"
RUNNER = Path(__file__)

SEED = 42
CUT = 0.50
MIN_TRAIN_QUARTERS = 8                      # Chapter III Algorithm 3, counted after Rule L
THR_GLOBAL_EXPECTED = 14.345
LAST_LABEL = "2025-Q4"
TEST_PRIMARY = ["2023-Q4", "2024-Q1", "2024-Q2", "2024-Q3", "2024-Q4", "2025-Q1", "2025-Q4"]
S5_EXTRA = "2023-Q3"                        # 7 eligible quarters; reported separately
S6_SUBSET = ["2024-Q3", "2024-Q4", "2025-Q1", "2025-Q4"]   # literal "8 consecutive" reading
ANALYSES = ("A-origin", "A-global")
PRIMARY_ANALYSIS = "A-origin"               # fallback if the adviser declines: A-global (fixed now)
SENSITIVITIES = ("base", "S1", "S2", "S4")
REVISED_FAMILIES = {"noaa_oni", "drought_alert", "ibtracs_typhoon", "nasa_power_rain"}
BOOTSTRAP_DRAWS = 10_000

FORBIDDEN_MODULE_PREFIXES = (
    "app.tasks", "app.api", "app.main", "app.services", "app.ml.training",
    "scripts.run_quarterly_pipeline", "uvicorn", "fastapi", "apscheduler",
)
PROTECTED_GLOBS = (
    "data/processed/**/*", "models/**/*", "data/supplementary/**/*", "evidence/**/*",
    "docs/*.md", "experiments/2026-10-09_*/**/*",
    "experiments/2026-10-11_devprotocol/*.md", "experiments/2026-10-11_devprotocol/*.csv",
    "app/ml/corpus/sws_hunger_fetcher.py", "app/ml/features/label_generator.py",
    "scripts/supplementary/*.py",
)
LABEL_COLUMNS = {"stress_score", "label_stress", "y", "label", "global_threshold"}


# ---------------------------------------------------------------- safety helpers
def assert_no_forbidden_modules() -> None:
    bad = sorted(m for m in sys.modules if m.startswith(FORBIDDEN_MODULE_PREFIXES))
    if bad:
        raise RuntimeError(f"production modules loaded: {bad}")


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def snapshot_hashes(globs=PROTECTED_GLOBS, root: Path = Path(".")) -> dict[str, str]:
    out = {}
    for g in globs:
        for p in sorted(root.glob(g)):
            if p.is_file() and "__pycache__" not in p.parts:
                out[p.as_posix()] = sha256(p)
    return out


def assert_unchanged(before: dict[str, str], after: dict[str, str]) -> None:
    changed = sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
    if changed:
        raise RuntimeError(f"protected files changed during the run: {changed}")


class RunDir:
    """A fresh output folder. Refuses to reuse a folder, overwrite a file or write outside it."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=False)
        self.written: dict[str, str] = {}

    def file(self, name: str) -> Path:
        p = (self.path / name).resolve()
        if self.path.resolve() not in p.parents:
            raise PermissionError(f"refusing to write outside the run folder: {name}")
        if p.exists():
            raise FileExistsError(f"refusing to overwrite {p}")
        return p

    def write_text(self, name: str, text: str) -> Path:
        p = self.file(name)
        p.write_text(text, encoding="utf-8")
        self.written[name] = sha256(p)
        return p

    def write_json(self, name: str, obj) -> Path:
        return self.write_text(name, json.dumps(obj, indent=2, default=str))

    def write_csv(self, name: str, df: pd.DataFrame) -> Path:
        return self.write_text(name, df.to_csv(index=False))


class LabelVault:
    """Holds the Eq. 3 stress scores. Training access is limited to eligible quarters before the
    target; a target's own labels are revealed only after its predictions were registered."""

    def __init__(self, labels: pd.DataFrame):
        lab = labels[["quarter", "province_code", "stress_score"]].copy()
        if (lab["quarter"] > LAST_LABEL).any() or set(lab["quarter"]) & D.PROTECTED:
            raise RuntimeError("a 2026 label is present; the run must not see any")
        self._lab = lab
        self._registered: dict[str, str] = {}
        self.revealed: list[str] = []

    @classmethod
    def from_project(cls) -> "LabelVault":
        lab = W.window_labels(THR_GLOBAL_EXPECTED)        # definition A rows, 2021-Q1 onwards
        return cls(lab[lab["quarter"] <= LAST_LABEL])

    def quarters(self) -> list[str]:
        return sorted(self._lab["quarter"].unique())

    def training(self, quarters: list[str], target: str) -> pd.DataFrame:
        if any(q >= target for q in quarters):
            raise PermissionError(f"training access to a quarter not before {target}")
        return self._lab[self._lab["quarter"].isin(quarters)].copy()

    def global_threshold(self) -> float:
        """The approved full-period median (A-global). Uses every labelled row: leaky by design."""
        return float(self._lab["stress_score"].median())

    def register_predictions(self, key: str, path: Path) -> None:
        self._registered[key] = sha256(path)

    def reveal(self, key: str, target: str) -> pd.DataFrame:
        if key not in self._registered:
            raise PermissionError(f"labels of {target} requested before predictions {key} were written")
        self.revealed.append(key)
        return self._lab[self._lab["quarter"] == target].copy()


# ---------------------------------------------------------------- plan
@dataclass
class Fold:
    target: str
    origin: pd.Timestamp
    train_quarters: list[str]
    note: str = ""


def fold_plan(targets: list[str], allow_short: bool = False) -> list[Fold]:
    folds = []
    for t in targets:
        if t > LAST_LABEL:
            raise ValueError(f"{t} has no label in this experiment")
        e = D.eligible_training_quarters(t, "development")
        if len(e) < MIN_TRAIN_QUARTERS and not allow_short:
            raise ValueError(f"{t}: {len(e)} eligible training quarters < {MIN_TRAIN_QUARTERS}")
        folds.append(Fold(t, T.qstart(t), e, "below minimum window (S5)" if len(e) < MIN_TRAIN_QUARTERS else ""))
    return folds


def feature_sets(usable: list[str]) -> dict[str, dict[str, list[str]]]:
    fp = D.feature_protocol().set_index("feature")
    revised = {c for c in usable if c in fp.index and fp.loc[c, "family"] in REVISED_FAMILIES}
    strict = set(D.feature_mask("strict"))
    primary = W.feature_sets(usable)["gov_c"]
    model_a = [c for c in EQUATION5_FEATURES if c in usable]
    if len(model_a) != len(EQUATION5_FEATURES):
        raise RuntimeError("an Equation 5 input is missing from the development mask")
    base = {"MODEL-B2": primary, "MODEL-A": model_a}
    return {
        "base": base,
        "S1": {k: [c for c in v if c not in revised] for k, v in base.items()},
        "S2": {k: [c for c in v if c in strict] for k, v in base.items()},
        "S4": base,
    }


def s4_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Development frame with the SWS inputs rebuilt from production rounds only (no supplementary)."""
    rounds = [r for r in D.sws_rounds() if r.source == "production"]
    f = frame.copy()
    sk = f["origin"].map(lambda o: D.sws_known(o, rounds))
    f["sws_hunger"] = [x["sws_hunger"] for x in sk]
    f["sws_change"] = [x["sws_change"] for x in sk]
    f["sws_age"] = [W.qi(t) - W.qi(x["sws_round_quarter"]) if x["sws_round_quarter"] else np.nan
                    for t, x in zip(f["target_quarter"], sk)]
    for k in ("sws_round", "sws_round_quarter", "sws_published", "sws_date_type", "sws_source"):
        f[k] = [x[k] for x in sk]
    return f


def test_matrix(frame: pd.DataFrame, target: str) -> pd.DataFrame:
    te = frame[frame["target_quarter"] == target].copy()
    if LABEL_COLUMNS & set(te.columns):
        raise RuntimeError("label columns present in the test feature matrix")
    if len(te) != 5:
        raise RuntimeError(f"{target}: expected 5 province rows, found {len(te)}")
    return te


def training_matrix(frame: pd.DataFrame, vault: LabelVault, fold: Fold) -> pd.DataFrame:
    lab = vault.training(fold.train_quarters, fold.target)
    tr = frame[frame["target_quarter"].isin(fold.train_quarters)].merge(
        lab, left_on=["target_quarter", "province_code"], right_on=["quarter", "province_code"],
        how="inner", suffixes=("", "_label"))
    if len(tr) != 5 * len(fold.train_quarters):
        raise RuntimeError(f"{fold.target}: training rows {len(tr)} != 5 x {len(fold.train_quarters)}")
    return tr


def fold_threshold(analysis: str, train: pd.DataFrame, vault: LabelVault) -> float:
    if analysis == "A-origin":
        return float(train["stress_score"].median())
    return vault.global_threshold()


# ---------------------------------------------------------------- models (fixed)
def fit_lgbm(X: pd.DataFrame, y: np.ndarray, class_weighted: bool):
    from lightgbm import LGBMClassifier
    p = {"objective": "binary", "random_state": SEED, "verbosity": -1}
    if class_weighted:
        pos = float(np.mean(y))
        p["scale_pos_weight"] = (1 - pos) / pos
    return LGBMClassifier(**p).fit(X, y)


def predict_fold(frame, vault, fold, analysis, fsets, fitter=fit_lgbm, check_determinism=True):
    """Label-free predictions for one fold. Never touches the target's labels."""
    tr = training_matrix(frame, vault, fold)
    te = test_matrix(frame, fold.target)
    tau = fold_threshold(analysis, tr, vault)
    y = (tr["stress_score"] > tau).astype(int).values
    share = float(y.mean())
    out = []

    def add(model, p, pred, note=""):
        out.append(pd.DataFrame({"target_quarter": fold.target, "province_code": te["province_code"].values,
                                 "model": model, "p": p, "pred": pred.astype(int), "tau": tau,
                                 "n_train_quarters": len(fold.train_quarters), "train_high_share": share,
                                 "note": note}))

    degenerate = share in (0.0, 1.0)
    for name, cols in fsets.items():
        if degenerate:
            add(name, np.full(5, np.nan), np.full(5, -1), "degenerate fold: not fitted")
            continue
        m = fitter(tr[cols], y, class_weighted=(name == "MODEL-B2"))
        p = m.predict_proba(te[cols])[:, 1]
        if check_determinism and name == "MODEL-B2":
            p2 = fitter(tr[cols], y, class_weighted=True).predict_proba(te[cols])[:, 1]
            if not np.array_equal(p, p2):
                raise RuntimeError(f"{fold.target}: MODEL-B2 not reproducible")
        add(name, p, (p >= CUT).astype(int))

    # Equation 3 rule on origin-known inputs; missing inputs fall back to the training majority
    s = te["sws_hunger"].values + 2 * te["cpi_rel"].values
    fallback = int(share >= 0.5)
    pred = np.where(np.isnan(s), fallback, (s > tau).astype(int))
    add("Eq3-rule", s - tau, pred, f"{int(np.isnan(s).sum())} rows used the training-majority fallback")

    # Carry-forward: province's latest published stress score
    last_q = max(fold.train_quarters)
    last = tr[tr["target_quarter"] == last_q].set_index("province_code")["stress_score"]
    s_cf = te["province_code"].map(last).values.astype(float)
    add("carry-forward", s_cf - tau, (s_cf > tau).astype(int), f"latest published label quarter {last_q}")

    add("always-HIGH (reference)", np.ones(5), np.ones(5))
    add("always-LOW (reference)", np.zeros(5), np.zeros(5))
    return pd.concat(out, ignore_index=True), tau


# ---------------------------------------------------------------- metrics
def clopper_pearson(k: int, n: int, a: float = 0.05):
    from scipy.stats import beta
    lo = 0.0 if k == 0 else beta.ppf(a / 2, k, n - k + 1)
    hi = 1.0 if k == n else beta.ppf(1 - a / 2, k + 1, n - k)
    return round(float(lo), 3), round(float(hi), 3)


def qacc(r: pd.DataFrame) -> float:
    return float((r["y"] == r["pred"]).groupby(r["target_quarter"]).mean().mean())


def metrics(r: pd.DataFrame, fitted: bool) -> dict:
    from sklearn.metrics import (balanced_accuracy_score, brier_score_loss, confusion_matrix,
                                 precision_recall_fscore_support, roc_auc_score)
    r = r[r["pred"] >= 0]
    if r.empty:
        return {"note": "no scored rows"}
    y, pr = r["y"].values, r["pred"].values
    k, n = int((y == pr).sum()), len(r)
    p_w, r_w, f_w, _ = precision_recall_fscore_support(y, pr, average="weighted", zero_division=0)
    miss = r[(r["y"] == 1) & (r["pred"] == 0)]
    out = {
        "rows": n, "quarters": int(r["target_quarter"].nunique()), "correct": k, "incorrect": n - k,
        "mean_quarter_accuracy": round(qacc(r), 4),
        "row_accuracy_clopper_pearson_95_OPTIMISTIC": clopper_pearson(k, n),
        "balanced_accuracy": round(float(balanced_accuracy_score(y, pr)), 4) if len(set(y)) > 1 else None,
        "weighted_precision": round(float(p_w), 4), "weighted_recall": round(float(r_w), 4),
        "weighted_f1": round(float(f_w), 4),
        "high_recall": round(float((pr[y == 1] == 1).mean()), 4) if (y == 1).any() else None,
        "missed_high_rows": int(len(miss)), "missed_high_quarters": sorted(miss["target_quarter"].unique()),
        "test_high_share": round(float(y.mean()), 4),
        "confusion_matrix_[[TN,FP],[FN,TP]]": confusion_matrix(y, pr, labels=[0, 1]).tolist(),
        "per_quarter_accuracy": {q: round(float((g["y"] == g["pred"]).mean()), 3)
                                 for q, g in r.groupby("target_quarter")},
        "per_province_accuracy": {pc: round(float((g["y"] == g["pred"]).mean()), 3)
                                  for pc, g in r.groupby("province_code")},
    }
    if fitted and r["p"].notna().all():
        out["roc_auc"] = round(float(roc_auc_score(y, r["p"])), 4) if len(set(y)) > 1 else None
        out["brier"] = round(float(brier_score_loss(y, r["p"])), 4)
        w = [roc_auc_score(g["y"], g["p"]) for _, g in r.groupby("target_quarter")
             if g["y"].nunique() == 2 and g["p"].nunique() > 1]
        out["within_quarter_auc"] = round(float(np.mean(w)), 4) if w else None
    return out


def quarter_bootstrap(r: pd.DataFrame, other: pd.DataFrame | None = None, draws: int = BOOTSTRAP_DRAWS):
    rng = np.random.default_rng(SEED)
    qs = sorted(r["target_quarter"].unique())
    a = (r["y"] == r["pred"]).groupby(r["target_quarter"]).mean().reindex(qs).values
    b = None if other is None else (other["y"] == other["pred"]).groupby(other["target_quarter"]).mean().reindex(qs).values
    stats = []
    for _ in range(draws):
        i = rng.integers(0, len(qs), len(qs))
        stats.append(a[i].mean() - (0 if b is None else b[i].mean()))
    lo, hi = np.percentile(stats, [2.5, 97.5])
    return round(float(lo), 4), round(float(hi), 4)


def mcnemar_exact(r: pd.DataFrame, other: pd.DataFrame) -> dict:
    from scipy.stats import binomtest
    m = r.merge(other, on=["target_quarter", "province_code"], suffixes=("", "_o"))
    a, b = m["pred"] == m["y"], m["pred_o"] == m["y"]
    n01, n10 = int((a & ~b).sum()), int((~a & b).sum())
    p = 1.0 if n01 + n10 == 0 else float(binomtest(n01, n01 + n10, 0.5).pvalue)
    return {"primary_only_correct": n01, "comparator_only_correct": n10, "p_value_OPTIMISTIC": round(p, 4)}


# ---------------------------------------------------------------- run
def build(frame_base, usable):
    return {"base": frame_base, "S1": frame_base, "S2": frame_base, "S4": s4_frame(frame_base)}, feature_sets(usable)


def plan_summary(vault: LabelVault) -> dict:
    frame, usable = D.development_frame()
    fs = feature_sets(usable)
    folds = fold_plan(TEST_PRIMARY) + fold_plan([S5_EXTRA], allow_short=True)
    taus = {}
    for f in folds:
        tr = training_matrix(frame, vault, f)
        taus[f.target] = round(fold_threshold("A-origin", tr, vault), 3)
    return {"folds": {f.target: len(f.train_quarters) for f in folds}, "tau_A_origin": taus,
            "tau_A_global": round(vault.global_threshold(), 3),
            "feature_counts": {s: {k: len(v) for k, v in d.items()} for s, d in fs.items()}}


def execute(authorized_by: str, runs_root: Path = RUNS) -> Path:
    assert_no_forbidden_modules()
    if not PROTOCOL.exists():
        raise FileNotFoundError(PROTOCOL)
    before = snapshot_hashes()
    vault = LabelVault.from_project()
    tau_g = vault.global_threshold()
    if abs(tau_g - THR_GLOBAL_EXPECTED) > 1e-3:
        raise RuntimeError(f"global median {tau_g} != {THR_GLOBAL_EXPECTED}")
    frame, usable = D.development_frame()
    frames, fsets = build(frame, usable)

    run = RunDir(runs_root / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    import lightgbm, sklearn, scipy
    folds = {"primary": fold_plan(TEST_PRIMARY), "S5": fold_plan([S5_EXTRA], allow_short=True)}
    run.write_json("config.json", {
        "authorized_by": authorized_by, "started_utc": datetime.now(timezone.utc).isoformat(),
        "protocol": {"path": PROTOCOL.as_posix(), "sha256": sha256(PROTOCOL)},
        "runner_sha256": sha256(RUNNER), "devprotocol_sha256": sha256(Path(D.__file__)),
        "seed": SEED, "cutoff": CUT, "min_train_quarters": MIN_TRAIN_QUARTERS,
        "primary_analysis": PRIMARY_ANALYSIS, "analyses": ANALYSES, "sensitivities": SENSITIVITIES,
        "test_primary": TEST_PRIMARY, "s5_extra": S5_EXTRA, "s6_subset": S6_SUBSET,
        "tau_A_global": tau_g,
        "eligible_training_quarters": {f.target: f.train_quarters for v in folds.values() for f in v},
        "feature_sets": fsets,
        "models": {"MODEL-B2": "LGBMClassifier(objective=binary, random_state=42, verbosity=-1, "
                               "scale_pos_weight=(1-p)/p from fold training labels)",
                   "MODEL-A": "LGBMClassifier(objective=binary, random_state=42, verbosity=-1)",
                   "Eq3-rule": "HIGH if sws_hunger + 2*cpi_rel > tau; NaN -> training majority",
                   "carry-forward": "HIGH if latest published stress of the province > tau"},
        "exclusions": {"inputs": "retail rice; anything outside the development mask",
                       "quarters": "2025-Q2/Q3 (no label); 2026 (exposed or protected)",
                       "sws_rounds": "unknown-date rounds (June 2026)"},
        "versions": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
                     "lightgbm": lightgbm.__version__, "sklearn": sklearn.__version__, "scipy": scipy.__version__},
        "input_provenance_sha256": {k: v for k, v in before.items()
                                    if k.startswith(("data/processed", "data/supplementary", "evidence/2026-10"))},
    })

    scored = []
    for analysis in ANALYSES:
        for sens in SENSITIVITIES:
            for group, fl in folds.items():
                if group == "S5" and sens != "base":
                    continue
                for fold in fl:
                    key = f"{analysis}__{sens}__{group}__{fold.target}"
                    preds, tau = predict_fold(frames[sens], vault, fold, analysis, fsets[sens])
                    path = run.write_csv(f"pred_{key}.csv", preds)          # label-free, written first
                    vault.register_predictions(key, path)
                    lab = vault.reveal(key, fold.target)
                    lab["y"] = (lab["stress_score"] > tau).astype(int)
                    s = preds.merge(lab[["province_code", "y"]], on="province_code")
                    s["analysis"], s["sensitivity"], s["group"] = analysis, sens, group
                    scored.append(s)
    allr = pd.concat(scored, ignore_index=True)
    run.write_csv("scored_rows.csv", allr)

    res = {}
    for (analysis, sens, group), g in allr.groupby(["analysis", "sensitivity", "group"]):
        block = {}
        prim = g[g["model"] == "MODEL-B2"]
        for model, mg in g.groupby("model"):
            fitted = model in ("MODEL-B2", "MODEL-A")
            block[model] = metrics(mg, fitted)
            if group == "primary" and (mg["pred"] >= 0).all():
                block[model]["quarter_bootstrap_95"] = quarter_bootstrap(mg)
                if model != "MODEL-B2" and (prim["pred"] >= 0).all():
                    block[model]["vs_MODEL-B2"] = {"mcnemar": mcnemar_exact(prim, mg),
                                                   "bootstrap_diff_B2_minus_this_95": quarter_bootstrap(prim, mg)}
            if group == "primary" and sens == "base":
                block[model]["S6_subset"] = metrics(mg[mg["target_quarter"].isin(S6_SUBSET)], fitted)
        block["tau_by_fold"] = g.groupby("target_quarter")["tau"].first().round(4).to_dict()
        res[f"{analysis} | {sens} | {group}"] = block
    run.write_json("metrics.json", {
        "label": "EXPLORATORY development estimate on reused quarters (5 provinces per quarter share "
                 "most inputs; effective n is near the number of quarters). Not a final or independent "
                 "evaluation; cannot establish 75% accuracy.",
        "primary": f"{PRIMARY_ANALYSIS} | base | primary (fallback if not approved: A-global | base | primary)",
        "results": res})

    after = snapshot_hashes()
    assert_unchanged(before, after)
    assert_no_forbidden_modules()
    run.write_json("manifest.json", {"finished_utc": datetime.now(timezone.utc).isoformat(),
                                     "protected_files_checked": len(before), "protected_files_unchanged": True,
                                     "labels_revealed_after_predictions": vault.revealed,
                                     "outputs_sha256": dict(run.written)})
    return run.path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--execute", action="store_true", help="fit and score (requires authorization)")
    ap.add_argument("--authorized-by", default="", help="name of the person authorizing the run")
    a = ap.parse_args(argv)
    if not Path("app/ml").is_dir() or not Path("scripts/supplementary").is_dir():
        ap.error("run from the aipheed-backend-aligned/ directory with PYTHONPATH=.")
    if a.execute and not a.authorized_by.strip():
        ap.error("--execute requires --authorized-by")
    assert_no_forbidden_modules()
    if not a.execute:
        print(json.dumps(plan_summary(LabelVault.from_project()), indent=2, default=str))
        print("DRY RUN: nothing fitted, nothing scored, nothing written.")
        return 0
    print(f"run written to {execute(a.authorized_by)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
