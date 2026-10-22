"""E99-F Q1-Q3 (PROTOCOL.md): SWS vs OCTA outcome reliability; MA2/MA4 smoothed persistence; FIRI v2 robustness.
Run from backend/:  py -3.13 ../aipheed-backend-aligned/experiments/E99_Final_Improvement/runner/forecast_evidence.py
"""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
E99 = HERE.parent
EXP = E99.parent
sys.path.insert(0, str(EXP / "E97_Validation_Completion" / "runner"))
sys.path.insert(0, str(EXP / "E98_Acceptance_Gate" / "runner"))
import common as C  # noqa: E402
import direct_target as D  # noqa: E402
from app.ml.inference import thesis_system as TS  # noqa: E402

SEED, LINE, OCTA_LINE = 99, 11.3, 11.0


def ma_outlook(t: int, lead: int, n: int) -> tuple[float | None, float | None]:
    """Mean of the last n posted quarterly SWS readings (quarters <= t, posted before the issue date) and
    P(> 11.3) with sigma from the rule's own past Lead-`lead` errors known at the issue (>= 4 pairs, else 4.0)."""
    def level(tt):
        hs = TS._posted(TS.issue_of(tt))
        ks = [q for q in hs if q <= tt][-n:]
        return float(np.mean([hs[q] for q in ks])) if ks else None
    issue = TS.issue_of(t)
    hs = TS._posted(issue)
    m = level(t)
    if m is None:
        return None, None
    errs = [hs[tp + lead] - level(tp) for tp in range(TS.qi("2021-Q2"), t - lead + 1)
            if tp + lead in hs and level(tp) is not None]
    sig = math.sqrt(sum(e * e for e in errs) / len(errs)) if len(errs) >= 4 else TS.SIGMA_DEFAULT
    return m, 1 - 0.5 * (1 + math.erf((LINE - m) / (sig * math.sqrt(2))))


def kappa(a, b) -> float | None:
    a, b = np.asarray(a, int), np.asarray(b, int)
    po = float((a == b).mean())
    pe = float(a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean()))
    return None if pe == 1 else (po - pe) / (1 - pe)


def q1() -> dict:
    o = json.loads((E99 / "inputs" / "octa_validation_E73.json").read_text(encoding="utf-8"))["quarters"]
    sws = D.outcome()
    h = pd.read_csv("data/thesis/firi2_history.csv")
    firi = h[h["kind"] == "backtest"].groupby("target")["FIRI"].mean()
    rows = []
    for q, ov in sorted(o.items(), key=lambda kv: TS.qi(kv[0])):
        t = TS.qi(q) - 2
        rows.append({"quarter": q, "octa": ov, "sws": sws.get(q), "firi_lead2": firi.get(q),
                     "h1_lead2": TS.regional_hunger(t, 2).get("probabilityAbove11_3")})
    R = pd.DataFrame(rows)
    res = {"rows": R.to_dict(orient="records")}
    Cm = R.dropna(subset=["sws"]).copy()
    for lab, ol in (("octa_gt_11.0", OCTA_LINE), ("octa_gt_11.3", LINE)):
        ys, yo = (Cm["sws"] > LINE).astype(int), (Cm["octa"] > ol).astype(int)
        agree = int((ys == yo).sum())
        sub = {"common_quarters": len(Cm), "class_agreement": agree, "agreement_share": agree / len(Cm),
               "cohen_kappa": kappa(ys, yo), "disagreeing_quarters": Cm.loc[ys != yo, "quarter"].tolist(),
               "survey_specific": (len(Cm) - agree) >= len(Cm) / 3}
        for arm in ("firi_lead2", "h1_lead2"):
            E = Cm.dropna(subset=[arm])
            sub[f"{arm}_vs_sws"] = C.metrics((E["sws"] > LINE).astype(int), E[arm])
            sub[f"{arm}_vs_octa"] = C.metrics((E["octa"] > ol).astype(int), E[arm])
        res[lab] = sub
    res["level_spearman"] = float(spearmanr(Cm["sws"], Cm["octa"]).statistic)
    res["level_mean_gap_sws_minus_octa"] = float((Cm["sws"] - Cm["octa"]).mean())
    return res


def lead_frame(lead: int) -> pd.DataFrame:
    F = D.frame(lead)
    for n in (2, 4):
        v = [ma_outlook(int(t), lead, n) for t in F["t"]]
        F[f"ma{n}_level"], F[f"MA{n}"] = [x[0] for x in v], [x[1] for x in v]
    F["ALWAYS"] = 1.0
    E = F[F["y"].notna()].dropna(subset=["firi", "h1", "MA2", "MA4"]).copy().rename(columns={"h1": "H1", "firi": "FIRI"})
    E["y"] = E["y"].astype(int)
    E["regime"] = np.where((E["H_last"] > LINE).astype(int) == E["y"], "regime", "transition")
    return E


def q2_q3(lead: int) -> tuple[dict, pd.DataFrame]:
    E = lead_frame(lead)
    arms = ["FIRI", "H1", "MA2", "MA4", "ALWAYS"]
    r = {"quarters": len(E), "class_counts": {"HIGH": int(E["y"].sum()), "LOW": int((1 - E["y"]).sum())},
         "metrics": {a: C.metrics(E["y"], E[a]) for a in arms}, "paired": {}}
    for a in ("MA2", "MA4"):
        for b in ("FIRI", "H1"):
            r["paired"][f"{a}_vs_{b}"] = D.paired(E.assign(target=E["target"]), a, b)
    # robustness (report only)
    margin = (E["FIRI"] - 0.5).abs()
    r["firi_margin"] = {"min": float(margin.min()), "within_0.05": int((margin <= 0.05).sum()),
                        "per_quarter": E[["target", "FIRI", "y"]].round(4).to_dict(orient="records")}
    r["threshold_sweep"] = {str(th): C.metrics(E["y"], E["FIRI"], thr=th)["accuracy"] for th in (0.45, 0.475, 0.5, 0.525, 0.55)}
    r["regime_split"] = {}
    for part in ("regime", "transition"):
        S = E[E["regime"] == part]
        r["regime_split"][part] = {"quarters": S["target"].tolist(),
                                   **{a: (int(((S[a] >= 0.5).astype(int) == S["y"]).sum()), len(S)) for a in arms}}
    return r, E


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    o = E99 / "runs" / f"{stamp}_forecast"
    o.mkdir(parents=True, exist_ok=True)
    res = {"stamp": stamp, "protocol_sha256": (E99 / "PROTOCOL.sha256").read_text().split()[0],
           "evidence_status": "development evidence (all quarters examined before E99)", "Q1": q1(), "leads": {}}
    print("Q1:", json.dumps({k: v for k, v in res["Q1"].items() if k != "rows"}, default=float)[:2500])
    for lead in (1, 2):
        r, E = q2_q3(lead)
        res["leads"][str(lead)] = r
        E.to_csv(o / f"frame_lead{lead}.csv", index=False)
        print(f"Lead {lead}: {r['quarters']} q {r['class_counts']}")
        for a, m in r["metrics"].items():
            print(f"  {a:6s} acc={m['accuracy']:.3f} bal={m['balanced_accuracy']} auc={m['auc_roc']} brier={m['brier']:.3f} {m['confusion']}")
        for k, v in r["paired"].items():
            print(f"  {k:10s} dAcc={v['accuracy_diff']:+.3f} {np.round(v['accuracy_ci95'], 3)} ({v['only_a_correct']}/{v['only_b_correct']}) "
                  f"dBrier={v['brier_diff']:+.3f} {np.round(v['brier_ci95'], 3)} p={v['brier_sign_p']:.3f}")
        print("  margin", {k: v for k, v in r["firi_margin"].items() if k != "per_quarter"}, "sweep", r["threshold_sweep"])
        print("  regime split", r["regime_split"])
    (o / "forecast_evidence.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print(o)


if __name__ == "__main__":
    main()
