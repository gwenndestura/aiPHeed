"""
E174: provenance ledger of every provincial food-security survey observation in the repository, its instrument, prior use in
E151-E173, and eligibility. Reads files only; E168, SIMPLE and every earlier artifact are untouched. No values are invented: an
observation enters the ledger only as it appears in a source file.

    python -m app.e174.ledger          writes backend/data/e174/independent_rows/*
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

import pandas as pd

from app.e151 import prov as Pv
from app.e150 import model as M
from app.e156 import leads as LD
from app.hfias.panel import norm as key
from app.paths import BACKEND_DIR

D = BACKEND_DIR / "data"
REPO = BACKEND_DIR.parent
OUT = D / "e174" / "independent_rows"
HEAT = D / "e147" / "raw" / "heatmap_provincial.jsonl"
FIES21 = REPO / "aipheed-backend-aligned" / "experiments" / "E87_Outcome_Gap" / "data_acquired" / "fnri_fies_observations.csv"
SDG = D / "fi_labels" / "clean" / "published_fies_psa_sdg212.csv"
ROUND = {"2011": "NNS/Updating 2011", "2013": "NNS2013", "2015": "FNRI2015", "2018": "ENNS2018", "2019": "ENNS2019", "2021": "ENNS2021"}
# Instrument per round, from the categories each round publishes (2011: household / mother-caregiver / child food insecurity, the
# Radimer-Cornell structure; 2013 onward: HFIAS food secure / mild / moderate / severe). 2011 is marked "verify" (inferred).
INSTRUMENT = {"2011": "Radimer-Cornell (inferred from categories; verify)", "2013": "HFIAS", "2015": "HFIAS", "2018": "HFIAS",
              "2019": "HFIAS", "2021": "HFIAS"}
PUBLISHED = {"2011": "2012", "2013": "2014-2015", "2015": "2016", "2018": "2019-2020", "2019": "2020", "2021": "2022"}


def _sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12]


def used_sets():
    """(key, survey) pairs E168 used: every label row of its training store (with 2021) and its 72-per-lead test rows."""
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    b = Pv.Store2(Pv.target_rows(with_2021=True)).base
    train = set(zip(b["key"], b["survey"]))
    F = pd.read_csv(D / "e168" / "out" / "oof.csv")
    test = set(zip(F["key"], F["survey"]))
    panel = set(b["key"])
    rounds = b.groupby("key")["survey"].apply(set).to_dict()
    return train, test, panel, rounds


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    train, test, panel, rounds = used_sets()
    h = pd.DataFrame([json.loads(l) for l in open(HEAT, encoding="utf-8")])
    dup = h.duplicated(["province_name", "actual_year", "fs_survey_category"], keep=False)
    obs = []
    for (name, yr), g in h.groupby(["province_name", "actual_year"]):
        if yr not in ROUND:                                    # '2018-2021' pooled rows: not a single survey round
            obs.append({"area": name, "year": yr, "status": "excluded", "reason": "pooled 2018-2021 row, not one survey round"})
            continue
        k, sv = key(name), ROUND[yr]
        cats = set(g["fs_survey_category"])
        has_ms = {"Moderately Food Insecure Households", "Severely Food Insecure Households"} <= cats
        d = bool(dup[g.index].any())
        is_city = " city" in f" {k}" or k.startswith("city of") or k == "pateros"
        prior = [r for r in rounds.get(k, set()) if r != sv and int(r[-4:]) < int(yr)]
        used = "test (E151-E173 evaluation rows)" if (k, sv) in test else "training/anchor (E151-E173)" if (k, sv) in train else "not used"
        if used != "not used":
            status, reason = "previously used", used
        elif INSTRUMENT[yr] != "HFIAS":
            status, reason = "excluded", "different instrument (not HFIAS); not combinable with the HFIAS target"
        elif d:
            status, reason = "excluded", "duplicate category rows in the Heat Map source"
        elif is_city:
            status, reason = "excluded", "city / HUC: no city-level model inputs, and no earlier own survey to anchor on"
        elif k not in panel:
            status, reason = "excluded", "area not in the forecasting panel (no region/inputs; e.g. created after 2015)"
        elif not prior:
            status, reason = "excluded", "no earlier own survey round to anchor the forecast"
        elif not has_ms and yr != "2011":
            status, reason = "excluded", "only the headline 'food insecure' share; moderate/severe split not published"
        else:
            status, reason = "eligible independent", "unused HFIAS province row with an earlier own round"
        obs.append({"source_record_id": f"HEAT-{yr}-{k.replace(' ', '_')}", "survey_round": sv, "year": int(yr), "area": name.title(), "key": k,
                    "level": "city/HUC" if is_city else "province", "instrument": INSTRUMENT[yr],
                    "outcome_definition": "share of households food insecure (any level) and moderate/severe categories, as published",
                    "categories_present": "; ".join(sorted(cats)), "raw_source": f"{HEAT.relative_to(REPO).as_posix()} (DOST-FNRI Heat Map API)",
                    "sampling_weight": "not in source (published estimate)", "fieldwork": yr, "published": PUBLISHED[yr],
                    "prior_use": used, "status": status, "reason": reason, "is_calabarzon": k in ("batangas", "cavite", "laguna", "quezon", "rizal")})
    O = pd.DataFrame(obs)
    # cross-source validation of unused rows: Heat Map 'Food Insecure Households' vs the ENNS publication's headline share
    e = pd.read_csv(D / "hfias" / "clean" / "enns_hfias.csv")
    e["key"], e["sv"] = e["area"].map(key), "ENNS" + e["year"].astype(str)
    ref = {(k, s): v for k, s, v in zip(e["key"], e["sv"], e["insecure_pct"].fillna(e["insecure_headline_pct"]))}
    hv = h[h["fs_survey_category"] == "Food Insecure Households"].assign(k=lambda x: x["province_name"].map(key))
    hv = {(k, ROUND.get(y)): float(v) for k, y, v in zip(hv["k"], hv["actual_year"], hv["fs_percentage"]) if v not in (None, "")}
    O["se_published"] = False
    O["cross_source_abs_diff"] = [abs(hv[(k, s)] - ref[(k, s)]) if (k, s) in ref and (k, s) in hv and pd.notna(ref[(k, s)]) else None
                                  for k, s in zip(O.get("key"), O.get("survey_round"))]
    bad = (O["status"] == "eligible independent") & (O["cross_source_abs_diff"].fillna(0) > 0.2)
    O.loc[bad, ["status", "reason"]] = ["excluded", "Heat Map and ENNS publication disagree (> 0.2 points); not reconciled"]
    # FIES provincial/regional observations (separate instrument; listed, never merged into the HFIAS target)
    f = pd.read_csv(FIES21)
    fies = [{"source_record_id": f"E87-{r.survey.replace(' ', '')}-{key(r.geography).replace(' ', '_')}-{r.indicator}", "survey_round": r.survey,
             "year": int(r.year), "area": r.geography, "key": key(r.geography), "level": r.level, "instrument": "FIES",
             "outcome_definition": r.indicator, "categories_present": r.indicator, "raw_source": f"{r.source_document} p.{r.page} ({r.source_url})",
             "sampling_weight": "not in source (published estimate)", "fieldwork": str(r.year), "published": "2022" if r.year == 2021 else str(r.year + 1),
             "prior_use": "not used as a target (E87/E129 external reference)",
             "status": "excluded",
             "reason": ("FIES, same ENNS 2021 households as the HFIAS row already tested" if r.year == 2021 and r.level == "province"
                        else "FIES; city/HUC" if "HUC" in r.level else "FIES; regional only"),
             "is_calabarzon": True} for r in f.itertuples(index=False)]
    s = pd.read_csv(SDG)
    sdg = [{"source_record_id": f"SDG212-{r.year}-{key(r.geography).replace(' ', '_')}", "survey_round": r.survey, "year": int(r.year), "area": r.geography,
            "key": key(r.geography), "level": r.level, "instrument": "FIES", "outcome_definition": r.category, "categories_present": r.category,
            "raw_source": str(r.source), "sampling_weight": "not in source", "fieldwork": str(r.year), "published": "PSA OpenSTAT",
            "prior_use": "face-validity reference only (E151, E166-E168 objectives)", "status": "excluded", "reason": f"FIES; {r.level} only",
            "is_calabarzon": "IV-A" in str(r.geography) or "CALABARZON" in str(r.geography)} for r in s.itertuples(index=False)]
    A = pd.concat([O[O["source_record_id"].notna()], pd.DataFrame(fies), pd.DataFrame(sdg)], ignore_index=True)
    pooled = O[O["source_record_id"].isna()]
    ind = A[A["status"] == "eligible independent"]
    ind.to_csv(OUT / "independent_rows.csv", index=False, lineterminator="\n")
    pd.concat([A[A["status"] == "excluded"], pooled.assign(source_record_id="HEAT-pooled-" + pooled["area"].str.replace(" ", "_"))],
              ignore_index=True).to_csv(OUT / "excluded_rows.csv", index=False, lineterminator="\n")
    A.to_csv(OUT / "observation_provenance.csv", index=False, lineterminator="\n")
    A.groupby(["instrument", "survey_round", "level", "status"]).size().rename("observations").reset_index().to_csv(
        OUT / "instrument_compatibility.csv", index=False, lineterminator="\n")
    A[A["is_calabarzon"].astype(bool)].groupby(["area", "survey_round", "instrument", "status"]).size().rename("n").reset_index().to_csv(
        OUT / "geographic_coverage.csv", index=False, lineterminator="\n")
    inv = [
        {"source": "DOST-FNRI Heat Map API (provincial bar charts)", "path": HEAT.relative_to(REPO).as_posix(), "rounds": "2011, 2013, 2015, 2018, 2019, 2021",
         "instrument": "Radimer-Cornell (2011, inferred); HFIAS (2013+)", "coverage": "124 areas (provinces and HUCs)", "rows": len(h), "sha256_12": _sha(HEAT),
         "existing_use": "E147+ label source (2018/2019 reconciled; 2021 sealed labels)"},
        {"source": "ENNS 2018/2019 HFIAS provincial tables", "path": "backend/data/hfias/clean/enns_hfias.csv", "rounds": "2018, 2019", "instrument": "HFIAS",
         "coverage": "38 + 38 areas", "rows": len(pd.read_csv(D / "hfias" / "clean" / "enns_hfias.csv")), "sha256_12": _sha(D / "hfias" / "clean" / "enns_hfias.csv"),
         "existing_use": "E137+ target (cities excluded)"},
        {"source": "FNRI 2015 Food Security Survey appendices", "path": "backend/data/hfias/clean/fnri2015_hfias.csv", "rounds": "2015", "instrument": "HFIAS",
         "coverage": "provinces", "rows": len(pd.read_csv(D / "hfias" / "clean" / "fnri2015_hfias.csv")), "sha256_12": _sha(D / "hfias" / "clean" / "fnri2015_hfias.csv"),
         "existing_use": "E137+ target / anchor"},
        {"source": "NNS 2013 HFIAS provincial", "path": "backend/data/hfias/clean/nns2013_hfias.csv" if (D / "hfias" / "clean" / "nns2013_hfias.csv").exists() else "backend/data/e141 clean nns2013_hfias.csv",
         "rounds": "2013", "instrument": "HFIAS", "coverage": "provinces", "rows": "", "sha256_12": "", "existing_use": "E141+ anchor"},
        {"source": "ENNS 2021 sealed provincial labels", "path": "backend/data/e147/raw/sealed_2021_labels.csv", "rounds": "2021", "instrument": "HFIAS",
         "coverage": "37 areas", "rows": len(pd.read_csv(D / "e147" / "raw" / "sealed_2021_labels.csv")), "sha256_12": _sha(D / "e147" / "raw" / "sealed_2021_labels.csv"),
         "existing_use": "E147+ held-out test round, used repeatedly since"},
        {"source": "ENNS 2021 provincial dissemination decks; 2023 NNS and 2025 Updating Survey regional decks", "path": FIES21.relative_to(REPO).as_posix(),
         "rounds": "2021 (province/HUC), 2023, 2025 (region)", "instrument": "FIES", "coverage": "Batangas, Cavite, Lucena City; CALABARZON", "rows": len(f),
         "sha256_12": _sha(FIES21), "existing_use": "E87/E129 external reference; never a target"},
        {"source": "PSA OpenSTAT SDG 2.1.2 (FNRI ENNS/NNS)", "path": SDG.relative_to(REPO).as_posix(), "rounds": "2019, 2021, 2023", "instrument": "FIES",
         "coverage": "national, regions", "rows": len(s), "sha256_12": _sha(SDG), "existing_use": "face validity only"},
        {"source": "Owner workbook (CALABARZON labelled provincial data)", "path": "backend/data/fi_labels/raw/owner_supplied/aiPHeed_CALABARZON_Labeled_Provincial_Data.xlsx",
         "rounds": "2015, 2018, 2019, 2021 (ENNS via RDP), 2023 (PSA subsistence, regional FIES)", "instrument": "HFIAS / FIES / PSA poverty", "coverage": "5 provinces",
         "rows": 50, "sha256_12": _sha(D / "fi_labels" / "raw" / "owner_supplied" / "aiPHeed_CALABARZON_Labeled_Provincial_Data.xlsx"),
         "existing_use": "verification of the same published rounds; no new survey round"},
        {"source": "2022 ENNS (FIES), about 20 provinces/HUCs", "path": "not in repository", "rounds": "2022 (Jul-Dec)", "instrument": "FIES", "coverage": "unverified",
         "rows": 0, "sha256_12": "", "existing_use": "listed in E129 inventory; DOST-FNRI request drafted (E87 request B), not sent"},
        {"source": "2024 POPCEN-CBMS SDG 2.1.2 (FIES) by LGU", "path": "not in repository", "rounds": "Jul 2023 - Jun 2024", "instrument": "FIES",
         "coverage": "LGU (aggregable to province)", "rows": 0, "sha256_12": "", "existing_use": "E129 inventory; PSA request drafted (E87 request A), not sent"},
        {"source": "Household microdata (any round: .dta/.sav/PUF)", "path": "none found in repository", "rounds": "", "instrument": "", "coverage": "", "rows": 0,
         "sha256_12": "", "existing_use": "eNutrition PUF pages returned HTTP 500 on 2026-11-07"},
    ]
    pd.DataFrame(inv).to_csv(OUT / "source_inventory.csv", index=False, lineterminator="\n")
    n = len(ind)
    ne = n / (1 + (LD.PER_CELL - 1) * LD.SHARED) if n else 0.0
    summ = {"generated_utc": datetime.now(timezone.utc).isoformat(), "heatmap_rows": len(h), "heatmap_duplicate_category_rows": int(dup.sum()),
            "observations": int(len(A)), "by_status": A["status"].value_counts().to_dict(), "by_instrument": A["instrument"].value_counts().to_dict(),
            "previously_used": int((A["status"] == "previously used").sum()), "eligible_independent_HFIAS": n,
            "eligible_independent_CALABARZON": int(ind["is_calabarzon"].astype(bool).sum()) if n else 0,
            "independent_distinct_provinces": int(ind["key"].nunique()) if n else 0, "independent_distinct_rounds": int(ind["survey_round"].nunique()) if n else 0,
            "effective_n_existing_method": round(ne, 1), "C1_C6_evaluable": bool(n >= 40),
            "excluded_reasons": A[A["status"] == "excluded"]["reason"].value_counts().to_dict()}
    (OUT / "summary.json").write_text(json.dumps(summ, indent=1), newline="\n")
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    build()
