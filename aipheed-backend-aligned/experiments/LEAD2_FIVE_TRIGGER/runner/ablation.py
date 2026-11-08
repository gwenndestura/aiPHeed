"""PROTOCOL section 6 with ADDENDUM_1 groups: leave-one-group-out refits of FINAL (C0 = served P0H4-U price model),
the no-trigger refit, group permutation (model fixed) and SHAP shares by lead, for the five trigger groups (market,
climate, employment, fish production, OFW remittances) and the other required inputs (news, poverty, hunger outlook).

    python ablation.py          # ../out/ablation.json, ../out/ablation_rows.csv
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import lt_lib as T

F, M, KEY = T.F, T.M, T.KEY
TRIG = list(T.GROUPS)
BLOCKS = {**T.GROUPS, **T.OTHER_INPUTS}


def boot(q, a, b, draws=4000, seed=2031):
    q, d = np.asarray(q), np.asarray(a, float) - np.asarray(b, float)
    uq = np.unique(q)
    by = [d[q == u] for u in uq]
    rng = np.random.default_rng(seed)
    bs = np.array([np.concatenate([by[i] for i in rng.integers(0, len(uq), len(uq))]).mean() for _ in range(draws)])
    return {"diff": float(d.mean()), "ci90": [float(np.quantile(bs, .05)), float(np.quantile(bs, .95))],
            "p_hurts": float((bs <= 0).mean())}


def holm(ps):
    items = sorted(ps.items(), key=lambda kv: kv[1])
    out, run = {}, 0.0
    for i, (k, p) in enumerate(items):
        run = max(run, min(1.0, (len(items) - i) * p))
        out[k] = run
    return out


def main():
    T.check_protocol(addendum=True)
    S = T.stack()
    E = pd.read_csv(T.OUT / "candidates.csv", dtype={"province_code": str})
    E = E[KEY + ["q", "y", "price", "pi_H_AB", "C0_price", "C0_p"]]
    origins = sorted(E["t"].unique())
    models = {}
    full = T.run(T.U2, origins, S, explain=True, models=models)
    chk = E[KEY + ["C0_price"]].merge(full[KEY + ["pi_P"]], on=KEY)
    assert len(chk) == len(E) and float((chk["C0_price"] - chk["pi_P"]).abs().max()) < 1e-5, "FINAL refit differs"
    variants = {f"drop_{b}": [c for c in T.U2 if c not in cols] for b, cols in BLOCKS.items()}
    trig_cols = [c for b in TRIG for c in BLOCKS[b]]
    variants["no_triggers"] = [c for c in T.U2 if c not in trig_cols]
    for name, cols in variants.items():
        P = T.run(cols, origins, S)
        E = E.merge(P[KEY + ["pi_P"]].rename(columns={"pi_P": f"{name}_price"}), on=KEY, how="left")
        print(name, "done", flush=True)
    # permutation (model fixed): a block's columns from a random other evaluation origin (same province and lead)
    Sev = S[S["t"].isin(origins)].set_index(KEY)
    for b, cols in BLOCKS.items():
        rng = np.random.default_rng(2031 + list(BLOCKS).index(b))
        acc = np.zeros(len(E))
        for _ in range(20):
            parts = []
            for t in origins:
                te = S[(S["t"] == t)].copy()
                src = int(rng.choice([o for o in origins if o != t]))
                for c in cols:
                    te[c] = [Sev[c].get((src, k, p), np.nan) for k, p in zip(te["lead"], te["province_code"])]
                parts.append(te[KEY].assign(p=models[int(t)].predict(te)))
            acc += E[KEY].merge(pd.concat(parts), on=KEY, how="left")["p"].to_numpy() / 20
        E[f"perm_{b}_price"] = acc
    res = {"addendum_sha256": T.sha256(T.LT / "ADDENDUM_1_TRIGGER_GROUPS.md"), "blocks": BLOCKS, "leads": {}}
    for k, g in E.groupby("lead"):
        if k > 4:
            continue
        base_t = (g["C0_p"] - g["y"]) ** 2
        base_p = (g["C0_price"] - g["price"]) ** 2
        r = {}
        for b in list(BLOCKS) + ["no_triggers"]:
            col = f"drop_{b}_price" if b != "no_triggers" else "no_triggers_price"
            pt = g["pi_H_AB"] * g[col]
            r[b] = {"loo_t43c": boot(g["q"], (pt - g["y"]) ** 2, base_t),
                    "loo_price": boot(g["q"], (g[col] - g["price"]) ** 2, base_p),
                    "predictions_changed": float((g[col] - g["C0_price"]).abs().max()),
                    "acc_without": float(((pt >= .5).astype(int) == g["y"]).mean())}
            if b in BLOCKS:
                pp = g[f"perm_{b}_price"]
                r[b]["perm_t43c"] = float(np.mean((g["pi_H_AB"] * pp - g["y"]) ** 2) - base_t.mean())
                r[b]["perm_price"] = float(np.mean((pp - g["price"]) ** 2) - base_p.mean())
        hp = holm({b: r[b]["loo_t43c"]["p_hurts"] for b in TRIG})
        for b in TRIG:
            r[b]["loo_t43c"]["holm_p_hurts"] = hp[b]
        sh = full[full["lead"] == k]
        tot = sum(sh[f"shap_{c}"].abs().mean() for c in T.U2 if c != "lead")
        for b, cols in BLOCKS.items():
            r[b]["shap_share"] = float(sum(sh[f"shap_{c}"].abs().mean() for c in cols) / tot) if tot else 0.0
        res["leads"][int(k)] = r
    cls = {}
    for b in BLOCKS:
        hurt = [k for k in (1, 2, 3, 4) if res["leads"][k][b]["loo_t43c"]["ci90"][0] > 0 or res["leads"][k][b]["loo_price"]["ci90"][0] > 0]
        perm = [k for k in hurt if res["leads"][k][b]["perm_price"] > 0 or res["leads"][k][b]["perm_t43c"] > 0]
        helped = [k for k in (1, 2, 3, 4) if res["leads"][k][b]["loo_t43c"]["ci90"][1] < 0]
        weak = any(res["leads"][k][b]["loo_t43c"]["diff"] > 0 for k in (1, 2, 3, 4))
        cls[b] = {"class": "predictive" if perm else "weak" if weak else "no demonstrated value",
                  "leads_where_removal_hurts": hurt, "leads_where_removal_helps": helped,
                  "model_uses_it": any(res["leads"][k][b]["predictions_changed"] > 1e-9 for k in (1, 2, 3, 4))}
    res["classification"] = cls
    E.to_csv(T.OUT / "ablation_rows.csv", index=False, lineterminator="\n", float_format="%.6g")
    T.OUT.joinpath("ablation.json").write_text(json.dumps(res, indent=1, default=float))
    for b in list(BLOCKS) + ["no_triggers"]:
        print(f"{b:17s}", " | ".join(
            f"L{k} dT {res['leads'][k][b]['loo_t43c']['diff']:+.4f}[{res['leads'][k][b]['loo_t43c']['ci90'][0]:+.3f},{res['leads'][k][b]['loo_t43c']['ci90'][1]:+.3f}]"
            f" dP {res['leads'][k][b]['loo_price']['diff']:+.4f}[{res['leads'][k][b]['loo_price']['ci90'][0]:+.3f},{res['leads'][k][b]['loo_price']['ci90'][1]:+.3f}]"
            f" acc {res['leads'][k][b]['acc_without']:.3f}" + (f" perm {res['leads'][k][b]['perm_price']:+.4f} shap {res['leads'][k][b]['shap_share']:.2f}" if b in BLOCKS else "")
            for k in (1, 2)), cls.get(b, ""))


if __name__ == "__main__":
    main()
