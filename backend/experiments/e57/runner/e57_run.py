"""E57: final label/model experiment (lead 1). Experiment only. Pre-registration: ../E57_results.md (written first).

    python -B backend/experiments/e57/runner/e57_run.py  -> backend/experiments/e57/E57_results.json

Reuses the E56 harness (e56_run: E53-A1 data with cond_* inputs, nested walk-forward, C2 shrinkage, label stats).
  V0  E53-A1, L0 label (sanity check; stops unless acc 0.785, bal 0.836, AUC 0.880)
  V1  L0 label; pool COMPACT_T5_C + y_last, COMB_T5_C (COMB_T5_C already holds y_last) x G1/G4/G3/G2
  V2  HIGH if S1(p,q) > S1(p,q-4), q-4 posted before the origin (else undefined); y_last = V2 label of the latest
      quarter <= t-1 posted before the origin whose V2 label is defined; pool E53-A1. Scored where defined.
"""
from __future__ import annotations

import hashlib
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
E57 = Path(__file__).resolve().parents[1]
BACKEND = E57.parents[1]
sys.path.insert(0, str(BACKEND / "experiments" / "e56" / "runner"))
import e56_run as H  # noqa: E402  (E56 harness; brings in e53/e50/e49/e48/e36)

E, X, R, L6, C, np, pd = H.E, H.X, H.R, H.L6, H.C, H.np, H.pd
L6.guard32.EXP = E57                                       # writes confined to E57
NAMES, PROVS = H.NAMES, H.PROVS
PROTECTED = {"data/e36/e36_record.json": "921f2130c2ab3380c3cd21c1b25fe31a",
             "data/e48/e48_record.json": "a2223c22f85cb4058c0e7e59229dcb67",
             "data/e49/e49_record.json": "14c818ea990b6959584fbff92afd3ade",
             "data/e49/model/E48-A1-LGBM_O2026-10-01.txt": "2b6be3e9ab5e63191aa03639a5640ab1",
             "data/e49/model/E49_C2_calibration.json": "8f0eae02d81857f1d3c72ca5965409df"}
POOLS = {"V0": "E53-A1", "V1": "E57-V1", "V2": "E53-A1"}


def md5s() -> dict:
    out = {p: hashlib.md5((BACKEND / p).read_bytes()).hexdigest() for p in PROTECTED}
    bad = [p for p, h in out.items() if h != PROTECTED[p]]
    if bad:
        raise SystemExit(f"protected md5 mismatch: {bad}")
    return out


def register():
    E.register()
    L6.FEATURE_SETS["COMPACT_T5_CY"] = L6.FEATURE_SETS["COMPACT_T5_C"] + ["y_last"]
    L6.POOLS["E57-V1"] = ([("COMPACT_T5_CY", g) for g in L6.COMPLEXITY] + [("COMB_T5_C", g) for g in L6.COMPLEXITY],
                          ("COMB_T5_C", "G1"))


class Data(H.Data):
    """L0 data (E56 harness); worsening=True -> the V2 label."""

    def __init__(self, cond, worsening: bool):
        super().__init__(cond, "L0")
        self.worsening = worsening
        self._posted = {}
        self.leak = []                                      # (origin, kind, quarter used, latest posting) records

    def posted(self, t) -> set:
        if t not in self._posted:
            self._posted[t] = set(self.posted_quarters(L6.origin(t)))
        return self._posted[t]

    def worse(self, p, q, t):
        """V2 label of (p, q) as known at origin O(t): q-4 must be posted before O(t)."""
        s, s0 = self.Sv.get((p, q)), self.Sv.get((p, q - 4))
        if s is None or s != s or s0 is None or s0 != s0 or (q - 4) not in self.posted(t):
            return None
        return int(s > s0)

    def label(self, p, target, t):
        if not self.worsening:
            return super().label(p, target, t)
        y = self.worse(p, target, t)
        if y is not None:
            self.leak.append((t, "V2 comparison", target - 4))
        return y

    def last_v2(self, p, t):
        for q in sorted((x for x in self.posted(t) if x <= t - 1), reverse=True):
            y = self.worse(p, q, t)
            if y is not None:
                return q, y
        return None, None

    def features(self, t, k):
        Xf = super().features(t, k)
        if self.worsening:
            ys = []
            for p in Xf["province_code"]:
                q, y = self.last_v2(p, t)
                ys.append(np.nan if y is None else float(y))
                if q is not None:
                    self.leak.append((t, "y_last quarter", q))
                    self.leak.append((t, "y_last comparison", q - 4))
            Xf["y_last"] = ys
        else:
            last = Xf["last_label_quarter"].iloc[0]
            if last:
                self.leak.append((t, "y_last quarter", C.qk(last)))
        return Xf

    def training_pairs(self, t, k):
        tr = super().training_pairs(t, k)
        if self.worsening and not tr.empty:
            tr = tr.assign(y=[self.worse(p, q, t) for p, q in zip(tr["province_code"], tr["target_q"])])
            for q in set(tr.loc[tr["y"].notna(), "target_q"]):
                self.leak.append((t, "V2 comparison (training)", q - 4))
            tr = tr[tr["y"].notna()].astype({"y": int}).reset_index(drop=True)
        return tr


def leakage(d: Data) -> dict:
    """every quarter used for y_last / the V2 comparison must have all its rounds posted before the origin."""
    usable = d.defA.groupby("tq")["usable"].max().to_dict()
    viol, n, latest = [], 0, {}
    for t, kind, q in set(d.leak):
        n += 1
        o = L6.origin(t)
        u = usable.get(q)
        if q not in d.posted(t) or u is None or not (u < o):
            viol.append({"origin": str(o.date()), "kind": kind, "quarter": C.qs(q), "posted": str(u)})
        if u is not None:
            latest[(str(o.date()), kind)] = max(latest.get((str(o.date()), kind), pd.Timestamp.min), u)
    return {"checks": n, "violations": viol,
            "latest_posting_by_origin": {f"{o} | {k}": str(v.date()) for (o, k), v in sorted(latest.items())}}


def run_variant(name, cond, E31):
    d = Data(cond, worsening=(name == "V2"))
    pool = POOLS[name]
    Pr, info = L6.walk_forward(d)
    wf = [C.qk(x) - 1 for x in info["dates"]]
    T = L6.OPERATIONAL_T
    alld = wf + [T]
    labels = {t: {c: int(d.label(c, t + 1, t)) for c in PROVS} for t in wf}
    labels_all = {**labels, T: {c: 0 for c in PROVS}}
    base = {t: float((d.train(t)["y"].sum() + 1) / (len(d.train(t)) + 2)) for t in alld}
    prior_of = {t: L6.eligible_prior_dates(d, t, wf) for t in alld}
    raw, cfg, ylast = {}, {}, {}
    for t in alld:
        fs, g = (L6.operational_choice(d, Pr, pool)[0] if t == T
                 else info["selections"][pool][C.qs(t + 1)]["chosen"].split("x"))
        tr, te = d.train(t), d.test(t)
        _ptr, pte, _m = X.lgbm_arrays(tr, te, L6.FEATURE_SETS[fs], g)
        raw[t], cfg[t] = dict(zip(te["province_code"], pte)), L6.cfg_name(fs, g)
        ylast[t] = dict(zip(te["province_code"], te["y_last"]))
    cal, _fb, pa = R.calibrated(raw, labels_all, base, prior_of, "shrink")
    dev = [t for t in wf if C.qs(t + 1) in H.E53_QUARTERS]
    g = pd.DataFrame([{"t": C.qs(t), "target_quarter": C.qs(t + 1), "province_code": c, "arm": name, "p": cal[t][c],
                       "p_raw": raw[t][c], "y": labels[t][c], "y_last": ylast[t][c]} for t in dev for c in PROVS])
    s = R.summary(g)
    pred = g["p"] >= 0.5
    sel = Pr["target_quarter"].isin(g["target_quarter"].unique())
    pers = Pr[(Pr["arm"] == "B1_PERSISTENCE") & sel]
    sp = R.summary(pers)
    flip = g["y_last"].notna() & (g["y"] != g["y_last"])
    st = H.label_stats(d, g)
    m = {"accuracy": s["accuracy"], "balanced_accuracy": s["balanced_accuracy"], "auc": s["auc"], "brier": s["brier"],
         "LOW_caught": int((~pred & (g["y"] == 0)).sum()), "LOW_rows": int((g["y"] == 0).sum()), "n": int(len(g)),
         "HIGH_share_2024_2026": st["share_HIGH_2024_2026"],
         "flips": int(flip.sum()), "flips_caught": int((flip & (pred == (g["y"] == 1))).sum()),
         "y_last_missing": int(g["y_last"].isna().sum())}
    per = {"accuracy": sp["accuracy"], "balanced_accuracy": sp["balanced_accuracy"], "n": int(len(pers))}
    crit = {"a_bal_ge_0.75_and_gt_persistence": (m["balanced_accuracy"] or 0) >= 0.75
                                                 and (m["balanced_accuracy"] or 0) > (per["balanced_accuracy"] or 0),
            "b_auc_ge_0.75": (m["auc"] or 0) >= 0.75, "c_keeps_H": True}
    if name == "V2":
        crit["d_HIGH_share_2024_2026_30_70"] = 0.30 <= st["share_HIGH_2024_2026"] <= 0.70
    st.pop("labels_by_quarter")
    return {"pool": pool, "scored_quarters": sorted(g["target_quarter"].unique()),
            "missing_dev_quarters": [q for q in H.E53_QUARTERS if q not in set(g["target_quarter"])],
            "model": m, "persistence": per, "label_stats": st,
            "pool_configs": {C.qs(t + 1): cfg[t] for t in alld},
            "q4_2026": {"CALABARZON": float(np.mean(list(cal[T].values()))), **{NAMES[c]: float(cal[T][c]) for c in PROVS}},
            "q4_2026_y_last": {NAMES[c]: (None if v != v else float(v)) for c, v in ylast[T].items()},
            "leakage": leakage(d),
            "adoption": {"criteria": crit, "eligible": name != "V0" and all(crit.values())}}, g


def main():
    os.chdir(BACKEND)
    res = {"md5_start": md5s()}
    register()
    E31 = X.live_engine()
    cond = E.build_cond()
    frames = []
    res["variants"] = {}
    for name in POOLS:
        print("running", name, flush=True)
        o, g = run_variant(name, cond, E31)
        res["variants"][name] = o
        frames.append(g)
        print(" ", name, {k: round(v, 3) if isinstance(v, float) else v for k, v in o["model"].items()},
              "pers bal", round(o["persistence"]["balanced_accuracy"], 3), "Q4", round(o["q4_2026"]["CALABARZON"], 3),
              "leak violations", len(o["leakage"]["violations"]), flush=True)
        if name == "V0":
            mm = o["model"]
            ok = (round(mm["accuracy"], 3), round(mm["balanced_accuracy"], 3), round(mm["auc"], 3)) == (0.785, 0.836, 0.880)
            res["V0_reproduces_E53_A1"] = ok
            if not ok:
                raise SystemExit(f"V0 does not reproduce E53-A1: {mm}")
    elig = [v for v in ("V1", "V2") if res["variants"][v]["adoption"]["eligible"]]
    res["adoption"] = {"eligible": elig,
                       "verdict": ("adopt V1" if "V1" in elig else "adopt V2" if elig
                                   else "Keep L0 / E53-A1; label experiments closed.")}
    res["md5_end"] = md5s()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run = E57 / "runs" / stamp
    run.mkdir(parents=True)
    pd.concat(frames).to_csv(run / "predictions.csv", index=False, float_format="%.10g")
    res["run"] = stamp
    C.write_json(E57 / "E57_results.json", C.clean(res))
    print("RUN", stamp, "eligible", elig, "verdict", res["adoption"]["verdict"])


if __name__ == "__main__":
    main()
