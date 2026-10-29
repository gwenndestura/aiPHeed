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
    c = C[(C["reference_month"] == m) & (C["series"] == "all_income") & C["release_date_iso"].notna()]
    own = c.loc[c["title"].map(lambda t: province_in_title(t) == [p]).astype(bool).to_numpy()]
    if len(own):
        return own, "province_release_page"
    reg = c.loc[c["title"].map(lambda t: not province_in_title(t) and "lucena" not in t.lower()).astype(bool).to_numpy()]
    reg = reg.loc[reg["provinces_with_figures"].fillna("").str.split(";").map(lambda s: p in s).astype(bool).to_numpy()]
    return reg, "regional_page_states_province"


def main():
    V = pd.read_csv(V2, dtype=str)
    C = pd.read_csv(T.DATA / "psa_release_evidence" / "wayback_catalog.csv", dtype=str)
    C = C[C["error"].isna() & C["reference_month"].notna()]
    assert not (C["reference_month"] >= "2026-10").any()                       # blind boundary
    for c in ARCH:
        V[c] = ""
    for i, r in V.iterrows():
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
    has_doc = V["archive_release_date"] != ""
    owner_yes = (V["confirmed_by_owner"].fillna("").str.lower().eq("yes")
                 & V["is_release_date_printed_on_document"].fillna("").str.lower().eq("yes")
                 & (V["saved_evidence_filename"].fillna("").ne("") | V["archive_evidence_file"].fillna("").ne("")))
    V["status"] = "unresolved"
    V.loc[has_doc | V["release_date_YYYY-MM-DD"].notna(), "status"] = "awaiting_owner_review"
    V.loc[owner_yes & (has_doc | V["release_date_YYYY-MM-DD"].notna()), "status"] = "confirmed"
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
           "rescore_can_run": bool((V["status"] == "confirmed").all())}
    T.OUT.joinpath("release_dates_map.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({k: v for k, v in res.items() if k not in ("unresolved_by_month",)}, indent=1, default=str))
    print("unresolved months:", {m: len(p) for m, p in res["unresolved_by_month"].items()})


if __name__ == "__main__":
    main()
