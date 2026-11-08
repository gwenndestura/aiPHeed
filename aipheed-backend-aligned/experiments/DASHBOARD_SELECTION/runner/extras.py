"""(a) Lead-1 Brier tests vs the earlier per-lead CH1-LGBM (reference, not a candidate);
(b) Lead 2 on the 60 rows where every comparator exists;
(c) Main/FIRI v2 news contribution: FIRI without the N domain (weights renormalised, firi.score_v2 rule) and 20
    shuffles of the N domain across issue dates within province.

    python extras.py   # out/extras.json
"""
import json

import compare as K

np, pd, FM, L = K.np, K.pd, K.FM, K.L


def firi_from(row, dom_n=None, drop_n=False):
    w = json.loads(row["weights_json"])
    dom = {d: row[f"dom_{d}"] for d in ("A", "V", "C", "E", "N", "H")}
    if dom_n is not None:
        dom["N"] = dom_n
    avail = {d: v for d, v in dom.items() if pd.notna(v) and not (drop_n and d == "N")}
    if len(avail) < 4:
        return np.nan
    ww = {d: w.get(d, 1.0) for d in avail}
    tot = sum(ww.values())
    return sum(ww[d] / tot * avail[d] for d in avail)


def main():
    K.X.U.setup()
    D = pd.read_csv(K.EXP / "FINAL_ARCHITECTURE" / "out" / "predictions.csv", dtype={"province_code": str})
    comp = []
    for k in (1, 2):
        v = pd.read_csv(K.EXP / "FINAL_VERIFICATION" / "out" / f"horizon_predictions_lead{k}.csv", dtype={"province_code": str})
        comp.append(v[["t", "lead", "province_code"] + list(K.COMP.values())])
    D = D.merge(pd.concat(comp), on=["t", "lead", "province_code"], how="left")
    out = {"lead1_brier_vs_CH1": {}}
    g1 = D[D["lead"] == 1]
    y1 = g1["y"].astype(int).to_numpy()
    for n, c in (("S3", "C_p"), ("P0H4", "P0H4_p3")):
        t = FM.boot_diff(g1, (g1[c] - y1) ** 2, (g1["CH1_p"] - y1) ** 2)
        out["lead1_brier_vs_CH1"][n] = {"diff": t["diff"], "ci90": t["ci90"], "p_two": t["p_two"]}
        print(f"Lead 1 Brier {n} - CH1-LGBM: {t['diff']:+.4f} CI {np.round(t['ci90'], 4)} p {t['p_two']:.3f}")
    g2 = D[(D["lead"] == 2) & D["CH1_p"].notna()]
    fi = pd.read_csv(K.ROOT / "backend" / "data" / "thesis" / "firi2_history.csv", dtype={"province_code": str})
    fi = fi[fi["kind"] == "backtest"].assign(q=lambda d: d["target"].map(L.qi), t=lambda d: d["origin_quarter"].map(L.qi))
    g2 = g2.merge(fi[["province_code", "q", "t", "FIRI"]], on=["province_code", "q", "t"], how="left")
    out["lead2_matched_60"] = {}
    print(f"\nLead 2 on the {len(g2)} rows with every comparator ({g2['q'].nunique()} quarters, {int(g2['y'].sum())} HIGH):")
    for n, c in {**K.PROB, **K.BASE, **K.COMP, "Main = FIRI v2": "FIRI"}.items():
        m = K.metrics(g2, c, prob=c != "FIRI")
        out["lead2_matched_60"][n] = m
        print(f"  {n:42s} acc {m['accuracy']:14s} bal {m['balanced']:.3f} R {m['recall']:12s} FP {m['fp']:2d} "
              f"Brier {m['brier'] if m['brier'] is None else round(m['brier'], 3)} AUC {m['auc'] if m['auc'] is None else round(m['auc'], 2)}")
    # (c) FIRI news ablation and placebo on the Lead-2 rows
    fr = fi.merge(D[D["lead"] == 2][["province_code", "q", "t", "y"]], on=["province_code", "q", "t"])
    fr = fr[fr["FIRI"].notna()].copy()
    fr["firi_recomputed"] = [firi_from(r) for _, r in fr.iterrows()]
    fr["firi_no_news"] = [firi_from(r, drop_n=True) for _, r in fr.iterrows()]

    def st(col, h=fr):
        y = h["y"].astype(int).to_numpy()
        yh = (h[col] >= .5).astype(int).to_numpy()
        tp, fp = int(((yh == 1) & (y == 1)).sum()), int(((yh == 1) & (y == 0)).sum())
        fn, tn = int(((yh == 0) & (y == 1)).sum()), int(((yh == 0) & (y == 0)).sum())
        from sklearn.metrics import roc_auc_score
        return {"acc": (tp + tn) / len(y), "bal": (tp / max(tp + fn, 1) + tn / max(tn + fp, 1)) / 2, "tp": tp, "fp": fp,
                "auc": float(roc_auc_score(y, h[col])), "rows": int(len(h))}
    res = {"recompute_max_abs_diff": float((fr["firi_recomputed"] - fr["FIRI"]).abs().max()),
           "news_domain_available_rows": int(fr["dom_N"].notna().sum()),
           "with_news": st("FIRI"), "without_news": st("firi_no_news")}
    rng = np.random.default_rng(2037)
    ts = sorted(fr["t"].unique())
    shuf = []
    src = fr.set_index(["province_code", "t"])["dom_N"]
    for _ in range(20):
        mp = dict(zip(ts, rng.permutation(ts)))
        fr["_n"] = [src.get((p, mp[t]), np.nan) for p, t in zip(fr["province_code"], fr["t"])]
        fr["_f"] = [firi_from(r, dom_n=r["_n"]) for _, r in fr.iterrows()]
        shuf.append(st("_f"))
    res["shuffled_news"] = {"auc_mean": float(np.mean([s["auc"] for s in shuf])), "acc_mean": float(np.mean([s["acc"] for s in shuf])),
                            "perm_p_auc": float(np.mean([s["auc"] >= res["with_news"]["auc"] for s in shuf]))}
    out["firi_news"] = res
    print("\nFIRI v2 news:", json.dumps(res, indent=1))
    FM.write_json(K.OUT / "extras.json", out)


if __name__ == "__main__":
    main()
