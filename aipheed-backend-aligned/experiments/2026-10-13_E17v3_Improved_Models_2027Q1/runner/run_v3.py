"""E17 v3 runner: rolling-origin backtests at h = 1..5 (h = 5 primary), frozen selection at h = 5, refit and the
2027-Q1 research forecast. Usage: python -B runner/run_v3.py [--deliverables]"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "21")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard  # noqa: E402

guard.install()
import hashlib  # noqa: E402
import io  # noqa: E402
import json  # noqa: E402
import platform  # noqa: E402
from datetime import datetime, timezone  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import v3_lib as V  # noqa: E402

EXP = guard.EXP
HS = [1, 2, 3, 4, 5]
PRIMARY_H = 5
TARGET_Q = "2027-Q1"
MAXQ = "2025-Q4"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def jd(o):
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(type(o))


def check_frozen():
    for ln in (EXP / "runner" / "PROTOCOL_SHA256.txt").read_text(encoding="utf-8").splitlines():
        p = ln.split()
        if len(p) == 2 and len(p[0]) == 64 and sha(EXP / p[1]) != p[0]:
            raise SystemExit(f"E17v3: {p[1]} differs from its frozen hash; stop.")


def load(log):
    comp = pd.read_csv(io.StringIO(guard.read_allowed_text(guard.E12_RUN / "realized_components_2021_2025.csv")),
                       dtype={"province_code": str})
    det = json.loads(guard.read_allowed_text(guard.E12_RUN / "details.json"))
    rounds = pd.DataFrame(det["two_layer"]["regional_layer_rounds"])
    ff = guard.read_allowed_parquet(guard.PROC / "features_fused.parquet", ["province_code", "quarter", "unemployment_rate"])
    for name, qcol in [("components", comp["quarter"]), ("rounds", rounds["quarter"]), ("features_fused", ff["quarter"])]:
        bad = [q for q in qcol if V.qk(q) > V.qk(MAXQ)]
        log.append({"assert": f"{name}: no quarter after {MAXQ}", "rows": int(len(qcol)), "violations": len(bad)})
        if bad:
            raise guard.AccessDenied(f"E17v3: {name} has quarters after {MAXQ}")
    hs = V.h_quarterly(rounds)
    f5 = comp.drop_duplicates("quarter").set_index("quarter")["mean5"]
    f5 = pd.Series(f5.values, index=[V.qk(q) for q in f5.index])
    U = ff.drop_duplicates("quarter").set_index("quarter")["unemployment_rate"]
    nu = ff.groupby("quarter")["unemployment_rate"].nunique()
    log.append({"check": "unemployment identical across provinces in each quarter", "ok": bool((nu == 1).all())})
    U = pd.Series(U.values, index=[V.qk(q) for q in U.index])
    return comp, rounds, hs, f5, U


def backtest_H(hs, f5, U):
    rows = []
    for h in HS:
        for T in hs.index:
            c, meta = V.h_candidates(hs, f5, U, T, h)
            for name, v in c.items():
                rows.append({"target": "H", "h": h, "origin_target": V.qs(T), "unit": "REGION", "candidate": name,
                             "forecast": v, "info_cutoff": meta["info_cutoff"], "latest_observed": meta.get("latest_observed"),
                             "n_train": meta.get(f"{name}_n_train")})
    return pd.DataFrame(rows)


def backtest_FD(comp):
    rows = []
    for var in ("F", "D"):
        for h in HS:
            for T in range(V.qk(V.FIRST_Q) + 1, V.qk(MAXQ) + 1):
                df, meta = V.fd_candidates(comp, var, T, h)
                if df.empty:
                    continue
                for r in df.itertuples(index=False):
                    for name in [c for c in df.columns if c != "province_code"]:
                        v = getattr(r, name)
                        if v == v:
                            rows.append({"target": var, "h": h, "origin_target": V.qs(T), "unit": r.province_code,
                                         "candidate": name, "forecast": float(v), "info_cutoff": V.qs(T - h),
                                         "latest_observed": V.qs(T - h), "n_train": meta.get("n_train_quarters")})
    return pd.DataFrame(rows)


def perturbation(hs, f5, U, comp, preds):
    """For every h=5 origin: overwrite everything after the cutoff and confirm identical candidate outputs."""
    ok = {}
    for T in sorted({V.qk(q) for q in preds.loc[preds["h"] == PRIMARY_H, "origin_target"]}):
        cut = T - PRIMARY_H
        hs2 = hs.copy(); hs2[hs2.index > cut] = 999.0
        f52 = f5.copy(); f52[f52.index > cut] = 999.0
        U2 = U.copy(); U2[U2.index > cut] = 999.0
        a, _ = V.h_candidates(hs, f5, U, T, PRIMARY_H)
        b, _ = V.h_candidates(hs2, f52, U2, T, PRIMARY_H)
        c2 = comp.copy(); c2.loc[c2["quarter"].map(V.qk) > cut, ["F", "D", "mean5"]] = 999.0
        same_fd = True
        for var in ("F", "D"):
            x, _ = V.fd_candidates(comp, var, T, PRIMARY_H)
            y, _ = V.fd_candidates(c2, var, T, PRIMARY_H)
            same_fd &= (x.empty and y.empty) or x.equals(y)
        ok[V.qs(T)] = bool(a == b and same_fd)
    if not all(ok.values()):
        raise RuntimeError(f"E17v3: perturbation check failed {ok}")
    return ok


def evaluate(preds, actual):
    d = preds.merge(actual, on=["target", "origin_target", "unit"], how="left")
    d = d[d["y"].notna()].copy()
    d["abs_err"] = (d["forecast"] - d["y"]).abs()
    d["err"] = d["forecast"] - d["y"]
    res, per = {}, []
    groups = {"H": (["C1_carry_forward"], V.H_SELECTABLE, V.H_DIAG), "F": (V.F_BASE, V.F_FIT, []), "D": (V.D_BASE, V.D_FIT, [])}
    for (tg, h), g in d.groupby(["target", "h"]):
        base, sel, diag = groups[tg]
        need = base + sel
        q_ok = None
        for c in need:
            qs_c = set(g.loc[g["candidate"] == c, "origin_target"])
            q_ok = qs_c if q_ok is None else (q_ok & qs_c)
        q_ok = sorted(q_ok or [], key=V.qk)
        gg = g[g["origin_target"].isin(q_ok)]
        per_origin = gg.groupby(["candidate", "origin_target"])["abs_err"].mean().unstack(0)
        per_origin.index = [V.qk(q) for q in per_origin.index]
        per_origin = per_origin.sort_index()
        r = {"common_origins": q_ok, "n_origins": len(q_ok),
             "evidence_label": "exploratory only (fewer than 8 origins)" if len(q_ok) < 8 else "8 or more origins",
             "candidates": {}}
        for c in [x for x in base + sel + diag if x in per_origin.columns]:
            gc = gg[gg["candidate"] == c]
            ordered = per_origin[c]
            k = len(ordered) // 2
            r["candidates"][c] = {"MAE": float(gc["abs_err"].mean()), "RMSE": float(np.sqrt((gc["err"] ** 2).mean())),
                                  "bias": float(gc["err"].mean()), "rows": int(len(gc)),
                                  "early_MAE": float(ordered.iloc[:k].mean()) if k else None,
                                  "late_MAE": float(ordered.iloc[k:].mean()) if len(ordered) else None,
                                  "per_origin_abs_err": {V.qs(i): float(v) for i, v in ordered.items()}}
        if len(q_ok) and h == PRIMARY_H:
            sel_res = {}
            for c in sel:
                if c not in per_origin.columns:
                    continue
                checks = {b: V.rule_check(per_origin[c], per_origin[b]) for b in base}
                sel_res[c] = {"vs": checks, "passes_all_baselines": all(x["passes"] for x in checks.values())}
            winners = [c for c, x in sel_res.items() if x["passes_all_baselines"]]
            chosen = min(winners, key=lambda c: r["candidates"][c]["MAE"]) if winners else base[0]
            r["selection"] = {"checks": sel_res, "qualifying": winners, "selected": chosen,
                              "status": ("no candidate satisfies the frozen rule; baseline kept" if not winners else
                                         f"{chosen} satisfies the frozen rule") +
                                        ("; exploratory only, not validated (fewer than 8 origins)" if len(q_ok) < 8 else "")}
        res[f"{tg}|h{h}"] = r
        for c, gc in gg.groupby("candidate"):
            for q, x in gc.groupby("origin_target"):
                per.append({"target": tg, "h": h, "candidate": c, "origin_target": q, "MAE": float(x["abs_err"].mean()),
                            "mean_error": float(x["err"].mean())})
    return d, res, pd.DataFrame(per)


def forecast_2027(hs, f5, U, comp, res):
    T = V.qk(TARGET_Q)
    out = {"target_quarter": TARGET_Q, "horizon_h": PRIMARY_H, "information_cutoff": MAXQ, "outputs": {}, "artifacts": {}}
    c, meta = V.h_candidates(hs, f5, U, T, PRIMARY_H)
    sel = res[f"H|h{PRIMARY_H}"].get("selection", {}).get("selected", "C1_carry_forward")
    out["outputs"]["H"] = {"label": "Research forecast of regional hunger (SWS Balance Luzon, % of families); "
                                    "this is not a forecast of provincial food insecurity.",
                           "selected_by_frozen_rule": sel, "selected_forecast": c.get(sel), "all_candidates_experimental": c,
                           "latest_observed": meta.get("latest_observed"), "steps_to_target": meta.get("steps_to_target")}
    out["artifacts"]["H"] = {k: v for k, v in meta.items() if k.endswith("_model")}
    for var, lab in (("F", "Research forecast of provincial food inflation (year-on-year %); not a forecast of food insecurity."),
                     ("D", "Research forecast of relative provincial food-price pressure (points vs the unweighted five-province mean); "
                           "not a forecast of food insecurity.")):
        df, m = V.fd_candidates(comp, var, T, PRIMARY_H)
        sel = res[f"{var}|h{PRIMARY_H}"].get("selection", {}).get("selected")
        out["outputs"][var] = {"label": lab, "selected_by_frozen_rule": sel,
                               "selected_forecast_by_province": df.set_index("province_code")[sel].to_dict() if sel in df else None,
                               "all_candidates_experimental": df.set_index("province_code").to_dict("index")}
        out["artifacts"][var] = m
    return out


def main(deliverables):
    check_frozen()
    started = datetime.now(timezone.utc)
    out = EXP / "runs" / started.strftime("%Y%m%dT%H%M%SZ")
    out.mkdir(parents=True)
    log = [{"check": "allowlist hashes (start)", "result": guard.verify_allowlist()}]
    comp, rounds, hs, f5, U = load(log)
    pH, pFD = backtest_H(hs, f5, U), backtest_FD(comp)
    preds = pd.concat([pH, pFD], ignore_index=True)
    pert = perturbation(hs, f5, U, comp, preds)
    log.append({"check": "future-perturbation (h=5 origins)", "result": pert})
    preds.to_csv(out / "rolling_origin_predictions.csv", index=False, lineterminator="\n", float_format="%.8g")
    seal = {"sha256": sha(out / "rolling_origin_predictions.csv"), "sealed_utc": datetime.now(timezone.utc).isoformat()}
    (out / "SEAL.json").write_text(json.dumps(seal, indent=1), encoding="utf-8", newline="\n")
    act = [{"target": "H", "origin_target": V.qs(k), "unit": "REGION", "y": float(v)} for k, v in hs.items()]
    for var in ("F", "D"):
        act += [{"target": var, "origin_target": r.quarter, "unit": r.province_code, "y": float(getattr(r, var))}
                for r in comp.itertuples()]
    d, res, per = evaluate(preds, pd.DataFrame(act))
    d.to_csv(out / "scored_predictions.csv", index=False, lineterminator="\n", float_format="%.8g")
    per.to_csv(out / "per_origin_errors.csv", index=False, lineterminator="\n", float_format="%.6g")
    fc = forecast_2027(hs, f5, U, comp, res)
    fc["generated_utc"] = datetime.now(timezone.utc).isoformat()
    (out / "metrics.json").write_text(json.dumps(res, indent=1, default=jd), encoding="utf-8", newline="\n")
    (out / "forecast_2027Q1.json").write_text(json.dumps(fc, indent=1, default=jd), encoding="utf-8", newline="\n")
    rows = []
    for key, r in res.items():
        tg, h = key.split("|")
        for c, m in r["candidates"].items():
            rows.append({"target": tg, "h": int(h[1:]), "candidate": c, "n_origins": r["n_origins"],
                         "evidence_label": r["evidence_label"], "MAE": m["MAE"], "RMSE": m["RMSE"], "bias": m["bias"],
                         "early_MAE": m["early_MAE"], "late_MAE": m["late_MAE"], "rows": m["rows"]})
    summ = pd.DataFrame(rows)
    summ.to_csv(out / "metrics_summary.csv", index=False, lineterminator="\n", float_format="%.6g")
    log.append({"check": "allowlist hashes (end)", "result": guard.verify_allowlist()})
    (out / "integrity_log.json").write_text(json.dumps({"log": log, "access_log": guard.ACCESS_LOG}, indent=1, default=jd),
                                            encoding="utf-8", newline="\n")
    if deliverables:
        summ.to_csv(EXP / "METRICS_SUMMARY.csv", index=False, lineterminator="\n", float_format="%.6g")
    man = {"started_utc": started.isoformat(), "finished_utc": datetime.now(timezone.utc).isoformat(),
           "frozen": (EXP / "runner" / "PROTOCOL_SHA256.txt").read_text(encoding="utf-8"),
           "code_sha256": {p.name: sha(p) for p in sorted((EXP / "runner").glob("*.py"))},
           "outputs_sha256": {p.name: sha(p) for p in sorted(out.glob("*")) if p.name != "manifest.json"},
           "environment": {"python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__}}
    (out / "manifest.json").write_text(json.dumps(man, indent=1), encoding="utf-8", newline="\n")
    print(out)


if __name__ == "__main__":
    main("--deliverables" in sys.argv)
