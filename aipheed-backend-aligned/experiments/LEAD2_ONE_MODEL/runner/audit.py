"""Step 2-3 (before any new model): P0H4 Lead-2 error audit and component audits.

    python audit.py   # out/p0h4_lead2_cases.csv, out/audit.json, out/audit.txt
"""
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP = HERE.parents[1]
sys.path.insert(0, str(EXP / "LEAD2_OPTIMIZATION" / "runner"))
import a3 as A3  # noqa: E402
import l2_lib as X  # noqa: E402

U, C, FM, E, L, np, pd = X.U, X.C, X.FM, X.E, X.L, X.np, X.pd
OUT = HERE.parent / "out"
L2OUT = EXP / "LEAD2_OPTIMIZATION" / "out"
LINES = []


def say(*a):
    s = " ".join(str(x) for x in a)
    LINES.append(s)
    print(s, flush=True)


def kind(p, y):
    return {(1, 1): "TP", (0, 1): "FN", (1, 0): "FP", (0, 0): "TN"}[(int(p >= .5), int(y))]


def pattern(r) -> str:
    """Event pattern of a Lead-2 error, from the observed components and issue-time inputs."""
    if r["type"] == "FN":
        if r["pi_H4"] < .5 and r["P0_price"] >= .5:
            return "sudden hunger increase; price risk flagged before hunger (food-price surge preceding hunger)"
        if r["pi_H4"] < .5:
            return "sudden hunger increase and price rise both after issue (no credible early warning)"
        if r["A1_food"] > 0 or r["A1_gap"] > 0:
            return "persistent high hunger; structural price projection pointed HIGH but the model said LOW"
        return "persistent high hunger; price shock after issue (no issue-time price warning)"
    if r["type"] == "FP":
        return ("persistent high hunger; price condition did not materialise"
                if r["hunger_obs"] == 1 else "hunger condition did not materialise")
    return ""


def main():
    U.setup()
    D = pd.read_csv(L2OUT / "predictions_addendum3.csv", dtype={"province_code": str})
    cases = pd.read_csv(L2OUT / "lead2_cases.csv")
    g = D[D["lead"] == 2].copy()
    g["origin"], g["target"] = g["t"].map(L.qs), g["q"].map(L.qs)
    g["province"] = g["province_code"].map(L.NAMES)
    keep = ["origin", "target", "province", "issue_date", "sws_newest_q", "sws_newest_published", "psa_newest_month",
            "news_latest_published", "A1_food", "A1_gap", "A1_food_d", "mom6", "A3", "R_rice_yoy", "W_rice_yoy", "N1",
            "C2", "C3", "C4", "E1", "E2", "V1"]
    g = g.merge(cases[keep], on=["origin", "target", "province"], how="left")
    g["type"] = [kind(p, y) for p, y in zip(g["P0H4_p3"], g["y"])]
    g["hunger_obs"] = g["hunger"]
    g["pattern"] = [pattern(r) for _, r in g.iterrows()]
    g["cause"] = np.where(g["type"] == "FN",
                          np.where(g["pi_H4"] < .5, np.where(g["P0_price"] < .5, "both", "hunger"),
                                   np.where(g["P0_price"] < .5, "price", "product")), "")
    g["news_available"] = g["N1"].notna()
    cols = ["origin", "issue_date", "target", "province", "y", "hunger_obs", "price", "H", "h_last", "sws_newest_q",
            "sws_newest_published", "pi_H4", "P0_price", "P0H4_p3", "type", "cause", "pattern", "A1_food", "A1_gap",
            "mom6", "A3", "R_rice_yoy", "W_rice_yoy", "N1", "news_latest_published", "C2", "C3", "C4", "E1", "E2"]
    g[cols].sort_values(["target", "province"]).to_csv(OUT / "p0h4_lead2_cases.csv", index=False, lineterminator="\n",
                                                       float_format="%.4g")
    res = {}
    say("== P0H4 Lead-2 outcome types:", g["type"].value_counts().to_dict())
    say("== missed HIGH by cause:", g[g["type"] == "FN"]["cause"].value_counts().to_dict())
    say("== error patterns:")
    for p_, n in g[g["type"].isin(["FN", "FP"])].groupby(["type", "pattern"]).size().items():
        say(f"   {p_[0]} x{n}: {p_[1]}")
    fn = g[g["type"] == "FN"]
    say("== news at issue for the 11 missed HIGH rows: available", int(fn["news_available"].sum()), "of", len(fn),
        "| news coverage on all Lead-2 rows:", round(float(g["news_available"].mean()), 2))
    res["types"] = g["type"].value_counts().to_dict()
    res["fn_cause"] = fn["cause"].value_counts().to_dict()
    # conjunction penalty: rows where both components >= .5 but the product < .5
    both = g[(g["pi_H4"] >= .5) & (g["P0_price"] >= .5)]
    sup = both[both["P0H4_p3"] < .5]
    say(f"== product rule: rows with both components >= 0.5: {len(both)}; product < 0.5 among them: {len(sup)} "
        f"(HIGH among those: {int(sup['y'].sum())})")
    res["product_suppression"] = {"both_ge_half": int(len(both)), "product_lt_half": int(len(sup)),
                                  "high_among_suppressed": int(sup["y"].sum())}
    # hunger component per quarter (13 independent outcomes)
    q = g.groupby("q").first().reset_index()
    kn = {}
    for t in q["t"]:
        k_ = [(a, b) for a, b, *_ in C.bl_known(E.issue(int(t)))]
        kn[int(t)] = k_
    q["persist"] = [float(kn[int(t)][-1][1] > X.H_LINE) for t in q["t"]]
    q["change_rule"] = [float(kn[int(t)][-1][1] + (kn[int(t)][-1][1] - kn[int(t)][-2][1]) > X.H_LINE) for t in q["t"]]
    q["any_of_last2"] = [float(max(x[1] for x in kn[int(t)][-2:]) > X.H_LINE) for t in q["t"]]
    hb = {}
    for name, col in (("pi_H4 (served)", "pi_H4"), ("pi_H0 (UNI-FINAL)", "H1"), ("persistence: latest > 11.3", "persist"),
                      ("latest + last change > 11.3", "change_rule"), ("either of last two readings > 11.3", "any_of_last2")):
        p = q[col].to_numpy(float)
        y = q["hunger"].to_numpy(int)
        hb[name] = {"correct": int(((p >= .5).astype(int) == y).sum()), "quarters": int(len(q)),
                    "brier": float(np.mean((p - y) ** 2)), "onsets_2023Q4_2024Q2": [round(float(v), 3) for v in
                                                                                  q.set_index("target")[col].reindex(["2023-Q4", "2024-Q2"])]}
        say(f"   hunger condition, Lead 2 (13 quarters): {name:38s} correct {hb[name]['correct']}/13 Brier "
            f"{hb[name]['brier']:.3f} onset values {hb[name]['onsets_2023Q4_2024Q2']}")
    res["hunger_component"] = hb
    # calibration of pi_H4 over the quarter-level outcomes
    # four-area sigma: are pooled errors independent?
    iss = E.issue(L.qi("2026-Q3"))
    err = {}
    for a in A3.AREAS:
        d = {x[0]: x[1] for x in FM.known(iss, a, "primary")}
        err[a] = {q0: d[q0 + 3] - d[q0] for q0 in d if q0 + 3 in d}
    common = sorted(set.intersection(*[set(v) for v in err.values()]))
    M = np.array([[err[a][c] for a in A3.AREAS] for c in common])
    R = np.corrcoef(M.T)
    rho = float((R.sum() - 4) / 12)
    n_pairs = sum(len(v) for v in err.values())
    deff = 1 + (4 - 1) * rho
    say(f"== four-area sigma (true horizon 3, all errors known by 2026-Q3): {n_pairs} pooled errors from {len(common)} "
        f"common start quarters; mean cross-area error correlation {rho:.2f}; design effect {deff:.2f}; "
        f"effective independent errors ~{n_pairs / deff:.1f}")
    say("   per-area RMSE:", {a: round(math.sqrt(np.mean(np.square(list(v.values())))), 2) for a, v in err.items()},
        "| BL-only RMSE vs pooled:", round(math.sqrt(np.mean(np.square(list(err['BL'].values())))), 2),
        round(math.sqrt(np.mean(np.square([x for v in err.values() for x in v.values()]))), 2))
    res["four_area_sigma"] = {"pooled_errors": n_pairs, "common_quarters": len(common), "mean_cross_area_corr": rho,
                              "design_effect": deff, "effective_errors": n_pairs / deff}
    # survey-design shift (household heads -> adults from 2025-Q2)
    h = C.bl_quarters()
    pre = h[(h.index >= L.qi("2023-Q4")) & (h.index < L.qi("2025-Q2"))]
    post = h[h.index >= L.qi("2025-Q2")]
    say(f"== SWS design shift: BL mean 2023-Q4..2025-Q1 {pre.mean():.1f} (sd {pre.std():.1f}, n {len(pre)}) vs "
        f"2025-Q2+ {post.mean():.1f} (sd {post.std():.1f}, n {len(post)}); share > 11.3: {float((pre > 11.3).mean()):.2f} vs "
        f"{float((post > 11.3).mean()):.2f}; quarter-to-quarter |change| {pre.diff().abs().mean():.1f} vs "
        f"{post.diff().abs().mean():.1f}")
    for name, m in (("targets < 2025-Q2", g["q"] < L.qi("2025-Q2")), ("targets >= 2025-Q2", g["q"] >= L.qi("2025-Q2"))):
        s = g[m]
        y, p = s["y"].to_numpy(int), s["P0H4_p3"].to_numpy(float)
        yh = (p >= .5).astype(int)
        say(f"   P0H4 Lead 2 {name}: rows {len(s)} quarters {s['q'].nunique()} HIGH {int(y.sum())} acc "
            f"{(yh == y).mean():.3f} recall {((yh == 1) & (y == 1)).sum()}/{int(y.sum())} hunger-true quarters "
            f"{int(s.groupby('q')['hunger'].first().sum())}/{s['q'].nunique()}")
    res["design_shift"] = {"pre_mean": float(pre.mean()), "post_mean": float(post.mean()), "pre_sd": float(pre.std()),
                           "post_sd": float(post.std())}
    FM.write_json(OUT / "audit.json", res)
    (OUT / "audit.txt").write_text("\n".join(LINES) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
