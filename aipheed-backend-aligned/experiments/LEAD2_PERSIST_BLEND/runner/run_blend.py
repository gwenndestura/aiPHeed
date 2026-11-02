"""LEAD2_PERSIST_BLEND (PLAN.md, EXPLORATORY): candidate B = pi_H4_m3 x (0.5 P0_price_m3 + 0.5 s), s = the province's
newest-CPI price condition at the M3 issue date. Reads LEAD2_MIDQUARTER_UPDATE/out/rows.csv; the price half of
LEAD2_POST_SWS_ISSUE/runner/score.persist_clim_at; the frozen R1-R7 code of P0H4_LEAD12_REVIEW/runner/reproduce.py.
Writes out/ only.

    python -B run_blend.py
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOTD = HERE.parent
EXP = ROOTD.parent
OUT = ROOTD / "out"
sys.path.insert(0, str(EXP / "LEAD2_POST_SWS_PRICE" / "runner"))
import price_refit as PR  # noqa: E402

SI, L, E, pd, np = PR.SI, PR.L, PR.E, PR.pd, PR.np
_spec = importlib.util.spec_from_file_location("p0h4_reproduce", EXP / "P0H4_LEAD12_REVIEW" / "runner" / "reproduce.py")
RP = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(RP)


def plan_ok() -> str:
    b = (ROOTD / "PLAN.md").read_bytes()
    i = b.rfind(b"\nPLAN-SHA256:") + 1
    h = hashlib.sha256(b[:i]).hexdigest()
    if h != b[i:].split(b":", 1)[1].strip().decode():
        raise SystemExit("PLAN.md changed after it was hashed")
    return h


def issue_m3(t: int) -> pd.Timestamp:
    n = t + 1
    return pd.Timestamp(year=n // 4, month=(n % 4) * 3 + 2, day=1)


def price_persistence(t: int, provs: list[str]) -> tuple[dict, int]:
    """The price half of score.persist_clim_at at the M3 issue date (None when a CPI month is missing)."""
    D = issue_m3(t)
    cutoff = SI.cpi_newest(D)
    avail = pd.Timestamp(year=(cutoff + 2) // 12, month=(cutoff + 2) % 12 + 1, day=1)
    assert avail <= D, f"CPI {L.ym_s(cutoff)} not available by {D.date()}"
    th = L.e40_spec()
    yoy = E.data()[0].yoy
    y = yoy[yoy["ym"].isin([cutoff - 2, cutoff - 1, cutoff])]
    assert int(y["ym"].max()) <= cutoff and set(y["ym"].unique()) <= {cutoff - 2, cutoff - 1, cutoff}
    out = {}
    for p in provs:
        f = y[(y["province_code"] == p) & (y["commodity"] == "food")]["yoy"]
        a = y[(y["province_code"] == p) & (y["commodity"] == "all_items")]["yoy"]
        out[p] = None if (len(f) < 3 or len(a) < 3) else float(f.mean() > th["food"][p] or (f.mean() - a.mean()) > th["gap"][p])
    return out, cutoff


_orig_scores = RP.scores


def evaluate(g: pd.DataFrame, col: str) -> dict:
    """reproduce.rules() calls scores(g) whose default column is bound to P0H4_p3 at import, so scores is pointed at
    `col` for the call (as in LEAD2_FOODINSECURITY/runner/run_fi.py)."""
    RP.P = col
    RP.scores = lambda h, c=None, thr=0.5: _orig_scores(h, col if c is None else c, thr)
    try:
        s = RP.scores(g, col)
        rules = RP.rules(g)
    finally:
        RP.scores = _orig_scores
    assert rules["R2 accuracy >= 0.75"]["value"] == round(s["accuracy"], 4)
    return {**{k: s[k] for k in ("n", "quarters", "TP", "FP", "FN", "TN", "accuracy", "balanced", "precision", "recall",
                                  "auc", "brier")},
            "rules": rules, "passed": sum(v["pass"] for v in rules.values()),
            "failed": [k.split()[0] for k, v in rules.items() if not v["pass"]]}


def main():
    sha = plan_ok()
    OUT.mkdir(exist_ok=True)
    PR.U.setup()
    g = pd.read_csv(EXP / "LEAD2_MIDQUARTER_UPDATE" / "out" / "rows.csv", dtype={"province_code": str})
    assert len(g) == 65 and g["q"].nunique() == 13 and ((g["q"] - g["t"]) == 2).all()
    provs = sorted(g["province_code"].unique())
    s_col, cut = [], {}
    for t, h in g.groupby("t"):
        ps, c = price_persistence(int(t), provs)
        cut[L.qs(int(t))] = {"issue": str(issue_m3(int(t)).date()), "cpiCutoff": L.ym_s(c)}
        s_col.append(h.assign(s=h["province_code"].map(ps)))
    g = pd.concat(s_col).sort_values(["q", "province_code"]).reset_index(drop=True)
    p = np.where(g["s"].isna(), g["P0_price_m3"], 0.5 * g["P0_price_m3"] + 0.5 * g["s"].fillna(0))
    g = g.assign(B=g["pi_H4_m3"] * p, target=g["q"].map(L.qs),
                 **{"PERSIST-SI_p": g["PERSIST_m3"], "CLIM_p": g["CLIM_m3"], "ALWAYS-LOW_p": 0.0})
    res = {"label": "EXPLORATORY, post-hoc (user-authorised; >= 8th Lead-2 variant on these 65 rows)", "planSha256": sha,
           "cpiCutoffs": cut, "sMissingRows": int(g["s"].isna().sum()),
           "B": evaluate(g, "B"), "M3_reference": evaluate(g, "M3")}
    res["perQuarter"] = [{"target": q, "y_high_provinces": int(h["y"].sum()), "B_high": int((h["B"] >= .5).sum()),
                          "M3_high": int((h["M3"] >= .5).sum()), "s_hot": int(h["s"].fillna(0).sum()),
                          "h": round(float(h["pi_H4_m3"].iloc[0]), 3)} for q, h in g.groupby("target")]
    g[["t", "q", "province_code", "y", "pi_H4_m3", "P0_price_m3", "s", "B", "M3", "PERSIST_m3", "CLIM_m3"]].to_csv(
        OUT / "rows.csv", index=False, lineterminator="\n", float_format="%.6f")
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    for k in ("B", "M3_reference"):
        r = res[k]
        print(f"{k:13s} {r['TP']}/{r['FP']}/{r['FN']}/{r['TN']} acc {r['accuracy']:.3f} bal {r['balanced']:.3f} "
              f"P {r['precision']:.3f} R {r['recall']:.3f} AUC {r['auc']:.3f} Brier {r['brier']:.4f} | "
              f"pass {r['passed']}/7 fails {r['failed']}")
    print("s missing rows:", res["sMissingRows"])
    for q in res["perQuarter"]:
        print(" ", q)


if __name__ == "__main__":
    main()
