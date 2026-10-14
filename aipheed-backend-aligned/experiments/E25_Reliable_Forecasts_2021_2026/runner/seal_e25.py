"""E25 prospective seal (FROZEN_EVALUATION_PROTOCOL.md section 9).

Origin O(2026-Q3) = 2026-10-01 00:00 PHT (later than every existing sealed origin). Information: authorized data only
(labels through 2026-Q2, D through 2026-Q2, SWS rounds through June 2026). Targets 2026-Q4 (k = 1), 2027-Q1 (k = 2).
Only arms whose every input is authorized are sealed; every other arm is recorded with the exact missing input.
The seal is written once (refused if one exists); --verify recomputes and compares bytes without writing.
Usage: python -B runner/seal_e25.py [--verify]"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard  # noqa: E402

guard.install()
import argparse  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
from datetime import datetime, timezone  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import e25lib as E  # noqa: E402
import run_e25 as R  # noqa: E402

EXP = guard.EXP
qk, qs = E.qk, E.qs
ORIGIN_Q = "2026-Q3"
TARGETS = {1: "2026-Q4", 2: "2027-Q1"}
SEALABLE_T1 = ["B1_naive_persistence", "B1p_calibrated_persistence", "CLIM_training_rate", "PCF21", "PCF21_SUPP",
               "PCF21_MR", "PCF21_LI", "ENS_PCF21_B1p", "GATE_PCF21_B1p", "CAL_PCF21", "E24_LR_P"]
SEALABLE_T2 = ["B1_naive_persistence", "B1p_calibrated_persistence", "CLIM_training_rate", "M3_21", "D_HIER",
               "E24_LR_P_T2"]
MISSING = {
    "PCF21_NOW": "Dnow(2026-Q3) = July-August 2026 provincial food CPI (not authorized)",
    "PCF21_HIER": "Dnow(2026-Q3) = July-August 2026 provincial food CPI (not authorized)",
    "M4_21 (FINAL_T2)": "Dnow(2026-Q3) = July-August 2026 provincial food CPI (not authorized)",
    "D_HIER_NOW": "Dnow(2026-Q3) = July-August 2026 provincial food CPI (not authorized)",
    "ENS_M4_B1p": "Dnow(2026-Q3) via M4_21 (not authorized)",
    "B2-B6, PROPOSED (feature models)": "2026-Q3 news articles and 2026-Q2 government indicators (not authorized)",
}
ASSUMPTION = ("No September 2026 SWS round was published before 2026-10-01 (every Q3 round in 2021-2025 was published "
              "on 17 October or later). Not verified: the protected round was not opened.")


def forecast_rows(T, t, tau):
    lv = E.last_values(T, t)
    rows = []
    for p in E.PROVS:
        last, m4, dif = lv[p]
        rows.append({"province_code": p, "t": t, "v_last": last, "margin_last": last - tau,
                     "y_last": float(last > tau), "v_mean4": m4, "v_diff": dif})
    return pd.DataFrame(rows)


def compute(data):
    t = qk(ORIGIN_Q)
    O = E.origin(t)
    # authorization assertions: no input after 2026-Q2 / June 2026
    assert max(q for _, q in data["Dm"]) <= qk("2026-Q2") and max(q for _, q in data["Nm"]) <= qk("2026-Q2")
    assert data["rounds"]["fieldwork_quarter"].map(qk).max() <= qk("2026-Q2")
    used_rounds = data["rounds"][data["rounds"]["published_eff"] < O]
    rows, comps = [], []
    for tname, arms in (("T1_A", SEALABLE_T1), ("T2", SEALABLE_T2)):
        T = data["targets"][tname]
        tau = T.tau(t)
        pub = T.published(t)
        for k, tq in TARGETS.items():
            te = forecast_rows(T, t, tau)
            tr = E.training_pairs(T, t, k, tau, {})
            assert tr["target_q"].nunique() >= E.MIN_TRAIN_QUARTERS and tr["target_q"].max() <= t - 1
            s, det = {}, {}
            s["B1_naive_persistence"] = te["y_last"].to_numpy(float)
            s["B1p_calibrated_persistence"] = E.calibrated_persistence(tr, te["y_last"].to_numpy())
            s["CLIM_training_rate"] = E.climatology(tr, 5)
            if tname == "T1_A":
                s["E24_LR_P"] = E.lr_p(tr, te)
                hc, dc = {}, {}
                for arm in ("PCF21", "PCF21_SUPP", "PCF21_MR", "PCF21_LI"):
                    o = E.pcf_t1(arm, data["rounds"], data["Dm"], data["Nm"], t, k, tau, data["extras"], hc, dc)
                    assert o is not None, arm
                    s[arm] = np.array([o[p]["p"] for p in E.PROVS])
                    det[arm] = o
                s["ENS_PCF21_B1p"] = (s["PCF21"] + s["B1p_calibrated_persistence"]) / 2
                inn = R.inner_gate_cal(T, data, t, k, tau, tr, {}, hc, dc)
                s["GATE_PCF21_B1p"] = s["PCF21"] if (inn is not None and inn["brier_pcf"] < inn["brier_b1p"] - 1e-12) \
                    else s["B1p_calibrated_persistence"]
                a = E.temperature(inn["p_pcf"], inn["y"]) if inn is not None else 1.0
                s["CAL_PCF21"] = E.apply_temperature(s["PCF21"], a)
            else:
                s["E24_LR_P_T2"] = E.lr_p(tr, te)
                dc = {}
                for arm, spec in (("M3_21", "ols"), ("D_HIER", "hier")):
                    o = E.t2_prob(spec, data["Dm"], data["Nm"], t, k, dc)
                    assert o is not None, arm
                    s[arm] = np.array([o[p]["p"] for p in E.PROVS])
                    det[arm] = o
            assert set(s) == set(arms)
            for arm in arms:
                for i, p in enumerate(E.PROVS):
                    r = {"target": tname, "arm": arm, "final": arm == ("PCF21" if tname == "T1_A" else "-"),
                         "target_quarter": tq, "lead": k, "origin": O.isoformat(), "info_cutoff": "2026-09-30T23:59:59+08:00",
                         "province_code": p, "province": E.PNAME[p], "p": round(float(s[arm][i]), 10),
                         "tau": round(tau, 10), "y_last": te["y_last"].iloc[i], "v_last": round(float(te["v_last"].iloc[i]), 10),
                         "lead_validated": False}
                    if arm in det:
                        o = det[arm][p]
                        for c in ("mu_S1", "sd_S1", "mu_H", "sd_H", "mu_D", "sd_D", "z", "regional_part",
                                  "provincial_part", "var_share_regional"):
                            if c in o:
                                r[c] = round(float(o[c]), 10)
                        if "mu_S1" in o:
                            r["lo80_S1"] = round(float(o["mu_S1"] - E.Z80 * o["sd_S1"]), 10)
                            r["hi80_S1"] = round(float(o["mu_S1"] + E.Z80 * o["sd_S1"]), 10)
                    rows.append(r)
        comps.append({"target": tname, "tau": tau, "labels_published": sorted(pub["quarter"].unique(), key=qk)})
    info = {"origin": O.isoformat(), "rounds_used": used_rounds[["quarter", "round", "H", "published", "published_eff",
                                                                  "definition_A", "source"]].astype(str).to_dict("records"),
            "thresholds": comps, "missing_input_arms": MISSING, "assumption": ASSUMPTION}
    return pd.DataFrame(rows), info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    R.check_frozen()
    existing = sorted((EXP / "runs").glob("SEAL_E25_*"))
    if existing and not a.verify:
        raise SystemExit(f"E25 seal refused: {existing[-1].name} exists (never seal twice). Use --verify.")
    if not existing and a.verify:
        raise SystemExit("nothing to verify")
    guard.verify_allowlist()
    data = R.load_real()
    df, info = compute(data)
    b = df.to_csv(index=False, lineterminator="\n").encode()
    h = hashlib.sha256(b).hexdigest()
    if a.verify:
        old = json.loads((existing[-1] / "SEAL.json").read_text(encoding="utf-8"))
        same = old["sha256_forecasts"] == h and (existing[-1] / "prospective_forecasts.csv").read_bytes() == b
        print(json.dumps({"seal": existing[-1].name, "recomputed_sha256": h, "sealed_sha256": old["sha256_forecasts"],
                          "identical": same}))
        if not same:
            raise SystemExit(2)
        return
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    sd = EXP / "runs" / f"SEAL_E25_{stamp}"
    sd.mkdir()
    (sd / "prospective_forecasts.csv").write_bytes(b)
    (sd / "seal_info.json").write_text(json.dumps(info, indent=1, default=str), encoding="utf-8")
    seal = {"sealed_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "sha256_forecasts": h,
            "sha256_seal_info": hashlib.sha256((sd / "seal_info.json").read_bytes()).hexdigest(),
            "rows": int(len(df)), "origin": info["origin"], "targets": TARGETS,
            "protocol": (EXP / "runner" / "PROTOCOL_SHA256.txt").read_text(encoding="utf-8"),
            "runner_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in sorted((EXP / "runner").glob("*.py"))},
            "statement": "Sealed before any 2026-Q4 or 2027-Q1 outcome exists; no 2026-Q3 outcome was opened. "
                         "Score only with runner/score_sealed.py after the researcher authorizes the outcomes."}
    (sd / "SEAL.json").write_text(json.dumps(seal, indent=1), encoding="utf-8")
    print(sd.name, h)


if __name__ == "__main__":
    main()
