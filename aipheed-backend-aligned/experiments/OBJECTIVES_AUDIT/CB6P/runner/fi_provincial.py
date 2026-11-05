"""FI-FOCUS Part B (../PREREGISTRATION_FI.md): C-B6D decomposition on the extended (spliced 2012+) provincial food-CPI
deviation, with Eq. 3 labels from 2013; component report (hunger part vs price part).

    python fi_provincial.py run
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cb6d_model as D  # noqa: E402
import fi_regional as FR  # noqa: E402

M, H, V = D.M, D.H, D.V
HERE, AUD, OUT = D.HERE, D.AUD, D.OUT
RAW = HERE / "data" / "raw"
PROV_NAMES = {"Batangas": "PH040500000", "Cavite": "PH040100000", "Laguna": "PH040200000", "Quezon": "PH040300000",
              "Rizal": "PH040400000"}
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
Q_EXT = H.qi("2013-Q1")
THR = 11.0


def _tidy(f: Path, food: str) -> pd.DataFrame:
    d = pd.read_csv(f, encoding="utf-8-sig")
    d["Geolocation"] = d["Geolocation"].str.strip(". ")
    d = d[d["Geolocation"].isin(PROV_NAMES) & (d["Commodity Description"] == food)]
    m = d.melt(id_vars=["Geolocation", "Commodity Description"], var_name="per", value_name="v")
    m = m[m["per"].str[-3:].isin(MON)]
    m["ym"] = m["per"].str[:4].astype(int) * 12 + m["per"].str[-3:].map({x: i for i, x in enumerate(MON)})
    m["v"] = pd.to_numeric(m["v"], errors="coerce")
    m["province_code"] = m["Geolocation"].map(PROV_NAMES)
    return m.pivot(index="ym", columns="province_code", values="v").sort_index()


def spliced_yoy() -> pd.DataFrame:
    a = _tidy(RAW / "psa_cpi_yoy_2012base_ACPI2.csv", "Food")
    b = _tidy(RAW / "psa_cpi_yoy_2018base_ACP10.csv", "01.1 - FOOD")
    e = pd.read_csv(M.CPI, dtype={"province_code": str})
    e = e[e["commodity"] == "food"].copy()
    e["ym"] = e["reference_month"].str[:4].astype(int) * 12 + e["reference_month"].str[5:7].astype(int) - 1
    e = e.pivot(index="ym", columns="province_code", values="yoy_pct")
    y19, y21 = 2019 * 12, 2021 * 12
    out = pd.concat([a[a.index < y19], b[(b.index >= y19) & (b.index < y21)], e[e.index >= y21]])
    return out[M.PROVS].sort_index()


def dev(Y: pd.DataFrame) -> pd.DataFrame:
    return Y.sub(Y.mean(axis=1), axis=0)


def q_dev_ext(Dm: pd.DataFrame) -> dict:
    out = {}
    for q in range(H.qi("2012-Q1"), H.qi("2026-Q4")):
        ms = [q // 4 * 12 + (q % 4) * 3 + i for i in range(3)]
        if all(m in Dm.index for m in ms):
            w = Dm.loc[ms]
            for p in M.PROVS:
                if w[p].notna().all():
                    out[(p, q)] = (float(w[p].mean()), max(ms))
    return out


def run():
    pre = FR.check()
    M._init()
    d, lab, T = M._G["d"], M._G["lab"], M._G["T"]
    Dm = dev(spliced_yoy())
    qd = q_dev_ext(Dm)
    bl = lab[lab["area"] == "BL"].set_index("q")["H"]
    L = pd.DataFrame([{"province": p, "q": q, "H": float(bl[q]), "D": v, "last_m": lm, "S": float(bl[q]) + 2 * v}
                      for (p, q), (v, lm) in qd.items() if q in bl.index])
    L["y"] = (L["S"] > THR).astype(int)
    old = pd.read_csv(OUT / "cb6p_labels.csv")
    j = old.merge(L, on=["province", "q"], suffixes=("_o", "_n"))
    label_check = {"old_rows": len(old), "matched": len(j), "y_identical": bool((j["y_o"] == j["y_n"]).all()),
                   "D_max_abs_diff": float((j["D_o"] - j["D_n"]).abs().max()),
                   "ext_rows_q_ge_2013": int((L["q"] >= Q_EXT).sum()), "ext_quarters": int(L[L["q"] >= Q_EXT]["q"].nunique()),
                   "ext_high_share": float(L[L["q"] >= Q_EXT]["y"].mean())}
    print(label_check, flush=True)
    L.to_csv(OUT / "fi_labels_ext.csv", index=False)
    sig = T[T["area"] == "BL"].set_index(["t", "lead"])["sigma_h"].to_dict()
    D1 = {t: M.d1(Dm, t) for t in range(H.qi("2012-Q2"), H.qi("2026-Q3") + 1)}
    RF = pd.read_csv(OUT / "fi_regional_fits.csv")
    REG = {"C-B6E": D.regional("C-B6E"), "C-B6": D.regional("C-B6"),
           **{n: {(int(r.t), int(r.lead)): r for r in RF[RF["name"] == n].itertuples()} for n in ("NP", "PO")}}

    def dmodel(t, k):
        X, Y = [], []
        for t2 in D1:
            if t2 >= t:
                continue
            for p in M.PROVS:
                v = qd.get((p, t2 + k))
                if v is None or v[1] > M.m_avail(t) or np.isnan(D1[t2][p]):
                    continue
                X.append(D1[t2][p])
                Y.append(v[0])
        if len(Y) < D.MIN_PAIRS:
            known = [v[0] for v in qd.values() if v[1] <= M.m_avail(t)]
            return None, (float(np.sqrt(np.mean(np.square(known)))) if len(known) >= 5 else D.SD_DEFAULT)
        X, Y = np.asarray(X), np.asarray(Y)
        b = float(X @ Y / (X @ X))
        return b, float(np.sqrt(np.mean((Y - b * X) ** 2)))

    ARMS = {"C-B6D-E-X": "C-B6E", "NP-P-X": "NP", "PO-P-X": "PO"}
    rows, comp_rows = [], []
    origins = list(range(H.qi("2012-Q3"), H.qi("2026-Q3") + 1))
    for t in origins:
        kb = V.known_labels(d, t, lab)
        kb = kb[kb["area"] == "BL"]
        Lk = L[L["q"].isin(kb["q"]) & (L["last_m"] <= M.m_avail(t))].sort_values("q")
        clim = float(Lk["y"].mean()) if len(Lk) else (float((kb["H"] > THR).mean()) if len(kb) else 0.5)
        base = float(kb.sort_values("q")["H"].iloc[-1] > THR) if len(kb) else 0.5
        pers = {p: (float(Lk[Lk["province"] == p]["y"].iloc[-1]) if (Lk["province"] == p).any() else base) for p in M.PROVS}
        for k in D.LEADS:
            b, sd = dmodel(t, k)
            r6 = REG["C-B6"].get((t, k))
            for p in M.PROVS:
                rows.append({"name": "PERSIST-X", "t": t, "lead": k, "q": t + k, "province": p, "p": pers[p]})
                rows.append({"name": "CLIM-X", "t": t, "lead": k, "q": t + k, "province": p, "p": clim})
                if r6 is not None:
                    rows.append({"name": "C-B6-R", "t": t, "lead": k, "q": t + k, "province": p, "p": float(r6.p)})
            for name, rn in ARMS.items():
                r = REG[rn].get((t, k))
                if r is None or pd.isna(r.p) or (t, k) not in sig:
                    continue
                sh = float(sig[(t, k)])
                mu = D.H_LINE + sh * norm.ppf(np.clip(float(r.p), 1e-3, 1 - 1e-3))
                s = float(np.sqrt(sh ** 2 + 4 * sd ** 2))
                for p in M.PROVS:
                    dh = 0.0 if b is None or np.isnan(D1[t][p]) else b * D1[t][p]
                    rows.append({"name": name, "t": t, "lead": k, "q": t + k, "province": p,
                                 "p": float(norm.cdf((mu + 2 * dh - THR) / s)), "D_hat": dh, "b": b, "sigma_D": sd,
                                 "p_hunger_part": float(norm.cdf((mu - THR) / sh))})
                    if name == "C-B6D-E-X":
                        shp = {c[5:]: float(getattr(r, c)) for c in r._fields if c.startswith("shap_") and pd.notna(getattr(r, c))}
                        tot = sum(abs(v) for v in shp.values()) or 1.0
                        reg_term = abs(mu - THR) / s
                        part = lambda cs: sum(reg_term * abs(shp.get(c, 0.0)) / tot for c in cs)  # noqa: E731
                        comp_rows.append({"t": t, "lead": k, "q": t + k, "province": p,
                                          "hunger": part(FR.HUNGER), "regional_price": part(FR.PRICE),
                                          "province_price": abs(2 * dh / s),
                                          "employment": part(["E1"]), "ofw_remittance": part(["E2"]),
                                          "other_nonprice": part(["ONI_last", "ONI_max12", "tc_mean", "R_C3", "R_C4",
                                                                  "ST1", "ST2", "z_N1R", "lead"])})
    F = pd.DataFrame(rows)
    C = pd.DataFrame(comp_rows)
    F.to_csv(OUT / "fi_provincial_fits.csv", index=False)

    # ------------------------------------------------------------------ scoring
    W0 = F.pivot_table(index=["t", "lead", "q", "province"], columns="name", values="p").reset_index()
    W0 = W0.merge(L[["province", "q", "y"]], on=["province", "q"])
    Dd = pd.read_csv(OUT / "cb6d_fits.csv")
    Dd = Dd[Dd["name"] == "C-B6D-E"][["t", "lead", "province", "p"]].rename(columns={"p": "C-B6D-E"})
    P2 = pd.read_csv(OUT / "cb6p2_fits.csv")[["t", "lead", "province", "p"]].rename(columns={"p": "C-B6P2"})
    W0 = W0.merge(Dd, on=["t", "lead", "province"], how="left").merge(P2, on=["t", "lead", "province"], how="left")
    Rr = H.rp()
    arms = ["C-B6D-E-X", "NP-P-X", "PO-P-X", "C-B6-R", "PERSIST-X", "CLIM-X"]
    res = {"prereg_sha256": pre, "label_check": label_check, "THR": THR, "B_old": {}, "B_ext": {}, "algorithm3_ext": {}}
    fam = {}
    for k in D.LEADS:
        Wk = W0[W0["lead"] == k]
        ext = Wk[Wk["q"] >= Q_EXT].dropna(subset=arms)
        E = {}
        for a in arms:
            if ext["y"].nunique() < 2:
                continue
            m = M.metrics(ext["y"], ext[a])
            if k <= 2:
                h = ext.copy()
                h[Rr.P], h["target"] = h[a], h["q"].map(H.qs)
                h["PERSIST-SI_p"], h["CLIM_p"], h["ALWAYS-LOW_p"] = h["PERSIST-X"], h["CLIM-X"], 0.0
                rl = Rr.rules(h)
                m["rules"] = {x.split()[0]: {"pass": v["pass"], "value": str(v["value"])} for x, v in rl.items()}
                m["failed"] = [x.split()[0] for x, v in rl.items() if not v["pass"]]
            E[a] = m
        res["B_ext"][str(k)] = E
        if k <= 2:
            for b in ("PERSIST-X", "CLIM-X", "C-B6-R", "PO-P-X", "NP-P-X"):
                fam[(k, b)] = M.paired(ext, "C-B6D-E-X", b)
            o = Wk[Wk["q"] >= M.Q0].dropna(subset=["C-B6D-E-X", "C-B6D-E", "C-B6P2"])
            res["B_old"][str(k)] = {"n": int(len(o)), **{a: M.metrics(o["y"], o[a]) for a in ("C-B6D-E-X", "C-B6D-E", "C-B6P2")},
                                    "X_vs_C-B6D-E": M.paired(o, "C-B6D-E-X", "C-B6D-E"),
                                    "X_vs_C-B6P2": M.paired(o, "C-B6D-E-X", "C-B6P2")}
            # components (B-ext rows of C-B6D-E-X)
            fx = F[(F["name"] == "C-B6D-E-X") & (F["lead"] == k) & (F["q"] >= Q_EXT)]
            hq = fx.drop_duplicates("q").merge(lab[lab["area"] == "BL"][["q", "H"]], on="q")
            hunger_acc = float(((hq["p_hunger_part"] >= .5) == (hq["H"] > THR)).mean())
            fd = fx.merge(L[["province", "q", "D"]], on=["province", "q"])
            fd = fd[fd["D_hat"].abs() > 0]
            sign_acc = float((np.sign(fd["D_hat"]) == np.sign(fd["D"])).mean()) if len(fd) else None
            c = C[(C["lead"] == k) & (C["q"] >= Q_EXT)].drop(columns=["t", "lead", "q", "province"])
            shp = c.div(c.sum(axis=1).replace(0, np.nan), axis=0) * 100
            res["B_ext"][str(k)]["components"] = {
                "hunger_part_accuracy_vs_measured_BL_hunger_gt_11": hunger_acc, "hunger_quarters": int(len(hq)),
                "price_part_sign_accuracy": sign_acc, "price_part_rows": int(len(fd)),
                "contribution_share_pct": {x: float(shp[x].mean()) for x in shp.columns},
                "price_total_share_pct": float((shp["regional_price"] + shp["province_price"]).mean()),
                "corr_D_hat_D": float(np.corrcoef(fd["D_hat"], fd["D"])[0, 1]) if len(fd) > 2 else None}
    hp = M.holm({key: v["p_one_sided"] for key, v in fam.items()})
    res["holm_family_10"] = [{"lead": k, "comparator": b, **v, "p_holm": hp[(k, b)],
                              "significant": bool(v["diff"] < 0 and hp[(k, b)] < .05)} for (k, b), v in fam.items()]
    for a in arms:
        mx = 0
        for k in D.LEADS:
            m = res["B_ext"][str(k)].get(a)
            if m and m["accuracy"] >= .75 and mx == k - 1:
                mx = k
        res["algorithm3_ext"][a] = mx
    bo = res["B_old"]
    res["decisions"] = {
        "B1_extended_history_improves (X<C-B6D-E on B-old)": all(bo[k]["X_vs_C-B6D-E"]["diff"] < 0 and
                                                                  bo[k]["X_vs_C-B6D-E"]["p_one_sided"] < .10 for k in ("1", "2")),
        "B2_reliable_R1_R7": {k: not res["B_ext"][k]["C-B6D-E-X"]["failed"] for k in ("1", "2")},
        "B3_nonprice_add (X<PO-P-X on B-ext)": all(fam[(k, "PO-P-X")]["diff"] < 0 and fam[(k, "PO-P-X")]["p_one_sided"] < .10
                                                   for k in (1, 2))}
    (OUT / "fi_provincial_results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    for k in ("1", "2"):
        print(f"=== Lead {k}  B-ext ({res['B_ext'][k]['C-B6D-E-X']['n']} rows)")
        for a in arms:
            m = res["B_ext"][k][a]
            print(f"{a:10s} acc {m['accuracy']:.3f} bal {m['balanced']:.3f} P {m['precision']:.3f} R {m['recall']:.3f} "
                  f"F1 {m['f1']:.3f} AUC {m['auc']:.3f} Brier {m['brier']:.4f} failed {m['failed']}")
        print("   components:", {x: (round(v, 3) if isinstance(v, float) else v) for x, v in res["B_ext"][k]["components"].items()
                                  if x != "contribution_share_pct"})
        print("   shares %:", {x: round(v, 1) for x, v in res["B_ext"][k]["components"]["contribution_share_pct"].items()})
        b = res["B_old"][k]
        print(f"   B-old n {b['n']}: X acc {b['C-B6D-E-X']['accuracy']:.3f} Brier {b['C-B6D-E-X']['brier']:.4f} | "
              f"C-B6D-E acc {b['C-B6D-E']['accuracy']:.3f} Brier {b['C-B6D-E']['brier']:.4f} | "
              f"X-vs-D-E {b['X_vs_C-B6D-E']['diff']:+.4f} p {b['X_vs_C-B6D-E']['p_one_sided']:.3f} | "
              f"X-vs-P2 {b['X_vs_C-B6P2']['diff']:+.4f} p {b['X_vs_C-B6P2']['p_one_sided']:.3f}")
    for f in res["holm_family_10"]:
        print(f"   L{f['lead']} vs {f['comparator']:9s} dBrier {f['diff']:+.4f} CI {f['ci95'][0]:+.3f}..{f['ci95'][1]:+.3f} "
              f"p {f['p_one_sided']:.3f} Holm {f['p_holm']:.3f} sig {f['significant']}")
    print("Algorithm 3 (B-ext):", res["algorithm3_ext"])
    print("Decisions:", res["decisions"])


if __name__ == "__main__":
    {"run": run}[sys.argv[1]]()
