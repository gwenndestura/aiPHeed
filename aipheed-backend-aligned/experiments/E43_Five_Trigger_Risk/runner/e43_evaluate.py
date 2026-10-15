"""E43 single evaluation run under the frozen PROTOCOL.md (run once; a byte-identical repeat may follow).

    backend/venv/Scripts/python.exe -B runner/e43_evaluate.py
      -> runs/<UTC stamp>/{predictions_T43.csv, predictions_L4.csv, features_asof.csv, results.json}
      -> frozen/E43_PROSPECTIVE_2027Q1.json (+ .sha256), origin 2026-10-01 (written once)
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
import e43_lib as K  # noqa: E402

L, np, pd = K.L, K.np, K.pd
OPER = L.qi("2026-Q3")
EXP = K.E43.parent
E38_PRED = EXP / "E38_Lead2_Diagnosis_Tuning" / "runs" / "20261015T033922Z" / "predictions.csv"
E41_PRED = EXP / "E41_Lead2_Audit" / "runs" / "20261015T101016Z" / "predictions_lead2.csv"
ML = [f"{a}-{s}" for a in ("LR", "LGBM") for s in ("GOV", "NLP", "COMB")]
BASE = ["B-maj", "B-persist", "B-clim"]
STRUCT = ["SIM-0", "SIM-5T"]
COMPARE = ["E38-served", "E41-M1"]
PRIMARY = "LGBM-COMB"


def verify_protocol() -> str:
    want = (HERE / "PROTOCOL_SHA256.txt").read_text().split()[0]
    got = hashlib.sha256((K.E43 / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if got != want:
        raise SystemExit("PROTOCOL.md changed after freezing")
    return got


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def calib(g, arm):
    from sklearn.linear_model import LogisticRegression
    p = np.clip(g[f"{arm}_p"].to_numpy(float), 1e-4, 1 - 1e-4)
    if g["y"].nunique() < 2 or len(np.unique(p)) < 2:
        return None
    return float(LogisticRegression(C=1e6, max_iter=5000).fit(np.log(p / (1 - p)).reshape(-1, 1), g["y"]).coef_[0][0])


def block(S, arm):
    g = S.dropna(subset=[f"{arm}_p", "y"])
    yh = (g[f"{arm}_p"] >= 0.5).astype(int)
    m = L.cls_metrics(g["y"], yh, g[f"{arm}_p"])
    g = g.assign(yh=yh)
    m["accuracy_ci95"] = L.date_bootstrap(g, lambda s: float((s["yh"] == s["y"]).mean()), seed=43)
    m["balanced_ci95"] = L.date_bootstrap(g, lambda s: L.cls_metrics(s["y"], s["yh"])["balanced_accuracy"], seed=43)
    m["brier_ci95"] = L.date_bootstrap(g, lambda s: float(((s[f"{arm}_p"] - s["y"]) ** 2).mean()), seed=43)
    m["citl_ci95"] = L.date_bootstrap(g, lambda s: float(s["y"].mean() - s[f"{arm}_p"].mean()), seed=43)
    m["slope"] = calib(g, arm)
    m["dates"] = int(g["target_q"].nunique())
    return m


def per_date(S, arm):
    return S.assign(acc=((S[f"{arm}_p"] >= 0.5).astype(int) == S["y"]).astype(float),
                    br=(S[f"{arm}_p"] - S["y"]) ** 2).groupby("target_q")[["acc", "br"]].mean()


def paired(S, cand, others):
    out, ps = {}, {}
    c = per_date(S, cand)
    for o in others:
        b = per_date(S, o)
        out[o] = {"brier_gain": L.sign_flip((b["br"] - c["br"]).to_numpy(), seed=43),
                  "accuracy_gain": L.sign_flip((c["acc"] - b["acc"]).to_numpy(), seed=43)}
        ps[o] = out[o]["brier_gain"]["p_one_sided"]
    for o, h in L.holm(ps).items():
        out[o]["brier_gain"]["p_one_sided_holm"] = h
    return out


def run_target(d, x, X, which, origins, e38, e41):
    truth = K.label_frame(d, which).rename(columns={"q": "target_q"})[["province_code", "target_q", "y", "signals"]]
    rows, models, shap, h5 = [], {}, {}, {}
    specs = {f"{a}-{s}": (cls, cols) for a, cls in (("LR", K.LRModel), ("LGBM", K.GBModel)) for s, cols in K.SETS.items()}
    for g, cols in K.TRIGGER_COLS.items():
        specs[f"LGBM-only_{g}"] = (K.GBModel, cols)
        specs[f"LGBM-drop_{g}"] = (K.GBModel, [c for c in K.COMB if c not in cols])
        specs[f"LR-only_{g}"] = (K.LRModel, cols)
        specs[f"LR-drop_{g}"] = (K.LRModel, [c for c in K.COMB if c not in cols])
    for t in origins:
        lab = K.available_labels(d, t, which)
        tr_lab = lab[lab["q"] <= t - 1]
        last = tr_lab.sort_values("q").groupby("province_code").last()["y"]
        rate = (tr_lab["y"].sum() + 1) / (len(tr_lab) + 2)
        prate = tr_lab.groupby("province_code")["y"].agg(["sum", "count"])
        c = d.cut(t)
        sim0 = K.simulate(c, t, which)
        shift, coef = K.h_shift_5t(X, d, t)
        h5[L.qs(t)] = {"shift_per_quarter": shift, "coef": coef}
        sim5 = K.simulate(c, t, which, h_shift=shift)
        te = X[X["t"] == t].set_index("province_code").loc[L.PROVS].reset_index()
        tr = K.training_pairs(X, d, t, which)
        fits = {}
        if K.eligible(tr):
            for name, (cls, cols) in specs.items():
                m = cls(cols).fit(tr)
                fits[name] = m.predict(te)
                if name in ("LGBM-COMB", "LR-COMB"):
                    models[(name, t)] = m
            shap[L.qs(t)] = models[("LGBM-COMB", t)].group_shap(te)
        for i, p in enumerate(L.PROVS):
            r = {"t": t, "target_q": t + 2, "province_code": p, "B-maj_p": rate, "B-persist_p": last.get(p, np.nan),
                 "B-clim_p": ((prate.loc[p, "sum"] + 1) / (prate.loc[p, "count"] + 2)) if p in prate.index else np.nan,
                 "SIM-0_p": sim0.get(p, np.nan), "SIM-5T_p": sim5.get(p, np.nan),
                 "E38-served_p": e38.get((L.qs(t), p), np.nan), "E41-M1_p": e41.get((t, p), np.nan),
                 "train_quarters": int(tr["q"].nunique()), "train_high": int(tr["y"].sum())}
            for name, v in fits.items():
                r[f"{name}_p"] = float(v[i])
            rows.append(r)
    P = pd.DataFrame(rows).merge(truth, on=["province_code", "target_q"], how="left")
    return P, models, shap, h5


def evaluate(P, models, X, which):
    lab = P.dropna(subset=["y"])
    lab = lab[lab["target_q"] <= L.qi("2026-Q3")]
    arms = BASE + STRUCT + COMPARE + ML
    SC = lab.dropna(subset=[f"{a}_p" for a in arms])
    SS = lab.dropna(subset=[f"{a}_p" for a in BASE + STRUCT])
    res = {"S_C": {"dates": int(SC["target_q"].nunique()), "rows": int(len(SC)),
                   "period": [L.qs(int(SC["target_q"].min())), L.qs(int(SC["target_q"].max()))] if len(SC) else None,
                   "HIGH_rows": int(SC["y"].sum()),
                   "metrics": {a: block(SC, a) for a in arms},
                   "paired_primary": paired(SC, PRIMARY, [a for a in arms if a != PRIMARY]) if len(SC) else {},
                   "nlp_value": {"LR": paired(SC, "LR-COMB", ["LR-GOV"])["LR-GOV"] if len(SC) else None,
                                 "LGBM": paired(SC, "LGBM-COMB", ["LGBM-GOV"])["LGBM-GOV"] if len(SC) else None}},
           "S_SIM": {"dates": int(SS["target_q"].nunique()), "rows": int(len(SS)), "HIGH_rows": int(SS["y"].sum()),
                     "period": [L.qs(int(SS["target_q"].min())), L.qs(int(SS["target_q"].max()))],
                     "metrics": {a: block(SS, a) for a in BASE + STRUCT},
                     "paired_SIM5T": paired(SS, "SIM-5T", BASE + ["SIM-0"])}}
    diag = [c[:-2] for c in P.columns if ("-only_" in c or "-drop_" in c) and c.endswith("_p")]
    if len(SC):
        res["S_C"]["single_and_drop"] = {a: {k: block(SC, a)[k] for k in ("accuracy", "balanced_accuracy", "brier", "roc_auc")
                                             if k in block(SC, a)} for a in diag}
    # permutation importance + missing-group sensitivity (LGBM-COMB, LR-COMB) on S-C rows
    rng = np.random.default_rng(43)
    perm, miss = {}, {}
    if len(SC):
        Xte = X.set_index(["t", "province_code"]).loc[list(zip(SC["t"], SC["province_code"]))].reset_index()
        y = SC["y"].to_numpy()
        for mname in ("LGBM-COMB", "LR-COMB"):
            def pred(F):
                return np.array([models[(mname, t)].predict(F.iloc[[i]])[0] for i, t in enumerate(F["t"])])
            base = pred(Xte)
            bb = float(np.mean((base - y) ** 2))
            perm[mname], miss[mname] = {}, {}
            for g, cols in {**K.TRIGGER_COLS, "hunger_history": K.GROUPS["hunger_history"]}.items():
                inc = []
                for _ in range(200):
                    Z = Xte.copy()
                    Z[cols] = Z[cols].to_numpy()[rng.permutation(len(Z))]
                    inc.append(float(np.mean((pred(Z) - y) ** 2)) - bb)
                Z = Xte.copy()
                Z[cols] = np.nan
                perm[mname][g] = {"mean_brier_increase": float(np.mean(inc)), "sd": float(np.std(inc))}
                miss[mname][g] = float(np.mean(pred(Z) - base))
    res["S_C"]["permutation"], res["S_C"]["missing_group_delta_p"] = perm, miss
    return res, SC


def gates(res, leak_ok):
    sc = res["S_C"]
    if not sc["rows"]:
        return {"classification": "insufficient evidence for Lead-2 operational use (no common evaluation rows)"}
    m = sc["metrics"][PRIMARY]
    pr = sc["paired_primary"]
    g = {"G0": leak_ok, "G1": m["accuracy"] >= 0.75,
         "G2": (m["balanced_accuracy"] or 0) >= 0.70 and (m["recall_HIGH"] or 0) >= 0.60 and (m["recall_LOW"] or 0) >= 0.60,
         "G3": pr["B-maj"]["brier_gain"]["mean_gain"] > 0 and pr["B-persist"]["brier_gain"]["mean_gain"] > 0
         and pr["B-persist"]["brier_gain"]["p_one_sided_holm"] < 0.05,
         "G4": m["citl_ci95"][0] is not None and m["citl_ci95"][0] <= 0 <= m["citl_ci95"][1]}
    if all(g.values()):
        g["classification"] = "suitable for exploratory decision-support testing"
    elif g["G0"] and g["G3"]:
        g["classification"] = "ready for a controlled demonstration; Lead-2 operational use remains experimental"
    else:
        g["classification"] = "insufficient evidence for Lead-2 operational use"
    # serving rule (PROTOCOL 6)
    if pr["B-maj"]["brier_gain"]["mean_gain"] > 0 and pr["B-persist"]["brier_gain"]["mean_gain"] > 0:
        g["served"] = PRIMARY
    else:
        ss = res["S_SIM"]["metrics"]
        g["served"] = min(STRUCT, key=lambda a: ss[a]["brier"])
    return g


def main():
    proto = verify_protocol()
    d, x = L.load(), K.load_extra()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = K.E43 / "runs" / stamp
    out.mkdir(parents=True)
    origins = list(range(L.qi("2021-Q3"), OPER + 1))
    X = K.features(d, x, origins)
    e38 = pd.read_csv(E38_PRED, dtype={"province_code": str})
    e38 = e38[e38["arm"] == "E38-LGBM"].set_index(["t", "province_code"])["p"].to_dict()
    e41 = pd.read_csv(E41_PRED, dtype={"province_code": str}).set_index(["t", "province_code"])["M1_p"].to_dict()
    leak = K.E43 / "runs" / "tests_status.json"
    leak_ok = bool(leak.exists() and json.loads(leak.read_text()).get("passed"))
    results = {"protocol_sha256": proto, "run_utc": stamp,
               "inputs_sha256": {k: sha(p) for k, p in K.EXTRA_FILES.items()} | {"fssi": sha(K.FSSI)},
               "feature_missing_share": {c: float(X[c].isna().mean()) for c in K.COMB}}
    frozen_rows = {}
    for which in ("T43", "L4"):
        P, models, shap, h5 = run_target(d, x, X, which, origins, e38, e41)
        res, SC = evaluate(P, models, X, which)
        res["gates"] = gates(res, leak_ok) if which == "T43" else None
        res["grouped_shap_LGBM_COMB"] = shap
        res["sim5t_hunger_model"] = h5
        res["by_year_primary_and_baselines"] = {
            str(yy): {a: float(((g[f"{a}_p"] >= 0.5).astype(int) == g["y"]).mean()) for a in [PRIMARY, "B-persist", "SIM-5T"]}
            | {"rows": int(len(g)), "HIGH": int(g["y"].sum())} for yy, g in SC.groupby(SC["target_q"] // 4)} if len(SC) else {}
        results[which] = res
        P.to_csv(out / f"predictions_{which}.csv", index=False)
        frozen_rows[which] = P[P["t"] == OPER].set_index("province_code")
    X.to_csv(out / "features_asof.csv", index=False)
    (out / "results.json").write_text(json.dumps(results, indent=1, default=float))

    fz = K.E43 / "frozen" / "E43_PROSPECTIVE_2027Q1.json"
    if not fz.exists():
        o = frozen_rows["T43"]
        served = results["T43"]["gates"].get("served")
        rec = {"issued_by": "E43", "origin": str(L.origin(OPER).date()), "target_quarter": L.qs(OPER + 2),
               "target": "T43: SWS hunger above 11.3 (regional) AND provincial food CPI above its E40 frozen P60 "
                         "(or food minus headline above its P60), in the target quarter; exploratory",
               "protocol_sha256": proto, "served_arm": served, "cpi_months_used_through": L.ym_s(L.m0_of(OPER)),
               "provinces": {L.NAMES[p]: {"province_code": p, **{c: (None if pd.isna(o.loc[p, c]) else float(o.loc[p, c]))
                                                                 for c in o.columns if c.endswith("_p")},
                                          "L4_" + served + "_p": (None if pd.isna(frozen_rows["L4"].loc[p, f"{served}_p"])
                                                                   else float(frozen_rows["L4"].loc[p, f"{served}_p"]))}
                             for p in L.PROVS}}
        fz.write_text(json.dumps(rec, indent=1))
        (fz.parent / (fz.stem + ".sha256")).write_text(sha(fz) + "  " + fz.name + "\n")

    for which in ("T43", "L4"):
        r = results[which]
        print(which, "S-C", r["S_C"]["dates"], "dates", r["S_C"]["rows"], "rows", r["S_C"]["HIGH_rows"], "HIGH", r["S_C"].get("period"))
        for a, m in r["S_C"]["metrics"].items():
            print(f"   {a:12s} acc {m['accuracy']:.3f} bal {m['balanced_accuracy'] if m['balanced_accuracy'] is None else round(m['balanced_accuracy'], 3)} "
                  f"recH {m['recall_HIGH']} recL {None if m['recall_LOW'] is None else round(m['recall_LOW'], 2)} brier {m['brier']:.3f} auc {m.get('roc_auc')}")
        print("  S-SIM", r["S_SIM"]["dates"], r["S_SIM"]["rows"], r["S_SIM"]["HIGH_rows"],
              {a: (round(m["accuracy"], 3), round(m["balanced_accuracy"] or 0, 3), round(m["brier"], 3)) for a, m in r["S_SIM"]["metrics"].items()})
        print("  gates", r["gates"])


if __name__ == "__main__":
    main()
