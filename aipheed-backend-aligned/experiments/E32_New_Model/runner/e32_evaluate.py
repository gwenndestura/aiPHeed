"""E32 walk-forward evaluation under the frozen protocol (PROTOCOL.md, sha in runner/PROTOCOL_SHA256.txt).

    python -B runner/e32_evaluate.py            -> runs/<UTC stamp>/{predictions.csv, results.json, meta.json}

Leads 1 and 2; targets 2023-Q4..2026-Q3 with a released label. Selection period = lead-1 targets <= 2025-Q4;
development test = 2026-Q1..2026-Q3. The selection rule and acceptance criteria A1-A3 are applied once, here.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "E31_Chapter1_Completion" / "runner"))
import e32_common as C  # noqa: E402
import e32_lib as L  # noqa: E402
import e28_metrics as M  # noqa: E402

np, pd = C.np, C.pd
E25RUN = C.EXPS / "E25_Reliable_Forecasts_2021_2026" / "runs" / "20261014T002026Z" / "predictions_T1_A.csv"
EXT = C.EXPS / "2026-10-14_P45_2026_Extension" / "runs" / "20261014T105026Z" / "predictions.csv"
P45_Q3 = C.EXPS / "E31_Chapter1_Completion" / "frozen" / "E31_FROZEN_Q3_P45_LEAD2.json"
FIRST_TARGET, LAST_TARGET, SEL_LAST = C.qk("2023-Q4"), C.qk("2026-Q3"), C.qk("2025-Q4")


def verify_protocol():
    want = (HERE / "PROTOCOL_SHA256.txt").read_text().split()[0]
    got = C.sha(C.E32 / "PROTOCOL.md")
    if got != want:
        raise SystemExit(f"protocol changed after freezing ({got} != {want})")
    return want


def p45_rows() -> dict:
    """{(lead, target_quarter, province): p} from the E25 run, the 2026 extension and the E31 frozen lead-2 Q3."""
    out = {}
    a = pd.read_csv(E25RUN, dtype={"province_code": str})
    a = a[a["model"] == "PROPOSED_lgbm_combined"]
    for r in a.itertuples():
        out[(int(r.lead), r.target_quarter, r.province_code)] = float(r.score)
    b = pd.read_csv(EXT, dtype={"province_code": str})
    b = b[b["model"] == "P45"]
    for r in b.itertuples():
        out[(int(r.lead), r.target_quarter, r.province_code)] = float(r.score)
    q3 = json.loads(P45_Q3.read_text(encoding="utf-8"))["forecast"]
    for p, v in q3["arms_p_high"]["P45"].items():
        out[(2, "2026-Q3", p)] = float(v)
    return out


def main():
    proto = verify_protocol()
    d = L.Data()
    p45 = p45_rows()
    rows, meta = [], {}
    for k in (1, 2):
        for target in range(FIRST_TARGET, LAST_TARGET + 1):
            t = target - k
            labs = {p: d.label(p, target, t) for p in C.PROVS}
            if any(v is None for v in labs.values()):
                continue                                    # no released definition-A label (2025-Q2/Q3)
            info = {}
            arms = {"E32-PCFN": L.pcfn(d, t, k, info), "E32-LR": L.lr(d, t, k), "E32-LGBM": L.lgbm(d, t, k),
                    "E32-ENS": L.ens(d, t, k), "PCF21": L.pcf21(d, t, k), **L.references(d, t, k)}
            tq = C.qs(target)
            if all((k, tq, p) in p45 for p in C.PROVS):
                arms["P45"] = {p: p45[(k, tq, p)] for p in C.PROVS}
            tr = d.training_pairs(t, k)
            meta[f"k{k}|{tq}"] = {"origin": str(L.origin(t).date()), "tau": d.tau(t), "training_pairs": int(len(tr)),
                                 "training_HIGH_share": float(tr["y"].mean()) if len(tr) else None,
                                 "H_last_quarter": d.features(t, k)["H_last_quarter"].iloc[0],
                                 "last_label_quarter": d.features(t, k)["last_label_quarter"].iloc[0], "pcfn": info}
            for arm, pr in arms.items():
                for p in C.PROVS:
                    rows.append({"lead": k, "t": C.qs(t), "target_quarter": tq, "province_code": p, "arm": arm,
                                 "p": float(pr[p]), "y": labs[p],
                                 "period": "selection" if target <= SEL_LAST else "devtest"})
    Pr = pd.DataFrame(rows)
    res = {"protocol_sha256": proto, "inputs": C.inputs_manifest(), "rice_sha256": C.sha(L.RICE), "metrics": {},
           "per_date_brier": {}, "tests": {}, "per_province": {}, "per_quarter": {}}
    for k in (1, 2):
        for period in ("selection", "devtest", "all"):
            s = Pr[(Pr["lead"] == k) & ((Pr["period"] == period) if period != "all" else True)]
            for arm, g in s.groupby("arm"):
                if arm == "P45":   # P45: only rows where it exists; flagged
                    pass
                m = M.point_metrics(g["y"], g["p"])
                nd = g["t"].nunique()
                m["flags"] = M.flags(m, nd)
                m.update(M.bootstrap(g.rename(columns={"t": "t"})))
                res["metrics"].setdefault(f"lead{k}", {}).setdefault(period, {})[arm] = m
    # per-date Brier and paired tests (lead 1, all dates, common rows)
    for k in (1, 2):
        s = Pr[Pr["lead"] == k]
        pd_b = {arm: M.per_date_losses(g)["bri"] for arm, g in s.groupby("arm")}
        res["per_date_brier"][f"lead{k}"] = {arm: v.round(6).to_dict() for arm, v in pd_b.items()}
        for arm in pd_b:
            for ref in ("PCF21", "B1", "ALWAYS_HIGH", "B1p"):
                if arm == ref:
                    continue
                common = pd_b[arm].index.intersection(pd_b[ref].index)
                diff = (pd_b[ref][common] - pd_b[arm][common]).to_numpy()
                res["tests"].setdefault(f"lead{k}", {}).setdefault(arm, {})[f"vs_{ref}"] = {
                    "dates": int(len(common)), "mean_brier_gain": float(diff.mean()) if len(diff) else None,
                    "p_one_sided": M.signflip_p(diff)}
        for arm, g in s.groupby("arm"):
            res["per_province"].setdefault(f"lead{k}", {})[arm] = {
                C.NAMES[p]: {"n": int(len(h)), "accuracy": float(((h.p >= .5).astype(int) == h.y).mean()),
                             "brier": float(((h.p - h.y) ** 2).mean())} for p, h in g.groupby("province_code")}
            res["per_quarter"].setdefault(f"lead{k}", {})[arm] = {
                q: {"HIGH": int(h.y.sum()), "accuracy": float(((h.p >= .5).astype(int) == h.y).mean()),
                    "brier": float(((h.p - h.y) ** 2).mean())} for q, h in g.groupby("target_quarter")}
    # ---- selection (lead 1, selection period, mean per-date Brier)
    sel = Pr[(Pr["lead"] == 1) & (Pr["period"] == "selection")]
    mb = {a: float(M.per_date_losses(sel[sel["arm"] == a])["bri"].mean()) for a in L.CANDIDATES}
    best = min(mb.values())
    chosen = next(a for a in L.SIMPLICITY if mb[a] <= best + 0.005)
    # ---- acceptance A1-A3 (lead 1, all dates)
    al = Pr[Pr["lead"] == 1]
    dates_brier = {a: float(M.per_date_losses(al[al["arm"] == a])["bri"].mean()) for a in al["arm"].unique()}
    acc = float(((al[al.arm == chosen].p >= .5).astype(int) == al[al.arm == chosen].y).mean())
    A = {"A1_brier_below_PCF21": dates_brier[chosen] < dates_brier["PCF21"],
         "A2_brier_not_worse_than_persistence": dates_brier[chosen] <= dates_brier["B1"],
         "A3_accuracy_at_least_0.75": acc >= 0.75}
    res["selection"] = {"mean_per_date_brier_selection_lead1": mb, "chosen": chosen}
    res["acceptance"] = {"model": chosen, "mean_per_date_brier_all_lead1": dates_brier, "accuracy_all_lead1": acc,
                         **A, "A4": "checked separately (inference at the operational origin; tests; API)",
                         "A1_A3_pass": all(A.values())}
    res["meta"] = meta
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run = C.E32 / "runs" / stamp
    run.mkdir(parents=True)
    Pr = Pr.sort_values(["lead", "arm", "target_quarter", "province_code"])
    (run / "predictions.csv").write_bytes(Pr.to_csv(index=False, float_format="%.10g", lineterminator="\n").encode())
    C.write_json(run / "results.json", C.clean(res))
    print(run.name, hashlib.sha256((run / "predictions.csv").read_bytes()).hexdigest()[:16])
    print("selection (lead-1 mean per-date Brier):", {a: round(v, 4) for a, v in mb.items()}, "->", chosen)
    print("all dates lead 1 Brier:", {a: round(v, 4) for a, v in sorted(dates_brier.items(), key=lambda x: x[1])})
    print("acceptance:", {k: v for k, v in res["acceptance"].items() if k.startswith("A")}, "acc", round(acc, 3))
    for period in ("selection", "devtest", "all"):
        mm = res["metrics"]["lead1"][period]
        print(period, {a: (round(m["accuracy"], 3), round(m["brier"], 3), m["n"]) for a, m in mm.items()})


if __name__ == "__main__":
    main()
