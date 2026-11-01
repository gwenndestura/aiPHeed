"""LEAD2_POST_SWS_PRICE (PROTOCOL.md + PROTOCOL_AMENDMENT_1.md): score M2 = H4(O') x P0_price' on the 65 official
Lead-2 rows, beside M0 = H4(O') x P0_price and the baselines recomputed at O'.

Order (stops on the first failure): protocol hashes -> refit parity and perturbation results present and passed ->
reproduction (P0H4 Lead 1/Lead 2, M0) -> SWS leakage at O' and cutoff agreement with the refit -> metrics, R1-R7,
onsets, thirds -> misses/false alarms vs M0 -> label noise and Monte Carlo -> decision. Read-only; writes out/.

    python -B price_refit.py served && python -B price_refit.py post && python -B score_price.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import price_refit as PR  # noqa: E402  (frozen check, issue module, read-only imports)

SI, OUT, ROOTD = PR.SI, PR.OUT, PR.ROOTD
P, R, RV = SI.P, SI.R, SI.RV
np, pd = PR.np, PR.pd
LOG: list[str] = []


def say(*a):
    s = " ".join(str(x) for x in a)
    LOG.append(s)
    print(s, flush=True)


def cm(s) -> str:
    return f"{s['TP']}/{s['FP']}/{s['FN']}/{s['TN']}"


def price_persist(X, t: int, provs, cutoff: int) -> dict:
    """Price condition alone on the newest three CPI months at the cutoff (the price half of PERSIST-SI at O')."""
    th = X.L.e40_spec()
    yoy = X.E.data()[0].yoy
    y = yoy[yoy["ym"].isin([cutoff - 2, cutoff - 1, cutoff])]
    out = {}
    for p in provs:
        f = y[(y["province_code"] == p) & (y["commodity"] == "food")]["yoy"]
        a = y[(y["province_code"] == p) & (y["commodity"] == "all_items")]["yoy"]
        out[p] = np.nan if (len(f) < 3 or len(a) < 3) else float(f.mean() > th["food"][p] or (f.mean() - a.mean()) > th["gap"][p])
    return out


def fast(y, p, q, base):
    """LEAD2_POST_SWS_ISSUE/runner/score.py section 6, unchanged."""
    yh = (p >= .5).astype(int)
    tp, fp = ((yh == 1) & (y == 1)).sum(), ((yh == 1) & (y == 0)).sum()
    fn, tn = ((yh == 0) & (y == 1)).sum(), ((yh == 0) & (y == 0)).sum()
    rec = tp / (tp + fn) if tp + fn else 0
    spec = tn / (tn + fp) if tn + fp else 0
    prec = tp / (tp + fp) if tp + fp else 0
    acc = (tp + tn) / len(y)
    qs = np.unique(q)
    a = lambda m: float((yh[m] == y[m]).mean())  # noqa: E731
    return {"R2": acc >= .75, "R3": (rec + spec) / 2 >= .70,
            "R4": acc > float((y == 0).mean()) and acc > float(((base >= .5).astype(int) == y).mean()),
            "R6": prec >= .6 and rec >= .6,
            "R7": min(a(np.isin(q, t)) for t in np.array_split(qs, 3)) >= .6 and min(a(q != u) for u in qs) >= .7}


def main():
    PR.frozen_ok()
    res = {"protocolSha256": hashlib.sha256((ROOTD / "PROTOCOL.md").read_bytes()).hexdigest(),
           "amendment1Sha256": hashlib.sha256((ROOTD / "PROTOCOL_AMENDMENT_1.md").read_bytes()).hexdigest()}

    # ---------------------------------------------------------------- 0. refit checks must have passed
    rs = json.loads((OUT / "refit_served.json").read_text(encoding="utf-8"))
    rp = json.loads((OUT / "refit_post.json").read_text(encoding="utf-8"))
    res["refit"] = {"parityStored": rs["parityStored"], "parityCode": rs["parityCode"], "parityPass": rs["parityPass"],
                    "perturbation": rp["perturbation"], "leakageServed": rs["leakageAudit"]["passed"],
                    "leakagePost": rp["leakageAudit"]["passed"]}
    if not (rs["parityPass"] and rp["perturbation"]["pass"] and rs["leakageAudit"]["passed"] and rp["leakageAudit"]["passed"]):
        raise SystemExit("refit checks failed: M2 is not scored")
    cut_refit = {r["origin"]: r["cpiCutoff"] for r in rp["leakageAudit"]["rows"]}

    X = SI.setup()
    C = X.C

    # ---------------------------------------------------------------- 1. reproduction
    d = P.load_p0h4()
    rep = {k: cm(RV.scores(d[d["lead"] == k])) for k in (1, 2)}
    say("reproduction P0H4", rep)
    if rep[1] != "11/5/6/48" or rep[2] != "6/4/11/44":
        raise SystemExit("P0H4 reproduction failed")
    g = d[d["lead"] == 2].copy().reset_index(drop=True)
    provs = sorted(g["province_code"].unique())

    # ---------------------------------------------------------------- 2. terms at O'(t), SWS leakage, cutoff agreement
    audit = []
    for t in sorted(int(x) for x in g["t"].unique()):
        o2 = SI.post_issue(t)
        iss = o2.date().isoformat()
        h4p, info = SI.h4_at(X, iss, t, 2)
        if not info["newestSwsPublished"] < iss:
            raise SystemExit(f"LEAKAGE: SWS round published {info['newestSwsPublished']} not before {iss}")
        cut = SI.cpi_newest(o2)
        if cut_refit[R.qs(t)] != X.L.ym_s(cut):
            raise SystemExit(f"refit cutoff {cut_refit[R.qs(t)]} != O' cutoff {X.L.ym_s(cut)} at {R.qs(t)}")
        ps, cl = SI.persist_clim_at(X, iss, t, provs, cut)
        pp = price_persist(X, t, provs, cut)
        m = g["t"] == t
        g.loc[m, "pi_H4_post"], g.loc[m, "CLIM_post"] = h4p, cl
        g.loc[m, "PERSIST_post"] = g.loc[m, "province_code"].map(ps)
        g.loc[m, "PRICE_PERSIST_post"] = g.loc[m, "province_code"].map(pp)
        audit.append({"origin": R.qs(t), "target": R.qs(t + 2), "O": str(R.issue(t).date()), "O_post": iss,
                      "newestSwsQ": info["newestSwsQ"], "newestSwsPublished": info["newestSwsPublished"],
                      "cpiCutoffServed": X.L.ym_s(PR.M0_SERVED(t)), "cpiCutoffPost": X.L.ym_s(cut)})
    res["issueAudit"] = audit
    for a in audit:
        say(f"  {a['origin']}->{a['target']}  O' {a['O_post']}  SWS {a['newestSwsQ']} (pub {a['newestSwsPublished']})  "
            f"CPI {a['cpiCutoffServed']} -> {a['cpiCutoffPost']}")

    post = pd.read_csv(OUT / "p0_price_post.csv", dtype={"province_code": str})
    post = post[post["lead"] == 2][["t", "province_code", "P0_price", "P0_cfg"]].rename(
        columns={"P0_price": "P0_price_post", "P0_cfg": "P0_cfg_post"})
    n0 = len(g)
    g = g.merge(post, on=["t", "province_code"], how="left")
    if len(g) != n0 or g["P0_price_post"].isna().any():
        raise SystemExit("P0_price' missing for an official row")
    g["M0"] = g["pi_H4_post"] * g["P0_price"]
    g["M2"] = g["pi_H4_post"] * g["P0_price_post"]
    g["ALWAYS_LOW"] = 0.0
    m0cm = cm(SI.metrics(g["y"], g["M0"]))
    say("reproduction M0", m0cm)
    res["reproduction"] = {"P0H4_lead1": rep[1], "P0H4_lead2": rep[2], "M0": m0cm}
    if m0cm != "10/6/7/42":
        raise SystemExit("M0 reproduction failed")

    # ---------------------------------------------------------------- 3. evaluation on the official rows
    lab = C.labels()
    labd = {(p, int(q)): int(y) for p, q, y in zip(lab["province_code"], lab["q"], lab["y"])}
    pf = g.copy()
    pf["PERSIST-SI_p"], pf["CLIM_p"] = pf["PERSIST_post"], pf["CLIM_post"]
    A = {}
    for name, col, frame in (("P0H4_original_issue", RV.P, g), ("M0_post_SWS", "M0", pf), ("M2_post_SWS_price", "M2", pf),
                             ("PERSIST-SI_post", "PERSIST_post", pf), ("CLIM_post", "CLIM_post", pf), ("ALWAYS-LOW", "ALWAYS_LOW", pf)):
        e = {"metrics": SI.with_ci(frame, col), "onsetsAnticipated": SI.onsets(frame, col, labd), "byThird": SI.thirds(frame, col)}
        if name in ("P0H4_original_issue", "M0_post_SWS", "M2_post_SWS_price"):
            o = P.official_rules(frame, col)
            e["rules"] = {k.split()[0]: {"pass": v["pass"], "value": v["value"]} for k, v in o["rules"].items()}
            e["failed"], e["passesAll"] = o["failed"], o["passesAll"]
        A[name] = e
    res["evaluation"] = A
    say("\nofficial 65 Lead-2 rows, T43c:")
    for k, e in A.items():
        m = e["metrics"]
        say(f"  {k:20s} acc {m['accuracy']:.3f} {m['CI95']['accuracy']} bal {m['balanced'] or 0:.3f} {m['CI95']['balanced']} "
            f"P {m['precision'] or 0:.3f} R {m['recall'] or 0:.3f} spec {m['specificity'] or 0:.3f} AUC {m['auc'] or 0:.3f} "
            f"Brier {m['brier']:.4f} {m['CI95']['brier']} CM {cm(m)} onsets {e['onsetsAnticipated']}"
            + (f" | fails {e['failed']}" if "failed" in e else ""))
        if "rules" in e:
            say("      rules", json.dumps(e["rules"], default=str))
        say("      by third", e["byThird"])

    # ---------------------------------------------------------------- 4. M2 vs M0, row by row
    cols = ["origin", "target", "province_code", "y", "hunger", "price", "pi_H4_post", "P0_price", "P0_price_post", "M0", "M2"]
    g["origin"], g["target"] = g["t"].map(R.qs), g["q"].map(R.qs)
    miss0 = g[(g["y"] == 1) & (g["M0"] < .5)]
    res["m0Misses"] = [{**{c: r[c] for c in cols}, "caughtByM2": bool(r["M2"] >= .5)} for _, r in miss0.iterrows()]
    nfa = g[(g["y"] == 0) & (g["M2"] >= .5) & (g["M0"] < .5)]
    res["m2NewFalseAlarms"] = [{c: r[c] for c in cols} for _, r in nfa.iterrows()]
    lost = g[(g["M0"] >= .5) & (g["M2"] < .5)]
    res["m0AlarmsDroppedByM2"] = [{c: r[c] for c in cols} for _, r in lost.iterrows()]
    say("\nM0's misses:")
    for r in res["m0Misses"]:
        say(f"  {r['target']} {r['province_code']} P0_price {r['P0_price']:.3f} -> {r['P0_price_post']:.3f}  M0 {r['M0']:.3f} M2 {r['M2']:.3f}  caught {r['caughtByM2']}")
    say("M2 new false alarms:", [(r["target"], r["province_code"], round(r["M2"], 3)) for r in res["m2NewFalseAlarms"]])
    say("M0 alarms dropped by M2:", [(r["target"], r["province_code"], r["y"], round(r["M2"], 3)) for r in res["m0AlarmsDroppedByM2"]])

    # price half on the official rows (development diagnostic only; not the independent gate)
    ph = {}
    for name, col in (("P0_price", "P0_price"), ("P0_price_post", "P0_price_post"), ("price_persistence_post", "PRICE_PERSIST_post")):
        h = g[g[col].notna()]
        ph[name] = {"rows": int(len(h)), **{k: v for k, v in SI.metrics(h["price"], h[col]).items()}}
    res["priceHalfOfficialRows"] = ph
    say("price half vs the price label (official rows; development only):",
        {k: (cm(v), round(v["brier"], 4), round(v["balanced"] or 0, 3)) for k, v in ph.items()})
    res["independentPriceGate"] = {"evaluable": False, "reason": "the served P0 features cannot be built before 2021 "
                                   "(E41 loader WindowViolation on CPI before 2021-01; news composites, PSA LGU vulnerability and "
                                   "Pink Sheet columns exist only from 2021); Y12's pre-2021 provincial CPI covers only the CPI family",
                                   "pass": False}

    # ---------------------------------------------------------------- 5. label noise + Monte Carlo (ISSUE section 6)
    FM = X.FM
    pr = FM.rounds("primary")
    bl = pr[pr["area"] == "BL"]
    lv = {int(q): (float(gq["H"].mean()), float((gq["moe"].mean() / 1.96) / np.sqrt(len(gq)))) for q, gq in bl.groupby("q")}
    border = sorted({int(q) for q in pf["q"] if abs(lv[int(q)][0] - R.H_LINE) <= 1.0})
    noise = {"borderlineQuarters": [(R.qs(q), lv[q][0]) for q in border]}
    price = pf["price"].to_numpy(int)
    qv = pf["q"].to_numpy(int)
    base = pf["PERSIST_post"].to_numpy(float)
    for col in ("M0", "M2"):
        p = pf[col].to_numpy(float)
        y0 = pf["y"].to_numpy(int)
        rc = {"observed": {k: bool(v) for k, v in fast(y0, p, qv, base).items()}, "flips": {}}
        for x in border + ["all"]:
            sel = np.isin(qv, border) if x == "all" else (qv == x)
            hung = (np.array([lv[int(u)][0] for u in qv]) > R.H_LINE).astype(int)
            hung = np.where(sel, 1 - hung, hung)
            rc["flips"][R.qs(x) if x != "all" else "all"] = {k: bool(v) for k, v in fast(hung * price, p, qv, base).items()}
        rng = np.random.default_rng(SI.SEED)
        cnt = {k: 0 for k in rc["observed"]}
        alln = 0
        for _ in range(2000):
            draw = {u: rng.normal(lv[int(u)][0], lv[int(u)][1]) for u in np.unique(qv)}
            yy = (np.array([draw[u] for u in qv]) > R.H_LINE).astype(int) * price
            if 0 < yy.sum() < len(yy):
                f = fast(yy, p, qv, base)
                for kk, vv in f.items():
                    cnt[kk] += int(vv)
                alln += int(all(f.values()))
        rc["monteCarloPassRate"] = {k: round(v / 2000, 3) for k, v in cnt.items()}
        rc["monteCarloAllPass"] = round(alln / 2000, 3)
        noise[col] = rc
    res["labelNoise"] = noise
    say("\nlabel noise:", json.dumps(noise))

    # ---------------------------------------------------------------- 6. decision (protocol section 6)
    r17 = A["M2_post_SWS_price"]["passesAll"]
    mc = noise["M2"]["monteCarloAllPass"]
    if r17:
        label = ("A-dev: Lead 2 issued after the SWS release, with its CPI cutoff moved to that date, passes on development "
                 "data; no independent price check was possible; needs sealed prospective confirmation") + (" (fragile)" if mc < .5 else "")
    else:
        label = "C"
    res["decision"] = {"R1toR7_M2": r17, "failed": A["M2_post_SWS_price"]["failed"], "independentPriceGate": "not evaluable (cap: development pass)",
                       "monteCarloAllPass_M2": mc, "decision": "A-dev" if r17 else "C", "label": label}
    say("\nDECISION", json.dumps(res["decision"]))
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    g[["t", "q", "origin", "target", "province_code", "y", "hunger", "price", "pi_H4", "pi_H4_post", "P0_price", "P0_price_post",
       "P0_cfg", "P0_cfg_post", RV.P, "M0", "M2", "PERSIST-SI_p", "CLIM_p", "PERSIST_post", "CLIM_post", "PRICE_PERSIST_post"]].to_csv(
        OUT / "eval_rows.csv", index=False, lineterminator="\n", float_format="%.6f")
    (OUT / "log_score.txt").write_text("\n".join(LOG) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
