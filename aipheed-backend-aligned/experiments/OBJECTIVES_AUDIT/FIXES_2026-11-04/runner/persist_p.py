"""Probabilistic persistence baseline (PLAN_PERSIST_P.md, hash checked). No candidate is refitted.

    python persist_p.py   # PERSIST-P forecasts, reference + primary 14-test families -> ../out/persist_p_*.{csv,json}
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

HERE = Path(__file__).resolve().parents[1]
AUD = HERE.parent
EXP = AUD.parent
PLAN = HERE / "PLAN_PERSIST_P.md"
OUT = HERE / "out"
sys.path.insert(0, str(AUD / "runner"))
import ce_model as CE  # noqa: E402

PC, N, V, H, R, A = CE.PC, CE.N, CE.V, CE.H, CE.R, CE.A
MODELS = {"C-b": (N.OUT / "forecasts.csv", None), "C-E6": (AUD / "out" / "ce6_fits.csv", AUD / "out" / "ce6_results.json"),
          "C-B6": (AUD / "out" / "cb6_fits.csv", AUD / "out" / "cb6_results.json")}


def check() -> str:
    b = PLAN.read_bytes().replace(b"\r\n", b"\n")
    body, last = b.rstrip(b"\n").rsplit(b"\n", 1)
    h = hashlib.sha256(body + b"\n").hexdigest()
    assert last.startswith(b"PLAN-SHA256: ") and last.split()[1].decode() == h, "PLAN_PERSIST_P changed"
    return h


def _auc(y, p):
    from sklearn.metrics import roc_auc_score
    return float(roc_auc_score(y, p)) if len(set(y)) == 2 and len(set(p)) > 1 else None


def main():
    pre = check()
    d = H.load()
    lab = V.area_labels(d)
    lab_bl = lab[lab["area"] == "BL"]
    iv2 = pd.read_csv(EXP / "IMPROVE_V2" / "out" / "forecasts.csv")
    h3 = pd.read_csv(EXP / "OBJECTIVES_COMPLETION" / "out" / "h3_forecasts.csv")
    L = pd.read_csv(N.LEADS_FILE)
    per = L[L["name"] == "PERSIST"][["t", "lead", "q", "p"]]
    rows = []
    for r in per.itertuples(index=False):
        pi = H.pi_h4l(d, int(r.t), int(r.lead))
        rows.append({"name": "PERSIST-P", "t": int(r.t), "lead": int(r.lead), "q": int(r.q),
                     "p": float(pi["pi"]) if pd.notna(pi["pi"]) else float(r.p), "h_last": pi["h_last"],
                     "true_horizon": pi["true_h"], "sigma_fallback": pi["fallback"], "persist_hard": float(r.p)})
    PP = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    PP.to_csv(OUT / "persist_p_forecasts.csv", index=False)
    base = [iv2[iv2["name"].isin(["LOGIT", "PSA-only", "NLP-only"])][["name", "t", "lead", "q", "p"]],
            h3[["name", "t", "lead", "q", "p"]], L[L["name"].isin(["PERSIST", "CLIM"])][["name", "t", "lead", "q", "p"]],
            PP[["name", "t", "lead", "q", "p"]]]
    res = {"prereg_sha256": pre, "label": "DEVELOPMENT EVIDENCE; comparator change only, no candidate refitted",
           "persist_p": {}, "models": {}}
    for k in (1, 2):
        W = R.frame(pd.concat(base, ignore_index=True), k, lab_bl)
        g = W.dropna(subset=["PERSIST-P"])
        res["persist_p"][str(k)] = {
            "n": int(len(g)), "calls_differing_from_PERSIST": int(((g["PERSIST-P"] >= .5) != (g["PERSIST"] >= .5)).sum()),
            "accuracy": float(((g["PERSIST-P"] >= .5).astype(int) == g["y"]).mean()),
            "brier": float(((g["PERSIST-P"] - g["y"]) ** 2).mean()), "brier_hard_PERSIST": float(((g["PERSIST"] - g["y"]) ** 2).mean()),
            "auc": _auc(g["y"], g["PERSIST-P"]), "auc_hard_PERSIST": _auc(g["y"], g["PERSIST"]),
            "sigma_fallback_rows": int(PP[(PP["lead"] == k) & PP["q"].isin(g["q"])]["sigma_fallback"].fillna(False).sum())}
    for name, (fp, stored_fp) in MODELS.items():
        F = pd.read_csv(fp)
        F = F[F["name"] == name][["name", "t", "lead", "q", "p"]]
        comp = pd.concat(base + [F], ignore_index=True)
        fam_ref, fam_new = {}, {}
        for k in (1, 2):
            W = R.frame(comp, k, lab_bl)
            era = W[W["t"] >= V.NEWS_ERA]
            for b in PC.COMPS:
                fam_ref[(k, b)] = PC._paired(era if b in A.NLP_ONLY else W, name, b)
            for b in ["PERSIST-P" if b == "PERSIST" else b for b in PC.COMPS]:
                fam_new[(k, b)] = PC._paired(era if b in A.NLP_ONLY else W, name, b)
        out = {}
        for tag, fam in (("reference_hard_PERSIST", fam_ref), ("primary_PERSIST_P", fam_new)):
            hp = R.holm({key: v["p_one_sided"] for key, v in fam.items()})
            out[tag] = [{"lead": k, "comparator": b, "n_quarters": v["n_quarters"], "brier_model": v["brier_candidate"],
                         "brier_comparator": v["brier_comparator"], "diff": v["diff"], "ci95": v["ci95"],
                         "p_one_sided": v["p_one_sided"], "p_holm_14": hp[(k, b)],
                         "significant": bool(v["diff"] < 0 and hp[(k, b)] < .05)} for (k, b), v in fam.items()]
            out[f"{tag}_n_significant"] = sum(x["significant"] for x in out[tag])
        if stored_fp is not None:
            st = {(x["lead"], x["comparator"]): x for x in json.loads(Path(stored_fp).read_text(encoding="utf-8"))["holm_family_14"]}
            dif = max(abs(x["p_holm_14"] - st[(x["lead"], x["comparator"])]["p_holm_14"]) +
                      abs(x["diff"] - st[(x["lead"], x["comparator"])]["diff"]) for x in out["reference_hard_PERSIST"])
            out["reference_reproduces_stored"] = {"max_abs_diff": float(dif), "ok": bool(dif < 1e-9)}
            assert dif < 1e-9, f"{name}: reference family does not reproduce the stored family ({dif})"
        res["models"][name] = out
        print(name, "reference", out["reference_hard_PERSIST_n_significant"], "of 14; primary (PERSIST-P)",
              out["primary_PERSIST_P_n_significant"], "of 14", out.get("reference_reproduces_stored"), flush=True)
        for x in out["primary_PERSIST_P"]:
            if x["comparator"] == "PERSIST-P":
                print(f"   L{x['lead']} vs PERSIST-P: {x['brier_model']:.4f} vs {x['brier_comparator']:.4f} diff {x['diff']:+.4f} "
                      f"CI {x['ci95'][0]:+.3f}..{x['ci95'][1]:+.3f} p {x['p_one_sided']:.4f} Holm {x['p_holm_14']:.4f} "
                      f"{'PROVEN' if x['significant'] else 'NOT PROVEN'}")
    print(json.dumps(res["persist_p"], indent=1))
    (OUT / "persist_p_results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
