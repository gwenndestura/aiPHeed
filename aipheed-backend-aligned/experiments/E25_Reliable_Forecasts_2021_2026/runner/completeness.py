"""E25 DATA_COMPLETENESS_MATRIX.csv: every province x quarter, 2021-Q1..2027-Q1, every input.

Status vocabulary (task section 1):
  present_verified   value in an authorized, hash-pinned file and checked
  present_disputed   value exists but its assignment or definition is disputed
  authorized_pending authorized by the researcher but not yet supplied (none at present)
  protected          exists or may exist, not authorized: never opened
  unavailable        does not exist in the window (not collected, not yet published, or outside the window)
Publication date kind: verified | proxy (national release + <= 6 days) | retrieval-based upper bound | unknown.
Nothing is filled: a missing cell stays missing.
Usage: python -B runner/completeness.py   -> DATA_COMPLETENESS_MATRIX.csv, runs/completeness_summary.json"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard  # noqa: E402

guard.install()
import pandas as pd  # noqa: E402

import e25lib as E  # noqa: E402

EXP = guard.EXP
qk, qs = E.qk, E.qs
Q = [qs(i) for i in range(qk("2021-Q1"), qk("2027-Q1") + 1)]
PIN = {Path(e["read_path"]).resolve(): e["sha256"] for e in json.loads((EXP / "inputs" / "PINS.json").read_text())["pins"]}
MAN = {(EXP / m["file"]).resolve(): m["sha256"] for m in json.loads((EXP / "inputs" / "INPUTS_MANIFEST.json").read_text())}


def h(p):
    return PIN.get(Path(p).resolve()) or MAN.get(Path(p).resolve())


def main():
    rounds = E.load_rounds()
    comp, c26, D = E.load_components()
    mon, Dnow, _ = E.load_monthly(c26, comp)
    rel = pd.read_csv(guard.CPI_2026_RELEASES, dtype=str) if False else None   # read through the guard below
    import io
    rel = pd.read_csv(io.StringIO(guard.read_allowed_text(guard.CPI_2026_RELEASES)), dtype=str)
    X, gov_cols, masked, const = E.load_features(rounds[rounds["definition_A"]])
    lc = guard.read_allowed_parquet(guard.LGU_CENSUS, ["province_code", "lgu_code", "population_2020", "land_area_km2"])
    lp = guard.read_allowed_parquet(guard.LGU_POVERTY, ["province_code", "lgu_code", "year", "poverty_incidence_pct",
                                                        "source_note"])
    rows = []

    def add(p, q, inp, status, source, pub, kind, sha, note="", value=None):
        rows.append({"province_code": p, "province": E.PNAME.get(p, "all provinces"), "quarter": q, "input": inp,
                     "status": status, "value": value, "source": source, "publication_date": pub,
                     "publication_date_kind": kind, "file_sha256": sha, "note": note})

    sws_src = "E12 details.json (SWS Balance Luzon rounds; verified publication dates)"
    for q in Q:
        rq = rounds[rounds["quarter"] == q]
        prod = rq[rq["definition_A"]]
        sup = rq[~rq["definition_A"]]
        for p in E.PROVS:
            # ---- SWS regional hunger (same value for the five provinces)
            if len(prod) and q <= "2025-Q4":
                add(p, q, "SWS hunger (H, regional)", "present_verified", sws_src,
                    ";".join(prod["published"].dt.date.astype(str)), "verified", h(guard.E12_DETAILS),
                    f"{len(prod)} production round(s): " + "; ".join(prod["round"]), round(prod["H"].mean(), 3))
            elif len(prod):
                add(p, q, "SWS hunger (H, regional)", "present_verified",
                    "production sws_hunger.parquet (authorized 2026-10-13)", "<= " + str(prod["published_eff"].iloc[0].date()),
                    "retrieval-based upper bound", h(guard.PROD_SWS),
                    "value verified; publication date unverified (strict rule: usable from the upper bound)",
                    round(prod["H"].mean(), 3))
            elif len(sup):
                add(p, q, "SWS hunger (H, regional)", "present_disputed", sws_src,
                    ";".join(sup["published"].dt.date.astype(str)), "verified", h(guard.E12_DETAILS),
                    "supplementary round(s) only; quarter assignment disputed (readings A/B/C): " + "; ".join(sup["round"]),
                    round(sup["H"].mean(), 3))
            elif q in ("2026-Q3",):
                add(p, q, "SWS hunger (H, regional)", "protected", "SWS (September 2026 round)", None, "unknown", None,
                    "may be published; not authorized; never opened")
            elif q in ("2026-Q4", "2027-Q1"):
                add(p, q, "SWS hunger (H, regional)", "unavailable", "SWS", None, "unknown", None,
                    "fieldwork not yet published (as of 2026-10-14)")
            else:
                add(p, q, "SWS hunger (H, regional)", "unavailable", "SWS", None, "unknown", None,
                    "no SWS round with fieldwork in this quarter in the authorized record")
            # ---- provincial food CPI (F, D)
            d = D[(D["province_code"] == p) & (D["quarter"] == q)]
            if len(d) and q <= "2025-Q4":
                add(p, q, "Provincial food CPI YoY (F) and D", "present_verified",
                    "E12 realized_components (PSA provincial food CPI YoY)", None, "proxy (national release + <= 6 days)",
                    h(guard.E12_COMPONENTS), "", round(float(d["D"].iloc[0]), 4))
            elif len(d):
                rr = rel[rel["reference_month"].str[:4].astype(int).eq(int(q[:4])) &
                         ((rel["reference_month"].str[5:7].astype(int) - 1) // 3 + 1).eq(int(q[-1]))]
                add(p, q, "Provincial food CPI YoY (F) and D", "present_verified",
                    "PSA OpenSTAT 0012M4ACP23 (authorized Jan-Jun 2026)", ";".join(rr["national_release_date"]),
                    "national release verified; provincial unverified", h(guard.CPI_2026H1), "",
                    round(float(d["D"].iloc[0]), 4))
            elif q == "2026-Q3":
                add(p, q, "Provincial food CPI YoY (F) and D", "protected", "PSA (July-September 2026)", None,
                    "unknown", None, "published by PSA; not authorized; never opened")
            else:
                add(p, q, "Provincial food CPI YoY (F) and D", "unavailable", "PSA", None, "unknown", None,
                    "not yet published (October 2026 CPI is released in early November)" if q == "2026-Q4"
                    else "future quarter")
            # ---- Dnow (months 1-2)
            dn = Dnow[(Dnow["province_code"] == p) & (Dnow["quarter"] == q)]
            if len(dn):
                src = "E24v2 cpi_index_2021_2025_ACP22.csv (in-window indices)" if q <= "2025-Q4" else \
                    "PSA OpenSTAT 0012M4ACP23 (authorized Jan-Jun 2026)"
                add(p, q, "Dnow (CPI months 1-2 of the quarter)", "present_verified", src, None,
                    "proxy (national release + <= 6 days)", h(guard.CPI_INDEX_2021_2025) if q <= "2025-Q4" else h(guard.CPI_2026H1),
                    "index file: public PSA, owner confirmation pending (A6)" if q <= "2025-Q4" else "",
                    round(float(dn["Dnow"].iloc[0]), 4))
            elif q < "2022-Q1":
                add(p, q, "Dnow (CPI months 1-2 of the quarter)", "unavailable", "PSA", None, "unknown", None,
                    "2021 monthly YoY would need 2020 indices (out of window); PSA's published 2021 YoY table not acquired")
            elif q == "2026-Q3":
                add(p, q, "Dnow (CPI months 1-2 of the quarter)", "protected", "PSA (July-August 2026)", None, "unknown",
                    None, "published; not authorized")
            else:
                add(p, q, "Dnow (CPI months 1-2 of the quarter)", "unavailable", "PSA", None, "unknown", None,
                    "October-November 2026 CPI not yet published" if q == "2026-Q4" else "future quarter")
            # ---- news (FSSI and triggers) and other government indicators (features_fused)
            x = X[(X["province_code"] == p) & (X["quarter"] == q)]
            if len(x):
                add(p, q, "News features (FSSI, triggers)", "present_verified", "features_fused.parquet (hash-pinned)",
                    None, "unknown", h(guard.FEATURES_FUSED),
                    "FSSI_lag2 masked at 2021-Q1/Q2; lag1/accel masked at 2021-Q1" if q <= "2021-Q2" else "",
                    round(float(x["FSSI"].iloc[0]), 4))
                add(p, q, "Other government indicators (quarter t-1 values)", "present_verified",
                    "features_fused.parquet (hash-pinned)", None, "proxy / schedule-based (E9)", h(guard.FEATURES_FUSED),
                    "forward-/zero-fill provenance of the fused file not recoverable" +
                    ("; 2020-Q4 values not loaded (out of window)" if q == "2021-Q1" else ""))
            else:
                st = "protected" if q in ("2026-Q1", "2026-Q2", "2026-Q3") else "unavailable"
                for inp in ("News features (FSSI, triggers)", "Other government indicators (quarter t-1 values)"):
                    add(p, q, inp, st, "news corpus / government fetchers", None, "unknown", None,
                        "2026 news and 2026 government indicators are not authorized" if st == "protected" else
                        ("2026-Q4 is in progress; news incomplete until the cutoff" if q == "2026-Q4" else "future quarter"))
            # ---- labels (derived)
            if q <= "2026-Q2" and len(d) and (len(prod) or len(sup)):
                add(p, q, "T1 label S1 = H + 2D (reading A)", "present_verified" if len(prod) else "present_disputed",
                    "derived (H + 2D)", None, "derived", None,
                    "" if len(prod) else "label exists only under readings B/C (supplementary rounds)")
            else:
                add(p, q, "T1 label S1 = H + 2D (reading A)", "unavailable" if q not in ("2026-Q3",) else "protected",
                    "derived (H + 2D)", None, "derived", None, "no H for this quarter" if q <= "2026-Q2" else
                    "outcome not authorized / not yet published")
    # ---- LGU static inputs
    nmun = lp[~lp["source_note"].str.contains("fallback", case=False)].groupby("province_code").size()
    nall = lc.groupby("province_code").size()
    for p in E.PROVS:
        add(p, "static", "LGU population and land area (2020 census, density)", "present_verified",
            "lgu_census.parquet (PSA 2020 CPH, released 2021)", None, "verified (release 2021)", h(guard.LGU_CENSUS),
            f"{int(nall.get(p, 0))} LGUs")
        add(p, "static", "LGU poverty incidence (PSA 2021 SAE)",
            "present_verified" if int(nmun.get(p, 0)) == int(nall.get(p, 0)) else "present_disputed",
            "lgu_poverty.parquet", None, "verified", h(guard.LGU_POVERTY),
            f"{int(nmun.get(p, 0))} of {int(nall.get(p, 0))} LGUs have a municipal estimate; the rest carry a labelled "
            "province-mean substitute. The PSA municipal SAE workbook is needed (AUTHORIZATION_REQUEST.md).")
    M = pd.DataFrame(rows)
    M.to_csv(EXP / "DATA_COMPLETENESS_MATRIX.csv", index=False, lineterminator="\n")
    summ = M[M["quarter"] != "static"].groupby(["input", "status"]).size().unstack(fill_value=0)
    w = M[M["quarter"].isin([qs(i) for i in range(qk("2025-Q1"), qk("2027-Q1") + 1)])]
    gaps = w[w["status"] != "present_verified"][["quarter", "input", "status", "note"]].drop_duplicates()
    out = {"cells": int(len(M)), "by_input_status": summ.to_dict(orient="index"),
           "gaps_2025Q1_2027Q1": gaps.to_dict("records")}
    (EXP / "runs" / "completeness_summary.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(summ.to_string())
    print(gaps.to_string())


if __name__ == "__main__":
    main()
