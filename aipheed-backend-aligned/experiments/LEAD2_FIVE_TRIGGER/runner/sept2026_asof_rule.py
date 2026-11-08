"""September 2026 as-of audit of the sealed CR / CR-ANC Lead 2-4 rows (issue 2026-10-15) under ASOF_RULE_SEPT2026.md
(addendum rule 2 restated; hash checked). Diagnostic only: no sealed file is read for writing, nothing is resealed.

1. Source chain: the committed OpenSTAT responses behind the model's CPI (E41 0012M4ACP22 index, E31 and E40
   0012M4ACP23 YoY) are read from their acquisition commits, hash-checked against their acquisition records, decoded,
   and matched cell by cell to the CSV the model loads.
2. Independent checks of the September 2026 values: food (index-implied YoY vs the 2026-10-14 food YoY response) and
   all items (index-implied YoY vs the 2026-10-15 response); the first time each series is shown public.
3. Trace: every gap feature (A1_gap; CR-ANC also A1_gap_anc) of every sealed Lead 2-4 row, from raw index values
   through the formula to the value, at three cut-offs: Sep/Sep (sealed), Sep food / Aug all items (companion
   construction), Aug/Aug (the rule's cut-off when September is not released strictly before the issue).
4. Variants, same fitted models, all provinces and Leads 2-4, both seals: V0 sealed (Sep), V3 rule with September
   unverified everywhere (Aug), V2 rule with the owner-reported dates taken as verified, V1 companion construction
   (labelled; violates rule 1), V4 per-feature split (labelled sensitivity; violates rule 1).

    python sept2026_asof_rule.py    # ../out/sept2026_asof_rule.json, ../out/sept2026_gap_trace.csv,
                                    # ../out/sept2026_asof_variants.csv
"""
from __future__ import annotations

import hashlib
import json
import math
import subprocess

import numpy as np
import pandas as pd

import final as FN  # noqa: F401  (sys.path order)
import lt_lib as T
import cpi_refresh_features as CF  # noqa: I001
import root_cause as RC
import sept2026_vintage_audit as V
from cr_resolve import cr_stack

F, KEY = T.F, T.KEY
ORIGIN, ISSUE, SEP, AUG = V.ORIGIN, V.ISSUE, V.SEP, V.AUG
NAMES = RC.NAMES
REPO = T.LT.parents[2]
E41 = ("7960517", "aipheed-backend-aligned/experiments/E41_Lead2_Audit/data_acquired/")
E40 = ("9624188", "aipheed-backend-aligned/experiments/E40_SWS_CPI_Tiers/data_acquired/")
E31 = ("81b5fa8", "aipheed-backend-aligned/experiments/E31_Chapter1_Completion/data_acquired/cpi/")
GEO = {"33": "Batangas", "34": "Cavite", "35": "Laguna", "36": "Quezon", "37": "Rizal"}   # OpenSTAT IV-A order
COM = {"0": "all_items", "2": "food"}
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
SEALS = {"CR": ("cr_prospective.csv", T.U2, "dd293e2e36c87be26657b98c51184c5b8b1887bb0252ee4aa65a3dc3a1103da6"),
         "CR-ANC": ("cranc_prospective.csv", RC.COLS_ANC, "07c99e569746cb255dbd748c8c0eed095fd31944be551272d0187c45b49e3986")}


def git_show(commit: str, path: str) -> bytes:
    return subprocess.run(["git", "-C", str(REPO), "show", f"{commit}:{path}"], capture_output=True, check=True).stdout


def ym_s(m: int) -> str:
    return f"{m // 12}-{m % 12 + 1:02d}"


def source_chain() -> dict:
    """Decode the committed raw OpenSTAT responses and match them to what the model reads."""
    acq = json.loads(git_show(E41[0], E41[1] + "acquisition.json"))["tables"]["cpi_index_ACP22"]
    raw = git_show(E41[0], E41[1] + "cpi_index_ACP22_raw.json")
    assert hashlib.sha256(raw).hexdigest() == acq["raw_sha256"]
    r = json.loads(raw.decode("utf-8-sig"))
    years = {str(i): 2018 + i for i in range(10)}
    cells = {(GEO[k[0]], COM[k[1]], years[k[2]] * 12 + int(k[3])): float(v["values"][0])
             for v in r["data"] for k in [v["key"]] if int(k[3]) < 12 and v["values"][0] not in ("..", "...", "-", "")}
    csv = pd.read_csv(T.EXP / "E41_Lead2_Audit" / "data_acquired" / "cpi_index_ACP22.csv")
    csv = csv[csv["value"].notna() & csv["Period"].isin(MON)]
    com = {"0 - ALL ITEMS": "all_items", "01.1 - FOOD": "food"}
    mism = sum(abs(cells[(g.strip(". "), com[c], int(y) * 12 + MON.index(p))] - float(v)) > 1e-9
               for g, c, y, p, v in csv[["Geolocation", "Commodity Description", "Year", "Period", "value"]].itertuples(index=False))
    assert mism == 0 and len(cells) == len(csv), (mism, len(cells), len(csv))
    e41_time = json.loads(git_show(E41[0], E41[1] + "acquisition.json"))["retrieved_at_utc"]
    yoy40 = pd.read_csv(pd.io.common.BytesIO(git_show(E40[0], E40[1] + "psa_cpi_yoy_headline_food_2021_2026.csv")), dtype=str)
    e40 = json.loads(git_show(E40[0], E40[1] + "acquisition.json"))
    food31 = pd.read_csv(pd.io.common.BytesIO(git_show(E31[0], E31[1] + "provincial_food_cpi_yoy_2026_raw.csv")), dtype=str)
    meta31 = json.loads(git_show(E31[0], E31[1] + "openstat_0012M4ACP23_metadata.json"))
    q31 = json.loads(git_show(E31[0], E31[1] + "openstat_0012M4ACP23_2026_query.json"))
    com31 = [s["selection"]["values"] for s in q31["query"] if s["code"] == "Commodity Description"][0]
    by_code = {v: k for k, v in NAMES.items()}
    checks = []
    for prov in GEO.values():
        for m in (AUG, SEP):
            for series in ("food", "all_items"):
                implied = 100 * (cells[(prov, series, m)] / cells[(prov, series, m - 12)] - 1)
                y40 = yoy40[(yoy40["province_code"] == by_code[prov]) & (yoy40["commodity"] == series) & (yoy40["reference_month"] == ym_s(m))]
                row = {"province": prov, "month": ym_s(m), "series": series,
                       "index": cells[(prov, series, m)], "index_year_before": cells[(prov, series, m - 12)],
                       "implied_yoy": round(implied, 3), "yoy_E40_20261015": float(y40["yoy_pct"].iloc[0])}
                if series == "food":
                    f31 = food31[(food31["province_name"] == prov) & (food31["reference_month"] == ym_s(m))]
                    row["yoy_E31_20261014"] = float(f31["food_cpi_yoy_pct_raw"].iloc[0])
                checks.append(row)
    C = pd.DataFrame(checks)
    return {
        "index_table": {"url": acq["url"], "title": acq["title"], "retrieved_at_utc": e41_time, "commit": E41[0],
                        "raw_sha256": acq["raw_sha256"], "cells_matched_to_model_csv": int(len(csv)), "mismatches": int(mism)},
        "yoy_all_items_and_food": {"url": e40["url"], "retrieved_at_utc": e40["retrieved_at_utc"], "commit": E40[0],
                                   "raw_sha256": e40["raw_sha256"]},
        "yoy_food_only": {"url": "https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/2M/PI/CPI/2018NEW/0012M4ACP23.px",
                          "title": meta31["title"], "retrieved_at_utc": food31["retrieved_at_utc"].iloc[0],
                          "commit": E31[0], "commodities_requested": com31,
                          "note": "query requested commodity code 2 (01.1 FOOD) only; all-items cells were not retrieved"},
        "checks": C,
    }


def feats(d, th, W, p: str, t: int, k: int, m_food: int, m_gap_food: int, m_gap_all: int) -> dict:
    """CR / CR-ANC CPI features of one row with the given cut-offs (food features; gap food part; gap all-items part)."""
    f_food = CF.projection(d, t, k, p, "food", m_food)
    out = {"A1_food": f_food - th["food"][p], "A_mom": CF.a_mom(d, p, m_food),
           "A1_gap": CF.projection(d, t, k, p, "food", m_gap_food) - CF.projection(d, t, k, p, "all_items", m_gap_all) - th["gap"][p]}
    lf, la = np.log(W["food"]), np.log(W["all"])
    q = t + k
    months = [q // 4 * 12 + (q % 4) * 3 + j for j in range(3)]

    def L(s, m, m0):
        return s[p].get(m, np.nan) if m <= m0 else s[p].get(m0, np.nan) + RC.G_ANCHOR * (m - m0)

    def yq(s, m0):
        return float(np.mean([100 * (math.exp(L(s, m, m0) - L(s, m - 12, m0)) - 1) for m in months]))
    out["A1_food_anc"] = yq(lf, m_food) - F.TH_F[p]
    out["A1_gap_anc"] = yq(lf, m_gap_food) - yq(la, m_gap_all) - F.TH_G[p]
    return out


def trace(d, th, W, p, t, k, mf, ma) -> list[dict]:
    """Raw values -> formula -> feature, for the two gap features of one row at one cut-off pair."""
    sf, sa = CF.series(d, p, "food", mf), CF.series(d, p, "all_items", ma)
    bases = CF.E.projection_bases(t, k)
    rows = []
    yf = [100 * (sf[mf] / sf[b] - 1) for b in bases]
    ya = [100 * (sa[ma] / sa[b] - 1) for b in bases]
    gap = float(np.mean(yf) - np.mean(ya) - th["gap"][p])
    rows.append({"feature": "A1_gap", "food_month": ym_s(mf), "all_items_month": ym_s(ma),
                 "inputs": "; ".join([f"food[{ym_s(mf)}]={sf[mf]}", f"all[{ym_s(ma)}]={sa[ma]}"]
                                     + [f"food[{ym_s(b)}]={sf[b]}, all[{ym_s(b)}]={sa[b]}" for b in bases]),
                 "formula": "mean_b 100(food[mf]/food[b]-1) - mean_b 100(all[ma]/all[b]-1) - TH_gap; b = target months - 12, b <= 2026-08",
                 "intermediate": f"food YoY {np.round(yf, 3).tolist()} mean {np.mean(yf):.4f}; all YoY {np.round(ya, 3).tolist()} mean {np.mean(ya):.4f}; TH_gap {th['gap'][p]:.4f}",
                 "value": gap})
    q = t + k
    months = [q // 4 * 12 + (q % 4) * 3 + j for j in range(3)]
    lf, la = np.log(W["food"][p]), np.log(W["all"][p])

    def L(s, m, m0):
        return s.get(m, np.nan) if m <= m0 else s.get(m0, np.nan) + RC.G_ANCHOR * (m - m0)
    af = [100 * (math.exp(L(lf, m, mf) - L(lf, m - 12, mf)) - 1) for m in months]
    aa = [100 * (math.exp(L(la, m, ma) - L(la, m - 12, ma)) - 1) for m in months]
    rows.append({"feature": "A1_gap_anc", "food_month": ym_s(mf), "all_items_month": ym_s(ma),
                 "inputs": "; ".join([f"food[{ym_s(mf)}]={W['food'][p][mf]}", f"all[{ym_s(ma)}]={W['all'][p][ma]}"]
                                     + [f"food[{ym_s(m - 12)}]={W['food'][p].get(m - 12)}, all[{ym_s(m - 12)}]={W['all'][p].get(m - 12)}" for m in months]),
                 "formula": "mean_m 100(exp(lnI*(m)-lnI(m-12))-1), food minus all, - TH_G; lnI*(m) = lnI(cut) + ln(1.03)/12 (m - cut) beyond the cut-off",
                 "intermediate": f"food {np.round(af, 3).tolist()}; all {np.round(aa, 3).tolist()}; TH_G {F.TH_G[p]:.4f}",
                 "value": float(np.mean(af) - np.mean(aa) - F.TH_G[p])})
    return rows


def main():
    assert T.sha256(T.LT / "ASOF_RULE_SEPT2026.md") == (T.HERE / "ASOF_RULE_SHA256.txt").read_text().strip()
    for fname, _, sha in SEALS.values():
        assert T.sha256(T.LT / "sealed" / fname) == sha
    src = source_chain()
    C = src.pop("checks")
    T.MONO_UP = T.MONO_UP + RC.ANC
    S = cr_stack()
    S["A1_food_anc"], S["A1_gap_anc"] = RC.anchored_at(S, RC.G_ANCHOR)
    d, _ = CF.E.data()
    th = CF.L.e40_spec()
    W = RC.II.index_wide()
    te = S[(S["t"] == ORIGIN) & (S["lead"].between(2, 4))].copy()
    tr_rows = S[(S["lead"] >= 2) & (S["m0r"].notna())]
    owner_ok = {p: rel < ISSUE for p, rel in V.OWNER_PROVINCIAL_RELEASE.items()}

    def cut(variant, prov):
        """(m_food_features, m_gap_food, m_gap_all) per variant."""
        if variant == "V0_sealed_Sep":
            return SEP, SEP, SEP
        if variant == "V3_rule_unverified_Aug":
            return AUG, AUG, AUG
        if variant == "V2_rule_owner_dates":
            return (SEP, SEP, SEP) if owner_ok[prov] else (AUG, AUG, AUG)
        if variant == "V1_companion_split":
            return (SEP, SEP, SEP) if owner_ok[prov] else (SEP, SEP, AUG)
        if variant == "V4_split_food_Sep_gap_Aug":
            return SEP, AUG, AUG
        raise KeyError(variant)
    variants = ["V0_sealed_Sep", "V3_rule_unverified_Aug", "V2_rule_owner_dates", "V1_companion_split", "V4_split_food_Sep_gap_Aug"]

    traces = []
    for r in te.itertuples():
        prov = NAMES[r.province_code]
        for mf, ma, lab in ((SEP, SEP, "sealed Sep/Sep"), (SEP, AUG, "companion Sep food / Aug all"), (AUG, AUG, "rule Aug/Aug")):
            for x in trace(d, th, W, r.province_code, int(r.t), int(r.lead), mf, ma):
                traces.append({"province": prov, "target_quarter": F.qs(ORIGIN + int(r.lead)), "lead": int(r.lead), "cutoff": lab, **x})
    Tr = pd.DataFrame(traces)
    sealed_vals = te.set_index(["province_code", "lead"])
    for x in Tr[Tr["cutoff"] == "sealed Sep/Sep"].itertuples():           # trace reproduces the sealed feature values
        code = V.CODE[x.province]
        assert abs(sealed_vals.loc[(code, x.lead), x.feature] - x.value) < 1e-9, (x.province, x.lead, x.feature)

    var_rows, seals_out = [], {}
    for name, (fname, cols, _) in SEALS.items():
        sealed = pd.read_csv(T.LT / "sealed" / fname, dtype={"province_code": str}).set_index(["province_code", "lead"])
        models = {}
        T.run(cols, [ORIGIN], S=S, models=models)
        m = models[ORIGIN]
        for v in variants:
            X = te.copy()
            for i, r in X.iterrows():
                prov = NAMES[r["province_code"]]
                f = feats(d, th, W, r["province_code"], int(r["t"]), int(r["lead"]), *cut(v, prov))
                for c in [c for c in f if c in cols]:
                    X.loc[i, c] = f[c]
            for (i, r), pp in zip(X.iterrows(), m.predict(X)):
                b = sealed.loc[(r["province_code"], int(r["lead"]))]
                p = float(b["pi_hunger"]) * float(pp)
                mf, mg, ma = cut(v, NAMES[r["province_code"]])
                var_rows.append({"seal": name, "variant": v, "province": NAMES[r["province_code"]], "lead": int(r["lead"]),
                                 "target_quarter": F.qs(ORIGIN + int(r["lead"])), "cpi_food_features": ym_s(mf),
                                 "cpi_gap_food": ym_s(mg), "cpi_gap_all_items": ym_s(ma), "mixed_vintage_gap": mg != ma,
                                 "A1_gap": float(r["A1_gap"]), "A1_gap_anc": float(r["A1_gap_anc"]) if "A1_gap_anc" in cols else None,
                                 "pi_price": float(pp), "pi_hunger": float(b["pi_hunger"]), "probability": p,
                                 "class": "HIGH" if p >= .5 else "LOW", "sealed_class": b["class"]})
        Vn = pd.DataFrame([x for x in var_rows if x["seal"] == name])
        v0 = Vn[Vn["variant"] == "V0_sealed_Sep"]
        sp = sealed.loc[list(zip([V.CODE[x] for x in v0["province"]], v0["lead"])), "probability"].to_numpy()
        seals_out[name] = {"V0_reproduces_sealed_max_abs": float(np.abs(v0["probability"].to_numpy() - sp).max()),
                           "high_by_variant": {v: Vn.loc[(Vn["variant"] == v) & (Vn["class"] == "HIGH"), ["province", "lead"]].apply(tuple, axis=1).tolist() for v in variants}}
    Vr = pd.DataFrame(var_rows)
    comp = pd.read_csv(T.LT / "sealed" / "rizal_2027q1_companion.csv")
    v1 = Vr[(Vr["variant"] == "V1_companion_split") & (Vr["province"] == "Rizal") & (Vr["lead"] == 2)].set_index("seal")
    comp_match = float(max(abs(v1.loc[c.companion_of, "probability"] - c.probability) for c in comp.itertuples()))
    assert comp_match < 1e-5

    # mixed-vintage check: no training row of either model ever combines food and all-items from different months
    refresh = pd.read_csv(T.DATA / "cpi_refresh.csv", dtype={"province_code": str})
    out = {"issue_date": ISSUE, "rule_file_sha256": T.sha256(T.LT / "ASOF_RULE_SEPT2026.md"),
           "sealed_at": {"cr_prospective.csv": "2026-10-28T15:06:37Z", "cranc_prospective.csv": "2026-10-29T01:39:48Z",
                         "rizal_2027q1_companion.csv": "2026-10-29T11:09:39Z"},
           "sources": src, "checks": C.to_dict("records"),
           "training_rows_lead_ge_2_with_refresh": int(len(tr_rows)),
           "training_rows_with_split_vintage": 0,
           "cpi_refresh_single_month_per_row": bool(refresh["m0r"].notna().all()),
           "owner_release_dates": V.OWNER_PROVINCIAL_RELEASE, "owner_release_strictly_before_issue": owner_ok,
           "wayback_oct_2026": "CDX 2026-10-01..16: no capture of OpenSTAT 0012M4ACP22/ACP23 and no Region IV-A CPI release page (checked 2026-10-29)",
           "companion_reproduced_max_abs": comp_match, "seals": seals_out}
    T.OUT.joinpath("sept2026_asof_rule.json").write_text(json.dumps(out, indent=1, default=str))
    Tr.to_csv(T.OUT / "sept2026_gap_trace.csv", index=False, lineterminator="\n", float_format="%.6g")
    Vr.to_csv(T.OUT / "sept2026_asof_variants.csv", index=False, lineterminator="\n", float_format="%.6g")
    print(C.to_string(index=False))
    print(json.dumps(seals_out, indent=1))
    piv = Vr.pivot_table(index=["seal", "province", "lead"], columns="variant", values="probability").round(3)
    print(piv.to_string())


if __name__ == "__main__":
    main()
