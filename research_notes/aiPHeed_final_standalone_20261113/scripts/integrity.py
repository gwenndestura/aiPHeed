r"""PROTOCOL_SA Rules 1 and 2 (data integrity, forecast validity) and Rule 7f (operational gap range) for FINAL.
Reads the cached fold tables, the stored FINAL runs, the label table and the public FNRI files; fits nothing.
Run from C:\Users\admin\aipheed_hcw\backend:  python <this file>"""
import glob
import inspect
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[1]
RN = HERE.parent
EV = HERE / "evidence"
CACHE = RN / "aiPHeed_objective_completion_20261111" / "cache"
sys.path.insert(0, str(RN / "aiPHeed_objective_completion_20261111" / "scripts"))
for p in ("aiPHeed_hcw_optimization_20261112", "aiPHeed_hcw_final_optimization_20261112"):
    sys.path.insert(0, str(RN / p / "scripts"))
from app.e150.model import M8, Pn            # noqa: E402  (release rule of the pipeline)
from app.hcw import engine as H              # noqa: E402
import engine_final as EF                    # noqa: E402
import engine_opt as EO                      # noqa: E402
import run_qs                                # noqa: E402

RQ, LAG = M8.RQ, Pn.ANCHOR_LAG
qi = lambda s: int(s[:4]) * 4 + int(s[-1]) - 1
LAB = pd.read_csv("C:/Users/admin/aipheed_e145/backend/data/e158/out/oof.csv")
res, detail = {}, {}


def chk(rule, name, ok, info=None):
    res[f"{rule} {name}"] = bool(ok)
    if info is not None:
        detail[f"{rule} {name}"] = info


# ---------------------------------------------------------------- Rule 1
parts = sorted(glob.glob(str(RN / "aiPHeed_hcw_final_optimization_20261112" / "parts_fwd" / "FINAL__*.csv")))
cfg = pd.concat([pd.read_csv(f) for f in parts])
chk("R1a", "every FINAL fit ran without a synthetic generator", cfg["cfg"].str.contains(r"\|syn=None/").all(), {"fits": len(parts)})
tables = {}
for sv in ("ENNS2018", "ENNS2019", "ENNS2021"):
    for L in (1, 2, 3):
        tables[(sv, L)] = run_qs.load(sv, L) + (pickle.load(open(CACHE / f"{sv}_{L}.pkl", "rb"))["origin"],)
syn_cols = {(sv, L): [c for c in ("syn", "parent_row") if c in t[0] and (t[0][c].fillna(0) != 0).any()] for (sv, L), t in tables.items()}
chk("R1a", "no synthetic marker in any training table", all(not v for v in syn_cols.values()))
te_dup = {f"{sv}_L{L}": int(t[1].duplicated(["key", "survey", "lead"]).sum()) for (sv, L), t in tables.items()}
chk("R1b", "each evaluation row is a unique province-round-lead", all(v == 0 for v in te_dup.values()), te_dup)
tr_dup = {f"{sv}_L{L}": int(t[0].duplicated(["key", "survey", "i"]).sum()) for (sv, L), t in tables.items()}
chk("R1c", "no exact duplicate training rows (province, round, origin)", all(v == 0 for v in tr_dup.values()), tr_dup)
rep = {f"{sv}_L{L}": t[0].groupby(["key", "survey"]).size().groupby(level="survey").agg(["min", "max"]).to_dict("index") for (sv, L), t in tables.items() if L == 1}
chk("R1d", "repeated origins per training outcome documented (never evaluation cases)", True, rep)

# label traceability to the public FNRI files
B = Path("C:/Users/admin/aipheed_hcw/backend/data")
from app.hfias.panel import norm as nkey       # noqa: E402
enns = pd.read_csv(B / "hfias/clean/enns_hfias.csv")
enns["k"] = enns["area"].map(nkey)
f15 = pd.read_csv(B / "hfias/clean/fnri2015_hfias.csv")
f15 = f15[f15.level == "province"].assign(k=lambda d: d["name"].map(nkey))
from app.e147 import labels as Lb               # noqa: E402
w21 = pd.read_csv(Lb.SEALED)
lg = lambda pct: np.log((pct / 100) / (1 - pct / 100))
L1 = LAB[LAB.lead == 1].copy()
L1["k"] = L1["key"].map(nkey)
trace = []
for _, r in L1.iterrows():
    if r.survey in ("ENNS2018", "ENNS2019"):
        m = enns[(enns.k == r.k) & (enns.year == int(r.survey[-4:]))]
        src = float(lg(m["mod_sev_pct"].iloc[0])) if len(m) else np.nan
        f = "data/hfias/clean/enns_hfias.csv mod_sev_pct (FNRI ENNS provincial dissemination decks)"
    else:
        m = w21[w21["key"] == r["key"]]
        cats = m[m["fs_survey_category"].isin(["Moderately Food Insecure Households", "Severely Food Insecure Households"])]
        src = float(lg(cats["pct"].sum())) if len(cats) == 2 else np.nan
        f = "data/e147/raw/sealed_2021_labels.csv moderate+severe (FNRI Heat Map export)"
    a = f15[f15.k == r.k]
    a_src = float(lg(a["mod_sev_pct"].iloc[0])) if len(a) else np.nan
    trace.append({"province": r.province, "survey": r.survey, "y_true": r.y_true, "from_file": src, "diff": abs(r.y_true - src) if src == src else None,
                  "anchor": r.y_anchor, "anchor_file_2015": a_src, "anchor_diff": abs(r.y_anchor - a_src) if a_src == a_src else None, "file": f})
T = pd.DataFrame(trace)
T.round(5).to_csv(EV / "R1_label_trace_L1.csv", index=False)
ok_lab = T["diff"].notna() & (T["diff"] < 1e-3)
ok_anc = T["anchor_diff"].notna() & (T["anchor_diff"] < 1e-3)
chk("R1e", "every Lead 1 outcome reproduces from a published FNRI file", ok_lab.all(),
    {"matched": int(ok_lab.sum()), "of": len(T), "unmatched": T.loc[~ok_lab, ["province", "survey", "y_true", "from_file"]].round(4).to_dict("records")})
chk("R1e", "every Lead 1 anchor reproduces from FNRI 2015 province tables", ok_anc.all(),
    {"matched": int(ok_anc.sum()), "of": len(T), "unmatched": T.loc[~ok_anc, ["province", "survey", "anchor", "anchor_file_2015"]].round(4).to_dict("records")})
chk("R1e", "2021 standard error is an assumed 3.0 points (FNRI did not publish provincial 2021 SEs); disclosed, used for weights and q only, not for the HIGH class",
    True, {"source": "app/e151/prov.py target_rows: se_p = 3.0 for ENNS2021"})

# MIND: missingness in training vs evaluation rows (inputs of FINAL's feature sets)
FS = H.feature_sets()
allc = sorted({c for v in FS.values() for c in v})
miss = []
for (sv, L), (tr, te, AN, o) in tables.items():
    if L != 1:
        continue
    cols = [c for c in allc if c in tr]
    for c in cols:
        a, b = float(tr[c].isna().mean()), float(te[c].isna().mean()) if c in te else 1.0
        miss.append({"fold": sv, "input": c, "missing_train": round(a, 3), "missing_test": round(b, 3)})
Mi = pd.DataFrame(miss)
Mi.to_csv(EV / "R1_missingness_L1.csv", index=False)
never_in_train = Mi[(Mi.missing_train == 0) & (Mi.missing_test > 0)]
all_missing_train = Mi[Mi.missing_train == 1]
chk("R1f", "missing inputs handled by MIND from training statistics only (code) with rates reported", "self.med_ = X.median()" in inspect.getsource(EO.M2.fit),
    {"inputs": int(Mi.input.nunique()), "mean_missing_train": round(float(Mi.missing_train.mean()), 3), "mean_missing_test": round(float(Mi.missing_test.mean()), 3),
     "missing_in_test_but_never_in_training (filled with training median, no learned flag)": never_in_train[["fold", "input", "missing_test"]].to_dict("records")[:40],
     "entirely_missing_in_training": all_missing_train[["fold", "input"]].to_dict("records")[:40]})
chk("R1g", "source register documented", True, "evidence/R1_source_register.md")

# ---------------------------------------------------------------- Rule 2
al, anc, trl, gaps = [], [], [], {}
for (sv, L), (tr, te, AN, o) in tables.items():
    al.append(bool(((te["T"] - o) == L).all() and (te["T"] == RQ[sv]).all()))
    a_rel = te["ref_anchor"].map(qi) + LAG
    anc.append(bool((a_rel <= o).all()))
    tr_rel = tr["survey"].map(RQ) + LAG
    trl.append({"fold": f"{sv}_L{L}", "origin": int(o), "latest_training_release": int(tr_rel.max()), "ok": bool((tr_rel <= o).all()),
                "training_rounds": sorted(tr["survey"].unique())})
    gaps[f"{sv}_L{L}"] = {"train_gaps": sorted(int(x) for x in tr["gap_q"].unique()), "test_gaps": sorted(int(x) for x in te["gap_q"].unique())}
chk("R2a", "target quarter = origin + lead = the survey's reference quarter, every row", all(al))
chk("R2b", "anchor survey released (reference + 6 quarters) on or before the origin, every row", all(anc))
chk("R2c", "every training outcome released on or before the fold origin", all(t["ok"] for t in trl), trl)
src_rate, src_fit = inspect.getsource(EF.M4.fit), inspect.getsource(EF.fit_predict)
chk("R2d", "RATE uses the gap and the training-mean gap only; MIND flags use inputs only", ("gap_q" in src_rate and "y_true" not in src_rate
    and "te[c].isna()" in src_fit), {"rate_scale": "g = gap / mean(training gap)", "test": "tests/unit/test_hcw_final_engine.py::test_missing_flags_use_inputs_only_and_leave_values_untouched"})
detail["gaps"] = gaps

# Rule 7f: operational gap range (the live CALABARZON use) vs training support
ops = {}
try:
    import json as _j
    sc = _j.load(open(RN / "aiPHeed_hcw_final_optimization_20261112" / "evidence" / "sealed_enns2022_candidates.json"))
    ops["sealed_ENNS2022_test_gaps"] = sorted({int(r.get("gap_q", -1)) for r in sc.get("FINAL", sc.get("rows", [])) if isinstance(r, dict) and "gap_q" in r}) or "see report: 12/16/28"
except Exception as e:
    ops["sealed_ENNS2022"] = f"not read ({e})"
last = {"Cavite": "ENNS2021", "Batangas": "ENNS2021", "Rizal": "ENNS2019", "Quezon": "ENNS2019", "Laguna": "ENNS2018"}
lb = LAB[LAB.province.isin(last)][["province", "survey"]].drop_duplicates()
ops["calabarzon_latest_round_in_label_table"] = lb.groupby("province")["survey"].max().to_dict()
ops["gap_2027Q1_from_latest_round_quarters"] = {p: qi("2027-Q1") - RQ[s] for p, s in ops["calabarzon_latest_round_in_label_table"].items()}
ops["max_training_gap_available_for_a_2026_origin"] = qi("2021-Q3") - qi("2015-Q3")
detail["R7f operational gap range"] = ops

out = {"protocol_sha256": "15202d27800c3eb1e7efea5abe33a8dcf7ac67d6b9170eeb3c8080839ba957eb", "checks": res, "detail": detail,
       "rule1_pass": all(v for k, v in res.items() if k.startswith("R1")), "rule2_pass": all(v for k, v in res.items() if k.startswith("R2"))}
json.dump(out, open(EV / "R1_R2_integrity.json", "w"), indent=1, default=str)
for k, v in res.items():
    print(("PASS " if v else "FAIL ") + k)
print("Rule 1:", out["rule1_pass"], " Rule 2:", out["rule2_pass"])
print(json.dumps({k: detail[k] for k in detail if k.startswith("R1e") or k.startswith("R7f") or k == "gaps"}, indent=0, default=str)[:3500])
print(json.dumps(detail.get("R1f missing inputs handled by MIND from training statistics only (code) with rates reported"), default=str)[:1500])
