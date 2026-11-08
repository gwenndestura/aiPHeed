"""
scripts/build_lgu_psa_2021_2024.py
----------------------------------
Rebuild the 142-LGU vulnerability inputs from two PSA workbooks downloaded by the researcher (psa.gov.ph blocks
automated access, so they are supplied by hand):

  * SAE  "2018 - 2021 SAE_with PSGC_noHUC.xlsx", sheet "2018-2021_NoHUC". Only the 2021 columns are read (poverty
         incidence, coefficient of variation, 90% CI). The 2018 columns are never loaded (study window 2021-2026).
         The table excludes highly urbanized cities, so Lucena City has no value in it.
  * POP  "3_Table B - Population and Annual PGR by Province, City, and Municipality - By Region - rev_0.xlsx",
         sheet "R04A". Only the 01-Jul-24 column (2024 Census of Population, POPCEN) is read; the 2010, 2015 and 2020
         columns and the growth rates are skipped.

Writes (all or nothing; any failed check raises before the first write):
  data/reference/sae2021_calabarzon_municipal.csv     141 LGUs, PSA 2021 SAE as published
  data/reference/popcen2024_calabarzon_municipal.csv  142 LGUs, 2024 POPCEN totals
  data/reference/psa_lgu_2021_2024_provenance.json    workbook hashes, columns read, checks, replaced values
  data/reference/calabarzon_lgus.csv                  population_2020 -> population_2024, pop_source popcen2024
  data/inputs/lgu_vulnerability.csv                   population_2024 + PSA 2021 municipal SAE
  data/inbox/lgu_vulnerability_v2.csv (+ .manifest.json)  registers vintage 2 at the next quarterly cycle

Usage:
  python scripts/build_lgu_psa_2021_2024.py --sae <SAE.xlsx> --pop <TableB.xlsx> [--dry-run]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "data" / "reference"
ROSTER = REF / "calabarzon_lgus.csv"
VULN = ROOT / "data" / "inputs" / "lgu_vulnerability.csv"
INBOX = ROOT / "data" / "inbox"

SAE_SHEET, POP_SHEET, POP_COLUMN = "2018-2021_NoHUC", "R04A", "01-Jul-24"
SAE_YEAR = 2021
PROVINCE_PREFIX = {"0410": "Batangas", "0421": "Cavite", "0434": "Laguna", "0456": "Quezon", "0458": "Rizal"}
# Highly urbanized cities are not in the no-HUC SAE table; they keep the province substitute, labelled as such.
HUC_NOT_IN_SAE = {"045624000": "Lucena"}
SAE_SOURCE = "PSA 2021 City and Municipal Level Small Area Estimates of Poverty (no-HUC table)"
# The substitute is the province value already stored in the inputs (4.3/4.2/16.8/3.5/7.1, from
# fix_primary_data.PROVINCE_POVERTY_2021). No source workbook for it is in the repository, and it is lower than the
# population-weighted mean of the supplied municipal SAE (Quezon 19.7), so it is labelled as unverified (E36).
SUBSTITUTE_SOURCE = ("province value stored in the aiPHeed inputs (labelled PSA 2021 province poverty incidence; "
                     "source workbook not in the repository, unverified), used because this highly urbanized city "
                     "is excluded from the PSA no-HUC table")

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}


# ------------------------------------------------------------------------------------------------ xlsx (stdlib)
def _col(ref: str) -> int:
    n = 0
    for ch in re.match(r"[A-Z]+", ref).group(0):
        n = n * 26 + ord(ch) - 64
    return n - 1


def read_sheet(path: Path, sheet: str) -> list[list]:
    """Cell values of one worksheet, row by row (no openpyxl in the backend environment)."""
    z = zipfile.ZipFile(path)
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS):
            shared.append("".join(t.text or "" for t in si.iter(f"{{{NS['m']}}}t")))
    rels = {r.get("Id"): r.get("Target") for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))}
    for sh in ET.fromstring(z.read("xl/workbook.xml")).find("m:sheets", NS):
        if sh.get("name") != sheet:
            continue
        target = rels[sh.get(f"{{{NS['r']}}}id")].lstrip("/")
        target = target if target.startswith("xl/") else "xl/" + target
        rows = []
        for row in ET.fromstring(z.read(target)).iter(f"{{{NS['m']}}}row"):
            vals = {}
            for c in row.findall("m:c", NS):
                t, v = c.get("t"), c.find("m:v", NS)
                if t == "s" and v is not None:
                    val = shared[int(v.text)]
                elif t == "inlineStr":
                    val = "".join(x.text or "" for x in c.iter(f"{{{NS['m']}}}t"))
                elif v is None:
                    val = None
                elif t in ("str", "e"):
                    val = v.text
                else:
                    f = float(v.text)
                    val = int(f) if f.is_integer() else f
                vals[_col(c.get("r"))] = val
            rows.append([vals.get(i) for i in range(max(vals) + 1)] if vals else [])
        return rows
    raise ValueError(f"{path.name}: sheet {sheet!r} not found")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def name_key(s: str) -> str:
    """'CITY OF DASMARIÑAS' / 'Dasmariñas' / 'City of Calaca 1' -> 'DASMARIAS' / 'DASMARIAS' / 'CALACA'.

    Ñ is dropped rather than folded because the POPCEN workbook stores it as U+FFFD."""
    s = re.sub(r"[ÑñÑ�]", "", str(s))
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().upper()
    s = re.sub(r"\(.*?\)", "", s)                       # 'Rodriguez (Montalban)'
    s = re.sub(r"[\d*]+", "", s).strip()                # footnote markers
    s = re.sub(r"^CITY OF\s+|\s+CITY$", "", s)
    return re.sub(r"[^A-Z]", "", s)


# ------------------------------------------------------------------------------------------------ SAE 2021
def parse_sae(path: Path) -> pd.DataFrame:
    rows = read_sheet(path, SAE_SHEET)
    h = next(i for i, r in enumerate(rows) if r and r[0] == "PSGC")
    yr = next(i for i in range(h, h + 5) if SAE_YEAR in rows[i])
    width = max(len(rows[i]) for i in range(h, yr + 2))
    group = year = None
    cols = {}
    for c in range(width):
        g = rows[h][c] if c < len(rows[h]) else None
        y = rows[yr][c] if c < len(rows[yr]) else None
        sub = rows[yr + 1][c] if c < len(rows[yr + 1]) else None
        group = g or group
        year = y if isinstance(y, int) else (year if sub == "Upper Limit" else None)
        if year != SAE_YEAR:
            continue
        if group == "Poverty Incidence":
            cols["poverty_incidence_2021"] = c
        elif group == "Coefficient of Variation":
            cols["cv_2021"] = c
        elif group == "90% Confidence Interval" and sub == "Lower Limit":
            cols["ci90_low_2021"] = c
        elif group == "90% Confidence Interval" and sub == "Upper Limit":
            cols["ci90_high_2021"] = c
    need = {"poverty_incidence_2021", "cv_2021", "ci90_low_2021", "ci90_high_2021"}
    if set(cols) != need:
        raise ValueError(f"SAE 2021 columns not found: {sorted(need - set(cols))}")
    out = []
    for r in rows[yr + 2:]:
        if not r or not isinstance(r[0], int):
            continue
        code = str(r[0]).zfill(6) + "000"              # 6-digit RRPPMM -> legacy 9-digit RRPPMMBBB
        if code[:4] not in PROVINCE_PREFIX:
            continue
        rec = {"lgu_code": code, "name_source": str(r[2]).strip(), "province": PROVINCE_PREFIX[code[:4]]}
        rec.update({k: (round(float(r[c]), 6) if c < len(r) and r[c] is not None else None)
                    for k, c in cols.items()})
        out.append(rec)
    df = pd.DataFrame(out)
    df.attrs["columns_read"] = {k: f"column {c + 1}" for k, c in cols.items()}
    return df


# ------------------------------------------------------------------------------------------------ POPCEN 2024
def parse_popcen(path: Path) -> tuple[pd.DataFrame, dict]:
    rows = read_sheet(path, POP_SHEET)
    hdr = next(i for i, r in enumerate(rows) if POP_COLUMN in r)
    c24 = rows[hdr].index(POP_COLUMN)
    provinces = {name_key(p): p for p in PROVINCE_PREFIX.values()}
    region_total, totals, lgus = None, {}, []
    province, after_blank = None, False
    for r in rows[hdr + 1:]:
        label = r[0] if r else None
        if label is None or (isinstance(label, str) and not label.strip()):
            after_blank = True
            continue
        if isinstance(label, str) and label.strip().startswith("Notes"):
            break
        value = r[c24] if c24 < len(r) else None
        key = name_key(label)
        if "CALABARZON" in str(label).upper():
            region_total = int(value)
        elif after_blank and key == "LUCENA":         # HUC, listed after Quezon ("* Excludes City of Lucena")
            lgus.append({"province": "Quezon", "name_source": label.strip(), "key": key, "population_2024": int(value),
                         "in_province_total": False})
        elif after_blank and key in provinces:
            province = provinces[key]
            totals[province] = int(value)
        else:
            lgus.append({"province": province, "name_source": label.strip(), "key": key,
                         "population_2024": int(value), "in_province_total": True})
        after_blank = False
    df = pd.DataFrame(lgus)
    sums = df[df["in_province_total"]].groupby("province")["population_2024"].sum().to_dict()
    checks = {"province_totals": totals, "sum_of_lgus_by_province": sums,
              "province_sums_match": sums == totals and len(totals) == 5,
              "region_total": region_total,
              "region_matches_provinces_plus_huc": region_total == sum(totals.values())
              + int(df.loc[~df["in_province_total"], "population_2024"].sum()),
              "column_read": f"{POP_COLUMN} (column {c24 + 1})"}
    return df, checks


# ------------------------------------------------------------------------------------------------ build
def build(sae_path: Path, pop_path: Path, dry_run: bool = False) -> dict:
    roster = pd.read_csv(ROSTER, dtype={"lgu_psgc": str})
    vuln = pd.read_csv(VULN, dtype={"lgu_code": str})
    assert len(roster) == 142 and roster["lgu_psgc"].is_unique
    problems = []

    # --- SAE: join by PSGC
    sae = parse_sae(sae_path)
    codes = set(roster["lgu_psgc"])
    extra = sorted(set(sae["lgu_code"]) - codes)
    missing = sorted(codes - set(sae["lgu_code"]))
    if extra:
        problems.append(f"SAE codes not in roster: {extra}")
    if sorted(missing) != sorted(HUC_NOT_IN_SAE):
        problems.append(f"roster LGUs without SAE other than the known HUC: {sorted(set(missing) - set(HUC_NOT_IN_SAE))}")
    if sae["lgu_code"].duplicated().any():
        problems.append("duplicate SAE codes")
    bad = sae[(sae["poverty_incidence_2021"] < 0) | (sae["poverty_incidence_2021"] > 100)
              | sae["poverty_incidence_2021"].isna()]
    if len(bad):
        problems.append(f"SAE values missing or out of range: {bad['lgu_code'].tolist()}")
    sae = sae.merge(roster[["lgu_psgc", "lgu_name", "lgu_aliases"]], left_on="lgu_code", right_on="lgu_psgc")
    name_bad = [(r.lgu_code, r.name_source, r.lgu_name) for r in sae.itertuples()
                if name_key(r.name_source) not in {name_key(a) for a in [r.lgu_name]
                                                   + str(r.lgu_aliases if pd.notna(r.lgu_aliases) else "").split("|")
                                                   if a}]
    if name_bad:
        problems.append(f"SAE PSGC/name disagreements: {name_bad}")

    # --- POPCEN: join by name within province
    pop, pop_checks = parse_popcen(pop_path)
    if not (pop_checks["province_sums_match"] and pop_checks["region_matches_provinces_plus_huc"]):
        problems.append(f"POPCEN totals do not add up: {pop_checks}")
    lookup = {}
    for r in roster.itertuples():
        for a in [r.lgu_name] + (str(r.lgu_aliases).split("|") if pd.notna(r.lgu_aliases) else []):
            lookup.setdefault((r.province_name, name_key(a)), set()).add(r.lgu_psgc)
    pop["lgu_code"] = [next(iter(lookup.get((p, k), {None}))) if len(lookup.get((p, k), ())) <= 1 else None
                       for p, k in zip(pop["province"], pop["key"])]
    if pop["lgu_code"].isna().any():
        problems.append(f"POPCEN names not matched: {pop.loc[pop['lgu_code'].isna(), 'name_source'].tolist()}")
    if pop["lgu_code"].dropna().duplicated().any() or set(pop["lgu_code"].dropna()) != codes:
        problems.append("POPCEN does not match the 142 roster LGUs one-to-one")
    if (pop["population_2024"] <= 0).any():
        problems.append("non-positive POPCEN population")
    if problems:
        raise SystemExit("REFUSED, nothing written:\n  " + "\n  ".join(problems))

    # --- reference tables
    sae_out = sae[["lgu_code", "name_source", "province", "poverty_incidence_2021", "cv_2021",
                   "ci90_low_2021", "ci90_high_2021"]].sort_values("lgu_code").reset_index(drop=True)
    pop_out = pop[["lgu_code", "name_source", "province", "population_2024"]].sort_values("lgu_code").reset_index(drop=True)

    # --- roster: replace the 2020 population with 2024
    pmap = dict(zip(pop_out["lgu_code"], pop_out["population_2024"]))
    new_roster = roster.copy()
    new_roster.insert(new_roster.columns.get_loc("population_2020"), "population_2024",
                      new_roster["lgu_psgc"].map(pmap).astype(int))
    new_roster = new_roster.drop(columns="population_2020")
    new_roster["pop_source"] = "popcen2024"

    # --- vulnerability input
    smap = sae_out.set_index("lgu_code")
    v = vuln.copy()
    old = v.set_index("lgu_code")
    v["population_2024"] = v["lgu_code"].map(pmap).astype(int)
    v["poverty_lgu_estimate"] = v["lgu_code"].map(smap["poverty_incidence_2021"])
    v["poverty_cv"] = v["lgu_code"].map(smap["cv_2021"]).round(4)
    has = v["poverty_lgu_estimate"].notna()
    # an LGU without a municipal estimate takes the province value the previous table used for its province's
    # substitutes (one value per province); it never keeps its own former, unverified LGU value
    was_sub = vuln["poverty_lgu_estimate"].isna()
    prov_value = vuln[was_sub].groupby("province")["poverty_value_used"].agg(["nunique", "first"])
    assert (prov_value["nunique"] == 1).all(), "previous substitutes are not one value per province"
    v["poverty_value_used"] = v["poverty_lgu_estimate"].where(has, v["province"].map(prov_value["first"]))
    v["poverty_source"] = [f"{SAE_SOURCE} (LGU-specific SAE)" if h else SUBSTITUTE_SOURCE for h in has]
    v = v[["lgu_code", "lgu_name", "lgu_type", "province", "population_2024", "land_area_km2",
           "poverty_lgu_estimate", "poverty_cv", "poverty_source", "poverty_value_used"]]
    assert len(v) == 142 and int(has.sum()) == 141 and v["poverty_value_used"].notna().all()

    replaced = [{"lgu_code": c, "lgu_name": old.at[c, "lgu_name"], "old_value": float(old.at[c, "poverty_lgu_estimate"]),
                 "official_2021": (None if pd.isna(v.set_index("lgu_code").at[c, "poverty_lgu_estimate"])
                                   else float(v.set_index("lgu_code").at[c, "poverty_lgu_estimate"]))}
                for c in old.index[old["poverty_lgu_estimate"].notna()]]
    cv = v["poverty_cv"].dropna()
    prov = {
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rule": "study window 2021-2026: only the SAE 2021 columns and the POPCEN 2024 column are read",
        "sae": {"file": sae_path.name, "sha256": sha256(sae_path), "sheet": SAE_SHEET,
                "columns_read": sae.attrs.get("columns_read") or parse_sae(sae_path).attrs["columns_read"],
                "reference_year": SAE_YEAR, "calabarzon_rows": int(len(sae_out)),
                "matched_by": "PSGC (6-digit RRPPMM in the workbook -> legacy 9-digit)",
                "not_in_table": {c: f"{n}: highly urbanized city, excluded from the no-HUC table"
                                 for c, n in HUC_NOT_IN_SAE.items()},
                "cv_over_20pct": v.loc[v["poverty_cv"] > 20, ["lgu_code", "lgu_name", "poverty_cv"]]
                .to_dict("records"),
                "cv_summary": {"median": round(float(cv.median()), 2), "max": round(float(cv.max()), 2)}},
        "popcen": {"file": pop_path.name, "sha256": sha256(pop_path), "sheet": POP_SHEET,
                   "census_date": "2024-07-01", "lgus": int(len(pop_out)),
                   "matched_by": "name within province (Table B has no PSGC); every roster LGU matched once",
                   **pop_checks},
        "land_area_km2": "unchanged from data/reference/calabarzon_lgus.csv (not part of either workbook)",
        "replaced_lgu_specific_values": replaced,
        "counts": {"municipal_sae": int(has.sum()), "province_substitute": int((~has).sum())},
    }

    manifest = {
        "source_id": "lgu_vulnerability", "kind": "static", "path": "lgu_vulnerability_v2.csv",
        "sha256": None, "observation_start": "2021-Q1", "observation_end": "2024-Q3",
        "available_at": "2025-06-18T16:01:34+00:00",
        "authorized_by": "researcher: downloaded both PSA workbooks by hand and asked for their integration (2026-10-15)",
        "authorization_ref": "data/reference/psa_lgu_2021_2024_provenance.json",
        "revision_note": "vintage 2: PSA 2021 municipal SAE for 141 LGUs (was 16 unverified values) and 2024 POPCEN "
                         "population (was 2020 CPH); available_at = POPCEN workbook creation time",
        "granularity": "lgu",
        "required_columns": ["lgu_code", "population_2024", "land_area_km2", "poverty_lgu_estimate",
                             "poverty_value_used"],
    }
    if dry_run:
        return prov

    REF.mkdir(parents=True, exist_ok=True)
    INBOX.mkdir(parents=True, exist_ok=True)
    kw = {"index": False, "lineterminator": "\n"}
    sae_out.to_csv(REF / "sae2021_calabarzon_municipal.csv", **kw)
    pop_out.to_csv(REF / "popcen2024_calabarzon_municipal.csv", **kw)
    new_roster.to_csv(ROSTER, **kw)
    v.to_csv(VULN, **kw)
    (INBOX / "lgu_vulnerability_v2.csv").write_bytes(VULN.read_bytes())
    manifest["sha256"] = sha256(INBOX / "lgu_vulnerability_v2.csv")
    (INBOX / "lgu_vulnerability_v2.manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    (REF / "psa_lgu_2021_2024_provenance.json").write_text(json.dumps(prov, indent=1, ensure_ascii=False) + "\n",
                                                          encoding="utf-8")
    return prov


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sae", required=True, type=Path)
    ap.add_argument("--pop", required=True, type=Path)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    prov = build(a.sae, a.pop, a.dry_run)
    print(json.dumps({k: prov[k] for k in ("counts", "replaced_lgu_specific_values")}, indent=1))
    print("popcen checks:", {k: prov["popcen"][k] for k in ("province_sums_match", "region_matches_provinces_plus_huc")})
    print("SAE CV>20%:", len(prov["sae"]["cv_over_20pct"]), "| dry run" if a.dry_run else "| written")


if __name__ == "__main__":
    main()
