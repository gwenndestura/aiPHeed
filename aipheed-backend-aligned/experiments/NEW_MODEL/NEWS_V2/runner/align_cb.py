"""NEWS_V2: complete the objective-level evidence for C-b (no tuning, no new candidate; C-b exactly as in PLAN.md).

    python align_cb.py shap     # refit C-b (identical procedure), full SHAP at Leads 1-2; must equal stored C-b forecasts
    python align_cb.py obj4     # Objective 4 (5 comparators) and H3 (6 comparators), Holm, Leads 1-2  -> ../out/obj4_h3.json
    python align_cb.py spatial  # Objective 3: province poverty-weighted scores + 142 LGU ranks, 2026-10-01 issue
    python align_cb.py seal     # C-b forecasts issued 2026-10-01 -> ../sealed_prospective_CB.csv + ../SEAL_LEDGER.md

The comparators are the stored IMPROVE_V2 / OBJECTIVES_COMPLETION forecasts (none refitted), as in OPTION_1.
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import hashlib
import json
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_news_v2 as N  # noqa: E402

V, H, R = N.V, N.H, N.R
EXP, HERE, OUT = N.EXP, N.HERE, N.OUT
ROOT = EXP.parents[1]
CB = N.MODELS["C-b"]
OBJ4 = ["PERSIST", "PSA-only", "NLP-only", "LOGIT", "ALWAYS-HIGH"]
H3 = ["PERSIST", "NLP-only", "PSA-only", "LOGIT", "LGBM-GOV", "LGBM-NLP"]
NLP_ONLY = {"NLP-only", "LGBM-NLP"}
SEAL_T = H.qi("2026-Q3")


def _origin_shap(t: int) -> pd.DataFrame:
    d, S, lab = N._G["d"], N._G["T"], N._G["lab"]
    src = S[S["area"] == "BL"]
    te = src[(src["t"] == t) & src["lead"].isin((1, 2))].copy()
    tr = src[(src["t"] < t) & (src["q"] <= t - 1)].merge(V.known_labels(d, t, lab)[["area", "q", "y", "H"]],
                                                          on=["area", "q"], how="inner")
    if not H.eligible(tr[tr["area"] == "BL"]):
        return pd.DataFrame()
    cfg = H.lgbm_select(tr, CB, mono=False)
    m = H.LGBM(cfg, CB, False).fit(tr)
    if m.m is None:
        return pd.DataFrame()
    sh = V.shap_frame(m.m, te[CB]).add_prefix("shap_")
    return pd.concat([te[["t", "lead", "q"]].reset_index(drop=True), sh.reset_index(drop=True),
                      pd.Series(m.predict(te), name="p")], axis=1)


def shap():
    N.check_plan()
    with Pool(8, initializer=N._init) as pool:
        parts = pool.map(_origin_shap, V.ORIGINS)
    S = pd.concat([p for p in parts if len(p)], ignore_index=True)
    F = pd.read_csv(OUT / "forecasts.csv")
    cb = F[(F["name"] == "C-b") & F["lead"].isin((1, 2))][["t", "lead", "p"]]
    m = S.merge(cb, on=["t", "lead"], suffixes=("", "_stored"))
    diff = float((m["p"] - m["p_stored"]).abs().max())
    assert diff <= 1e-12, f"refit differs from stored C-b ({diff})"
    S.to_csv(OUT / "shap_cb.csv", index=False)
    lab = V.area_labels(H.load())
    lab = set(lab[lab["area"] == "BL"]["q"])
    V.GROUPS["N1 News"] = list(V.GROUPS["N1 News"]) + ["z_N1R"]
    res = {"refit_equals_stored_max_abs_diff": diff}
    for k in (1, 2):
        s = S[(S["lead"] == k) & (S["q"] >= H.qi("2010-Q1")) & (S["q"] <= H.qi("2026-Q3")) & S["q"].isin(lab)]
        res[f"L{k}"] = {"rows": int(len(s)), "group_shares_pct": V.group_shares(s, CB),
                        "news_era_group_shares_pct": V.group_shares(s[s["t"] >= N.ERA], CB),
                        "by_period": {p: V.group_shares(s[(s["q"] >= H.qi(a)) & (s["q"] <= H.qi(b))], CB)
                                      for p, (a, b) in {"2010-2015Q1": ("2010-Q1", "2015-Q1"),
                                                        "2015Q2-2020": ("2015-Q2", "2020-Q4"),
                                                        "2021-2026Q3": ("2021-Q1", "2026-Q3")}.items()}}
    (OUT / "shap_cb.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({k: (v if not isinstance(v, dict) else v["group_shares_pct"]) for k, v in res.items()}, indent=1))


def _paired(g, a, b):
    g = g[g[a].notna() & g[b].notna()]
    dv = ((g[a] - g["y"]) ** 2 - (g[b] - g["y"]) ** 2).to_numpy(float)
    return {"n_quarters": int(g["q"].nunique()), "brier_cb": float(((g[a] - g["y"]) ** 2).mean()),
            "brier_comp": float(((g[b] - g["y"]) ** 2).mean()), "diff": float(dv.mean()),
            "p_one_sided": float(np.mean(H.boot_mean(g["q"].to_numpy(), dv, H.rp()) >= 0)),
            "acc_cb": float(((g[a] >= .5).astype(int) == g["y"]).mean()),
            "acc_comp": float(((g[b] >= .5).astype(int) == g["y"]).mean())}


def obj4():
    N.check_plan()
    d = H.load()
    lab = V.area_labels(d)
    lab_bl = lab[lab["area"] == "BL"]
    iv2 = pd.read_csv(EXP / "IMPROVE_V2" / "out" / "forecasts.csv")
    h3 = pd.read_csv(EXP / "OBJECTIVES_COMPLETION" / "out" / "h3_forecasts.csv")
    L = pd.read_csv(N.LEADS_FILE)
    F = pd.read_csv(OUT / "forecasts.csv")
    comp = pd.concat([iv2[iv2["name"].isin(["LOGIT", "PSA-only", "NLP-only"])][["name", "t", "lead", "q", "p"]],
                      h3[["name", "t", "lead", "q", "p"]],
                      L[L["name"].isin(["PERSIST", "CLIM"])][["name", "t", "lead", "q", "p"]],
                      F[F["name"] == "C-b"][["name", "t", "lead", "q", "p"]]], ignore_index=True)
    res = {"plan_sha256": N.check_plan(), "comparators_source": "stored IMPROVE_V2 forecasts.csv (LOGIT, PSA-only, "
           "NLP-only), OBJECTIVES_COMPLETION h3_forecasts.csv (LGBM-GOV, LGBM-NLP), IMPROVE_V2_LEADS (PERSIST, CLIM); "
           "none refitted", "leads": {}}
    for k in (1, 2):
        W = R.frame(comp, k, lab_bl)
        era = W[W["t"] >= V.NEWS_ERA]
        Lk = {}
        for tab, names in (("objective4", OBJ4), ("h3", H3)):
            out = {c: _paired(era if c in NLP_ONLY else W, "C-b", c) for c in names}
            hp = R.holm({c: v["p_one_sided"] for c, v in out.items()})
            for c in out:
                out[c]["p_holm"] = hp[c]
                out[c]["significantly_better"] = bool(out[c]["diff"] < 0 and hp[c] < .05)
            Lk[tab] = out
        Lk["h3_rejected"] = all(v["significantly_better"] for v in Lk["h3"].values())
        res["leads"][str(k)] = Lk
    (OUT / "obj4_h3.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    for k, Lk in res["leads"].items():
        print(f"Lead {k}:")
        for tab in ("objective4", "h3"):
            print(f"  {tab}: " + "; ".join(f"{c} {v['diff']:+.3f} (Holm {v['p_holm']:.3f}, n {v['n_quarters']})"
                                         for c, v in Lk[tab].items()))
        print("  H3 rejected:", Lk["h3_rejected"])


def spatial():
    N.check_plan()
    F = pd.read_csv(OUT / "forecasts.csv")
    ev = json.loads((ROOT / "backend" / "data" / "foodinsecurity_engine" / "evaluation.json").read_text(encoding="utf-8"))
    pv = pd.DataFrame(ev["province_poverty"])
    mx = pv["pov_families_2023"].max()
    rows = []
    for k in (1, 2):
        p = float(F[(F["name"] == "C-b") & (F["t"] == SEAL_T) & (F["lead"] == k)]["p"].iloc[0])
        for r in pv.itertuples():
            rows.append({"issue_date": H.issue(SEAL_T), "lead": k, "target_quarter": H.qs(SEAL_T + k),
                         "province_code": r.province_code, "province": r.province, "regional_probability": p,
                         "class": "HIGH" if p >= .5 else "LOW", "pov_families_2023": r.pov_families_2023,
                         "province_score": p * r.pov_families_2023 / mx})
    P = pd.DataFrame(rows)
    v = pd.read_csv(ROOT / "backend" / "data" / "foodinsecurity_engine" / "lgu_vulnerability.csv", dtype={"lgu_code": str})
    v["density"] = v["population_2024"] / v["land_area_km2"]
    nrm = lambda s: (s - s.min()) / (s.max() - s.min())  # noqa: E731
    v["vulnerability_index"] = 0.6 * v.groupby("province")["poverty_value_used"].transform(nrm) + \
        0.4 * v.groupby("province")["density"].transform(nrm)
    lg = []
    for k in (1, 2):
        sc = P[P["lead"] == k].set_index("province")["province_score"]
        x = v[["lgu_code", "lgu_name", "province", "poverty_value_used", "density", "vulnerability_index"]].copy()
        x["lead"], x["target_quarter"] = k, H.qs(SEAL_T + k)
        x["risk_index"] = (x["province"].map(sc) * x["vulnerability_index"]).clip(0, 1)
        x["rank_in_province"] = x.groupby("province")["risk_index"].rank(ascending=False, method="min").astype(int)
        x["rank_region"] = x["risk_index"].rank(ascending=False, method="min").astype(int)
        x["class"] = P[P["lead"] == k]["class"].iloc[0]
        x["disaggregation_label"] = ("vulnerability-weighted estimate (PSA poverty 60%, density 40%, within province) "
                                     "of the regional food-insecurity forecast; not a measured municipal rate")
        lg.append(x)
    LG = pd.concat(lg, ignore_index=True)
    P.to_csv(OUT / "cb_province_2026-10-01.csv", index=False)
    LG.to_csv(OUT / "cb_lgu_2026-10-01.csv", index=False)
    print(P.round(4).to_string())
    print(LG[LG["lead"] == 2].sort_values("rank_region").head(5)[["lgu_name", "province", "risk_index", "rank_region"]]
          .round(4).to_string())


def seal():
    plan = N.check_plan()
    F = pd.read_csv(OUT / "forecasts.csv")
    d = H.load()
    kn = H.known(d, SEAL_T, "BL")
    lab = V.area_labels(d)
    kb = V.known_labels(d, SEAL_T, lab)
    clim = float(kb[kb["area"] == "BL"]["y"].mean())
    rows = []
    for k in (1, 2):
        p = float(F[(F["name"] == "C-b") & (F["t"] == SEAL_T) & (F["lead"] == k)]["p"].iloc[0])
        rows.append({"issue_date": H.issue(SEAL_T), "origin": H.qs(SEAL_T), "lead": k, "target_quarter": H.qs(SEAL_T + k),
                     "model": "C-b (REF + FSSI anomaly)", "p_high": p, "class": "HIGH" if p >= .5 else "LOW",
                     "persist_si": float(kn[-1][1] > H.H_LINE), "clim": clim, "newest_sws_q": H.qs(kn[-1][0]),
                     "newest_sws_reading": kn[-1][1], "newest_sws_published": kn[-1][2], "plan_sha256": plan,
                     "sealed_on": "2026-11-03",
                     "label": "SEALED AFTER THE DEVELOPMENT RESULTS WERE KNOWN; prospective, not an independent test"})
    path = HERE / "sealed_prospective_CB.csv"
    assert not path.exists(), "a sealed file is never overwritten"
    pd.DataFrame(rows).to_csv(path, index=False)
    h = hashlib.sha256(path.read_bytes()).hexdigest()
    (HERE / "SEAL_LEDGER.md").write_text(
        "# NEWS_V2 seal ledger (C-b)\n\nSealed on 2026-11-03, **after the development results were known**. Prospective: "
        "the target quarters have no published SWS round yet. Not an independent test. Sealed files are never edited.\n\n"
        "| File | SHA-256 | Issue date | Leads | Targets | Sealed on |\n|---|---|---|---|---|---|\n"
        f"| `{path.name}` | `{h}` | {rows[0]['issue_date']} | 1, 2 | {rows[0]['target_quarter']}, "
        f"{rows[1]['target_quarter']} | 2026-11-03 |\n", encoding="utf-8")
    print(pd.DataFrame(rows)[["lead", "target_quarter", "p_high", "class", "persist_si", "clim"]].to_string(), "\n", h)


if __name__ == "__main__":
    {"shap": shap, "obj4": obj4, "spatial": spatial, "seal": seal}[sys.argv[1]]()
