"""E98 Question D (PROTOCOL.md section 2): models trained directly on the measured regional outcome R (SWS involuntary
hunger > 11.3%, Balance Luzon) versus the served FIRI v2 and the persistence outlook H1, Lead 1 and Lead 2.
Run from backend/:  py -3.13 ../aipheed-backend-aligned/experiments/E98_Acceptance_Gate/runner/direct_target.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
E98 = HERE.parent
EXP = E98.parent
sys.path.insert(0, str(EXP / "E97_Validation_Completion" / "runner"))
import common as C  # noqa: E402
from app.ml.inference import thesis_system as TS  # noqa: E402

SEED, LINE = 98, 11.3
ARMS = {"D1": ["H_last"], "D2": ["H_last", "C_reg"], "D3": ["H_last", "C_reg", "E_reg"]}


def outcome() -> dict[str, float]:
    s = pd.read_csv("data/inputs/sws_rounds.csv")
    s = s[s["definition_A"].astype(str) == "True"]
    return s.groupby("quarter")["H"].mean().to_dict()


def posted(issue: str) -> set[str]:
    s = pd.read_csv("data/inputs/sws_rounds.csv")
    return set(s[(s["definition_A"].astype(str) == "True") & (s["published"].str[:10] < issue)]["quarter"])


def frame(lead: int) -> pd.DataFrame:
    h = pd.read_csv("data/thesis/firi2_history.csv", dtype={"province_code": str})
    dom = h.groupby("origin_quarter")[["dom_C", "dom_E"]].mean().rename(columns={"dom_C": "C_reg", "dom_E": "E_reg"})
    if lead == 2:
        firi = h[h["kind"] == "backtest"].groupby("origin_quarter")["FIRI"].mean()
    else:
        r = pd.read_csv(EXP / "E97_Validation_Completion" / "recovered" / "regional.csv")
        firi = r[r["lead"] == 1].set_index("origin_quarter")["C3"]
    out = outcome()
    rows = []
    for oq in dom.index:
        t = TS.qi(oq)
        rh = TS.regional_hunger(t, lead)
        tq = TS.qs(t + lead)
        rows.append({"origin": oq, "t": t, "target": tq, "issue": TS.issue_of(t), "H_last": rh.get("latestReading"),
                     "h1": rh.get("probabilityAbove11_3"), "C_reg": dom.loc[oq, "C_reg"], "E_reg": dom.loc[oq, "E_reg"],
                     "firi": firi.get(oq, np.nan), "H": out.get(tq, np.nan)})
    F = pd.DataFrame(rows).sort_values("t").reset_index(drop=True)
    F["y"] = (F["H"] > LINE).astype(float).where(F["H"].notna())
    return F


def walk_forward(F: pd.DataFrame, feats: list[str]) -> tuple[list, list, list]:
    from sklearn.linear_model import LogisticRegression
    preds, fallback, audit = [], [], []
    for _, r in F.iterrows():
        known = posted(r["issue"])
        tr = F[(F["t"] < r["t"]) & F["target"].isin(known) & F["y"].notna()].dropna(subset=feats)
        audit.append({"target": r["target"], "issue": r["issue"], "pairs": len(tr),
                      "latest_pair_target": tr["target"].iloc[-1] if len(tr) else None,
                      "all_pair_outcomes_posted_before_issue": bool(tr["target"].isin(known).all())})
        ok = len(tr) >= 6 and tr["y"].sum() >= 2 and (1 - tr["y"]).sum() >= 2 and pd.notna(r[feats]).all()
        if not ok:
            preds.append(r["h1"])
            fallback.append(True)
            continue
        A = tr[feats].astype(float)
        mu, sd = A.mean(), A.std(ddof=0).replace(0, 1.0)
        m = LogisticRegression(C=1.0, max_iter=5000).fit((A - mu) / sd, tr["y"].astype(int))
        x = (r[feats].astype(float).to_frame().T - mu) / sd
        preds.append(float(m.predict_proba(x)[0, 1]))
        fallback.append(False)
    return preds, fallback, audit


def paired(E: pd.DataFrame, a: str, b: str) -> dict:
    y, g = E["y"].to_numpy(), E["target"].to_numpy()
    db = (E[a] - y) ** 2 - (E[b] - y) ** 2
    ca = ((E[a] >= 0.5).astype(int) == y).astype(int) - ((E[b] >= 0.5).astype(int) == y).astype(int)
    bal = lambda yy, s: C.metrics(yy, s)["balanced_accuracy"]  # noqa: E731

    def dbal(i):
        x, z = bal(y[i], E[a].to_numpy()[i]), bal(y[i], E[b].to_numpy()[i])
        return None if x is None or z is None else x - z
    return {"brier_diff": float(db.mean()), "brier_ci95": C.boot_ci(g, lambda i: float(db.to_numpy()[i].mean()), seed=SEED),
            "brier_sign_p": C.sign_test(db), "brier_better_quarters": int((db < -1e-12).sum()), "brier_worse_quarters": int((db > 1e-12).sum()),
            "accuracy_diff": float(ca.mean()), "accuracy_ci95": C.boot_ci(g, lambda i: float(ca.to_numpy()[i].mean()), seed=SEED),
            "only_a_correct": int((ca > 0).sum()), "only_b_correct": int((ca < 0).sum()), "accuracy_sign_p": C.sign_test(ca),
            "balanced_accuracy_diff": (None if bal(y, E[a]) is None or bal(y, E[b]) is None else bal(y, E[a]) - bal(y, E[b])),
            "balanced_accuracy_ci95": C.boot_ci(g, dbal, seed=SEED)}


def reliability(y, p) -> list[dict]:
    y, p = np.asarray(y), np.asarray(p)
    out = []
    for lo, hi in ((0, 0.5), (0.5, 1.0001)):
        m = (p >= lo) & (p < hi)
        out.append({"bin": f"[{lo}, {min(hi, 1)})", "n": int(m.sum()), "mean_p": float(p[m].mean()) if m.any() else None,
                    "observed_rate": float(y[m].mean()) if m.any() else None})
    return out


def run_lead(lead: int) -> tuple[dict, pd.DataFrame]:
    F = frame(lead)
    audits = {}
    for a, feats in ARMS.items():
        F[a], F[f"{a}_fallback"], audits[a] = walk_forward(F, feats)
    F["ALWAYS"] = 1.0
    E = F[F["y"].notna()].dropna(subset=["firi", "h1"] + list(ARMS)).copy()
    E["y"] = E["y"].astype(int)
    arms = ["H1", "FIRI", *ARMS, "ALWAYS"]
    E = E.rename(columns={"h1": "H1", "firi": "FIRI"})
    res = {"lead": lead, "quarters": len(E), "targets": E["target"].tolist(), "class_counts": {"HIGH": int(E["y"].sum()), "LOW": int((1 - E["y"]).sum())},
           "metrics": {a: C.metrics(E["y"], E[a]) for a in arms},
           "model_issued_quarters": {a: int((~E[f"{a}_fallback"]).sum()) for a in ARMS},
           "paired": {f"{a}_vs_{b}": paired(E, a, b) for a in ["FIRI", *ARMS] for b in ("H1", "FIRI") if a != b},
           "reliability": {a: reliability(E["y"], E[a]) for a in ["H1", *ARMS]},
           "training_audit": {a: [x for x in audits[a] if x["target"] in set(E["target"])] for a in ARMS}}
    on = E[(E["y"] == 1) & (E["H_last"] <= LINE)]
    rec = E[(E["y"] == 0) & (E["H_last"] > LINE)]
    res["onsets"] = {"quarters": on["target"].tolist(), **{a: int((on[a] >= 0.5).sum()) for a in arms}}
    res["recoveries"] = {"quarters": rec["target"].tolist(), **{a: int((rec[a] < 0.5).sum()) for a in arms}}
    res["leakage_audit_ok"] = all(x["all_pair_outcomes_posted_before_issue"] for a in ARMS for x in audits[a])
    return res, E


def decide(lead2: dict) -> dict:
    m, p = lead2["metrics"], lead2["paired"]
    passing = []
    for a in ARMS:
        ci = p[f"{a}_vs_H1"]["brier_ci95"]
        if m[a]["accuracy"] >= m["FIRI"]["accuracy"] - 1e-12 and ci[1] is not None and ci[1] < 0:
            passing.append(a)
    sel = min(passing, key=lambda a: (round(m[a]["brier"], 12), len(ARMS[a]))) if passing else None
    best = sel or "FIRI"
    acc = m[best]["accuracy"]
    goal = acc > 0.75 and acc > m["H1"]["accuracy"] and acc > m["ALWAYS"]["accuracy"]
    return {"passing_rule_D": passing, "selected_direct_model": sel, "best_defensible_regional_model": best,
            "regional_probability_offered": sel is not None, "lead2_accuracy_best": acc,
            "goal75_on_intended_outcome": "met (development evidence)" if goal else "not demonstrated"}


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    o = E98 / "runs" / f"{stamp}_direct"
    o.mkdir(parents=True, exist_ok=True)
    res = {"stamp": stamp, "protocol_sha256": (E98 / "PROTOCOL.sha256").read_text().split()[0],
           "outcome": "SWS involuntary hunger > 11.3%, Balance Luzon (regional), definition_A rounds",
           "evidence_status": "development evidence: all scored quarters examined before E98", "leads": {}}
    for lead in (1, 2):
        r, E = run_lead(lead)
        res["leads"][str(lead)] = r
        E.to_csv(o / f"predictions_lead{lead}.csv", index=False)
        print(f"Lead {lead}: {r['quarters']} quarters {r['class_counts']} issued={r['model_issued_quarters']} leak_ok={r['leakage_audit_ok']}")
        for a, m in r["metrics"].items():
            print(f"  {a:6s} acc={m['accuracy']:.3f} {np.round(m['accuracy_wilson95'], 2)} bal={m['balanced_accuracy']} "
                  f"P={m['precision_HIGH']} R={m['recall_HIGH']} F1={m['f1_HIGH']:.2f} auc={m['auc_roc']} brier={m['brier']:.3f} {m['confusion']}")
        for k, v in r["paired"].items():
            print(f"  {k:12s} dBrier={v['brier_diff']:+.3f} {np.round(v['brier_ci95'], 3)} p={v['brier_sign_p']:.3f} "
                  f"dAcc={v['accuracy_diff']:+.3f} {np.round(v['accuracy_ci95'], 3)} ({v['only_a_correct']}/{v['only_b_correct']}) dBal={v['balanced_accuracy_diff']}")
        print("  onsets", r["onsets"], "recoveries", r["recoveries"])
        print("  reliability", json.dumps(r["reliability"]))
    res["decision"] = decide(res["leads"]["2"])
    print("DECISION", res["decision"])
    (o / "direct_target.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print(o)


if __name__ == "__main__":
    main()
