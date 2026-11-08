"""Companion record for the one sealed row whose call depends on unresolved same-day CPI timing (owner-approved
2026-10-29; LEAD2_SEPT2026_VINTAGE_AND_CAUSES_REPORT section 1): Rizal, target 2027-Q1, Lead 2, in both CR and CR-ANC.

The row is re-predicted with the same fitted models as the original seals and every input unchanged, except that the
all-items CPI behind A1_gap (and A1_gap_anc) stops at 2026-08, whose release precedes the 2026-10-15 issue. Food CPI
stays at 2026-09 (on OpenSTAT by 2026-10-14). The original sealed files are only read and their hashes checked; nothing
in them is replaced or resealed. The companion is sealed before the 2027-Q1 outcome exists.

Scoring (as approved): both the original and the companion row are scored and reported; the companion is the one
counted if the issue-day posting time of Rizal's September 2026 all-items CPI is never established before the issue.

    python rizal_companion_seal.py   # ../sealed/rizal_2027q1_companion.csv, ../sealed/rizal_2027q1_companion.sha256
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

import pandas as pd

import final as FN  # noqa: F401  (sys.path order)
import lt_lib as T
import cpi_refresh_features as CF  # noqa: I001
import root_cause as RC
import sept2026_vintage_audit as V
from cr_resolve import cr_stack

F = T.F
ORIGIN, LEAD, PROV = V.ORIGIN, 2, "Rizal"
SEALS = {"CR": ("cr_prospective.csv", T.U2, "dd293e2e36c87be26657b98c51184c5b8b1887bb0252ee4aa65a3dc3a1103da6"),
         "CR-ANC": ("cranc_prospective.csv", RC.COLS_ANC, "07c99e569746cb255dbd748c8c0eed095fd31944be551272d0187c45b49e3986")}


def main():
    lab = pd.read_csv(T.EXP / "FORECAST_RESEARCH_II" / "out" / "labels_rebuilt.csv")
    assert int(lab["q"].max()) < ORIGIN + LEAD, "the 2027-Q1 outcome already exists"
    for fname, _, sha in SEALS.values():
        assert T.sha256(T.LT / "sealed" / fname) == sha, f"{fname} changed"
    T.MONO_UP = T.MONO_UP + RC.ANC
    S = cr_stack()
    S["A1_food_anc"], S["A1_gap_anc"] = RC.anchored_at(S, RC.G_ANCHOR)
    d, _ = CF.E.data()
    th = CF.L.e40_spec()
    code = V.CODE[PROV]
    row = S[(S["t"] == ORIGIN) & (S["lead"] == LEAD) & (S["province_code"] == code)].copy()
    assert len(row) == 1 and int(row["m0r"].iloc[0]) == V.SEP
    out = []
    for name, (fname, cols, sha) in SEALS.items():
        sealed = pd.read_csv(T.LT / "sealed" / fname, dtype={"province_code": str})
        orig = sealed[(sealed["province_code"] == code) & (sealed["lead"] == LEAD)].iloc[0]
        models = {}
        T.run(cols, [ORIGIN], S=S, models=models)
        m = models[ORIGIN]
        assert abs(float(m.predict(row)[0]) - float(orig["pi_price"])) < 1e-5, f"{name}: original row not reproduced"
        X = row.copy()
        r = X.iloc[0]
        X["A1_gap"] = V.gap_mixed(d, th, ORIGIN, LEAD, code, V.SEP, V.AUG)
        if "A1_gap_anc" in cols:
            X["A1_gap_anc"] = V.anchored_gap_mixed(r, RC.G_ANCHOR, V.SEP, V.AUG)
        pp = float(m.predict(X)[0])
        p = float(orig["pi_hunger"]) * pp
        out.append({"companion_of": name, "original_file": fname, "original_sha256": sha,
                    "province_code": code, "province": PROV, "target_quarter": F.qs(ORIGIN + LEAD), "lead": LEAD,
                    "issue_date": orig["issue_date"], "sws_reading_used": orig["sws_reading_used"], "h_last": orig["h_last"],
                    "pi_hunger": orig["pi_hunger"], "pi_price": pp, "probability": p, "class": "HIGH" if p >= .5 else "LOW",
                    "cpi_through": "food 2026-09, all items 2026-08",
                    "original_probability": orig["probability"], "original_class": orig["class"],
                    "original_cpi_through": "food 2026-09, all items 2026-09",
                    "A1_gap_original": float(r["A1_gap"]), "A1_gap_companion": float(X["A1_gap"].iloc[0]),
                    "A1_gap_anc_original": float(r["A1_gap_anc"]) if "A1_gap_anc" in cols else None,
                    "A1_gap_anc_companion": float(X["A1_gap_anc"].iloc[0]) if "A1_gap_anc" in cols else None,
                    "model": orig["model"] + "; companion record, all-items CPI through 2026-08"})
    O = pd.DataFrame(out)
    path = T.LT / "sealed" / "rizal_2027q1_companion.csv"
    O.to_csv(path, index=False, lineterminator="\n", float_format="%.6g")
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    (T.LT / "sealed" / "rizal_2027q1_companion.sha256").write_text(json.dumps(
        {"file": path.name, "sha256": sha, "sealed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
         "approved_by_owner": "2026-10-29 (chat: 'Yes, seal companion')",
         "reason": "Rizal September 2026 all-items CPI: provincial release 2026-10-15 (owner-reported) = issue day; "
                   "OpenSTAT first seen 2026-10-15T09:18:32Z; posting time unknown",
         "scoring_rule": "score and report both the original and the companion; count the companion unless the "
                         "September 2026 Rizal all-items CPI is shown public before 2026-10-15",
         "originals_unchanged": {f: s for f, _, s in SEALS.values()},
         "targets": ["2027-Q1"], "latest_outcome_quarter_at_seal": F.qs(int(lab["q"].max())),
         "input_sha256": {p: T.sha256(T.DATA / p) for p in ("stack_l2.csv", "known_price_l2.csv", "cpi_refresh.csv")}}, indent=1) + "\n")
    print(O.round(4).T.to_string())
    print(sha)


if __name__ == "__main__":
    main()
