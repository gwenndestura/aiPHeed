"""
2026-Q4 prospective forecast: generation and seal, exactly per 05_Q4_2026_PROSPECTIVE_PROTOCOL.md
(SHA-256 55c96b54d25d518e8a1cf9f14707c98e676e71cb70442e5c730ce97465e0963e). Authorized by the user 2026-10-12.
Reads only hash-pinned allowlisted inputs. Writes a new q4/ folder (refuses to overwrite) and marks files read-only.
Run from the aligned backend root:  python -B <this file>
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import guard  # noqa: E402

H1 = "data/supplementary/collection_2026-10-09/provincial_food_cpi_yoy_2026H1_raw.csv"
guard.ALLOW[H1] = ("57f09e91149be56f0602d63dad40216d3fc38d01e66499e07f110d1b2fd2e6e9", None)   # COLLECTION_MANIFEST hash
guard.install()

import hashlib  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import platform  # noqa: E402
import stat  # noqa: E402
import warnings  # noqa: E402
from datetime import datetime, timezone  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

E9R = guard.AL / "experiments" / "2026-10-12_E9_S1_safe_training" / "runner"
sys.path.insert(0, str(E9R))
sys.path.insert(0, str(guard.AL))
import scripts.supplementary.devprotocol_rule_l as D  # noqa: E402
from app.ml.features import risk_score_v2 as R  # noqa: E402
import safe_frame as F  # noqa: E402

warnings.filterwarnings("ignore")
PROTOCOL = guard.EXP / "05_Q4_2026_PROSPECTIVE_PROTOCOL.md"
PROTOCOL_SHA = "55c96b54d25d518e8a1cf9f14707c98e676e71cb70442e5c730ce97465e0963e"
DEADLINE = pd.Timestamp("2026-10-31 23:59:59", tz="Asia/Manila")
TAU_APPROVED = 14.345
TARGET = "2026-Q4"
OUT = guard.EXP / "q4"
CORE = ["last_published_stress", "sws_hunger", "sws_change"]
PARAMS = dict(num_leaves=4, min_child_samples=5, n_estimators=100, learning_rate=0.05, random_state=42, verbosity=-1)
MONO_UP = {"last_published_stress", "sws_hunger"}


class Stop(RuntimeError):
    pass


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def fit_models(X: pd.DataFrame, y_reg: np.ndarray, y_bin: np.ndarray):
    from lightgbm import LGBMClassifier, LGBMRegressor
    mono = [1 if c in MONO_UP else 0 for c in X.columns]
    reg = LGBMRegressor(objective="regression", **PARAMS, monotone_constraints=mono).fit(X, y_reg)
    clf = LGBMClassifier(objective="binary", **PARAMS, monotone_constraints=mono).fit(X, y_bin) \
        if len(set(y_bin)) == 2 else None
    return reg, clf


def train_filter(X: pd.DataFrame) -> list[str]:
    return [c for c in X.columns if not (X[c].isna().mean() > 0.5 or X[c].dropna().nunique() < 2)]


def main() -> None:
    now_utc = datetime.now(timezone.utc)
    now_mnl = pd.Timestamp(now_utc).tz_convert("Asia/Manila")
    if sha(PROTOCOL) != PROTOCOL_SHA:
        raise Stop("protocol hash differs from the freeze record")
    if not now_mnl < DEADLINE:
        raise Stop("issue deadline passed: no forecast (protocol section 2)")
    OUT.mkdir(parents=False, exist_ok=False)                       # never overwrite
    snapshot = pd.Timestamp(now_mnl.tz_localize(None))             # naive Manila time for registry comparisons
    allow_start = guard.verify_allowlist()

    # ---------- SWS input (protocol section 3)
    rounds_all = D.sws_rounds()                                     # registry asserts no protected quarter
    sw = D.sws_known(snapshot, rounds_all)
    if not (sw["sws_round_quarter"] == "2026-Q1" and "March 2026" in str(sw["sws_round"])
            and pd.Timestamp(sw["sws_published"]) == pd.Timestamp("2026-05-12") and sw["sws_date_type"] == "verified"):
        raise Stop(f"SWS input is not the protocol's March 2026 round: {sw['sws_round_quarter']} {sw['sws_round']}")
    avail = [r for r in rounds_all if r.published is not None and r.published < snapshot]
    prev = avail[-2]
    if prev.quarter != "2025-Q4":
        raise Stop(f"previous SWS round is {prev.quarter}, protocol expects 2025-Q4 (November 2025)")
    sws_age = F.qi(TARGET) - F.qi(sw["sws_round_quarter"])
    q1_rounds = [r for r in rounds_all if r.quarter == "2026-Q1"]
    if len(q1_rounds) != 1:
        raise Stop("expected exactly one 2026-Q1 SWS round")

    # ---------- 2026-H1 provincial food CPI YoY (retrieval-evidenced)
    h1 = pd.read_csv(guard.AL / H1, dtype={"province_code": str, "reference_month": str})
    checks = {"rows": len(h1), "commodity": sorted(h1["commodity"].unique()), "status": sorted(h1["value_status"].unique()),
              "months": sorted(h1["reference_month"].unique()), "provinces": sorted(h1["province_code"].unique()),
              "retrieved_at_utc": sorted(h1["retrieved_at_utc"].unique())}
    if not (checks["rows"] == 30 and checks["commodity"] == ["01.1 - FOOD"] and checks["status"] == ["reported"]
            and checks["months"] == [f"2026-0{m}" for m in range(1, 7)] and set(checks["provinces"]) == set(R.PROVINCES)
            and checks["retrieved_at_utc"] == ["2026-10-09T14:40:49.508579+00:00"]):
        raise Stop(f"2026-H1 CPI file failed the protocol checks: {checks}")
    if pd.Timestamp(checks["retrieved_at_utc"][0]) >= pd.Timestamp(now_utc):
        raise Stop("retrieval evidence is not before the snapshot")
    h1["yoy"] = pd.to_numeric(h1["food_cpi_yoy_pct_raw"], errors="coerce")
    h1["quarter"] = "2026-Q" + ((h1["reference_month"].str[-2:].astype(int) - 1) // 3 + 1).astype(str)
    cnt = h1.dropna(subset=["yoy"]).groupby(["province_code", "quarter"]).size()
    if not (cnt == 3).all() or len(cnt) != 10:
        raise Stop("a province-quarter lacks three monthly YoY values")
    yq = h1.groupby(["province_code", "quarter"], as_index=False)["yoy"].mean().rename(columns={"yoy": "food_cpi_yoy"})
    q2 = yq[yq["quarter"] == "2026-Q2"].set_index("province_code")["food_cpi_yoy"]
    cpi_rel_q2 = (q2 - q2.mean()).to_dict()                         # all five present (checked above)

    # ---------- historical S1 labels and training frame (E9 safe frame; reads <= 2025-Q4 only)
    src = F.load_sources(guard)
    stress, rounds_le = F.s1_targets(D, R, src["psa"])
    chk = stress.merge(src["lab"], on=["province_code", "quarter"], how="inner")
    if len(chk) != len(stress) or (chk["stress"] - chk["stress_score"]).abs().max() > 1e-3:
        raise Stop("S1 cross-check failed")
    published = lambda q: D.label_published(q, "development")[0]
    tau, tau_q = R.reference_threshold(stress[["province_code", "quarter", "stress"]], published, pd.Timestamp("2026-07-01"))
    if abs(tau - TAU_APPROVED) > 1e-3 or len(tau_q) != 16:
        raise Stop(f"tau {tau} / {len(tau_q)} quarters differs from the approved 14.345 / 16")
    labels_hist = sorted(stress["quarter"].unique(), key=F.qi)
    if any(published(q) is None or published(q) >= snapshot for q in labels_hist):
        raise Stop("a historical label lacks availability before the snapshot")

    # S1 for 2026-Q1 (primary last-published label and primary-variant training label)
    q1 = R.compute_stress(pd.DataFrame([{"quarter": "2026-Q1", "sws_hunger_pct": q1_rounds[0].value}]),
                          yq[yq["quarter"] == "2026-Q1"][["province_code", "quarter", "food_cpi_yoy"]])
    if q1["stress"].isna().any() or len(q1) != 5:
        raise Stop("2026-Q1 S1 not computable for all five provinces")
    s_q1 = q1.set_index("province_code")["stress"].to_dict()
    s_q4_25 = stress[stress["quarter"] == "2025-Q4"].set_index("province_code")["stress"].to_dict()

    frame = F.build_frame(D, R, src, stress, rounds_le, F.quarter_range("2021-Q2", "2026-Q1"))
    lab_all = pd.concat([stress[["province_code", "quarter", "stress"]], q1[["province_code", "quarter", "stress"]]])

    def train_and_predict(variant: str, train_quarters: list[str], lps: dict) -> tuple[pd.DataFrame, dict]:
        tr = frame[frame["target_quarter"].isin(train_quarters)].merge(
            lab_all, left_on=["target_quarter", "province_code"], right_on=["quarter", "province_code"], how="inner")
        keep = train_filter(tr[CORE])
        y_reg, y_bin = tr["stress"].values, (tr["stress"] > tau).astype(int).values
        reg, clf = fit_models(tr[keep], y_reg, y_bin)
        reg2, clf2 = fit_models(tr[keep], y_reg, y_bin)               # determinism check
        rows, info = [], {"variant": variant, "train_quarters": train_quarters, "n_train_rows": int(len(tr)),
                          "train_HIGH": int(y_bin.sum()), "train_LOW": int((y_bin == 0).sum()), "features_used": keep}
        for p in R.PROVINCES:
            x = pd.DataFrame([{"last_published_stress": lps[p], "sws_hunger": sw["sws_hunger"], "sws_change": sw["sws_change"]}])[keep]
            base = {"province_code": p, "target_quarter": TARGET, "variant": variant}
            reasons = []
            if sws_age > R.SWS_MAX_AGE_QUARTERS:
                reasons.append("stale SWS input")
            preds = {
                "P_S1_rule": sw["sws_hunger"] + 2.0 * cpi_rel_q2[p] if not np.isnan(cpi_rel_q2[p]) else np.nan,
                "B1_carry_forward": lps[p],
                "B2_regional": sw["sws_hunger"],
                "M1_core_regressor": float(reg.predict(x)[0]),
            }
            if float(reg2.predict(x)[0]) != preds["M1_core_regressor"]:
                raise Stop("non-deterministic regressor")
            for arm, v in preds.items():
                r_ = list(reasons) + ([] if pd.notna(v) else ["missing input"])
                rows.append({**base, "arm": arm, "output": "stress", "stress_pred": v, "probability": np.nan,
                             "classification": R.INSUFFICIENT_DATA if r_ else (R.HIGH if v > tau else R.LOW),
                             "insufficient_reasons": "; ".join(r_)})
            if clf is not None:
                pr = float(clf.predict_proba(x)[0, 1])
                if float(clf2.predict_proba(x)[0, 1]) != pr:
                    raise Stop("non-deterministic classifier")
                rows.append({**base, "arm": "M1_core_classifier", "output": "uncalibrated_probability", "stress_pred": np.nan,
                             "probability": pr, "classification": R.final_classification(pr, reasons),
                             "insufficient_reasons": "; ".join(reasons)})
        return pd.DataFrame(rows), info

    P_primary, info_p = train_and_predict("primary_lps_2026Q1", labels_hist + ["2026-Q1"], s_q1)
    P_sens, info_s = train_and_predict("sensitivity_lps_2025Q4", labels_hist, s_q4_25)
    preds = pd.concat([P_primary, P_sens], ignore_index=True)

    # ---------- input snapshot (every input value with source and evidence)
    snap = [{"input": "sws_hunger", "province_code": "REGION", "value": sw["sws_hunger"], "source": "SWS registry (app/ml/corpus/sws_hunger_fetcher.py)",
             "evidence": f"published {pd.Timestamp(sw['sws_published']).date()} ({sw['sws_date_type']}); round {sw['sws_round']}"},
            {"input": "sws_change", "province_code": "REGION", "value": sw["sws_change"], "source": "SWS registry",
             "evidence": f"minus {prev.label} published {prev.published.date()} ({prev.date_type})"},
            {"input": "sws_age_quarters", "province_code": "REGION", "value": sws_age, "source": "derived", "evidence": "limit 3 (only > 3 is stale)"}]
    for p in R.PROVINCES:
        snap += [{"input": "food_cpi_yoy_2026Q2", "province_code": p, "value": float(q2[p]), "source": H1,
                  "evidence": "retrieved 2026-10-09T14:40:49Z (OpenStat 0012M4ACP23); official provincial release date unverified"},
                 {"input": "cpi_rel_2026Q2", "province_code": p, "value": cpi_rel_q2[p], "source": "derived", "evidence": "five-province mean of the above"},
                 {"input": "last_published_stress_2026Q1 (primary)", "province_code": p, "value": s_q1[p], "source": f"S1 from SWS registry + {H1}",
                  "evidence": "SWS 2026-05-12 verified; CPI retrieved 2026-10-09"},
                 {"input": "last_published_stress_2025Q4 (sensitivity)", "province_code": p, "value": s_q4_25[p],
                  "source": "S1 from SWS registry + data/processed/psa_indicators.parquet",
                  "evidence": "SWS Nov 2025 published 2026-01-14; CPI in blob 03a4ec47 committed 2026-09-10"}]
    snap_df = pd.DataFrame(snap)
    snap_df.to_csv(OUT / "inputs_snapshot.csv", index=False)
    lab_all.assign(source=lambda d: np.where(d["quarter"] == "2026-Q1", "S1 computed (primary variant only)", "S1 <= 2025-Q4")) \
        .to_csv(OUT / "training_labels.csv", index=False)
    preds.to_csv(OUT / "predictions.csv", index=False)
    issue_utc = datetime.now(timezone.utc)

    import lightgbm, sklearn  # noqa: E401
    manifest = {
        "protocol": {"file": PROTOCOL.name, "sha256": PROTOCOL_SHA, "verified_at_start": True},
        "authorization": "user message 2026-10-12: 'Generate and seal the Q4 forecast now'",
        "target_quarter": TARGET, "tau": tau, "tau_quarters": tau_q, "tau_approved": TAU_APPROVED,
        "snapshot_time_manila": str(snapshot), "issue_time_utc": issue_utc.isoformat(),
        "issue_deadline_manila": str(DEADLINE), "deadline_met": True,
        "sws_input": {"round": sw["sws_round"], "quarter": sw["sws_round_quarter"], "published": str(sw["sws_published"]),
                      "date_type": sw["sws_date_type"], "age_quarters": sws_age, "previous_round": prev.label},
        "h1_cpi_checks": checks,
        "training": {"primary": info_p, "sensitivity": info_s},
        "allowlist_sha256_start": allow_start, "allowlist_sha256_end": guard.verify_allowlist(),
        "code_sha256": {"q4_forecast.py": sha(Path(__file__)), "guard.py": sha(HERE / "guard.py"),
                        "E9 safe_frame.py": sha(E9R / "safe_frame.py"),
                        "risk_score_v2.py": guard.sha256("app/ml/features/risk_score_v2.py"),
                        "devprotocol_rule_l.py": guard.sha256("scripts/supplementary/devprotocol_rule_l.py"),
                        "sws_hunger_fetcher.py": guard.sha256("app/ml/corpus/sws_hunger_fetcher.py")},
        "environment": {"python": sys.version.split()[0], "platform": platform.platform(), "pandas": pd.__version__,
                        "numpy": np.__version__, "lightgbm": lightgbm.__version__, "sklearn": sklearn.__version__},
        "params": PARAMS, "determinism_check": "models fitted twice; identical predictions",
        "outputs_sha256": {p.name: sha(p) for p in sorted(OUT.glob("*.csv"))},
        "access_log": [a for a in guard.ACCESS_LOG if a["op"] == "read_parquet"] +
                      sorted({json.dumps(a) for a in guard.ACCESS_LOG if a["op"] == "open"}),
        "outcome_information_accessed": False,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str), encoding="utf-8")
    man_sha = sha(OUT / "manifest.json")
    (OUT / "SEAL.md").write_text(
        "# 2026-Q4 Forecast Seal\n\n"
        f"- Issued (UTC): {issue_utc.isoformat()}\n"
        f"- Protocol SHA-256: `{PROTOCOL_SHA}`\n"
        f"- predictions.csv SHA-256: `{manifest['outputs_sha256']['predictions.csv']}`\n"
        f"- inputs_snapshot.csv SHA-256: `{manifest['outputs_sha256']['inputs_snapshot.csv']}`\n"
        f"- **manifest.json SHA-256: `{man_sha}`**\n\n"
        "Email the manifest SHA-256 to your adviser today as an independent timestamp. "
        "Before any outcome collection, re-verify every hash above; any mismatch voids the forecast.\n",
        encoding="utf-8")
    for p in OUT.iterdir():
        os.chmod(p, stat.S_IREAD)
    print(f"SEALED {TARGET}: issue {issue_utc.isoformat()} | manifest {man_sha}")


if __name__ == "__main__":
    main()
