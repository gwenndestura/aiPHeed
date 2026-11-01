"""Y15 Investigation C (EXPERIMENT_PLAN.md sections 3-5): five candidates vs hunger persistence H1 for TFI-2 on
independent years (targets 2001-Q1..2020-Q4), the frozen gate, and the seven-rule table on the 17 official FIRI
Lead-2 targets (descriptive unless a candidate passes the gate).
Writes out/dev_rows.csv, out/dev_results.json, out/confirm_results.json, out/confirm_rows.csv.

    python -B run.py
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
import warnings
from pathlib import Path

sys.dont_write_bytecode = True

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import norm  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
Y15 = HERE.parent
RES = Y15.parent
EXP = RES.parent
OUT = Y15 / "out"
sys.path.insert(0, str(RES / "y14_food_insecurity_forecast" / "runner"))
sys.path.insert(0, str(EXP / "FIRI_LEAD2_FEASIBILITY" / "runner"))
import run as Y14  # noqa: E402  (frame(), metrics(), boot(), holm(), calib(): read-only reuse)

R, HM = Y14.R, Y14.HM
DRIVERS = ["A2", "A3", "C1", "C2", "C3", "C4", "E1", "E2"]
CONT = ("A2", "A3", "C2", "C3", "C4", "E1", "E2")
DOMS = {"A": ("A2", "A3"), "C": ("C1", "C2", "C3", "C4"), "E": ("E1", "E2"), "H": ("H1",), "V": ("V1",)}
# plan IDs C1..C5 -> code names (the plan IDs clash with the climate indicators C1..C4)
CANDS = ("FIRIR", "SCREEN", "KAL", "CONT", "REMIT")
DEV_FIRST, DEV_LAST = R.qi("2001-Q1"), R.qi("2020-Q4")


def plan_ok():
    want = (HERE / "PLAN_SHA256.txt").read_text().split()[0]
    assert hashlib.sha256((Y15 / "EXPERIMENT_PLAN.md").read_bytes()).hexdigest() == want, "plan changed after freezing"


def e2_series() -> dict[int, float]:
    r = pd.read_csv(Y15 / "data_acquired" / "remittances_quarterly_usd_mn.csv")
    s = pd.Series(r["personal_transfers"].to_numpy(float), index=r["quarter"].map(R.qi).to_numpy())
    out = {}
    for t in range(R.qi("1997-Q1"), R.qi("2027-Q1")):
        q = t - 2
        if q in s.index and q - 4 in s.index and s[q - 4] > 0:
            out[t] = -100 * (s[q] / s[q - 4] - 1)
    return out


def frame() -> pd.DataFrame:
    ind = pd.read_csv(RES / "y14_food_insecurity_forecast" / "out" / "indicators.csv")
    e2 = e2_series()
    ind["E2"] = ind["t"].map(e2)
    d = Y14.frame(ind)                      # outcome, H_last, m_known, CLIM, PERSIST, pub_target (point in time)
    # C1 FIRI-R: explicit missingness, domain abstention, >= 4 domains, equal weights
    for k in CONT:
        sc = []
        for t in d.index:
            prior = d.loc[d.index < t, k].dropna().to_numpy()
            x = d.loc[t, k]
            sc.append(np.nan if pd.isna(x) or len(prior) < 8 else float(((prior < x).sum() + 0.5 * (prior == x).sum()) / len(prior)))
        d[f"r_{k}"] = sc
    for k in ("C1", "H1", "V1"):
        d[f"r_{k}"] = d[k].clip(0, 1)
    doms = {}
    for dm, ks in DOMS.items():
        s = d[[f"r_{k}" for k in ks]]
        doms[dm] = s.mean(1, skipna=True).where(s.notna().sum(1) >= math.ceil(len(ks) / 2))
    D = pd.DataFrame(doms)
    d["FIRIR"] = D.mean(1, skipna=True).where(D.notna().sum(1) >= 4)
    d["FIRIR_domains"] = D.notna().sum(1)
    for dm in DOMS:
        d[f"rdom_{dm}"] = D[dm]
    return d


def screen(tr: pd.DataFrame) -> list[str]:
    keep = []
    dev = (tr["H_last"] - tr["m_known"]).to_numpy(float)
    dy = (tr["H_target"] - tr["H_last"]).to_numpy(float)
    for x in DRIVERS:
        m = tr[x].notna().to_numpy()
        if m.sum() < 20:
            continue
        X = np.column_stack([np.ones(m.sum()), dev[m], tr[x].to_numpy(float)[m]])
        b, *_ = np.linalg.lstsq(X, dy[m], rcond=None)
        e = dy[m] - X @ b
        s2 = float(e @ e) / (m.sum() - 3)
        cov = s2 * np.linalg.inv(X.T @ X)
        tval = b[2] / math.sqrt(cov[2, 2])
        if abs(tval) >= 2:
            keep.append((abs(tval), x))
    return [x for _, x in sorted(keep, reverse=True)[:2]]


def logit(tr, x0, cols):
    X = np.column_stack([Y14.z(tr["H1"])] + [tr[c].to_numpy(float) for c in cols]) if cols else Y14.z(tr["H1"]).reshape(-1, 1)
    xx = np.r_[Y14.z([x0["H1"]]), [x0[c] for c in cols]].reshape(1, -1)
    mu = np.nanmean(X, 0)
    X = np.where(np.isnan(X), mu, X)
    xx = np.where(np.isnan(xx), mu, xx)
    sd = X.std(0)
    sd[sd == 0] = 1
    return float(LogisticRegression(C=1.0, max_iter=3000).fit((X - mu) / sd, tr["y"].to_numpy(int)).predict_proba((xx - mu) / sd)[0, 1])


def rw_sigma(t: int, h: int) -> float:
    pr = R.pairs(tuple(R.AREAS), R.issue(t), h)
    return math.sqrt(float(np.mean((pr["y1"] - pr["y0"]) ** 2)))


def crps(y, mu, s):
    zz = (y - mu) / s
    return float(s * (zz * (2 * norm.cdf(zz) - 1) + 2 * norm.pdf(zz) - 1 / math.sqrt(math.pi)))


def fit_predict(d: pd.DataFrame, t: int) -> dict:
    iss = R.issue(t)
    tr = d[(d.index < t) & d["y"].notna() & (d["pub_target"] < iss) & d["H1"].notna()].copy()
    x0 = d.loc[t]
    y = tr["y"].to_numpy(int)
    ok = len(tr) >= 30 and y.sum() >= 5 and (1 - y).sum() >= 5
    keep = screen(tr) if len(tr) >= 30 else []
    out = {"trainRows": len(tr), "kept": "|".join(keep), "fallback": int(not ok)}
    out["SCREEN"] = logit(tr, x0, keep) if ok else float(x0["H1"])
    out["REMIT"] = logit(tr, x0, ["E2"]) if ok and tr["E2"].notna().sum() >= 20 else float(x0["H1"])
    out["KAL"] = HM.kalman("BL", int(t), 2, tuple(R.AREAS))
    # C4 continuous
    if len(tr) >= 30:
        cols = keep
        A = np.column_stack([np.ones(len(tr)), (tr["H_last"] - tr["m_known"]).to_numpy(float)] + [tr[c].to_numpy(float) for c in cols])
        mu_c = np.nanmean(A, 0)
        A = np.where(np.isnan(A), mu_c, A)
        a = np.r_[1.0, x0["H_last"] - x0["m_known"], [x0[c] for c in cols]]
        a = np.where(np.isnan(a), mu_c, a)
        dy = (tr["H_target"] - tr["H_last"]).to_numpy(float)
        b = np.linalg.lstsq(A, dy, rcond=None)[0]
        sig = max(math.sqrt(float(np.mean((dy - A @ b) ** 2))), 0.5)
        mu = float(x0["H_last"] + a @ b)
    else:
        mu, sig = float(x0["H_last"]), rw_sigma(t, int(x0["h_true"]))
    out.update(CONT=float(norm.cdf((mu - R.H_LINE) / sig)), CONT_mu=mu, CONT_sig=sig)
    out["RW_mu"], out["RW_sig"] = float(x0["H_last"]), rw_sigma(t, int(x0["h_true"]))
    known = list(R.known("BL", iss).values())
    out["CLIM_mu"], out["CLIM_sig"] = float(np.mean(known)), float(np.std(known, ddof=1))
    return out


def main():
    plan_ok()
    d = frame()
    preds = [{"t": t, **fit_predict(d, t)} for t in d.index if t + 2 >= DEV_FIRST and pd.notna(d.loc[t, "H1"])]
    d = d.join(pd.DataFrame(preds).set_index("t"))
    d["target"] = [R.qs(t + 2) for t in d.index]
    dev = d[(d.index + 2 >= DEV_FIRST) & (d.index + 2 <= DEV_LAST) & d["y"].notna() & d["H1"].notna()].copy()
    res = {"rows": len(dev), "period": f"{dev['target'].min()}..{dev['target'].max()}", "prevalence": float(dev["y"].mean()),
           "fallbackRows": int(dev["fallback"].sum()), "FIRIR_issued": int(dev["FIRIR"].notna().sum()),
           "FIRIR_domainCounts": dev["FIRIR_domains"].value_counts().to_dict(),
           "C2_keptFrequency": pd.Series("|".join(dev["kept"]).split("|")).replace("", "(none)").value_counts().to_dict()}
    for c in ("PERSIST", "CLIM", "H1") + CANDS:
        g = dev[dev[c].notna()]
        res[c] = {**Y14.metrics(g["y"], g[c]), "calibration": Y14.calib(g["y"], g[c])}
    res["vsH1"] = {}
    for c in ("PERSIST", "CLIM") + CANDS:
        g = dev[dev[c].notna()]
        res["vsH1"][c] = {"rows": len(g), "iid": Y14.boot(g, c, "H1"), "block4": Y14.boot(g, c, "H1", 4),
                          "H1_balanced_sameRows": Y14.metrics(g["y"], g["H1"])["balanced"]}
    hp = Y14.holm({c: res["vsH1"][c]["iid"]["p_one_sided"] for c in CANDS})
    gate = {c: {"G1": res["vsH1"][c]["iid"]["diff"] < 0 and hp[c] < 0.10,
                "G2": (res[c]["balanced"] or 0) >= (res["vsH1"][c]["H1_balanced_sameRows"] or 0)} for c in CANDS}
    for c in gate:
        gate[c]["passes"] = all(gate[c].values())
    res["holm"], res["gate"] = hp, gate
    res["passedGate"] = [c for c in CANDS if gate[c]["passes"]]
    # continuous evaluation (C4 vs RW vs climatological mean)
    cont = {}
    for nm, mu, sg in (("CONT", "CONT_mu", "CONT_sig"), ("RW", "RW_mu", "RW_sig"), ("CLIM", "CLIM_mu", "CLIM_sig")):
        cont[nm] = {"MAE": float(np.mean(np.abs(dev[mu] - dev["H_target"]))),
                    "CRPS": float(np.mean([crps(y, m, s) for y, m, s in zip(dev["H_target"], dev[mu], dev[sg])]))}
    l = np.array([crps(y, m, s) for y, m, s in zip(dev["H_target"], dev["CONT_mu"], dev["CONT_sig"])]) - \
        np.array([crps(y, m, s) for y, m, s in zip(dev["H_target"], dev["RW_mu"], dev["RW_sig"])])
    rng = np.random.default_rng(Y14.SEED)
    cont["CONT_minus_RW_CRPS"] = {"diff": float(l.mean()), "p_one_sided": float(np.mean(l[rng.integers(0, len(l), (Y14.B, len(l)))].mean(1) >= 0))}
    res["continuous"] = cont
    # E2 leading vs concurrent
    dd = d[(d.index + 2 >= DEV_FIRST) & (d.index + 2 <= DEV_LAST)].assign(dH=lambda x: x["H_target"] - x["H_last"])
    conc = dd["E2"].reindex(dd.index + 2).to_numpy()
    g = pd.DataFrame({"lead": dd["E2"].to_numpy(), "conc": conc, "dH": dd["dH"].to_numpy()}).dropna(subset=["dH"])
    res["E2_lead_test"] = {}
    for lab in ("lead", "conc"):
        h = g.dropna(subset=[lab])
        v = [h.iloc[rng.integers(0, len(h), len(h))][[lab, "dH"]].corr().iloc[0, 1] for _ in range(2000)]
        res["E2_lead_test"][lab] = {"r": round(float(h[lab].corr(h["dH"])), 3), "n": len(h),
                                    "CI90": [round(float(np.quantile(v, .05)), 3), round(float(np.quantile(v, .95)), 3)]}
    OUT.mkdir(exist_ok=True)
    (OUT / "dev_results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    dev.reset_index().to_csv(OUT / "dev_rows.csv", index=False, lineterminator="\n", float_format="%.5f")

    # ---------------------------------------------------------------- the 17 official FIRI targets
    import score_firi_l2 as F
    fr = pd.read_csv(EXP / "FIRI_LEAD2_FEASIBILITY" / "out" / "firi_l2_rows.csv")
    fr["q"] = fr["target"].map(R.qi)
    fr["t"] = fr["q"] - 2
    fr["ALWAYS-HIGH"], fr["ALWAYS-LOW"] = 1.0, 0.0
    cr = {"status": ("confirmatory on an already-used period for " + str(res["passedGate"])) if res["passedGate"]
          else "DESCRIPTIVE ONLY: no candidate passed the development gate; nothing is selected from these rows"}
    for name, src in [("served_FIRI_v2", None), ("H1_firi_rows", "H1row")] + [(f"Y15_{c}", c) for c in ("H1",) + CANDS]:
        g = fr.copy()
        vals = g["F2"] if src is None else g["H1"] if src == "H1row" else g["t"].map(d[src])
        g["F2"] = vals.to_numpy()
        k = g[g["F2"].notna()].copy()
        r = F.rules(k)["rules"]
        cr[name] = {"rowsWithForecast": len(k), "abstained": int(g["F2"].isna().sum()), "metrics": Y14.metrics(k["y"], k["F2"]),
                    "rules": {kk.split()[0]: v["pass"] for kk, v in r.items()},
                    "failed": [kk.split()[0] for kk, v in r.items() if not v["pass"]], "passesAll": all(v["pass"] for v in r.values())}
    (OUT / "confirm_results.json").write_text(json.dumps(cr, indent=1, default=str), encoding="utf-8")
    fr.assign(**{f"Y15_{c}": fr["t"].map(d[c]) for c in CANDS}, kept=fr["t"].map(d["kept"])).to_csv(
        OUT / "confirm_rows.csv", index=False, lineterminator="\n", float_format="%.4f")

    print({k: res[k] for k in ("rows", "period", "prevalence", "fallbackRows", "FIRIR_issued", "FIRIR_domainCounts", "C2_keptFrequency")})
    for c in ("PERSIST", "CLIM", "H1") + CANDS:
        m = res[c]
        tail = "" if c == "H1" else (f" | n {res['vsH1'][c]['rows']} vsH1 {res['vsH1'][c]['iid']['diff']:+.4f} p {res['vsH1'][c]['iid']['p_one_sided']:.3f} "
                                     f"(blk {res['vsH1'][c]['block4']['p_one_sided']:.3f}) H1bal {res['vsH1'][c]['H1_balanced_sameRows'] or 0:.3f}")
        print(f"{c:7s} n {m['n']} acc {m['accuracy']:.3f} bal {m['balanced'] or 0:.3f} P {m['precision'] or 0:.2f} R {m['recall'] or 0:.2f} "
              f"spec {m['specificity'] or 0:.2f} F1 {m['f1']:.3f} AUC {m['auc'] or 0:.3f} Brier {m['brier']:.4f} CM {m['TP']}/{m['FP']}/{m['FN']}/{m['TN']} "
              f"slope {m['calibration']['slope']}" + tail)
    print("holm", hp)
    print("gate", gate, "passed:", res["passedGate"])
    print("continuous", cont)
    print("E2 lead test", res["E2_lead_test"])
    print("CONFIRM:", cr["status"])
    for k, v in cr.items():
        if isinstance(v, dict):
            m = v["metrics"]
            print(f"  {k:15s} rows {v['rowsWithForecast']} abst {v['abstained']} acc {m['accuracy']:.3f} bal {m['balanced'] or 0:.3f} "
                  f"P {m['precision'] or 0:.2f} R {m['recall'] or 0:.2f} AUC {m['auc'] or 0:.3f} Brier {m['brier']:.4f} "
                  f"CM {m['TP']}/{m['FP']}/{m['FN']}/{m['TN']} rules {''.join('P' if x else 'F' for x in v['rules'].values())} fails {v['failed']}")


if __name__ == "__main__":
    main()
