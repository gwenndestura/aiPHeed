"""
scripts/run_simple_method.py
----------------------------
Runs the simple aiPHeed methodology end to end (protocol: aipheed-backend-aligned/experiments/E106_Simple_Methodology/
PROTOCOL.md): the rolling-origin evaluation of SM and every comparison arm at Leads 1-3, and the current forecast
record (origin 2026-Q3: Lead 1 -> 2026-Q4, Lead 2 -> 2027-Q1) with LGU rankings and a prospective seal.

    cd backend && venv/Scripts/python.exe -B scripts/run_simple_method.py

Writes backend/data/simple_method/ only. Refuses to run if the protocol changed, and checks that no other file under
backend/data or the E100-E105 experiment folders changed during the run.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import binomtest  # noqa: E402
from sklearn.impute import SimpleImputer  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import roc_auc_score  # noqa: E402
from sklearn.pipeline import make_pipeline  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

from app.ml import simple_method as S  # noqa: E402

OUT = BACKEND / "data/simple_method"
EXP = S.REPO / "aipheed-backend-aligned/experiments"
PROTOCOL = EXP / "E106_Simple_Methodology/PROTOCOL.md"
E63 = EXP / "E63_Lead_Time_Study/sealed/predictions.csv"
EVAL_TARGETS = {1: ("2023-Q4", "2026-Q3"), 2: ("2024-Q2", "2026-Q3"), 3: ("2024-Q3", "2026-Q3")}
CURRENT_ORIGIN = "2026-Q3"


def verify_protocol() -> str:
    for name, sha_file in (("PROTOCOL.md", "PROTOCOL_SHA256.txt"), ("ADDENDUM_1.md", "ADDENDUM_1_SHA256.txt")):
        want = (PROTOCOL.parent / "runner" / sha_file).read_text().split()[0]
        got = hashlib.sha256((PROTOCOL.parent / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        assert got == want, f"E106 {name} changed after freezing"
    return hashlib.sha256(PROTOCOL.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def protected_hashes() -> dict:
    files = [p for p in (BACKEND / "data").rglob("*") if p.is_file() and "simple_method" not in p.parts]
    files += [p for d in EXP.glob("E10[0-5]_*") for p in d.rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files) if p.suffix != ".db"}


# ------------------------------------------------------------------------------------------------ arms
def logistic(tr: pd.DataFrame, cols):
    if len(tr) < S.MIN_TRAIN or tr["y"].nunique() < 2:
        return float(tr["y"].mean()) if len(tr) else 0.5
    m = make_pipeline(SimpleImputer(strategy="median", keep_empty_features=True), StandardScaler(),
                      LogisticRegression(C=1.0, max_iter=1000))
    return m.fit(tr[cols].astype(float), tr["y"].to_numpy(int))


def lpredict(model, x: dict, cols) -> float:
    if isinstance(model, float):
        return model
    return float(model.predict_proba(pd.DataFrame([{c: np.nan if x[c] is None else float(x[c]) for c in cols}]))[0, 1])


def with_news_flag(df_or_x):
    if isinstance(df_or_x, pd.DataFrame):
        df_or_x = df_or_x.copy()
        df_or_x["NEWS_missing"] = df_or_x["NEWS"].isna().astype(float)
        return df_or_x
    return {**df_or_x, "NEWS_missing": 1.0 if df_or_x.get("NEWS") is None else 0.0}


def persistence(t: int, p: str) -> float | None:
    for q in range(t - 1, S.qi("2021-Q1") - 1, -1):
        if S.label_known(q, t, needs_sws=True):
            y = S.target_label(p, q)
            if y is not None:
                return float(y)
    return None


def run_lead(lead: int, e56: dict, e56_price: dict) -> pd.DataFrame:
    a, b = EVAL_TARGETS[lead]
    rows = []
    for t in range(S.qi(a) - lead, S.qi(b) - lead + 1):
        q = t + lead
        ph = {r: S.p_hunger(t, lead, r)[0] for r in ("rw", "ma2", "ar1d")}
        price_model = S.fit_lgbm(S.training_rows(t, lead, "price", S.PRICE_FEATURES), S.PRICE_FEATURES)
        tr_all = S.training_rows(t, lead, "target", S.ALL_FEATURES)
        sm1 = S.fit_lgbm(tr_all, S.ALL_FEATURES)
        psa_cols, nlp_cols = ["F_last", "RICE", "UNEMP"], ["NEWS", "NEWS_missing"]
        tr_flag = with_news_flag(tr_all) if len(tr_all) else tr_all
        m_psa = logistic(tr_all, psa_cols)
        m_nlp = logistic(tr_flag, nlp_cols)
        m_log = logistic(tr_all, S.ALL_FEATURES)
        share = float(tr_all["y"].mean()) if len(tr_all) else 0.5
        for p in S.PROVINCES:
            y = S.target_label(p, q)
            if y is None:
                continue
            x = S.features(t, p)
            pp = S.predict(price_model, x, S.PRICE_FEATURES)
            rows.append({"lead": lead, "origin": S.qs(t), "target": S.qs(q), "province_code": p, "y": int(y),
                         "hunger_obs": S.outcome(q), "SM": None if ph["rw"] is None else ph["rw"] * pp,
                         "SM_MA2": None if ph["ma2"] is None else ph["ma2"] * pp,
                         "SM_AR1D": None if ph["ar1d"] is None else ph["ar1d"] * pp,
                         "SM_B": (None if ph["rw"] is None or e56_price.get((lead, t, p)) is None
                                  else ph["rw"] * e56_price[(lead, t, p)]),    # Addendum 1
                         "P_hunger": ph["rw"], "P_price": pp, "SM1": S.predict(sm1, x, S.ALL_FEATURES),
                         "E56": e56.get((lead, t, p)), "Persistence": persistence(t, p),
                         "PSA_only": lpredict(m_psa, x, psa_cols), "NLP_only": lpredict(m_nlp, with_news_flag(x), nlp_cols),
                         "Logistic": lpredict(m_log, x, S.ALL_FEATURES),
                         "Majority": float(share >= 0.5), "Climatology": share, "train_rows_target": int(len(tr_all))})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------ metrics
def wilson(k, n, z=1.959964):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [float(c - h), float(c + h)]


def metrics(y, p) -> dict:
    y, p = np.asarray(y, int), np.asarray(p, float)
    yh = (p >= 0.5).astype(int)
    tp, tn = int(((yh == 1) & (y == 1)).sum()), int(((yh == 0) & (y == 0)).sum())
    fp, fn = int(((yh == 1) & (y == 0)).sum()), int(((yh == 0) & (y == 1)).sum())
    r = lambda a, b: a / (a + b) if a + b else None  # noqa: E731
    pre_h, rec_h, pre_l, rec_l = r(tp, fp), r(tp, fn), r(tn, fn), r(tn, fp)
    f1 = lambda a, b: 2 * a * b / (a + b) if a and b else (0.0 if a is not None and b is not None else None)  # noqa: E731
    n = len(y)
    return {"rows": n, "HIGH": int(y.sum()), "accuracy": (tp + tn) / n, "accuracy_wilson95": wilson(tp + tn, n),
            "balanced_accuracy": None if rec_h is None or rec_l is None else (rec_h + rec_l) / 2,
            "precision_HIGH": pre_h, "recall_HIGH": rec_h, "f1_HIGH": f1(pre_h, rec_h),
            "precision_LOW": pre_l, "recall_LOW": rec_l, "f1_LOW": f1(pre_l, rec_l),
            "auc_roc": float(roc_auc_score(y, p)) if 0 < y.sum() < n else None, "brier": float(np.mean((p - y) ** 2)),
            "share_predicted_HIGH": float(yh.mean()), "confusion": {"TP": tp, "FP": fp, "FN": fn, "TN": tn}}


def by_quarter_paired(df, a, b, seed=2026) -> dict:
    g = df.groupby("target").apply(lambda s: float(np.mean((s[a] - s.y) ** 2 - (s[b] - s.y) ** 2)), include_groups=False)
    d = g.to_numpy(float)
    rng = np.random.default_rng(seed)
    bs = [float(np.mean(rng.choice(d, len(d)))) for _ in range(2000)]
    n = len(d)
    signs = ((np.arange(2 ** n)[:, None] >> np.arange(n)) & 1) * 2 - 1
    perm = float((np.abs((signs * d).mean(1)) >= abs(d.mean()) - 1e-15).mean())
    w, l_ = int((d < -1e-12).sum()), int((d > 1e-12).sum())
    return {"quarters": n, "mean_quarter_brier_diff": float(d.mean()), "ci95": [float(np.percentile(bs, 2.5)),
            float(np.percentile(bs, 97.5))], "perm_p": perm, "wins": w, "losses": l_,
            "sign_p": float(binomtest(w, w + l_, .5).pvalue) if w + l_ else 1.0}


def reliable(m: dict, maj: dict, per: dict) -> bool:
    return bool(m["accuracy"] > 0.75 and m["accuracy"] > maj["accuracy"] and m["accuracy"] > per["accuracy"]
                and (m["recall_HIGH"] or 0) >= 0.5 and (m["recall_LOW"] or 0) >= 0.5 and (m["auc_roc"] or 0) > 0.5
                and 0.1 <= m["share_predicted_HIGH"] <= 0.9)


ARMS = ["SM", "SM_MA2", "SM_AR1D", "SM1", "SM_B", "E56", "Persistence", "PSA_only", "NLP_only", "Logistic", "Majority",
        "Climatology"]


def main():
    sha = verify_protocol()
    before = protected_hashes()
    OUT.mkdir(parents=True, exist_ok=True)
    s63 = pd.read_csv(E63, dtype={"province_code": str})
    assert hashlib.sha256(E63.read_bytes()).hexdigest() == (E63.parent / (E63.name + ".sha256")).read_text().split()[0]
    e56 = {(int(r.lead), int(r.t), r.province_code): float(r.E56_p) for r in s63.itertuples()}
    e56_price = {(int(r.lead), int(r.t), r.province_code): float(r.E56_p_price) for r in s63.itertuples()}
    res = {"protocolSha256": sha, "method": "SM = P_hunger (latest SWS) x P_price (LightGBM)", "leads": {}}
    for lead in (1, 2, 3):
        df = run_lead(lead, e56, e56_price)
        df.to_csv(OUT / f"evaluation_rows_lead{lead}.csv", index=False, lineterminator="\n", float_format="%.6f")
        common = df.dropna(subset=ARMS)
        R = {"rows_all": int(len(df)), "rows_common": int(len(common)), "quarters_common": int(common["target"].nunique()),
             "targets": sorted(common["target"].unique(), key=S.qi), "arms": {}, "paired_vs_SM": {}, "paired_vs_E56": {}}
        for a in ARMS:
            R["arms"][a] = metrics(common["y"], common[a])
        for a in ARMS:
            if a != "SM":
                R["paired_vs_SM"][a] = by_quarter_paired(common, a, "SM")
        R["paired_vs_E56"]["SM"] = by_quarter_paired(common, "SM", "E56")
        R["paired_vs_E56"]["SM_B"] = by_quarter_paired(common, "SM_B", "E56")
        R["reliable"] = {a: reliable(R["arms"][a], R["arms"]["Majority"], R["arms"]["Persistence"]) for a in ARMS}
        reg = common.groupby("target").agg(SM=("SM", "mean"), E56=("E56", "mean"), hunger=("hunger_obs", "first"))
        reg["y_region"] = (reg["hunger"] > S.HUNGER_LINE).astype(int)
        R["regional_secondary"] = {a: metrics(reg["y_region"], reg[a]) for a in ("SM", "E56")}
        per_q = common.groupby("target").apply(lambda s: pd.Series({a: float(((s[a] >= .5).astype(int) == s.y).mean()) for a in ARMS}
                                                                   | {"HIGH": int(s.y.sum()), "hunger": float(s.hunger_obs.iloc[0])}),
                                               include_groups=False)
        R["per_quarter_accuracy"] = per_q.round(3).reset_index().to_dict("records")
        res["leads"][str(lead)] = R
    # current forecast record, LGU rankings and seal. Recommended (Addendum 1 rule): the production E56 combined
    # P(HIGH) at Lead 2; SM-B and SM are shown beside it. The production pipeline issues no Lead-1 forecast for the
    # current origin, so Lead 1 carries SM only, marked as not the recommended method.
    t = S.qi(CURRENT_ORIGIN)
    e58 = json.loads((BACKEND / "data/e58/e58_record.json").read_text(encoding="utf-8"))
    assert e58["originQuarter"] == CURRENT_ORIGIN
    record = {"protocolSha256": sha, "origin": CURRENT_ORIGIN, "issue_date": S.issue_of(t), "forecasts": {},
              "recommended": {"2": "E56", "1": None}}
    seal = []
    for lead in (1, 2):
        f = S.forecast(t, lead)
        for p, v in f["provinces"].items():
            v["SM"] = v["p_high"]
            if lead == 2 and e58["targetQuarter"] == f["target"]:
                comp = e58["provinces"][p]["forecast"]
                v["E56"] = float(comp["probability"])
                v["E56_p_price"] = float(comp["components"]["probabilityPricePressure"])
                v["SM_B"] = None if f["p_hunger"] is None else f["p_hunger"] * v["E56_p_price"]
            else:
                v["E56"] = v["E56_p_price"] = v["SM_B"] = None
        rec_arm = record["recommended"][str(lead)]
        rank_prob = {p: (v[rec_arm] if rec_arm else v["SM"]) for p, v in f["provinces"].items()}
        rk = S.lgu_ranking(rank_prob)
        f["lgu"] = {"rows": rk["rows"], "meaning": rk["meaning"], "method": rk["method"],
                    "ranked_on": rec_arm or "SM (not recommended; no recommended Lead-1 forecast)"}
        f["status"] = ("recommended: E56 combined P(HIGH); SM-B and SM for comparison" if rec_arm else
                       "no recommended Lead-1 forecast: SM failed its evaluation; shown for transparency only")
        record["forecasts"][str(lead)] = f
        for p, v in f["provinces"].items():
            seal.append({"lead": lead, "target": f["target"], "province_code": p, "p_hunger": f["p_hunger"],
                         "SM": v["SM"], "SM_B": v["SM_B"], "E56": v["E56"]})
    (OUT / "record.json").write_text(json.dumps(record, indent=1, default=str), encoding="utf-8")
    blob = pd.DataFrame(seal).to_csv(index=False, lineterminator="\n", float_format="%.6f").encode()
    (OUT / "sealed_prospective.csv").write_bytes(blob)
    (OUT / "sealed_prospective.csv.sha256").write_text(hashlib.sha256(blob).hexdigest() + "  sealed_prospective.csv\n")
    res["sealed_sha256"] = hashlib.sha256(blob).hexdigest()
    after = protected_hashes()
    res["protected_files_unchanged"] = before == after
    assert before == after, "a protected file changed during the run"
    (OUT / "evaluation.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    for lead in ("1", "2", "3"):
        R = res["leads"][lead]
        print(f"Lead {lead}: {R['rows_common']} rows / {R['quarters_common']} quarters; reliable: "
              f"{[a for a, v in R['reliable'].items() if v]}")


if __name__ == "__main__":
    main()
