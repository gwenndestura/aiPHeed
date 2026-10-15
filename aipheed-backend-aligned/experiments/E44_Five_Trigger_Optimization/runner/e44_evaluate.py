"""E44 single evaluation run under the frozen PROTOCOL.md (I1, I2, I3, variants, comparators; run once + repeat).

    backend/venv/Scripts/python.exe -B runner/e44_evaluate.py
      -> runs/<UTC stamp>/{predictions.csv, selections.json, results.json}
      -> frozen/E44_PROSPECTIVE_2027Q1.json (+ .sha256), origin 2026-10-01 (written once)
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
import e44_components as P2  # noqa: E402

C, K, L, np, pd = P2.C, P2.K, P2.L, P2.np, P2.pd
E44 = HERE.parent
OPER = L.qi("2026-Q3")
E43_PRED = E44.parent / "E43_Five_Trigger_Risk" / "runs" / "20261015T134756Z" / "predictions_T43.csv"
COMPARATORS = ["B-maj", "B-persist", "B-clim", "SIM-0", "SIM-5T", "E38-served", "E41-M1"]
VARIANTS = {"I2-MKT": dict(groups=["market"], hunger_rw=True)}
for g in ["climate", "fish_kill", "employment", "ofw_remittance", "news"]:
    VARIANTS[f"I2-MKT+{g}"] = dict(groups=["market", g])
for g in P2.ALL_GROUPS:
    VARIANTS[f"I2-drop_{g}"] = dict(groups=[x for x in P2.ALL_GROUPS if x != g])
VARIANTS["I2-GOV"] = dict(groups=[x for x in P2.ALL_GROUPS if x != "news"])
VARIANTS["I2-NLP"] = dict(groups=["news"])
ITER = ["I1", "I2", "I3"]


def verify_protocol() -> str:
    want = (HERE / "PROTOCOL_SHA256.txt").read_text().split()[0]
    got = hashlib.sha256((E44 / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if got != want:
        raise SystemExit("PROTOCOL.md changed after freezing")
    return got


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def block(S, arm):
    g = S.dropna(subset=[f"{arm}_p", f"{arm}_yhat", "y"]).copy()
    m = L.cls_metrics(g["y"], g[f"{arm}_yhat"].astype(int), g[f"{arm}_p"])
    m["accuracy_ci95"] = L.date_bootstrap(g, lambda s: float((s[f"{arm}_yhat"] == s["y"]).mean()), seed=44)
    m["citl_ci95"] = L.date_bootstrap(g, lambda s: float(s["y"].mean() - s[f"{arm}_p"].mean()), seed=44)
    m["dates"] = int(g["target_q"].nunique())
    m["by_quarter"] = {L.qs(int(q)): {"acc": float((h[f"{arm}_yhat"] == h["y"]).mean()), "HIGH": int(h["y"].sum())}
                       for q, h in g.groupby("target_q")}
    return m


def per_date(S, arm):
    return S.assign(acc=(S[f"{arm}_yhat"] == S["y"]).astype(float), br=(S[f"{arm}_p"] - S["y"]) ** 2) \
        .groupby("target_q")[["acc", "br"]].mean()


def paired(S, cand, others):
    out, ps = {}, {}
    c = per_date(S, cand)
    for o in others:
        b = per_date(S, o)
        out[o] = {"brier_gain": L.sign_flip((b["br"] - c["br"]).to_numpy(), seed=44),
                  "accuracy_gain": L.sign_flip((c["acc"] - b["acc"]).to_numpy(), seed=44)}
        ps[o] = out[o]["brier_gain"]["p_one_sided"]
    for o, h in L.holm(ps).items():
        out[o]["brier_gain"]["p_one_sided_holm"] = h
    return out


def gates(m, pr, leak_ok):
    g = {"A0": leak_ok, "A1": m["accuracy"] >= 0.75,
         "A2": (m["balanced_accuracy"] or 0) >= 0.70 and (m["recall_HIGH"] or 0) >= 0.60 and (m["recall_LOW"] or 0) >= 0.60,
         "A3": pr["B-maj"]["brier_gain"]["mean_gain"] > 0 and pr["B-persist"]["brier_gain"]["mean_gain"] > 0,
         "A4": m["citl_ci95"][0] is not None and m["citl_ci95"][0] <= 0 <= m["citl_ci95"][1]}
    g["passes"] = all(g.values())
    return g


def main():
    proto = verify_protocol()
    d, x = L.load(), K.load_extra()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = E44 / "runs" / stamp
    out.mkdir(parents=True)
    origins = list(range(L.qi("2021-Q3"), OPER + 1))
    X = P2.features(d, x, origins)
    for fs, cols in C.FEATURE_SETS.items():
        assert C.covers_five(cols), fs
    B = P2.bases(d, origins)
    truth = K.label_frame(d, "T43").rename(columns={"q": "target_q"})[["province_code", "target_q", "y"]]
    rows, sel, keep = [], {}, {}
    configs = C.grid(C.FEATURE_SETS)
    for t in origins:
        te = X[X["t"] == t].set_index("province_code").loc[L.PROVS].reset_index()
        r = pd.DataFrame({"t": t, "target_q": t + 2, "province_code": L.PROVS})
        # ---- I1
        tr = K.training_pairs(X, d, t)
        if C.eligible(tr):
            s1 = C.select_and_predict(tr, te, configs, C.FEATURE_SETS)
            r["I1_p"], r["I1_yhat"] = s1["p"], (s1["p"] >= s1["threshold"]).astype(int)
            sel.setdefault("I1", {})[L.qs(t)] = {"config": s1["config"], "threshold": s1["threshold"],
                                                 "inner_brier": s1["inner_brier"]}
            if t == OPER:
                keep["I1"] = s1
        # ---- I2, I3, variants
        for name, kw in [("I2", {}), ("I3", {"supplementary": True})] + list(VARIANTS.items()):
            f = P2.forecast(d, X, B, t, **kw)
            if f is None:
                continue
            r[f"{name}_p"], r[f"{name}_yhat"] = f["p"], (f["p"] >= f["threshold"]).astype(int)
            if name in ("I2", "I3"):
                r[f"{name}_p_hunger"], r[f"{name}_p_price"], r[f"{name}_F_hat"] = f["p_hunger"], f["p_price"], f["F_hat"]
                sel.setdefault(name, {})[L.qs(t)] = {"price_cfg": f["price_cfg"], "price_rmse": f["price_rmse"],
                                                     "hunger_alpha": f["hunger_alpha"], "hunger_rmse": f["hunger_rmse"],
                                                     "threshold": f["threshold"], "platt": f["platt"],
                                                     "H_hat": f["H_hat"], "price_train_q": f["n_price_train_q"],
                                                     "hunger_pairs": f["n_hunger_pairs"]}
                if t == OPER:
                    keep[name] = f
        rows.append(r)
    P = pd.concat(rows, ignore_index=True)
    e43 = pd.read_csv(E43_PRED, dtype={"province_code": str})
    for a in COMPARATORS + ["LGBM-COMB"]:
        e43[f"{a}_yhat"] = np.where(e43[f"{a}_p"].notna(), (e43[f"{a}_p"] >= 0.5).astype(float), np.nan)
    P = P.merge(e43[["t", "province_code"] + [f"{a}_{s}" for a in COMPARATORS + ["LGBM-COMB"] for s in ("p", "yhat")]],
                on=["t", "province_code"], how="left").merge(truth, on=["province_code", "target_q"], how="left")
    lab = P[P["y"].notna() & (P["target_q"] <= L.qi("2026-Q3"))]
    req = ITER + list(VARIANTS) + COMPARATORS
    S = lab.dropna(subset=[f"{a}_p" for a in req])
    leak = E44 / "runs" / "tests_status.json"
    leak_ok = bool(leak.exists() and json.loads(leak.read_text()).get("passed"))
    res = {"protocol_sha256": proto, "run_utc": stamp,
           "S44": {"dates": int(S["target_q"].nunique()), "rows": int(len(S)), "HIGH": int(S["y"].sum()),
                   "period": [L.qs(int(S["target_q"].min())), L.qs(int(S["target_q"].max()))] if len(S) else None,
                   "metrics": {a: block(S, a) for a in req}}}
    res["S44"]["paired"] = {it: paired(S, it, [a for a in req if a != it]) for it in ITER}
    res["S44"]["gates"] = {it: gates(res["S44"]["metrics"][it], res["S44"]["paired"][it], leak_ok) for it in ITER}
    final = next((it for it in ITER if res["S44"]["gates"][it]["passes"]), None)
    res["final_candidate"] = final or "I2"
    res["forecasting_acceptance_met"] = final is not None
    for it in ("I2", "I3"):
        L2 = lab.dropna(subset=[f"{it}_p"] + [f"{a}_p" for a in COMPARATORS])
        res[f"{it}_long"] = {"dates": int(L2["target_q"].nunique()), "rows": int(len(L2)), "HIGH": int(L2["y"].sum()),
                             "metrics": {a: block(L2, a) for a in [it] + COMPARATORS},
                             "paired": paired(L2, it, COMPARATORS)}
    LG = lab.dropna(subset=["LGBM-COMB_p", "I2_p", "I1_p"])
    res["vs_E43_LGBM_subset"] = {"dates": int(LG["target_q"].nunique()),
                                 "metrics": {a: block(LG, a) for a in ["I1", "I2", "I3", "LGBM-COMB", "B-maj"]}}
    (out / "selections.json").write_text(json.dumps(sel, indent=1, default=str))
    P.to_csv(out / "predictions.csv", index=False)
    X.to_csv(out / "features_asof.csv", index=False)
    (out / "results.json").write_text(json.dumps(res, indent=1, default=float))

    fz = E44 / "frozen" / "E44_PROSPECTIVE_2027Q1.json"
    if not fz.exists():
        o = P[P["t"] == OPER].set_index("province_code")
        fc = res["final_candidate"]
        rec = {"issued_by": "E44", "origin": str(L.origin(OPER).date()), "origin_quarter": L.qs(OPER),
               "target_quarter": L.qs(OPER + 2), "lead_from_origin": 2, "protocol_sha256": proto,
               "final_candidate": fc, "forecasting_acceptance_met": res["forecasting_acceptance_met"],
               "cpi_months_used_through": L.ym_s(L.m0_of(OPER)), "selections_at_origin": {}, "provinces": {}}
        for it in ITER:
            if it in keep:
                k = keep[it]
                rec["selections_at_origin"][it] = ({"config": k["config"], "threshold": k["threshold"], "features": k["cols"]}
                                                   if it == "I1" else
                                                   {"price_cfg": k["price_cfg"], "price_rmse": k["price_rmse"],
                                                    "hunger_alpha": k["hunger_alpha"], "hunger_rmse": k["hunger_rmse"],
                                                    "threshold": k["threshold"], "H_hat": k["H_hat"],
                                                    "price_features": k["pcols"], "hunger_features": k["hcols"]})
        for p in L.PROVS:
            rec["provinces"][L.NAMES[p]] = {"province_code": p, **{c: (None if pd.isna(o.loc[p, c]) else float(o.loc[p, c]))
                                                                   for c in o.columns if c.endswith(("_p", "_yhat", "_p_hunger",
                                                                                                     "_p_price", "_F_hat"))}}
        fz.write_text(json.dumps(rec, indent=1))
        (fz.parent / (fz.stem + ".sha256")).write_text(sha(fz) + "  " + fz.name + "\n")

    s = res["S44"]
    print(stamp, "S44", s["dates"], "dates", s["rows"], "rows", s["HIGH"], "HIGH", s["period"])
    for a in req:
        m = s["metrics"][a]
        print(f"  {a:22s} acc {m['accuracy']:.3f} bal {m['balanced_accuracy'] if m['balanced_accuracy'] is None else round(m['balanced_accuracy'], 3)} "
              f"recH {None if m['recall_HIGH'] is None else round(m['recall_HIGH'], 2)} recL {None if m['recall_LOW'] is None else round(m['recall_LOW'], 2)} "
              f"brier {m['brier']:.3f} auc {m.get('roc_auc')}")
    print("  gates", s["gates"], "final", res["final_candidate"], "accepted", res["forecasting_acceptance_met"])
    for it in ("I2", "I3"):
        lg = res[f"{it}_long"]
        print(f"  {it} long", lg["dates"], lg["rows"], lg["HIGH"],
              {a: (round(m["accuracy"], 3), round(m["balanced_accuracy"] or 0, 3), round(m["brier"], 3)) for a, m in lg["metrics"].items()})


if __name__ == "__main__":
    main()
