"""PROTOCOL_LEAD2_ASOF_REEVAL (hash checked): Lead 2 under evidence-based CPI availability. Diagnostic only: nothing is
adopted, served, counted or resealed, and the sealed prospective files are not read.

1. Ledger: every province-month the CR refresh can use gets one evidence class (V1/V2/V3 verified, P provisional,
   N not before issue, U unresolved) from the archived PSA pages, the committed OpenSTAT retrievals and the
   owner-reported dates; archived headline inflation is compared with the final-vintage index the model reads.
2. Cut-offs: S-VER (verified only), S-PROV (verified + owner-reported), S-D10 (sealed construction, reproduced).
   One cut-off per province-month for food and all items; the same rule for training, validation and evaluation.
3. Refits of CR and CR-ANC per scenario; P0H4, B0 = P0H4-U; R1-R7, adoption rule, baselines, calibration.
4. Five-group chronological ablation (B0 and CR-ANC S-VER), diagnostics and leakage checks.

    python asof_reeval.py   # ../out/asof_reeval.json, ../out/asof_reeval_rows.csv, ../out/asof_reeval_cutoffs.csv,
                            # ../data/psa_cpi_availability_ledger_20261029.csv
"""
from __future__ import annotations

import html
import json
import re
import sys
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

import final as FN
import lt_lib as T
import cpi_refresh_features as CF  # noqa: I001  (sys.path order)
import root_cause as RC
import sept2026_vintage_audit as V
from cr_resolve import GROUPS5, SEPARATE, boot, cr_stack, holm
from features_v2 import II

F, M, KEY = T.F, T.M, T.KEY
NAMES = RC.NAMES
CODE = {v: k for k, v in NAMES.items()}
CPI = ["A1_food", "A1_gap", "A_mom"]
VERIFIED, PROVISIONAL = {"V1", "V2", "V3"}, {"V1", "V2", "V3", "P"}
MON = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November",
       "December"]
SCEN = {"VER": VERIFIED, "PROV": PROVISIONAL}


def ym(s: str) -> int:
    y, m = s.split("-")
    return int(y) * 12 + int(m) - 1


def ym_s(m: int) -> str:
    return f"{m // 12}-{m % 12 + 1:02d}"


# ------------------------------------------------------------------------------------------------------------ ledger
def page_text(path) -> str:
    t = path.read_text(encoding="utf-8", errors="replace")
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", t, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t)))


def headline(text: str, ref: str, prov: str, regional: bool) -> float | None:
    """Headline (all-items) inflation the page prints for the province and its reference month, if it states one.
    A regional page is read only where it names the province."""
    y, m = ref.split("-")
    end = rf"(-?\d+(?:\.\d+)?)\s*(?:percent|%)\s*in\s*{MON[int(m) - 1]},?\s*{y}"
    s = r"(?:(?!\.\s).)"                                     # within one sentence
    pats = [] if regional else [rf"headline (?:or overall )?inflation{s}{{0,140}}?" + end]
    pats += [rf"{prov}(?:\W?s)?{s}{{0,40}}?inflation rate{s}{{0,100}}?" + end, rf"{prov}[^0-9]{{0,60}}?(?:at|to) (-?\d+\.\d+)\s*percent"]
    for pat in pats:
        g = re.search(pat, text, flags=re.I)
        if g:
            return float(g.group(1))
    return None


def published_yoy() -> dict:
    """All-items YoY as published in the final OpenSTAT vintage (0012M4ACP23, retrieved 2026-10-15, E40)."""
    raw = V_git("9624188", "aipheed-backend-aligned/experiments/E40_SWS_CPI_Tiers/data_acquired/psa_cpi_yoy_headline_food_2021_2026.csv")
    y = pd.read_csv(pd.io.common.BytesIO(raw), dtype=str)
    y = y[(y["commodity"] == "all_items") & y["yoy_pct"].notna()]
    return {(r.reference_month, r.province_code): float(r.yoy_pct) for r in y.itertuples()}


def V_git(commit: str, path: str) -> bytes:
    import subprocess
    return subprocess.run(["git", "-C", str(T.LT.parents[2]), "show", f"{commit}:{path}"], capture_output=True, check=True).stdout


def ledger() -> pd.DataFrame:
    v = pd.read_csv(T.DATA / "psa_cpi_release_dates_TO_FILL_v2.csv", dtype=str)
    W = II.index_wide()
    pub = published_yoy()
    rows = []
    for rd in v.to_dict("records"):
        ref, prov, iss = rd["reference_month"], rd["province"], rd["must_be_released_before"]
        m, code = ym(ref), CODE[prov]
        a = W["all"][code]
        implied = float(round(100 * (a[m] / a[m - 12] - 1), 2)) if m in a.index and (m - 12) in a.index else None
        out = {"reference_month": ref, "province": prov, "issue_date": iss, "role": rd["role"],
               "archive_release_date": rd["archive_release_date"], "archive_capture_pht": None,
               "archive_evidence_level": rd["archive_evidence_level"], "archive_file": rd["archive_evidence_file"],
               "archive_sha256": rd["archive_file_sha256"], "archive_headline_yoy": None,
               "final_vintage_implied_yoy": implied, "final_vintage_published_yoy": pub.get((ref, code)),
               "headline_abs_diff": None, "headline_vs_published_diff": None,
               "owner_reported_date": rd["release_date_YYYY-MM-DD"], "owner_ledger_date": rd["ledger_release_date"],
               "owner_ledger_status": rd["ledger_status"], "retrieval_evidence": None}
        cls, why = "U", "no dated evidence"
        if isinstance(rd["archive_release_date"], str):
            cap = re.search(r"/web/(\d{14})/", rd["archive_wayback_url"]).group(1)
            cap_pht = datetime.strptime(cap, "%Y%m%d%H%M%S") + timedelta(hours=8)
            out["archive_capture_pht"] = cap_pht.isoformat(timespec="minutes")
            f = T.DATA / rd["archive_evidence_file"]
            hl = headline(page_text(f), ref, prov, rd["archive_evidence_level"] != "province_release_page") if f.exists() else None
            out["archive_headline_yoy"] = hl
            if hl is not None and implied is not None:
                out["headline_abs_diff"] = round(abs(hl - implied), 3)
            if hl is not None and out["final_vintage_published_yoy"] is not None:
                out["headline_vs_published_diff"] = round(hl - out["final_vintage_published_yoy"], 2)
            if rd["archive_release_date"] < iss:
                cls = "V1" if cap_pht.date().isoformat() < iss else "V2"
                why = f"archived PSA page: printed release {rd['archive_release_date']}, captured {cap_pht:%Y-%m-%d %H:%M} PHT"
            else:
                cls, why = "N", f"archived PSA page printed release {rd['archive_release_date']} is not before the issue"
        if cls == "U":
            owner = [d for d in (rd["release_date_YYYY-MM-DD"], rd["ledger_release_date"]) if isinstance(d, str) and d]
            if owner:
                if min(owner) < iss:
                    cls, why = "P", f"owner-reported {min(owner)}, no saved copy" + (
                        "; ledger source is the 2012=100 release" if rd["ledger_status"] == "series_mismatch_2012_base_not_confirmed_for_2018_base_model" else "")
                else:
                    cls, why = "N", f"owner-reported {min(owner)} is not before the issue"
        out["class"], out["evidence"] = cls, why
        rows.append(out)
    L = pd.DataFrame(rows)
    # September 2026: owner dates from the vintage audit; repository retrievals (food 10-14, all items first 10-15)
    sep = L["reference_month"] == "2026-09"
    for i in L.index[sep]:
        p = L.at[i, "province"]
        od = V.OWNER_PROVINCIAL_RELEASE[p]
        L.at[i, "owner_reported_date"] = od
        L.at[i, "retrieval_evidence"] = ("food YoY values (0012M4ACP23) retrieved 2026-10-14 23:34 PHT; all-items values and the "
                                         "0012M4ACP22 index first retrieved 2026-10-15 17:18 / 17:54 PHT (same day as issue)")
        L.at[i, "class"], L.at[i, "evidence"] = ("P", f"owner-reported {od}, no saved copy; no all-items retrieval before the issue") \
            if od < "2026-10-15" else ("N", f"owner-reported {od} is not before the issue; all-items first retrieved on the issue date")
    return L


# ---------------------------------------------------------------------------------------------------------- cut-offs
def cutoffs(L: pd.DataFrame) -> pd.DataFrame:
    cls = {(r.reference_month, r.province): (r.cls, r.issue_date) for r in L.rename(columns={"class": "cls"}).itertuples()}
    S = T.stack()
    d, _ = CF.E.data()
    dmax = int(d.idx["ym"].max())
    out = []
    for t, k, p in zip(S["t"], S["lead"], S["province_code"]):
        t, k = int(t), int(k)
        if k < 2:
            continue
        m0, iss = CF.L.m0_of(t), F.issue(t, "B")
        CF.RELEASE_DAY = 10
        row = {"t": t, "lead": k, "province_code": p, "issue_B": iss, "m0": m0, "m_D10": min(CF.newest_month(iss, m0), dmax)}
        for s, ok in SCEN.items():
            m, stop = m0, None
            for j in (1, 2):
                c, ci = cls.get((ym_s(m0 + j), NAMES[p]), ("U", None))
                assert ci in (None, iss), (ym_s(m0 + j), p, ci, iss)
                if c in ok and m0 + j <= dmax:
                    m = m0 + j
                else:
                    stop = f"{ym_s(m0 + j)} {c}"
                    break
            row[f"m_{s}"], row[f"stop_{s}"] = m, stop
        out.append(row)
    return pd.DataFrame(out)


def scenario_stack(C: pd.DataFrame, s: str) -> pd.DataFrame:
    S = T.stack().copy()
    d, _ = CF.E.data()
    th = CF.L.e40_spec()
    vals = {(r.t, r.lead, r.province_code): (getattr(r, f"m_{s}"), CF.cols(d, th, r.t, r.lead, r.province_code, getattr(r, f"m_{s}")))
            for r in C.itertuples()}
    S["m0r"] = np.nan
    for i, (t, k, p) in enumerate(zip(S["t"], S["lead"], S["province_code"])):
        v = vals.get((int(t), int(k), p))
        if v is not None:
            S.loc[i, "m0r"] = v[0]
            S.loc[i, CPI] = [float(f"{x:.10g}") for x in v[1]]   # the precision cpi_refresh.csv stores
    S["A1_food_anc"], S["A1_gap_anc"] = RC.anchored_at(S, RC.G_ANCHOR)
    return S


# --------------------------------------------------------------------------------------------------------- evaluation
def summ(ev, k):
    d = ev["leads"][k]
    s = RC.summary(d)
    s["n"], s["high"] = int(d["metrics"]["tp"] + d["metrics"]["fn"] + d["metrics"]["fp"] + d["metrics"]["tn"]), int(d["metrics"]["tp"] + d["metrics"]["fn"])
    s["false_alarms"], s["missed_high"] = int(d["metrics"]["fp"]), int(d["metrics"]["fn"])
    s["brier_vs_persist"], s["brier_vs_clim"] = d["brier_vs_persist"], d["brier_vs_clim"]
    s["acc_by_year"] = d["acc_by_year"]
    return s


def baselines(g):
    y = g["y"].to_numpy(int)
    out = {}
    for b, c in (("always_low", "ALWAYS-LOW_p"), ("persistence", "PERS_AB"), ("climatology", "CLIM_p")):
        k = (g[c] >= .5).astype(int).to_numpy()
        tp, fp = int(((k == 1) & (y == 1)).sum()), int(((k == 1) & (y == 0)).sum())
        out[b] = {"accuracy": float((k == y).mean()), "brier": float(((g[c] - y) ** 2).mean()),
                  "recall": tp / max(1, int(y.sum())), "false_alarms": fp, "missed_high": int(((k == 0) & (y == 1)).sum())}
    return out


def lopo(cols, origins, S):
    out = []
    for p in sorted(S["province_code"].unique()):
        for t in origins:
            tr = T.train_rows(S, int(t))
            tr = tr[tr["province_code"] != p]
            te = S[(S["t"] == t) & (S["province_code"] == p)]
            if not T.eligible(tr) or not len(te):
                continue
            cfg, _ = T.select(tr, cols)
            out.append(te[KEY].assign(pi_P=T.Uni(cfg, cols).fit(tr).predict(te)))
    return pd.concat(out, ignore_index=True)


def overfit(cols, origins, S, E, pc):
    g = []
    for t in origins:
        tr = T.train_rows(S, int(t))
        if not T.eligible(tr):
            continue
        cfg, _ = T.select(tr, cols)
        mdl = T.Uni(cfg, cols).fit(tr)
        te = S[S["t"] == t].merge(E[E["t"] == t][KEY + ["price"]], on=KEY)
        g.append({"origin": F.qs(int(t)), "train_brier": float(np.mean((mdl.predict(tr) - tr["y"]) ** 2)),
                  "test_brier": float(np.mean((mdl.predict(te) - te["price"]) ** 2))})
    G = pd.DataFrame(g)
    return {"by_origin": g, "mean_train": float(G["train_brier"].mean()), "mean_test": float(G["test_brier"].mean())}


def parts(g, pc, hc="pi_H_AB"):
    """Food insecurity vs price pressure: the hunger part, the price part and the oracle swaps."""
    y, h, pr = g["y"].to_numpy(int), g["hunger"].to_numpy(int), g["price"].to_numpy(int)
    ph, pp = g[hc].to_numpy(float), g[pc].to_numpy(float)
    call = (ph * pp >= .5).astype(int)
    wrong = call != y
    hw, pw = (ph >= .5).astype(int) != h, (pp >= .5).astype(int) != pr
    acc = lambda p: float(((p >= .5).astype(int) == y).mean())  # noqa: E731
    return {"hunger_part_accuracy_vs_hunger": float(((ph >= .5).astype(int) == h).mean()),
            "price_part_accuracy_vs_price": float(((pp >= .5).astype(int) == pr).mean()),
            "price_part_brier_vs_price": float(((pp - pr) ** 2).mean()),
            "model_accuracy": acc(ph * pp), "oracle_true_hunger_x_model_price": acc(h * pp),
            "oracle_model_hunger_x_true_price": acc(ph * pr),
            "errors": int(wrong.sum()), "errors_hunger_part_wrong_only": int((wrong & hw & ~pw).sum()),
            "errors_price_part_wrong_only": int((wrong & pw & ~hw).sum()), "errors_both_wrong": int((wrong & hw & pw).sum()),
            "errors_neither_part_wrong_by_sign": int((wrong & ~hw & ~pw).sum()),
            "hunger_high_rows": int(h.sum()), "price_high_rows": int(pr.sum()), "target_high_rows": int(y.sum()),
            "corr_p_with_price_label": float(np.corrcoef(ph * pp, pr)[0, 1]),
            "corr_p_with_hunger_label": float(np.corrcoef(ph * pp, h)[0, 1])}


def ablate(cols, origins, S, E, full, extra_market=()):
    res = {}
    for name, grp in {**GROUPS5, **SEPARATE, "all_five_groups": sum(GROUPS5.values(), [])}.items():
        drop = set(grp) | (set(extra_market) if name in ("market_prices", "all_five_groups") else set())
        Q = T.run([c for c in cols if c not in drop], origins, S=S)
        X = E[KEY + ["q", "y", "pi_H_AB", full]].merge(Q, on=KEY)
        X["x_p"] = X["pi_H_AB"] * X["pi_P"]
        res[name] = {}
        for k in (1, 2):
            g = X[X["lead"] == k]
            y = g["y"].to_numpy(int)
            a, b = (g["x_p"] >= .5).astype(int).to_numpy(), (g[full] >= .5).astype(int).to_numpy()
            tp = lambda c: int(((c == 1) & (y == 1)).sum())  # noqa: E731
            fp = lambda c: int(((c == 1) & (y == 0)).sum())  # noqa: E731
            res[name][k] = boot(g["q"], (g["x_p"] - g["y"]) ** 2, (g[full] - g["y"]) ** 2) | {
                "accuracy_change": float((a == y).mean() - (b == y).mean()),
                "recall_change": (tp(a) - tp(b)) / max(1, int(y.sum())),
                "false_alarm_change": fp(a) - fp(b), "calls_changed": int((a != b).sum())}
    for k in (1, 2):
        hp = holm({n: res[n][k]["p_hurts"] for n in GROUPS5})
        for n in GROUPS5:
            res[n][k]["holm_p_hurts"] = hp[n]
    return res


def leakage(L, E, C):
    g2 = E[E["lead"] == 2]
    hl = L.dropna(subset=["headline_vs_published_diff"])
    R = F.rounds()
    bl = R[R["area"] == "BL"].groupby("q").agg(H=("H", "mean"), pub=("published", "max"))
    iss2 = sorted({F.issue(int(t), "B") for t in g2["t"]})
    S = T.stack()
    iss_all = pd.Series([F.issue(int(t), "B") if int(k) >= 2 else F.issue(int(t), "A") for t, k in zip(S["t"], S["lead"])])
    rc = json.loads((T.OUT / "root_cause.json").read_text())
    return {
        "cpi_vintage_archived_headline_vs_final_vintage": {"pages_with_headline": int(len(hl)),
                                                            "equal_to_published_final_vintage": int((hl["headline_vs_published_diff"].abs() < .001).sum()),
                                                            "differ": hl.loc[hl["headline_vs_published_diff"].abs() >= .001, ["reference_month", "province", "archive_headline_yoy", "final_vintage_published_yoy", "final_vintage_implied_yoy"]].to_dict("records"),
                                                            "max_abs_diff_index_implied_pp": float(hl["headline_abs_diff"].max())},
        "cpi_base_2012_vs_2018": {"latest_archived_2012_base_release": "2021-06-30", "earliest_archived_2018_base_release": "2022-06-07",
                                  "stack_rows_issued_before_2022_06_07": int((iss_all < "2022-06-07").sum()),
                                  "stack_rows_total": int(len(S)), "first_lead2_evaluation_issue": iss2[0],
                                  "evaluation_rows_affected": 0 if iss2[0] >= "2022-06-07" else None,
                                  "note": "training rows issued before the 2018=100 series was public use final 2018=100 values; unresolved (2012=100 vintage decision pending)"},
        "price_thresholds": {"window": "2021-2022 P60 per province (fixed)", "last_month_in_window": "2022-12",
                             "first_lead2_evaluation_issue": iss2[0],
                             "dec_2022_archived_release": L.loc[L["reference_month"] == "2022-12", "archive_release_date"].dropna().tolist()},
        "sws_hunger_published_before_issue": "by construction (fr_lib.known keeps rounds published < issue)",
        "news_timing": rc["news_timing"],
        "base_cutoff_m0_vs_archived_release": m0_timing(),
        "regional_hunger_near_line_lead2_targets": {"quarters": int(bl.loc[bl.index.isin(g2["q"].unique())].shape[0]),
                                                    "within_1pt_of_11.3": [F.qs(int(q)) + f" {h:.1f}" for q, h in bl.loc[bl.index.isin(g2["q"].unique()), "H"].items() if abs(h - F.H_LINE) <= 1]},
    }


def m0_timing():
    """Archived provincial pages for months that serve as the base cut-off m0 (month 2 of a quarter): printed release
    date vs the quarter-start issue (Lead 1) that first uses them; and the largest archived release lag."""
    c = pd.read_csv(T.DATA / "psa_release_evidence" / "wayback_catalog.csv", dtype=str)
    c = c[c["error"].isna() & c["reference_month"].notna() & (c["series"] == "all_income") & c["release_date_iso"].notna()]
    out, lags = [], []
    for r in c.itertuples():
        m = ym(r.reference_month)
        end = date(m // 12, m % 12 + 1, 1) + pd.offsets.MonthEnd(0)
        lags.append((pd.Timestamp(r.release_date_iso) - pd.Timestamp(end)).days)
        if m % 3 == 1:                                           # month 2 of its quarter
            t = (m // 12) * 4 + (m % 12) // 3
            iss = F.issue(t, "A")
            out.append({"reference_month": r.reference_month, "subject": r.subject, "release": r.release_date_iso,
                        "lead1_issue": iss, "before_issue": r.release_date_iso < iss})
    return {"m0_pages": len(out), "m0_pages_before_issue": int(sum(o["before_issue"] for o in out)),
            "max_release_lag_days_after_month_end": int(max(lags)), "median_lag_days": float(np.median(lags)),
            "pages": out}


def main():
    proto = T.LT / "PROTOCOL_LEAD2_ASOF_REEVAL.md"
    assert T.sha256(proto) == (T.HERE / "ASOF_REEVAL_SHA256.txt").read_text().strip(), "protocol changed after freezing"
    T.MONO_UP = T.MONO_UP + RC.ANC
    res = {"protocol_sha256": T.sha256(proto)}
    L = ledger()
    L.to_csv(T.DATA / "psa_cpi_availability_ledger_20261029.csv", index=False, lineterminator="\n")
    res["ledger_classes"] = L["class"].value_counts().to_dict()
    res["ledger_by_province"] = {p: g["class"].value_counts().to_dict() for p, g in L.groupby("province")}
    res["ledger_sept2026"] = L[L["reference_month"] == "2026-09"][["province", "class", "evidence", "retrieval_evidence"]].to_dict("records")
    C = cutoffs(L)
    C.to_csv(T.OUT / "asof_reeval_cutoffs.csv", index=False, lineterminator="\n")

    E = pd.read_csv(T.OUT / "root_cause_rows.csv", dtype={"province_code": str})
    E = E[KEY + ["q", "y", "price", "hunger", "pi_H_AB", "PERS_AB", "CLIM_p", "ALWAYS-LOW_p", "B0_price", "B0_p",
                 "P0H4_price", "P0H4_p", "CR_price", "CR_p", "CRANC_price", "CRANC_p"]].copy()
    origins = sorted(E["t"].unique())
    Ce = C.merge(E[KEY], on=KEY)
    res["cutoffs_eval_lead2"] = {s: Ce[Ce["lead"] == 2][f"m_{s}"].sub(Ce[Ce["lead"] == 2]["m0"]).value_counts().sort_index().to_dict()
                                 for s in ("D10", "VER", "PROV")}
    res["cutoffs_all_rows"] = {s: C[f"m_{s}"].sub(C["m0"]).value_counts().sort_index().to_dict() for s in ("D10", "VER", "PROV")}
    res["eval_lead2_rows_where_VER_differs_from_D10"] = int((Ce[Ce["lead"] == 2]["m_VER"] != Ce[Ce["lead"] == 2]["m_D10"]).sum())

    stacks = {}
    for s in ("D10", "VER", "PROV"):
        S = scenario_stack(C, s)
        stacks[s] = S
        if s == "D10":                                           # reproduces the sealed construction
            S0 = cr_stack()
            res["D10_reproduces_cr_stack_max_abs"] = float(max((S[c] - S0[c]).abs().max() for c in CPI))
            assert res["D10_reproduces_cr_stack_max_abs"] < 1e-12, res["D10_reproduces_cr_stack_max_abs"]
        cr = T.run(T.U2, origins, S=S).rename(columns={"pi_P": f"CR{s}_price"})
        an = T.run(RC.COLS_ANC, origins, S=S).rename(columns={"pi_P": f"CRANC{s}_price"})
        E = E.merge(cr[KEY + [f"CR{s}_price"]], on=KEY, how="left").merge(an[KEY + [f"CRANC{s}_price"]], on=KEY, how="left")
        for c in (f"CR{s}", f"CRANC{s}"):
            E[f"{c}_p"] = E["pi_H_AB"] * E[f"{c}_price"]
        print(s, "fitted", flush=True)
    res["D10_reproduces_rows_max_abs"] = {"CR": float((E["CRD10_p"] - E["CR_p"]).abs().max()),
                                          "CRANC": float((E["CRANCD10_p"] - E["CRANC_p"]).abs().max())}
    assert res["D10_reproduces_cr_stack_max_abs"] < 1e-9 and max(res["D10_reproduces_rows_max_abs"].values()) < 1e-6

    cands = ["P0H4", "B0", "CRD10", "CRANCD10", "CRPROV", "CRANCPROV", "CRVER", "CRANCVER"]
    ev = {c: FN.lead_eval(E, c) for c in cands}
    res["timing_label"] = {"P0H4": "base cut-off m0 (archive-checked)", "B0": "base cut-off m0 (archive-checked)",
                           "CRVER": "verified", "CRANCVER": "verified", "CRPROV": "provisional", "CRANCPROV": "provisional",
                           "CRD10": "provisional (day-10 assumption)", "CRANCD10": "provisional (day-10 assumption)"}
    res["results"] = {c: {k: summ(ev[c], k) for k in (1, 2)} | {"max_reliable_lead": ev[c]["max_reliable_lead"]} for c in cands}
    res["adoption_vs_B0"] = {c: {"rule": (r := FN.adoption_rule(ev["B0"]["leads"], ev[c]["leads"])), "failed": [k for k, v in r.items() if not v]}
                             for c in cands if c not in ("P0H4", "B0")}
    g2 = E[E["lead"] == 2]
    res["baselines_lead2"] = baselines(g2)
    res["calibration_lead2"] = {c: RC.calib(g2["y"], g2[f"{c}_p"]) for c in cands}
    res["class_bias_lead2"] = {c: {"predicted_high_rate": float((g2[f"{c}_p"] >= .5).mean()), "observed_high_rate": float(g2["y"].mean()),
                                   "mean_p_high": float(g2.loc[g2["y"] == 1, f"{c}_p"].mean()), "mean_p_low": float(g2.loc[g2["y"] == 0, f"{c}_p"].mean())}
                               for c in cands}
    res["parts_lead2"] = {c: parts(g2, f"{c}_price") for c in ("B0", "CRANCVER", "CRANCD10")}
    res["high_by_quarter_lead2"] = {F.qs(int(q)): int(h["y"].sum()) for q, h in g2.groupby("q")}
    res["errors_lead2_VER"] = {c: [f"{NAMES[r.province_code]} {F.qs(int(r.q))} y={int(r.y)} p={getattr(r, c + '_p'):.3f}"
                                   for r in g2.itertuples() if int(getattr(r, c + "_p") >= .5) != int(r.y)] for c in ("B0", "CRVER", "CRANCVER")}
    print("evaluated", flush=True)

    # five-group chronological ablation
    res["ablation_B0"] = ablate(T.U2, origins, T.stack(), E, "B0_p")
    res["ablation_CRANCVER"] = ablate(RC.COLS_ANC, origins, stacks["VER"], E, "CRANCVER_p", extra_market=RC.ANC)
    print("ablated", flush=True)

    # province generalization, overfitting
    gen = {}
    for c, cols, S, full in (("B0", T.U2, T.stack(), "B0"), ("CRANCVER", RC.COLS_ANC, stacks["VER"], "CRANCVER")):
        Q = lopo(cols, origins, S)
        X = E[KEY + ["q", "y", "pi_H_AB", "price", f"{full}_p", f"{full}_price"]].merge(Q, on=KEY)
        X["lopo_p"] = X["pi_H_AB"] * X["pi_P"]
        g = X[X["lead"] == 2]
        gen[c] = {NAMES[p]: {"n": int(len(h)), "high": int(h["y"].sum()),
                             "acc_in_sample": float(((h[f"{full}_p"] >= .5).astype(int) == h["y"]).mean()),
                             "acc_lopo": float(((h["lopo_p"] >= .5).astype(int) == h["y"]).mean()),
                             "brier_in_sample": float(((h[f"{full}_p"] - h["y"]) ** 2).mean()),
                             "brier_lopo": float(((h["lopo_p"] - h["y"]) ** 2).mean()),
                             "price_brier_in_sample": float(((h[f"{full}_price"] - h["price"]) ** 2).mean()),
                             "price_brier_lopo": float(((h["pi_P"] - h["price"]) ** 2).mean())}
                  for p, h in g.groupby("province_code")}
        gen[c]["all"] = {"acc_in_sample": float(((g[f"{full}_p"] >= .5).astype(int) == g["y"]).mean()),
                         "acc_lopo": float(((g["lopo_p"] >= .5).astype(int) == g["y"]).mean()),
                         "brier_in_sample": float(((g[f"{full}_p"] - g["y"]) ** 2).mean()),
                         "brier_lopo": float(((g["lopo_p"] - g["y"]) ** 2).mean())}
    res["province_generalization_lead2"] = gen
    res["overfitting"] = {"B0": overfit(T.U2, origins, T.stack(), E, "B0"),
                          "CRANCVER": overfit(RC.COLS_ANC, origins, stacks["VER"], E, "CRANCVER")}
    res["leakage"] = leakage(L, E, C)
    E.to_csv(T.OUT / "asof_reeval_rows.csv", index=False, lineterminator="\n", float_format="%.6g")
    (T.OUT / "asof_reeval.json").write_text(json.dumps(res, indent=1, default=float))
    for c in cands:
        r = res["results"][c][2]
        print(c, r["n"], r["high"], round(r["accuracy"], 3), round(r["balanced_accuracy"], 3), round(r["precision"], 3),
              round(r["recall"], 3), round(r["f1"], 3), round(r["brier"], 4), r["failed"], res["adoption_vs_B0"].get(c, {}).get("failed"))


if __name__ == "__main__":
    sys.exit(main())
