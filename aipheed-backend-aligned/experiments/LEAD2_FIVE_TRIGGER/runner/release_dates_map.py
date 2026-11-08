"""Match the archived PSA Region IV-A release pages (data/psa_release_evidence/wayback_catalog.csv) to the 180
province-month rows of data/psa_cpi_release_dates_TO_FILL_v2.csv, without touching the owner's columns.

Evidence accepted per row (month m, province p), all-income-households CPI only (bottom-30% and Lucena City are other
series and are never used):
1. p's own release for m: its **Release-Date** field, from the archived release page (level `province_release_page`);
2. otherwise a regional CALABARZON release for m whose text states p's figures (level `regional_page_states_province`;
   the owner must confirm its tables carry p's food and all-items CPI);
3. otherwise the row stays `unresolved`.
A release of another province is never evidence for p. The release PDFs were not archived, so no date is "printed on
the PDF" in this evidence; the level says exactly what was read. A row is `confirmed` only when the owner marks
`confirmed_by_owner = yes`; document evidence alone makes it `awaiting_owner_review`.

    python release_dates_map.py     # updates the archive_* columns and status of the v2 file; ../out/release_dates_map.json
"""
from __future__ import annotations

import json

import pandas as pd

import lt_lib as T

PROV = ["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]
V2 = T.DATA / "psa_cpi_release_dates_TO_FILL_v2.csv"
ARCH = ["archive_release_date", "archive_evidence_level", "archive_document_title", "archive_release_date_label",
        "archive_reference_no", "archive_source_url", "archive_wayback_url", "archive_evidence_file", "archive_file_sha256",
        "archive_available_by_issue", "owner_vs_archive"]


def province_in_title(t: str) -> list[str]:
    return [p for p in PROV if p.lower() in t.lower()]


def candidates(C: pd.DataFrame, m: str, p: str) -> tuple[pd.DataFrame, str]:
    """p's own release (by its subject: generic titles hide many provincial releases), else a regional release that
    states p's figures. Another province's release is never used, even when it ranks p."""
    c = C[(C["reference_month"] == m) & (C["series"] == "all_income") & C["release_date_iso"].notna()]
    own = c.loc[(c["subject"] == p).to_numpy()]
    if len(own):
        return own, "province_release_page"
    reg = c.loc[(c["subject"] == "regional").to_numpy()]
    reg = reg.loc[reg["provinces_with_figures"].fillna("").str.split(";").map(lambda s: p in s).astype(bool).to_numpy()]
    return reg, "regional_page_states_province"


LEDGER = T.DATA / "psa_cpi_release_date_web_research_ledger_20261029.csv"
LEDGER_COLS = ["ledger_release_date", "ledger_scope", "ledger_source_title", "ledger_source_url", "ledger_status", "ledger_notes"]


def ledger_for(Lg: pd.DataFrame, m: str, p: str) -> dict:
    """The owner's web-research ledger: a province-specific entry for p, else a regional entry (content unverified)."""
    g = Lg[Lg["reference_month"] == m]
    own = g[g["province_or_coverage"] == p]
    reg = g[g["source_scope"].str.startswith("regional")]
    e = own.iloc[0] if len(own) else reg.iloc[0] if len(reg) else None
    if e is None:
        return {}
    return dict(zip(LEDGER_COLS, [e["release_date_from_official_page"], e["source_scope"] if len(own) else "regional (province coverage unverified)",
                                  e["source_title"], e["source_url"], e["status"], e["series_and_review_notes"]]))


def main():
    V = pd.read_csv(V2, dtype=str)
    C = pd.read_csv(T.DATA / "psa_release_evidence" / "wayback_catalog.csv", dtype=str)
    C = C[C["error"].isna() & C["reference_month"].notna()]
    assert not (C["reference_month"] >= "2026-10").any()                       # blind boundary
    Lg = pd.read_csv(LEDGER, dtype=str).fillna("")
    for c in ARCH + LEDGER_COLS + ["evidence_flags"]:
        V[c] = ""
    for i, r in V.iterrows():
        for k, v in ledger_for(Lg, r["reference_month"], r["province"]).items():
            V.loc[i, k] = v
        cand, level = candidates(C, r["reference_month"], r["province"])
        if not len(cand):
            continue
        b = cand.sort_values("release_date_iso").iloc[0]                       # earliest official release carrying p's figures
        V.loc[i, ARCH[:-2]] = [b["release_date_iso"], level, b["title"], b["release_date_label"], b["reference_no"] if pd.notna(b["reference_no"]) else "",
                               b["url"], b["wayback_url"], f"psa_release_evidence/{b['file']}", b["sha256"]]
        V.loc[i, "archive_available_by_issue"] = "yes" if b["release_date_iso"] < r["must_be_released_before"] else "no"
        own = r["release_date_YYYY-MM-DD"]
        if isinstance(own, str) and own:
            V.loc[i, "owner_vs_archive"] = "same" if own == b["release_date_iso"] else f"differs (owner {own})"
    # flags: any source dated on/after the issue date; 2012-based series; regional coverage unverified; owner date from another province's release
    bad_owner = {("2025-07", p) for p in PROV if p != "Batangas"}                # priority file used the Batangas July 2025 release for all five
    for i, r in V.iterrows():
        f = []
        for col in ("release_date_YYYY-MM-DD", "archive_release_date", "ledger_release_date"):
            d = r[col] if isinstance(r[col], str) else ""
            if d and d >= r["must_be_released_before"]:
                f.append(f"{col}_not_before_issue")
        if "2012" in r["ledger_notes"] or r["ledger_status"].startswith("series_mismatch"):
            f.append("ledger_source_2012_base")
        if r["ledger_scope"].startswith("regional") or r["archive_evidence_level"] == "regional_page_states_province":
            f.append("regional_coverage_unverified")
        if (r["reference_month"], r["province"]) in bad_owner and isinstance(r["release_date_YYYY-MM-DD"], str) and r["release_date_YYYY-MM-DD"]:
            f.append("owner_date_from_batangas_release")
        V.loc[i, "evidence_flags"] = ";".join(f)
    has_doc = V["archive_release_date"] != ""
    owner_yes = (V["confirmed_by_owner"].fillna("").str.lower().eq("yes")
                 & V["is_release_date_printed_on_document"].fillna("").str.lower().eq("yes")
                 & (V["saved_evidence_filename"].fillna("").ne("") | V["archive_evidence_file"].fillna("").ne("")))
    V["status"] = "unresolved"
    any_date = has_doc | V["release_date_YYYY-MM-DD"].notna() | (V["ledger_release_date"] != "")
    V.loc[any_date, "status"] = "awaiting_owner_review"
    V.loc[owner_yes & any_date, "status"] = "confirmed"
    V.to_csv(V2, index=False, lineterminator="\n")
    un = V[V["status"] == "unresolved"]
    res = {"rows": int(len(V)), "status": V["status"].value_counts().to_dict(),
           "archive_dated_rows": int(has_doc.sum()), "by_level": V.loc[has_doc, "archive_evidence_level"].value_counts().to_dict(),
           "archive_not_available_by_issue": V.loc[V["archive_available_by_issue"] == "no",
                                                   ["reference_month", "province", "must_be_released_before", "archive_release_date", "role"]].to_dict("records"),
           "owner_vs_archive": V["owner_vs_archive"].replace("", pd.NA).dropna().value_counts().to_dict(),
           "owner_vs_archive_differences": V.loc[V["owner_vs_archive"].str.startswith("differs"),
                                                 ["reference_month", "province", "owner_vs_archive", "archive_release_date", "archive_evidence_level"]].to_dict("records"),
           "unresolved_by_month": un.groupby("reference_month")["province"].apply(list).to_dict(),
           "cutoff_rows": V[V["role"] == "could_be_added"][["reference_month", "province", "must_be_released_before", "archive_release_date",
                                                              "archive_evidence_level", "archive_available_by_issue", "status"]].to_dict("records"),
           "flags": V["evidence_flags"].str.split(";").explode().replace("", pd.NA).dropna().value_counts().to_dict(),
           "not_before_issue_rows": V.loc[V["evidence_flags"].str.contains("not_before_issue"),
                                          ["reference_month", "province", "role", "must_be_released_before", "release_date_YYYY-MM-DD",
                                           "archive_release_date", "ledger_release_date"]].to_dict("records"),
           "rescore_can_run": bool((V["status"] == "confirmed").all())}
    T.OUT.joinpath("release_dates_map.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({k: v for k, v in res.items() if k not in ("unresolved_by_month",)}, indent=1, default=str))
    print("unresolved months:", {m: len(p) for m, p in res["unresolved_by_month"].items()})


if __name__ == "__main__":
    main()
