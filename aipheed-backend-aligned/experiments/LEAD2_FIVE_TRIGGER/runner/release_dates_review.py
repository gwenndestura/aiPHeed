"""Review of the PSA provincial CPI release dates collected by the project owner (no model is run).

Inputs:
- data/psa_cpi_release_dates_owner_research_20261029.csv (the owner's collection, kept verbatim);
- data/psa_cpi_release_months_needed.csv (every reference month the ADDENDUM_ROOT_CAUSE_RELEASE_DATES re-score depends
  on, for every Lead-2+ stack row, training rows included).

Outputs:
- out/release_dates_review.json: coverage, the check "released before the issue date" for every dated row, and
  whether the addendum's re-score can run (it needs every needed province-month confirmed);
- data/psa_cpi_release_dates_TO_FILL_v2.csv: the full 36-month x 5-province list, prefilled with the owner's dates.

A collected date counts as confirmed only when the owner marks it as the release date printed on the release itself
(not a page posting date) and a saved copy is named. Until then it is "reported", and the re-score does not run.

    python release_dates_review.py
"""
from __future__ import annotations

import json

import pandas as pd

import lt_lib as T

PROV = ["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]


def main():
    O = pd.read_csv(T.DATA / "psa_cpi_release_dates_owner_research_20261029.csv", dtype=str)
    N = pd.read_csv(T.DATA / "psa_cpi_release_months_needed.csv", dtype=str)
    full = N.merge(pd.DataFrame({"province": PROV}), how="cross")
    got = O[O["release_date_YYYY_MM_DD"].notna()][["reference_month", "province", "release_date_YYYY_MM_DD", "source_type",
                                                    "document_title", "source_url", "date_checked", "saved_evidence_filename"]]
    full = full.merge(got, on=["reference_month", "province"], how="left")
    full["status"] = full["release_date_YYYY_MM_DD"].notna().map({True: "reported", False: "UNKNOWN"})
    dated = full[full["status"] == "reported"].copy()
    dated["before_issue"] = dated["release_date_YYYY_MM_DD"] < dated["issue_date"]
    dated["days_before_issue"] = (pd.to_datetime(dated["issue_date"]) - pd.to_datetime(dated["release_date_YYYY_MM_DD"])).dt.days
    res = {"owner_file_sha256": T.sha256(T.DATA / "psa_cpi_release_dates_owner_research_20261029.csv"),
           "needed": {"reference_months": int(N["reference_month"].nunique()), "province_month_checks": int(len(full)),
                      "included_by_day10": int((N["role"] == "included_by_day10").sum()), "could_be_added": int((N["role"] == "could_be_added").sum())},
           "reported": int(len(dated)), "confirmed": 0, "unknown": int((full["status"] == "UNKNOWN").sum()),
           "reported_rows_all_before_issue": bool(dated["before_issue"].all()),
           "reported_days_before_issue_min": int(dated["days_before_issue"].min()),
           "reported_later_than_day10": dated.loc[dated["release_date_YYYY_MM_DD"].str[8:].astype(int) > 10,
                                                  ["reference_month", "province", "release_date_YYYY_MM_DD", "issue_date"]].to_dict("records"),
           "saved_copies_named": int(dated["saved_evidence_filename"].notna().sum()),
           "rescore_can_run": False,
           "why_not": "the addendum needs every needed province-month confirmed; 0 are confirmed (no saved copies, and the release-date "
                      "vs page-date check is pending), 153 of 180 are unknown, and the two 'could_be_added' months are not collected",
           "erratum": "ADDENDUM_ROOT_CAUSE_RELEASE_DATES says 18 months; its rule 2 (every Lead-2+ row) needs the 36 months listed here"}
    v2 = T.DATA / "psa_cpi_release_dates_TO_FILL_v2.csv"
    if not v2.exists():                                   # create once; never overwrite the owner's working file
        tf = full.rename(columns={"issue_date": "must_be_released_before", "release_date_YYYY_MM_DD": "release_date_YYYY-MM-DD"})
        tf["priority"] = tf["in_first_list_of_18"].map({"True": "HIGH", "False": "needed"})
        tf.loc[tf["role"] == "could_be_added", "priority"] = "check: released before this date?"
        tf["is_release_date_printed_on_document"] = ""
        tf["confirmed_by_owner"] = ""
        cols = ["reference_month", "province", "must_be_released_before", "role", "priority", "release_date_YYYY-MM-DD", "source_type",
                "document_title", "source_url", "date_checked", "saved_evidence_filename", "is_release_date_printed_on_document",
                "confirmed_by_owner", "status"]
        tf[cols].to_csv(v2, index=False, lineterminator="\n")
    V = pd.read_csv(v2, dtype=str)
    res["v2_status"] = V["status"].value_counts().to_dict()
    res["confirmed"] = int((V["status"] == "confirmed").sum())
    res["rescore_can_run"] = bool(len(V) == 180 and (V["status"] == "confirmed").all())
    res["why_not"] = ("" if res["rescore_can_run"] else
                      f"the addendum needs all 180 province-months confirmed by the owner; v2 status now: {res['v2_status']}")
    T.OUT.joinpath("release_dates_review.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
