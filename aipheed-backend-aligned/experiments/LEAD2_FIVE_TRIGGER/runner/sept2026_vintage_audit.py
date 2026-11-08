"""September 2026 CPI vintage audit of the sealed CR and CR-ANC forecasts (issue 2026-10-15, Leads 2-4, CPI through
2026-09). Diagnostic only: the sealed files are read, never rewritten or resealed.

1. Trace: the exact CPI-derived inputs of every sealed Lead-2+ row (A1_food, A1_gap, A_mom; CR-ANC also A1_food_anc,
   A1_gap_anc), recomputed from the committed snapshot exactly as the seal scripts did, with the CPI months each uses.
2. Provenance: which repository snapshots of PSA OpenSTAT held the September 2026 provincial values, and when they
   were retrieved (from the committed acquisition records):
   - E31 0012M4ACP23 (YoY), FOOD only, retrieved 2026-10-14T15:34:40Z (commit 81b5fa86);
   - E40 0012M4ACP23 (YoY), food and all items, retrieved 2026-10-15T09:18:32Z (commit 9624188);
   - E41 0012M4ACP22 (index, the model's source), retrieved 2026-10-15T09:54:05Z (commit 7960517).
   The food index values used imply exactly the food YoY of the 2026-10-14 snapshot (checked here).
3. Classification of every input (province x lead x feature x seal) against the issue date 2026-10-15, using the owner's
   provincial release dates (chat, 2026-10-29; sources not yet supplied) for the all-items part.
4. Sensitivity (labelled diagnostic, not a replacement): the sealed rows re-predicted with the same fitted models and the
   all-items cut-off at 2026-08 for the provinces whose all-items timing is unresolved.

    python sept2026_vintage_audit.py    # ../out/sept2026_vintage_audit.json, ../out/sept2026_vintage_inputs.csv
"""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd

import final as FN  # noqa: F401  (sys.path order)
import lt_lib as T
import cpi_refresh_features as CF  # noqa: I001
import root_cause as RC
from cr_resolve import cr_stack

F, KEY = T.F, T.KEY
ORIGIN, ISSUE = 2026 * 4 + 2, "2026-10-15"
SEP, AUG = 2026 * 12 + 8, 2026 * 12 + 7
NAMES = RC.NAMES
CODE = {v: k for k, v in NAMES.items()}
OWNER_PROVINCIAL_RELEASE = {"Cavite": "2026-10-12", "Laguna": "2026-10-13", "Batangas": "2026-10-13", "Rizal": "2026-10-15", "Quezon": "2026-10-16"}
FOOD_PRE_ISSUE = "2026-10-14T15:34:40Z (OpenSTAT 0012M4ACP23, 01.1 FOOD, E31 commit 81b5fa86)"
ALL_ITEMS_FIRST = "2026-10-15T09:18:32Z (OpenSTAT 0012M4ACP23, E40 commit 9624188); index table 2026-10-15T09:54:05Z (E41 commit 7960517)"
FEATURES = {"A1_food": "food", "A_mom": "food", "A1_food_anc": "food", "A1_gap": "food+all_items", "A1_gap_anc": "food+all_items"}


def classify(prov: str, part: str) -> tuple[str, str]:
    if part == "food":
        return "demonstrably available before issue", f"food YoY published by {FOOD_PRE_ISSUE}; value-matched"
    rel = OWNER_PROVINCIAL_RELEASE[prov]
    if rel < ISSUE:
        return ("available before issue (owner-reported provincial release; source and content pending)",
                f"provincial release {rel} (owner); OpenSTAT all items first seen {ALL_ITEMS_FIRST}")
    return ("same-day timing unresolved",
            f"provincial release {rel} (owner){' is after the issue' if rel > ISSUE else ' is the issue day'}; the model's source "
            f"(OpenSTAT) held all items by {ALL_ITEMS_FIRST}, i.e. on the issue day, time of posting unknown")


def gap_mixed(d, th, t, k, p, m_food, m_all):
    f = CF.projection(d, t, k, p, "food", m_food)
    h = CF.projection(d, t, k, p, "all_items", m_all)
    return (f - h) - th["gap"][p]


def anchored_gap_mixed(S_row, g, m_food, m_all):
    W = RC.II.index_wide()
    lf, la = np.log(W["food"]), np.log(W["all"])
    p, t, k = S_row["province_code"], int(S_row["t"]), int(S_row["lead"])
    q = t + k
    months = [q // 4 * 12 + (q % 4) * 3 + j for j in range(3)]

    def L(series, m, m0):
        return series[p].get(m, np.nan) if m <= m0 else series[p].get(m0, np.nan) + g * (m - m0)
    yf = [100 * (math.exp(L(lf, m, m_food) - L(lf, m - 12, m_food)) - 1) for m in months]
    ya = [100 * (math.exp(L(la, m, m_all) - L(la, m - 12, m_all)) - 1) for m in months]
    return float(np.mean(yf)) - float(np.mean(ya)) - F.TH_G[p]


def main():
    T.MONO_UP = T.MONO_UP + RC.ANC
    S = cr_stack()
    S["A1_food_anc"], S["A1_gap_anc"] = RC.anchored_at(S, RC.G_ANCHOR)
    d, _ = CF.E.data()
    th = CF.L.e40_spec()
    te = S[(S["t"] == ORIGIN) & (S["lead"].between(2, 4))].copy()
    assert (te["m0r"] == SEP).all(), "sealed Lead-2+ rows must use CPI through 2026-09"
    seals = {"CR": ("cr_prospective.csv", T.U2), "CR-ANC": ("cranc_prospective.csv", RC.COLS_ANC)}
    out = {"issue_date": ISSUE, "owner_release_dates": OWNER_PROVINCIAL_RELEASE, "food_pre_issue_source": FOOD_PRE_ISSUE,
           "all_items_first_seen": ALL_ITEMS_FIRST, "seals": {}}
    inputs = []
    for name, (fname, cols) in seals.items():
        sealed = pd.read_csv(T.LT / "sealed" / fname, dtype={"province_code": str})
        models = {}
        P = T.run(cols, [ORIGIN], S=S, models=models)
        m = models[ORIGIN]
        chk = sealed.merge(P[KEY[1:] + ["pi_P"]], on=["province_code", "lead"])
        repro = float((chk["pi_price"] - chk["pi_P"]).abs().max())
        assert repro < 1e-5, (name, repro)
        X = te.copy()
        for r in X.itertuples():
            prov = NAMES[r.province_code]
            for feat in [c for c in FEATURES if c in cols]:
                cls, ev = classify(prov, FEATURES[feat])
                inputs.append({"seal": name, "province": prov, "target_quarter": F.qs(ORIGIN + int(r.lead)), "lead": int(r.lead),
                               "issue_date": ISSUE, "feature": feat, "value_used": float(getattr(r, feat)),
                               "cpi_months": "food 2026-09" if FEATURES[feat] == "food" else "food 2026-09, all items 2026-09",
                               "classification": cls, "evidence": ev})
        # sensitivity: all-items cut-off at 2026-08 for provinces whose all-items timing is unresolved
        unresolved = [p for p, rel in OWNER_PROVINCIAL_RELEASE.items() if rel >= ISSUE]
        Xs = X.copy()
        for i, r in Xs.iterrows():
            if NAMES[r["province_code"]] in unresolved:
                Xs.loc[i, "A1_gap"] = gap_mixed(d, th, int(r["t"]), int(r["lead"]), r["province_code"], SEP, AUG)
                if "A1_gap_anc" in cols:
                    Xs.loc[i, "A1_gap_anc"] = anchored_gap_mixed(r, RC.G_ANCHOR, SEP, AUG)
        base = sealed.set_index(["province_code", "lead"])
        rows = []
        for (i, r), pp in zip(Xs.iterrows(), m.predict(Xs)):
            b = base.loc[(r["province_code"], int(r["lead"]))]
            p_new = float(b["pi_hunger"]) * float(pp)
            rows.append({"province": NAMES[r["province_code"]], "lead": int(r["lead"]), "sealed_probability": float(b["probability"]),
                         "sealed_class": b["class"], "probability_all_items_aug": p_new, "class_all_items_aug": "HIGH" if p_new >= .5 else "LOW",
                         "changed_class": ("HIGH" if p_new >= .5 else "LOW") != b["class"]})
        out["seals"][name] = {"file": fname, "sha256": T.sha256(T.LT / "sealed" / fname), "reproduced_max_abs": repro,
                              "sensitivity_all_items_aug_for": unresolved, "sensitivity": rows,
                              "classes_changed": int(sum(r["changed_class"] for r in rows))}
    I = pd.DataFrame(inputs)
    I.to_csv(T.OUT / "sept2026_vintage_inputs.csv", index=False, lineterminator="\n", float_format="%.6g")
    out["classification_counts"] = I.groupby(["seal", "classification"]).size().unstack(fill_value=0).to_dict("index")
    out["rows_with_unresolved_inputs"] = sorted({(r.seal, r.province, r.lead) for r in I.itertuples() if r.classification.startswith("same-day")})
    T.OUT.joinpath("sept2026_vintage_audit.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({k: out[k] for k in ("classification_counts", "rows_with_unresolved_inputs")}, indent=1, default=str))
    for n, s in out["seals"].items():
        print(n, "reproduced", s["reproduced_max_abs"], "classes changed", s["classes_changed"])
        print(pd.DataFrame(s["sensitivity"]).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
