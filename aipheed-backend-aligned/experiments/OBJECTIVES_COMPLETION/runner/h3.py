"""H3 single-source LightGBM comparators (H3_COMPARATORS.md, sha b700cb45...). Comparators only.

    python h3.py     # -> out/h3_forecasts.csv, out/h3_results.json

Reuses IMPROVE_V2's code and stored table read-only. Before the two variants are trusted, the same fitting function
run with the reference's columns must reproduce IMPROVE_V2's REF forecasts exactly."""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import hashlib
import json
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

OC = Path(__file__).resolve().parents[1]
OUT = OC / "out"
sys.path.insert(0, str(OC.parent / "IMPROVE_V2" / "runner"))
import iv2_lib as V  # noqa: E402
import run_iv2 as RUN  # noqa: E402

H = V.H
GOV = ["R_food_yoy", "R_head_yoy", "R_rice_yoy", "R_food_mom", "R_C3", "R_C4", "ONI_last", "ONI_max12",
       "tc_mean"] + H.WORLD
SPECS = {"REF-check": (H.T2_B + ["lead"], H.FIRST_ORIGIN), "LGBM-GOV": (GOV + ["lead"], H.FIRST_ORIGIN),
         "LGBM-NLP": (V.NEWS + ["lead"], V.NEWS_ERA)}
PROPOSED = ["REF", "REF+news"]
COMPARATORS = ["PERSIST", "NLP-only", "PSA-only", "LOGIT", "LGBM-GOV", "LGBM-NLP"]
NEWS_ERA_ONLY = {"NLP-only", "LGBM-NLP"}


def note_sha() -> str:
    b = (OC / "H3_COMPARATORS.md").read_bytes()
    i = b.rfind(b"\nNOTE-SHA256:") + 1
    h = hashlib.sha256(b[:i]).hexdigest()
    if h != b[i:].split(b":", 1)[1].strip().decode():
        raise SystemExit("H3_COMPARATORS.md changed after it was hashed: refusing to run")
    return h


def _fit(name: str) -> pd.DataFrame:
    """The reference's LightGBM path (IMPROVE_V2 fit_base, classification, BL rows) with a column list and a first
    origin: unchanged GRID, inner validation, eligibility and fallback."""
    cc, m0 = SPECS[name]
    d = H.load()
    lab = V.area_labels(d)
    T = pd.read_csv(OC.parent / "IMPROVE_V2" / "out" / "table_pooled.csv", dtype={"area": str})
    S = T[(T["area"] == "BL") & (T["t"] >= m0)]
    out = []
    for t in H.ORIGINS_EVAL:
        if t < m0:
            continue
        te = S[(S["t"] == t) & S["lead"].isin([1, 2])].copy()
        kb = V.known_labels(d, t, lab)
        kb = kb[kb["area"] == "BL"]
        clim = float(kb["y"].mean()) if len(kb) else 0.0
        tr = S[(S["t"] < t) & (S["q"] <= t - 1)].merge(kb[["area", "q", "y"]], on=["area", "q"], how="inner")
        if H.eligible(tr):
            cfg = H.lgbm_select(tr, cc, mono=False)
            p, fb, cid = H.LGBM(cfg, cc, False).fit(tr).predict(te), False, cfg["id"]
        else:
            p, fb, cid = float(tr["y"].mean()) if len(tr) else clim, True, None
        out.append(te[["t", "lead", "q"]].assign(name=name, p=p, fallback=fb, cfg=cid))
    return pd.concat(out, ignore_index=True)


def main():
    OUT.mkdir(exist_ok=True)
    sha = note_sha()
    with Pool(3) as pool:
        F3 = pd.concat(pool.map(_fit, list(SPECS)), ignore_index=True)
    F = pd.read_csv(OC.parent / "IMPROVE_V2" / "out" / "forecasts.csv")
    ref = F[(F["name"] == "REF") & F["t"].isin(H.ORIGINS_EVAL)][["t", "lead", "p"]]
    chk = F3[F3["name"] == "REF-check"][["t", "lead", "p"]].merge(ref, on=["t", "lead"], suffixes=("", "_iv2"))
    fid = {"n": int(len(chk)), "max_abs_diff": float((chk["p"] - chk["p_iv2"]).abs().max())}
    fid["equal"] = bool(len(chk) == len(ref) and fid["max_abs_diff"] < 1e-12)
    print("REF reproduced:", fid, flush=True)
    if not fid["equal"]:
        raise SystemExit("the fitting path does not reproduce IMPROVE_V2 REF: nothing scored")
    new = F3[F3["name"] != "REF-check"]
    new.to_csv(OUT / "h3_forecasts.csv", index=False)
    d = H.load()
    lab = V.area_labels(d)
    lab_bl = lab[lab["area"] == "BL"]
    A = pd.concat([F, new], ignore_index=True)
    res = {"note_sha256": sha, "ref_reproduced": fid, "leads": {}}
    for k in RUN.LEADS:
        W = RUN.frame(A, k, lab_bl)
        era = W[W["t"] >= V.NEWS_ERA]
        L = {"models": {}, "fallbacks": {}, "h3": {}}
        for n in ("LGBM-GOV", "LGBM-NLP"):
            g = W[W[n].notna()]
            r = H.evaluate(g, n)
            r["n_quarters_scored"] = int(g["q"].nunique())
            r["period_scored"] = f"{H.qs(g['q'].min())}..{H.qs(g['q'].max())}"
            L["models"][n] = r
            L["fallbacks"][n] = int(new[(new["name"] == n) & (new["lead"] == k) & new["q"].isin(g["q"])]["fallback"].sum())
        for prop in PROPOSED:
            cmp_ = {c: RUN.paired(era if c in NEWS_ERA_ONLY else W, prop, c) for c in COMPARATORS}
            hp = RUN.holm({c: v["p_one_sided"] for c, v in cmp_.items()})
            for c in cmp_:
                cmp_[c]["p_holm"] = hp[c]
            L["h3"][prop] = cmp_
        res["leads"][f"L{k}"] = L
        print(f"lead {k} done", flush=True)
    (OUT / "h3_results.json").write_text(json.dumps(res, indent=1, default=str))
    for k, L in res["leads"].items():
        for n, r in L["models"].items():
            m = r["metrics"]
            print(k, n, r["n_quarters_scored"], f"acc {m['accuracy']:.3f} bal {m['balanced']:.3f} P {m['precision']} "
                  f"R {m['recall']:.3f} F1 {m['f1']:.3f} AUC {m.get('auc')} Brier {m['brier']:.3f}",
                  "fails", [x.split()[0] for x, v in r["rules"].items() if not v["pass"]], "fallback", L["fallbacks"][n])
        for prop, cm in L["h3"].items():
            for c, v in cm.items():
                print(k, prop, "vs", c, v["n_quarters"], f"{v['brier_a']:.3f} {v['brier_b']:.3f} {v['diff']:+.3f} "
                      f"p {v['p_one_sided']:.3f} holm {v['p_holm']:.3f}")


if __name__ == "__main__":
    main()
