"""Re-score the Chapter I risk forecast (CH1-LGBM) with the audited inputs (FINAL_THESIS_OBJECTIVES Addendum 1).

    python rerun_ch1.py          # out/rerun_predictions_lead{k}.csv, out/rerun_results.json

The study data object returned by E107's data() is swapped for the corrected one, so every feature, baseline and
comparator of the unchanged ch1_lib code is computed from the audited inputs. The pooled-area sigma sensitivity
replaces only pi_H's sigma.
"""
from __future__ import annotations

import json
import math
import sys

import audit_build as A

C, FM, B, E, L, np, pd = A.C, A.FM, A.B, A.E, A.L, A.np, A.pd
OUT = A.OUT
CH1 = A.EXP / "FINAL_THESIS_OBJECTIVES"


def _check():
    want = (CH1 / "runner" / "ADDENDUM_1_SHA256.txt").read_text().strip()
    assert FM.sha256(CH1 / "ADDENDUM_1_DATA_CORRECTIONS.md") == want, "Addendum 1 changed after freezing"


def use_corrected():
    d, x = A.corrected_data()
    E._CACHE["d"], E._CACHE["x"] = d, x


def pooled_pi_h(t: int, k: int):
    """pi_H with sigma from latest-reading errors pooled over the four SWS areas (Addendum 1 sensitivity)."""
    kn = C.bl_known(E.issue(t))
    if not kn:
        return float("nan"), {}
    q_last, h_last = kn[-1][0], kn[-1][1]
    h = (t + k) - q_last
    errs = []
    for a in ("NCR", "BL", "VIS", "MIN"):
        d = {x[0]: x[1] for x in FM.known(E.issue(t), a, "primary")}
        errs += [d[q + h] - d[q] for q in d if q + h in d]
    sig = math.sqrt(np.mean(np.square(errs))) if len(errs) >= 4 else C.SIGMA_H_FALLBACK
    from scipy.stats import norm
    return float(norm.cdf((h_last - C.H_LINE) / max(sig, 0.5))), {
        "sws_newest_q": L.qs(q_last), "sws_newest_published": kn[-1][3], "sws_newest_fieldwork_end": kn[-1][2],
        "h_last": h_last, "true_horizon": h, "sigma_h": sig}


def score(tag: str) -> dict:
    res = {"leads": {}, "superiority": {}, "news_ablation": {}}
    for k in C.LEADS:
        D = C.run_lead(k)
        D.to_csv(OUT / f"{tag}_predictions_lead{k}.csv", index=False, lineterminator="\n", float_format="%.6g")
        res["leads"][k] = C.decide(D)
        res["superiority"][k] = C.superiority(D)
        y = D["y"].astype(int).to_numpy()
        b = FM.boot_diff(D, (D["CH1_p"] - y) ** 2, (D["LGBM-GOV_p"] - y) ** 2)
        res["news_ablation"][k] = {"acc_with": float(((D["CH1_p"] >= .5).astype(int) == y).mean()),
                                   "acc_without": float(((D["LGBM-GOV_p"] >= .5).astype(int) == y).mean()),
                                   "brier_diff": b, "mcnemar_p": FM.mcnemar(y, D["CH1_p"] >= .5, D["LGBM-GOV_p"] >= .5)}
        d = res["leads"][k]
        print(f"[{tag}] lead {k}: n {d['n']} acc {d['metrics']['accuracy']:.3f} CI {[round(v, 3) for v in d['accuracy_ci90']]} "
              f"bal {d['metrics']['balanced_accuracy']:.3f} P {d['metrics']['precision']:.2f} R {d['metrics']['recall']:.2f} "
              f"AUC {d['metrics']['auc']:.3f} | persist {d['baseline_accuracy']['PERSIST-SI']:.3f} "
              f"always-low {d['baseline_accuracy']['ALWAYS-LOW']:.3f} gov {d['baseline_accuracy']['LGBM-GOV']:.3f} | "
              f"fail {[c for c, v in d['criteria'].items() if not v]}")
    hp = FM.holm({k: res["news_ablation"][k]["brier_diff"]["p_two"] for k in res["news_ablation"]})
    for k in res["news_ablation"]:
        res["news_ablation"][k]["holm_p"] = hp[k]
    res["max_reliable_lead"] = C.max_reliable_lead(res["leads"])
    res["max_reliable_lead_strict"] = C.max_reliable_lead(res["leads"], "reliable_strict")
    return res


def main():
    _check()
    use_corrected()
    out = {"addendum_sha256": FM.sha256(CH1 / "ADDENDUM_1_DATA_CORRECTIONS.md"), "primary": score("rerun")}
    C.pi_h = pooled_pi_h
    out["pooled_sigma_sensitivity"] = score("pooled")
    FM.write_json(OUT / "rerun_results.json", out)
    print("max reliable lead (audited inputs):", out["primary"]["max_reliable_lead"],
          "| pooled-sigma:", out["pooled_sigma_sensitivity"]["max_reliable_lead"])


if __name__ == "__main__":
    main()
