"""E32 step 1: why did the previous models fail? Descriptive diagnosis on the E31 corrected data (2021-Q2..2026-Q3).

Nothing here is fitted for selection. Every quantity is computed with the release-time rules of the evaluation
(the threshold of a target quarter is the one in force at its lead-1 origin), so it describes what a forecaster could
actually face. Output: runs/e32_diagnosis.json (+ printed summary).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e32_common as C  # noqa: E402

np, pd, P = C.np, C.pd, C.P
from scipy.stats import spearmanr  # noqa: E402


def origin_of(target_q: int) -> pd.Timestamp:
    """Lead-1 origin O(t) for target t+1 = first day of the target quarter (E25 convention)."""
    y, n = divmod(target_q, 4)
    return pd.Timestamp(y, 3 * n + 1, 1)


def main():
    d = C.load()
    S1, rounds, Dm = d["S1"], d["rounds"], d["Dm"]
    S1 = S1.assign(tq=S1["quarter"].map(C.qk))
    H = rounds[rounds["definition_A"].astype(str).str.lower() == "true"].groupby("quarter")["H"].mean()
    S1["H"] = S1["quarter"].map(H)
    S1["D"] = [Dm.get((p, t)) for p, t in zip(S1["province_code"], S1["tq"])]
    out = {"inputs": C.inputs_manifest()}
    # ---- 1. how much of the label is regional
    v = S1.dropna(subset=["S1"])
    between = v.groupby("quarter")["S1"].transform("mean")
    out["S1_variance_share_between_quarters"] = float(between.var() / v["S1"].var())
    out["S1_variance_share_H"] = float(v["H"].var() / v["S1"].var())
    # ---- 2. labels at the evaluation thresholds (lead-1 origin of each target)
    lab = []
    for tq in sorted(v["tq"].unique()):
        if tq < C.qk("2022-Q1"):
            continue
        o = origin_of(tq)
        try:
            tau, n_tau = P.threshold_at(d["S1"], rounds, tq - 1, o)
        except Exception:
            continue
        if not n_tau or tau != tau:
            continue
        g = v[v["tq"] == tq]
        lab.append({"quarter": C.qs(tq), "tau": tau, "n_tau_labels": n_tau, "H": float(g["H"].iloc[0]),
                    "n_HIGH": int((g["S1"] > tau).sum()), "n": int(len(g)),
                    "min_margin": float((g["S1"] - tau).abs().min())})
    L = pd.DataFrame(lab)
    out["labels_by_target_quarter"] = L.to_dict("records")
    ev = L[L["quarter"].map(C.qk) >= C.qk("2023-Q4")]
    out["evaluable_targets_2023Q4_2026Q3"] = {
        "quarters": int(len(ev)), "rows": int(ev["n"].sum()), "HIGH": int(ev["n_HIGH"].sum()),
        "LOW": int((ev["n"] - ev["n_HIGH"]).sum()),
        "quarters_all_five_same_label": int(((ev["n_HIGH"] == 0) | (ev["n_HIGH"] == 5)).sum()),
        "always_HIGH_accuracy": float(ev["n_HIGH"].sum() / ev["n"].sum())}
    L["year"] = L["quarter"].str[:4]
    out["HIGH_share_by_year"] = (L.groupby("year")["n_HIGH"].sum() / L.groupby("year")["n"].sum()).round(3).to_dict()
    # ---- 3. persistence of the components
    Hs = H.sort_index()
    dH = Hs.diff().dropna()
    out["H"] = {"rounds_quarters": int(len(Hs)), "sd_quarterly_change_pp": float(dH.std()),
                "autocorr_of_changes": float(dH.autocorr()), "level_2021_2023": float(Hs[Hs.index < "2024"].mean()),
                "level_2024_2026": float(Hs[Hs.index >= "2024"].mean())}
    pairs = [(Dm[(p, t)], Dm[(p, t + 1)]) for (p, t) in Dm if (p, t + 1) in Dm]
    a = np.array(pairs)
    out["D"] = {"sd_pp": float(np.std(list(Dm.values()))), "lag1_autocorr": float(np.corrcoef(a[:, 0], a[:, 1])[0, 1]),
                "n_pairs": int(len(a))}
    # between-province persistent component of D
    dd = pd.DataFrame([(p, t, v_) for (p, t), v_ in Dm.items()], columns=["p", "t", "D"])
    out["D"]["share_of_D_variance_between_provinces"] = float(dd.groupby("p")["D"].transform("mean").var() / dd["D"].var())
    # ---- 4. SWS publication lag (days after the end of the fieldwork quarter)
    r = rounds[rounds["definition_A"].astype(str).str.lower() == "true"].copy()
    r["pub"] = pd.to_datetime(r["published_eff"], format="ISO8601", errors="coerce")
    r["qend"] = r["quarter"].map(lambda q: origin_of(C.qk(q) + 1))
    lag = (r["pub"] - r["qend"]).dt.days
    out["sws_posting_days_after_quarter_end"] = {"median": float(lag.median()), "min": float(lag.min()),
                                                 "max": float(lag.max()),
                                                 "share_posted_after_next_quarter_start": float((lag >= 0).mean())}
    # ---- 5. does the validated news signal relate to the NEXT quarter's outcome? (Spearman, available pairs)
    N = d["news"].assign(tq=lambda x: x["quarter"].map(C.qk))
    rel = {}
    prov = N[N["province_code"] != "REGION"]
    rows = []
    for x in prov.itertuples():
        nxt = v[(v["province_code"] == x.province_code) & (v["tq"] == x.tq + 1)]
        dn = Dm.get((x.province_code, x.tq + 1))
        rows.append({"n_rel": x.n_rel, "fssi": x.fssi_v2, "D_next": dn, "D_now": Dm.get((x.province_code, x.tq)),
                     "S1_next": float(nxt["S1"].iloc[0]) if len(nxt) else np.nan})
    R = pd.DataFrame(rows)

    def sp(a, b):
        m = R[[a, b]].dropna()
        if len(m) < 8:
            return {"n": int(len(m)), "rho": None, "p": None}
        rho, pv = spearmanr(m[a], m[b])
        return {"n": int(len(m)), "rho": float(rho), "p": float(pv)}
    for a_ in ("n_rel", "fssi"):
        for b_ in ("D_next", "D_now", "S1_next"):
            rel[f"{a_}_vs_{b_}"] = sp(a_, b_)
    reg = N[N["province_code"] == "REGION"].set_index("tq")
    rr = [{"n_rel": reg.loc[t, "n_rel"], "fssi": reg.loc[t, "fssi_v2"],
           "dH_next": (H.get(C.qs(t + 1)) - H.get(C.qs(t))) if (C.qs(t + 1) in H.index and C.qs(t) in H.index) else np.nan,
           "H_next": H.get(C.qs(t + 1), np.nan)} for t in reg.index]
    R2 = pd.DataFrame(rr)
    for a_ in ("n_rel", "fssi"):
        for b_ in ("dH_next", "H_next"):
            m = R2[[a_, b_]].dropna()
            rho, pv = spearmanr(m[a_], m[b_]) if len(m) >= 8 else (np.nan, np.nan)
            rel[f"region_{a_}_vs_{b_}"] = {"n": int(len(m)), "rho": None if rho != rho else float(rho),
                                           "p": None if pv != pv else float(pv)}
    out["news_vs_next_quarter"] = rel
    # ---- 6. oracle bounds on the evaluable targets (lead 1): what if one component were known?
    acc = {"oracle_H_with_D_last": [], "oracle_D_with_H_last": [], "persistence": []}
    for row in ev.itertuples():
        tq = C.qk(row.quarter)
        g = v[v["tq"] == tq]
        Hlast = rounds_last_H(rounds, origin_of(tq))
        prev = v[v["tq"] == tq - 1]
        for x in g.itertuples():
            y = int(x.S1 > row.tau)
            dl = Dm.get((x.province_code, tq - 2))      # D(t-1) is the latest published at O(t)
            if dl is not None:
                acc["oracle_H_with_D_last"].append(int((x.H + 2 * dl > row.tau) == y))
            if Hlast is not None:
                acc["oracle_D_with_H_last"].append(int((Hlast + 2 * x.D > row.tau) == y))
            pp = prev[prev["province_code"] == x.province_code]
            if len(pp):
                acc["persistence"].append(int((float(pp["S1"].iloc[0]) > row.tau) == y))
    out["oracle_accuracy_lead1"] = {k: {"accuracy": float(np.mean(v_)), "n": len(v_)} for k, v_ in acc.items() if v_}
    C.write_json(C.E32 / "runs" / "e32_diagnosis.json", C.clean(out))
    s = out["evaluable_targets_2023Q4_2026Q3"]
    print("S1 variance between quarters", round(out["S1_variance_share_between_quarters"], 3), "| H share", round(out["S1_variance_share_H"], 3))
    print("evaluable", s)
    print("HIGH share by year", out["HIGH_share_by_year"])
    print("H", out["H"]); print("D", out["D"]); print("SWS lag", out["sws_posting_days_after_quarter_end"])
    print("news", {k: (v_["n"], None if v_["rho"] is None else round(v_["rho"], 2), None if v_["p"] is None else round(v_["p"], 3)) for k, v_ in rel.items()})
    print("oracle", out["oracle_accuracy_lead1"])


def rounds_last_H(rounds, origin):
    rr = P.rounds_at_origin(rounds, origin)
    if not len(rr):
        return None
    rr = rr.assign(tq=rr["quarter"].map(C.qk))
    last = rr[rr["tq"] == rr["tq"].max()]
    return float(last["H"].mean())


if __name__ == "__main__":
    main()
