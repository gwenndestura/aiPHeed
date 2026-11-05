"""C-B6D (../PREREGISTRATION_D.md, hash checked): decomposed Eq. 3 province-quarter model.

P(HIGH) = Phi((mu_H + 2*D_hat - THR) / sqrt(sigma_H^2 + 4*sigma_D^2)); mu_H from a regional model's walk-forward
P(BL hunger > 11.3%) and sigma_h; D_hat from the province's latest known food-price deviation (slope fitted on past
pairs only).

    python cb6d_model.py run     # fits (no tree fitting needed), metrics, R1-R7, Holm, decisions -> ../out/cb6d_*.{csv,json}
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cb6p_model as M  # noqa: E402

H, V = M.H, M.V
HERE, AUD, EXP, OUT = M.HERE, M.AUD, M.EXP, M.OUT
PLAN = HERE / "PREREGISTRATION_D.md"
H_LINE, MIN_PAIRS, SD_DEFAULT = 11.3, 10, 2.0
LEADS = list(range(1, 9))
SEC_GROUPS = {"market": ["R_food_yoy", "R_head_yoy", "R_food_mom", "R_rice_yoy"] + H.WORLD,
              "climate": ["ONI_last", "ONI_max12", "tc_mean", "R_C3"], "fish_kill": ["R_C4"],
              "hunger": ["h_last", "h_change", "h_mean4", "true_h", "pi_H4L"], "news": ["z_N1R"], "lead": ["lead"],
              "employment": ["E1"], "ofw_remittance": ["E2"], "supply": ["ST1", "ST2"]}


def check() -> str:
    b = PLAN.read_bytes().replace(b"\r\n", b"\n")
    body, last = b.rstrip(b"\n").rsplit(b"\n", 1)
    h = hashlib.sha256(body + b"\n").hexdigest()
    assert last.startswith(b"PLAN-SHA256: ") and last.split()[1].decode() == h, "C-B6D pre-registration changed"
    return h


def dev_monthly_any(commodity: str) -> pd.DataFrame:
    c = pd.read_csv(M.CPI, dtype={"province_code": str})
    c = c[c["commodity"] == commodity].assign(commodity="food")
    return M.dev_monthly(c)


def regional(name: str) -> dict:
    if name == "C-B6E":
        f = pd.read_csv(AUD / "FIXES_2026-11-04" / "out" / "cb6e_fits.csv")
    elif name == "C-B6":
        f = pd.read_csv(AUD / "out" / "cb6_fits.csv")
    else:
        f = pd.read_csv(EXP / "IMPROVE_V2" / "out" / "forecasts.csv")
        f = f[f["name"] == name]
    return {(int(r.t), int(r.lead)): r for r in f.itertuples()}


def run():
    pre = check()
    M._init()
    d, lab, L, thr, T = M._G["d"], M._G["lab"], M._G["L"], M._G["thr"], M._G["T"]
    assert abs(thr - 11.0) < 1e-12
    Dm, Dh = M._G["Dm"], dev_monthly_any("all_items")
    qd = M.q_dev(Dm)                                   # (p, q) -> (D, last month)
    sig = T[T["area"] == "BL"].set_index(["t", "lead"])["sigma_h"].to_dict()
    origins = list(range(M.FIRST, H.qi("2026-Q3") + 1))
    D1 = {t: M.d1(Dm, t) for t in range(H.qi("2019-Q1"), H.qi("2026-Q3") + 1)}
    DH1 = {t: M.d1(Dh, t) for t in D1}
    REG = {n: regional(n) for n in ("C-B6E", "C-B6", "PSA-only", "NLP-only")}

    def dmodel(t, k, ex):
        X, Y = [], []
        for t2 in D1:
            if t2 >= t:
                continue
            for p in M.PROVS:
                v = qd.get((p, t2 + k))
                if v is None or v[1] > M.m_avail(t) or np.isnan(D1[t2][p]):
                    continue
                if ex and np.isnan(DH1[t2][p]):
                    continue
                X.append([D1[t2][p]] + ([DH1[t2][p]] if ex else []))
                Y.append(v[0])
        if len(Y) < MIN_PAIRS:
            known = [v[0] for (p, q), v in qd.items() if v[1] <= M.m_avail(t)]
            return None, (float(np.sqrt(np.mean(np.square(known)))) if len(known) >= 5 else SD_DEFAULT), len(Y)
        X, Y = np.asarray(X), np.asarray(Y)
        b, *_ = np.linalg.lstsq(X, Y, rcond=None)
        return b, float(np.sqrt(np.mean((Y - X @ b) ** 2))), len(Y)

    ARMS = {"C-B6D-E": ("C-B6E", "D1"), "C-B6D": ("C-B6", "D1"), "C-B6D-EX": ("C-B6E", "EX"),
            "PSA-only-P": ("PSA-only", "D1"), "NLP-only-P": ("NLP-only", "none")}
    rows, contrib = [], []
    for t in origins:
        kb = V.known_labels(d, t, lab)
        kb = kb[kb["area"] == "BL"]
        Lk = L[L["q"].isin(kb["q"]) & (L["last_m"] <= M.m_avail(t))]
        clim = float(Lk["y"].mean()) if len(Lk) else float((kb["H"] > thr).mean()) if len(kb) else 0.5
        for k in LEADS:
            models = {ex: dmodel(t, k, ex) for ex in (False, True)}
            for name, (rn, pm) in ARMS.items():
                r = REG[rn].get((t, k))
                if r is None or pd.isna(r.p) or (t, k) not in sig:
                    continue
                sh = float(sig[(t, k)])
                mu = H_LINE + sh * norm.ppf(np.clip(float(r.p), 1e-3, 1 - 1e-3))
                b, sd, npairs = models[pm == "EX"]
                for p in M.PROVS:
                    if pm == "none" or b is None or np.isnan(D1[t][p]) or (pm == "EX" and np.isnan(DH1[t][p])):
                        dh = 0.0
                    else:
                        dh = float(b[0] * D1[t][p] + (b[1] * DH1[t][p] if pm == "EX" else 0.0))
                    s = float(np.sqrt(sh ** 2 + 4 * sd ** 2))
                    z = (mu + 2 * dh - thr) / s
                    rows.append({"name": name, "t": t, "lead": k, "q": t + k, "province": p, "p": float(norm.cdf(z)),
                                 "p_R": float(r.p), "sigma_H": sh, "D_hat": dh, "sigma_D": sd, "n_pairs": npairs,
                                 "b": None if b is None else [float(x) for x in b], "CLIM": clim})
                    if name == "C-B6D-E":
                        reg_term, prov_term = (mu - thr) / s, 2 * dh / s
                        shp = {c[5:]: float(getattr(r, c)) for c in r._fields if c.startswith("shap_")
                               and pd.notna(getattr(r, c))}
                        tot = sum(abs(v) for v in shp.values()) or 1.0
                        g = {gn: sum(np.sign(shp.get(c, 0.0)) * abs(reg_term) * abs(shp.get(c, 0.0)) / tot for c in cs)
                             for gn, cs in SEC_GROUPS.items()}
                        g["province_price"] = prov_term
                        contrib.append({"t": t, "lead": k, "q": t + k, "province": p, **{f"c_{x}": v for x, v in g.items()}})
    F = pd.DataFrame(rows)
    C = pd.DataFrame(contrib)
    F.to_csv(OUT / "cb6d_fits.csv", index=False)
    C.to_csv(OUT / "cb6d_contrib.csv", index=False)

    # ---------------------------------------------------------------- scoring
    P1 = pd.read_csv(OUT / "cb6p_fits.csv")
    P2 = pd.read_csv(OUT / "cb6p2_fits.csv")
    R6 = pd.read_csv(AUD / "out" / "cb6_fits.csv")[["t", "lead", "p"]]
    base = pd.concat([P1[P1["name"].isin(["PERSIST", "LOGIT"])][["name", "t", "lead", "q", "province", "p"]],
                      P2[["name", "t", "lead", "q", "province", "p"]],
                      P1[P1["name"] == "PERSIST"][["t", "lead", "q", "province"]].merge(R6, on=["t", "lead"]).assign(name="C-B6-R"),
                      F[["name", "t", "lead", "q", "province", "p"]]], ignore_index=True)
    W0 = base.pivot_table(index=["t", "lead", "q", "province"], columns="name", values="p").reset_index()
    W0 = W0.merge(F[F["name"] == "C-B6D-E"][["t", "lead", "province", "CLIM"]], on=["t", "lead", "province"], how="left")
    W0 = W0.merge(L[["province", "q", "y"]], on=["province", "q"], how="inner")
    W0 = W0[W0["q"] >= M.Q0]
    mixed_q = set(L.groupby("q")["y"].agg(lambda s: 0 < s.sum() < len(s)).pipe(lambda s: s[s].index))
    arms = ["C-B6D-E", "C-B6D", "C-B6D-EX", "PSA-only-P", "NLP-only-P", "C-B6P2", "C-B6-R", "PERSIST", "LOGIT"]
    Rr = H.rp()
    res = {"prereg_sha256": pre, "label": "DEVELOPMENT EVIDENCE; Eq. 3 province-quarters 2021-Q1..2026-Q3",
           "THR": thr, "mixed_label_quarters": len(mixed_q), "leads": {}, "algorithm3": {}}
    fam = {}
    for k in LEADS:
        W = W0[W0["lead"] == k]
        Lk = {}
        for a in arms:
            g = W.dropna(subset=[a])
            if len(g) == 0 or g["y"].nunique() < 2:
                continue
            m = M.metrics(g["y"], g[a])
            gm = g[g["q"].isin(mixed_q)]
            m["accuracy_mixed_quarters"] = float(((gm[a] >= .5) == gm["y"]).mean()) if len(gm) else None
            m["quarters_calls_differ"] = int(g.assign(c=g[a] >= .5).groupby("q")["c"].nunique().gt(1).sum())
            if k <= 2:
                h = g.dropna(subset=["PERSIST", "CLIM"]).copy()
                h[Rr.P], h["target"] = h[a], h["q"].map(H.qs)
                h["PERSIST-SI_p"], h["CLIM_p"], h["ALWAYS-LOW_p"] = h["PERSIST"], h["CLIM"], 0.0
                rl = Rr.rules(h)
                m["rules"] = {x.split()[0]: {"pass": v["pass"], "value": str(v["value"])} for x, v in rl.items()}
                m["failed"] = [x.split()[0] for x, v in rl.items() if not v["pass"]]
            Lk[a] = m
        if k <= 2:
            for b in ("PERSIST", "LOGIT", "PSA-only-P", "NLP-only-P", "C-B6P2", "C-B6-R"):
                fam[(k, b)] = {**M.paired(W.dropna(subset=["C-B6D-E", b]), "C-B6D-E", b),
                               "n": int(W.dropna(subset=["C-B6D-E", b]).shape[0])}
            Lk["secondary"] = {"C-B6D-E_vs_C-B6D": M.paired(W.dropna(subset=["C-B6D-E", "C-B6D"]), "C-B6D-E", "C-B6D"),
                               "C-B6D-EX_vs_C-B6D-E": M.paired(W.dropna(subset=["C-B6D-EX", "C-B6D-E"]), "C-B6D-EX", "C-B6D-E"),
                               "C-B6D-E_vs_C-B6P2": M.paired(W.dropna(subset=["C-B6D-E", "C-B6P2"]), "C-B6D-E", "C-B6P2")}
            c = C[(C["lead"] == k) & (C["q"] >= M.Q0)]
            cc = c.filter(like="c_").abs()
            sh = cc.div(cc.sum(axis=1).replace(0, np.nan), axis=0) * 100
            Lk["C-B6D-E_contribution_share_pct_mean"] = {x[2:]: float(sh[x].mean()) for x in cc.columns}
            Lk["C-B6D-E_nonzero_share"] = {x[2:]: float((c[x].abs() > 1e-12).mean()) for x in cc.columns}
        res["leads"][str(k)] = Lk
    hp = M.holm({key: v["p_one_sided"] for key, v in fam.items()})
    res["holm_family_12"] = [{"lead": k, "comparator": b, **v, "p_holm": hp[(k, b)],
                              "significant": bool(v["diff"] < 0 and hp[(k, b)] < .05)} for (k, b), v in fam.items()]
    for a in arms:
        mx = 0
        for k in LEADS:
            m = res["leads"][str(k)].get(a)
            if m and m["accuracy"] >= .75 and mx == k - 1:
                mx = k
        res["algorithm3"][a] = mx
    l1, l2 = res["leads"]["1"], res["leads"]["2"]
    s1, s2 = l1["secondary"], l2["secondary"]
    res["decisions"] = {
        "improves_on_C-B6P2": all(x["C-B6D-E_vs_C-B6P2"]["diff"] < 0 and x["C-B6D-E_vs_C-B6P2"]["p_one_sided"] < .10
                                  for x in (s1, s2)) and all(x["C-B6D-E"]["accuracy"] >= x["C-B6P2"]["accuracy"] for x in (l1, l2)),
        "meets_paper_targets": all(x["C-B6D-E"]["accuracy"] >= .75 and x["C-B6D-E"]["f1"] >= .75 for x in (l1, l2))
                               and (l1["C-B6D-E"]["auc"] or 0) >= .80,
        "reliable_R1_R7": {k: not res["leads"][k]["C-B6D-E"]["failed"] for k in ("1", "2")},
        "employment_ofw_predictive_value": all(x["C-B6D-E_vs_C-B6D"]["diff"] < 0 and x["C-B6D-E_vs_C-B6D"]["p_one_sided"] < .10
                                               for x in (s1, s2)),
        "headline_adds_value": all(x["C-B6D-EX_vs_C-B6D-E"]["diff"] < 0 and x["C-B6D-EX_vs_C-B6D-E"]["p_one_sided"] < .10
                                   for x in (s1, s2))}
    (OUT / "cb6d_results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    for k in ("1", "2"):
        print(f"--- Lead {k}")
        for a in arms:
            m = res["leads"][k].get(a)
            if m:
                print(f"{a:11s} n {m['n']:3d} acc {m['accuracy']:.3f} bal {m['balanced']:.3f} P {m['precision']:.3f} "
                      f"R {m['recall']:.3f} F1 {m['f1']:.3f} AUC {m['auc']:.3f} Brier {m['brier']:.4f} "
                      f"mixedAcc {m['accuracy_mixed_quarters']:.3f} differ {m['quarters_calls_differ']:2d} failed {m['failed']}")
        for x, v in res["leads"][k]["secondary"].items():
            print(f"   {x}: dBrier {v['diff']:+.4f} p {v['p_one_sided']:.3f}")
        print("   contribution %:", {x: round(v, 1) for x, v in res["leads"][k]["C-B6D-E_contribution_share_pct_mean"].items()})
        print("   nonzero:", {x: round(v, 2) for x, v in res["leads"][k]["C-B6D-E_nonzero_share"].items()})
    for f in res["holm_family_12"]:
        print(f"   L{f['lead']} vs {f['comparator']:10s} n {f['n']} dBrier {f['diff']:+.4f} p {f['p_one_sided']:.3f} "
              f"Holm {f['p_holm']:.3f} sig {f['significant']}")
    print("Algorithm 3:", res["algorithm3"])
    print("Decisions:", res["decisions"])


if __name__ == "__main__":
    {"run": run}[sys.argv[1]]()
