"""E101 runner (PROTOCOL.md, frozen sha in PROTOCOL_SHA256.txt): access-informed FIRI weighting vs the served and
equal-weight indexes, Leads 1-3, sensitivity, duplication, independent-outcome check and the prospective seal.

Reads only served, local files; writes only to ../out/. Run from backend/ with the backend venv:

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E101_Access_Informed_Weighting/runner/e101_run.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "out"
EXP = HERE.parents[1]
sys.path.insert(0, str(EXP / "E100_Market_Trigger_Investigation" / "runner"))
import e100_run as R  # noqa: E402  (verified FIRI v2 reproduction, metrics, evidence weights)

np, pd, TS, qi, qs = R.np, R.pd, R.TS, R.qi, R.qs
from scipy.stats import spearmanr  # noqa: E402

E63 = EXP / "E63_Lead_Time_Study" / "sealed" / "predictions.csv"
LEAD_ORIGINS = {1: ("2021-Q4", "2026-Q2"), 2: ("2021-Q4", "2026-Q1"), 3: ("2021-Q4", "2025-Q4")}
PUBLISHED = {1: (0.889, 0.180), 2: (0.941, 0.189), 3: (0.812, 0.200)}       # firi2_evaluation.json, C3
T1_W = {"ACCESS": 0.50, "AVAIL": 0.25, "STAB": 0.25}
DIMS = ("ACCESS", "AVAIL", "STAB")


def verify():
    want = (HERE / "PROTOCOL_SHA256.txt").read_text().split()[0]
    got = hashlib.sha256((HERE.parent / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    assert got == want, "PROTOCOL.md changed after freezing"
    want63 = (E63.parent / (E63.name + ".sha256")).read_text().split()[0]
    assert hashlib.sha256(E63.read_bytes()).hexdigest() == want63, "E63 sealed predictions changed"
    return got


def mean(vals):
    v = [x for x in vals if x is not None]
    return float(np.mean(v)) if v else None


# ------------------------------------------------------------------------------------------------ rows per lead
def rel_scores(LV):
    """REL percentile against strictly earlier origins (all provinces pooled, >= 8)."""
    out = {}
    for t in sorted(LV["t"].unique()):
        prior = LV[(LV["t"] < t) & LV["REL"].notna()]["REL"].tolist()
        for r in LV[(LV["t"] == t) & LV["REL"].notna()].itertuples():
            if len(prior) >= 8:
                out[(int(t), r.province_code)] = (sum(v < r.REL for v in prior) + 0.5 * sum(v == r.REL for v in prior)) / len(prior)
    return out


def lead_rows(H, lead, a1_63, rel):
    t0, t1 = LEAD_ORIGINS[lead]
    if lead == 2:
        t1 = "2026-Q3"                                           # forward origins for the seal
    rows = []
    hcache = {}
    for _, r in H.iterrows():
        t = int(r["t"])
        if not (qi(t0) <= t <= qi(t1)):
            continue
        s = {k: (None if v.get("score") is None else float(v["score"])) for k, v in r["ind"].items()}
        if lead != 2:
            s["A1"] = a1_63.get((lead, t, r["province_code"]))
        if t not in hcache:
            hcache[t] = TS.regional_hunger(t, lead).get("probabilityAbove11_3")
        s["H1"] = hcache[t]
        s["REL"] = rel.get((t, r["province_code"]))
        dom = {"A": mean([s["A1"], s["A2"], s["A3"]]), "V": s["V1"],
               "C": mean([s["C1"], s["C2"], s["C3"], s["C4"]]), "E": mean([s["E1"], s["E2"]]), "N": s["N1"], "H": s["H1"]}
        if lead == 2:                                            # stored domain scores are the served ones
            for d in "AVCEN":
                dom[d] = None if pd.isna(r[f"dom_{d}"]) else float(r[f"dom_{d}"])
        rows.append({"t": t, "code": r["province_code"], "target": qs(t + lead), "s": s, "dom": dom})
    return rows


def served_equal(rows, lead, doms=R.DOMS):
    reg_hist, served, equal = [], {}, {}
    for t in sorted({x["t"] for x in rows}):
        known = {qs(q): h for q, h in TS._posted(TS.issue_of(t)).items()}
        w, n, _ = R.evidence_weights([(dm, tq) for (tt, dm, tq) in reg_hist if tt < t], known, list(doms))
        cur = [x for x in rows if x["t"] == t]
        for x in cur:
            served[(x["target"], x["code"])] = R.index_of(x["dom"], w, doms)
            equal[(x["target"], x["code"])] = R.index_of(x["dom"], None, doms)
        regm = {d: mean([x["dom"][d] for x in cur]) for d in doms}
        reg_hist.append((t, regm, qs(t + lead)))
    return served, equal


def t1_value(s, w=T1_W, use_h=True, use_rel=False, drop=None):
    A = mean([s["A1"], s["REL"] if use_rel else s["A2"], s["A3"]])
    comps = {"A": A, "E": mean([s["E1"], s["E2"]]), "V": s["V1"], "H": s["H1"] if use_h else None}
    if drop:
        comps[drop] = None
    avail = [v for v in comps.values() if v is not None]
    D = {"ACCESS": float(np.mean(avail)) if len(avail) >= 2 else None,
         "AVAIL": mean([s["C3"], s["C4"]]), "STAB": mean([s["C1"], s["C2"], s["N1"]])}
    if D["ACCESS"] is None or sum(D[d] is not None for d in DIMS) < 2:
        return None, D
    tot = sum(w[d] for d in DIMS if D[d] is not None)
    return sum(w[d] / tot * D[d] for d in DIMS if D[d] is not None), D


# ------------------------------------------------------------------------------------------------ evaluation
def regional(rows, arms, out_h, lead):
    t0, t1 = LEAD_ORIGINS[lead]
    targets = sorted({x["target"] for x in rows if qi(t0) <= x["t"] <= qi(t1) and x["target"] in out_h}, key=qi)
    Q = pd.DataFrame({"target": targets})
    Q["t"] = Q["target"].map(lambda q: qi(q) - lead)
    Q["H_obs"] = Q["target"].map(out_h)
    Q["y"] = (Q["H_obs"] > R.HUNGER_LINE).astype(int)
    for a, vals in arms.items():
        Q[a] = [np.mean([v for p in R.PROVS if (v := vals.get((q, p))) is not None]) if any(vals.get((q, p)) is not None
                for p in R.PROVS) else np.nan for q in targets]
    Q["H1"] = [next(x["s"]["H1"] for x in rows if x["target"] == q) for q in targets]
    Q["ALWAYS"] = 1.0
    Q["CLIM"] = [np.mean([h > R.HUNGER_LINE for h in TS._posted(TS.issue_of(int(t))).values()]) or 0.5 for t in Q["t"]]
    return Q


def score(Q, names, refs=("SERVED", "EQUAL")):
    res = {}
    for a in names:
        g = Q.dropna(subset=[a])
        if g.empty:
            continue
        m = R.metrics(g["y"], g[a])
        m["spearman_with_hunger_level"] = float(spearmanr(g[a], g["H_obs"]).correlation) if g[a].nunique() > 1 else None
        m["quarters"] = int(len(g))
        for ref in refs:
            if a != ref and ref in Q:
                gg = Q.dropna(subset=[a, ref])
                p = R.paired(gg["y"].to_numpy(float), gg[a].to_numpy(float), gg[ref].to_numpy(float))
                p["quarters"] = int(len(gg))
                m[f"vs_{ref}"] = p
        res[a] = m
    return res


def main():
    sha = verify()
    OUT.mkdir(exist_ok=True)
    H = R.load_history()
    out_h = R.outcome_series()
    LV = R.level_indicator()
    rel = rel_scores(LV)
    S63 = pd.read_csv(E63, dtype={"province_code": str})
    a1_63 = {(int(r.lead), int(r.t), r.province_code): float(r.E56_p_price) for r in S63.itertuples()}

    result = {"protocolSha256": sha, "weights_T1": T1_W, "leads": {}}
    rows_by_lead, Q_by_lead = {}, {}
    for lead in (1, 2, 3):
        rows = lead_rows(H, lead, a1_63, rel)
        rows_by_lead[lead] = rows
        served, equal = served_equal(rows, lead)
        arms = {"SERVED": served, "EQUAL": equal}
        for name, kw in {"T1": {}, "T1-noH": {"use_h": False}, "T1-REL": {"use_rel": True},
                         "T1-EQD": {"w": {d: 1 / 3 for d in DIMS}}}.items():
            arms[name] = {(x["target"], x["code"]): t1_value(x["s"], **kw)[0] for x in rows}
        Q = regional(rows, arms, out_h, lead)
        Q_by_lead[lead] = (Q, arms)
        Q.to_csv(OUT / f"regional_lead{lead}.csv", index=False, lineterminator="\n")
        sc = score(Q, list(arms) + ["H1", "ALWAYS", "CLIM"])
        pa, pb = PUBLISHED[lead]
        rep = {"accuracy": sc["SERVED"]["accuracy"], "brier": sc["SERVED"]["brier"], "quarters": sc["SERVED"]["quarters"],
               "published": {"accuracy": pa, "brier": pb}}
        rep["reproduced"] = bool(abs(rep["accuracy"] - pa) <= 0.01 and abs(rep["brier"] - pb) <= 0.01)
        result["leads"][str(lead)] = {"reproduction": rep, "arms": sc}

    # sensitivity, Lead 2
    rows2 = rows_by_lead[2]
    Q2, arms2 = Q_by_lead[2]

    def arm_score(vals):
        q = Q2[["target", "y", "H_obs", "SERVED"]].copy()
        q["X"] = [np.mean([v for p in R.PROVS if (v := vals.get((t, p))) is not None]) if any(vals.get((t, p)) is not None
                  for p in R.PROVS) else np.nan for t in q["target"]]
        g = q.dropna(subset=["X", "SERVED"])            # correction: the quarters SERVED is scored on (see out/NOTES.md)
        return float(((g["X"] >= 0.5).astype(int) == g["y"]).mean()), float(np.mean((g["X"] - g["y"]) ** 2)), int(len(g))
    sens = {"access_grid": {}, "drop_component": {}, "dirichlet": {}}
    for wa in (1 / 3, 0.40, 0.50, 0.60, 2 / 3):
        w = {"ACCESS": wa, "AVAIL": (1 - wa) / 2, "STAB": (1 - wa) / 2}
        acc, br, n = arm_score({(x["target"], x["code"]): t1_value(x["s"], w=w)[0] for x in rows2})
        sens["access_grid"][f"{wa:.2f}"] = {"accuracy": acc, "brier": br, "quarters": n}
    for c in ("A", "E", "V", "H"):
        acc, br, n = arm_score({(x["target"], x["code"]): t1_value(x["s"], drop=c)[0] for x in rows2})
        sens["drop_component"][c] = {"accuracy": acc, "brier": br, "quarters": n}
    rng = np.random.default_rng(2026)
    draws = rng.dirichlet(20 * np.array([0.50, 0.25, 0.25]), 1000)
    accs, brs = [], []
    for d in draws:
        w = dict(zip(DIMS, d))
        acc, br, _ = arm_score({(x["target"], x["code"]): t1_value(x["s"], w=w)[0] for x in rows2})
        accs.append(acc)
        brs.append(br)
    sens["dirichlet"] = {"draws": 1000, "alpha": [10, 5, 5], "accuracy_p5_p50_p95": np.percentile(accs, [5, 50, 95]).tolist(),
                         "brier_p5_p50_p95": np.percentile(brs, [5, 50, 95]).tolist(),
                         "share_brier_below_SERVED": float(np.mean(np.array(brs) < result["leads"]["2"]["arms"]["SERVED"]["brier"])),
                         "share_accuracy_ge_ALWAYS": float(np.mean(np.array(accs) >= result["leads"]["2"]["arms"]["ALWAYS"]["accuracy"]))}
    result["sensitivity_lead2"] = sens

    # duplication: province rows (Lead 2 evaluation origins) and regional components per origin
    ev = [x for x in rows2 if x["t"] <= qi(LEAD_ORIGINS[2][1])]
    X = pd.DataFrame([{k: x["s"].get(k) for k in ("A1", "A2", "A3", "REL", "V1", "E1", "E2", "H1", "C1", "C3", "C4")}
                      for x in ev]).astype(float)
    result["duplication_province_rows"] = X.corr(method="spearman", min_periods=8).round(2).to_dict()
    comp = []
    for t in sorted({x["t"] for x in ev}):
        cur = [x for x in ev if x["t"] == t]
        D = [t1_value(x["s"])[1] for x in cur]
        comp.append({"t": t, "A": mean([mean([x["s"]["A1"], x["s"]["A2"], x["s"]["A3"]]) for x in cur]),
                     "E": mean([mean([x["s"]["E1"], x["s"]["E2"]]) for x in cur]), "V": mean([x["s"]["V1"] for x in cur]),
                     "H": cur[0]["s"]["H1"], "AVAIL": mean([d["AVAIL"] for d in D]), "STAB": mean([d["STAB"] for d in D])})
    result["duplication_regional_components"] = pd.DataFrame(comp).drop(columns="t").astype(float).corr(
        method="spearman", min_periods=6).round(2).to_dict()

    # independent outcome: PSA subsistence 2023 (descriptive, n = 5)
    sub = pd.read_parquet(R.BACKEND / "data/processed/psa_subsistence.parquet", filters=[("year", ">=", 2021)])
    names = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal",
             "PH040500000": "Batangas"}
    s23 = sub[(sub["year"] == 2023) & (sub["geographic_level"] == "province")].set_index("area_name")
    ind = {}
    for a in ("SERVED", "T1", "T1-noH"):
        vals = {p: mean([arms2[a].get((f"2023-Q{k}", p)) for k in range(1, 5)]) for p in R.PROVS}
        ok = [p for p in R.PROVS if vals[p] is not None and names[p] in s23.index]
        ind[a] = {"province_mean_2023": {names[p]: vals[p] for p in ok},
                  "spearman_with_subsistence_2023": float(spearmanr([vals[p] for p in ok],
                                                                     [s23.loc[names[p], "subsistence_pct"] for p in ok]).correlation)
                  if len(ok) >= 4 else None, "n": len(ok)}
    ind["subsistence_2023"] = {r: {"pct": float(v.subsistence_pct), "cv": float(v.subsistence_cv),
                                   "usable_for_validation": bool(v.usable_for_validation)} for r, v in s23.iterrows()}
    result["independent_subsistence_2023"] = ind

    # prospective seal, Lead 2 targets 2026-Q4 and 2027-Q1
    seal = []
    for x in rows2:
        if x["target"] in ("2026-Q4", "2027-Q1"):
            seal.append({"target": x["target"], "province_code": x["code"], "SERVED": arms2["SERVED"].get((x["target"], x["code"])),
                         "T1": arms2["T1"].get((x["target"], x["code"])), "T1-noH": arms2["T1-noH"].get((x["target"], x["code"])),
                         "T1-REL": arms2["T1-REL"].get((x["target"], x["code"]))})
    S = pd.DataFrame(seal).sort_values(["target", "province_code"])
    reg = S.groupby("target")[["SERVED", "T1", "T1-noH", "T1-REL"]].mean().reset_index()
    reg["province_code"] = "REGION"
    S = pd.concat([S, reg[S.columns]], ignore_index=True)
    blob = S.to_csv(index=False, lineterminator="\n", float_format="%.6f").encode()
    (OUT / "sealed_prospective.csv").write_bytes(blob)
    (OUT / "sealed_prospective.csv.sha256").write_text(hashlib.sha256(blob).hexdigest() + "  sealed_prospective.csv\n")
    result["sealed"] = {"sha256": hashlib.sha256(blob).hexdigest(), "rows": len(S)}

    (OUT / "results.json").write_text(json.dumps(result, indent=1, default=str), encoding="utf-8")
    for lead in ("1", "2", "3"):
        print("LEAD", lead, result["leads"][lead]["reproduction"])


if __name__ == "__main__":
    main()
