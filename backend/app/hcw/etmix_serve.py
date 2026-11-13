"""
FINAL-ETMIX live issue for the five CALABARZON provinces (EXPERIMENTAL; not served on the public dashboard; E196 stays production).

    python -m app.hcw.etmix_serve live [--issue 2026-Q4] [--leads 1,2]   -> data/etmix/out/live.json + rows.csv + lgus.csv
    python -m app.hcw.etmix_serve registry                                -> copies the research contributor registry

Rows are built exactly as the served pipelines build them (app.hcw.serve._rows: data published before the issue quarter,
anchors from released survey rounds only), the model is app.hcw.etmix (5 seeds), contributions are exact TreeSHAP of the
fitted model. Nothing here is hardcoded: probabilities, classes, contributor values and LGU priorities come from the fits.
"""
from __future__ import annotations

import argparse
import json
import pickle
import shutil
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from app.hcw import etmix as X
from app.paths import BACKEND_DIR

warnings.filterwarnings("ignore")
OUT = BACKEND_DIR / "data" / "etmix" / "out"
LIVE, ROWS, LGUS, REG = OUT / "live.json", OUT / "rows.csv", OUT / "lgus.csv", OUT / "contributor_registry.json"
RESEARCH = Path(r"C:\Users\admin\aipheed_final\research_notes\aiPHeed_final_etmix_20261113")
CODES = {"Cavite": "PH040100000", "Laguna": "PH040200000", "Quezon": "PH040300000", "Rizal": "PH040400000", "Batangas": "PH040500000"}
VALUES = {"regional_accounts": ["hh_grdp_rel", "hh_grdp_g", "income_rel", "income_growth"],
          "market_prices": ["cpi_food_yoy", "cpi_food_3m", "cpi_food_rel_nat", "cpi_rice_yoy", "l_rice_yoy", "l_rice_rel", "l_fg_yoy"],
          "poverty_vulnerability": ["p_poverty", "p_poverty_gap", "p_subsistence", "p_density"],
          "agri_fish_production": ["c_agri_yoy", "ag_palay_yoy", "ag_corn_yoy", "l_fish_yoy"],
          "climate": ["c_tc_4q", "vu_tc_strong", "vu_dry6", "oni"], "employment": ["unemp_rate", "unemp_yoy"], "news_nlp": ["p_e_net", "a_e_net", "n_e_net"]}
pct = lambda y: 100 / (1 + np.exp(-np.asarray(y, float)))


def _one(lead: int, seed: int, issue_label: str) -> dict:
    from app.hcw import serve as S
    tr, te, AN, issue = S._rows(lead, issue_label)
    r = X.fit_predict(tr, te, AN, seed)
    r.update(lead=lead, seed=seed, issue=issue, province=te["province"].tolist(), train_rows=len(tr),
             train_rounds=sorted(tr["survey"].dropna().unique().tolist()), anchor_survey=te.get("ref_anchor", pd.Series([None] * len(te))).tolist())
    return r


LGU_INPUT = BACKEND_DIR / "data" / "inputs" / "lgu_vulnerability.csv"     # the served 142-LGU table (PSA 2021 SAE + POPCEN 2024)


def _lgus(prob_l1: dict) -> pd.DataFrame:
    """Approved prioritisation (app.quarterly.lgu_poverty.rank_lgus via forecaster_v2.lgu_table) on the served LGU input."""
    from app.quarterly.forecaster_v2 import lgu_table
    return lgu_table(pd.read_csv(LGU_INPUT, dtype={"lgu_code": str}), prob_l1)


def live(issue_label: str = "2026-Q4", leads=(1, 2), reuse: bool = False) -> dict:
    from app.fi5.target import qlabel
    from app.hcw import serve as S
    # the cut-off label must match the panels the rows are built from (refreshed panels need AIPHEED_LIVE_ASOF); otherwise refuse
    cut = S.check_cutoff(issue_label)
    FITS = OUT / f"fits_{issue_label}_{cut['information_cutoff']}_{'-'.join(map(str, leads))}.pkl"
    if reuse and FITS.exists():                               # same issue, same code: reuse the 10 fits instead of refitting
        R = pickle.loads(FITS.read_bytes())
    else:
        R = Parallel(n_jobs=min(20, len(leads) * len(X.SEEDS)))(delayed(_one)(l, s, issue_label) for l in leads for s in X.SEEDS)
        OUT.mkdir(parents=True, exist_ok=True)
        FITS.write_bytes(pickle.dumps([{k: v for k, v in r.items()} for r in R]))
    rows = []
    for lead in leads:
        rs = [r for r in R if r["lead"] == lead]
        names = rs[0]["province"]
        p, pg, ps, mug, mus = (np.mean([r[k] for r in rs], axis=0) for k in ("p", "p_g", "p_s", "mu_g", "mu_s"))
        hg, hs = (np.mean([r[k] for r in rs], axis=0) for k in ("half_g", "half_s"))
        G = sum(X.group_contributions(r["contrib"], r["cols"], r["bias"]) for r in rs) / len(rs)
        anc = np.mean([r["anchor_logit"] for r in rs], axis=0)
        Xv = rs[0]["X"]
        for k, name in enumerate(names):
            mu_mix = 0.5 * (mug[k] + mus[k])
            o = {"province_code": CODES[name], "province": name, "lead": lead, "target_quarter": qlabel(rs[0]["issue"] + lead),
                 "issue_quarter": issue_label, "information_cutoff": cut["information_cutoff"], "model": X.VERSION,
                 "probability": round(float(p[k]), 4), "class": "HIGH" if p[k] >= X.P_HIGH else "LOW",
                 "p_own_survey_gap": round(float(pg[k]), 4), "p_since_latest_round": round(float(ps[k]), 4),
                 "own_survey_gap_q": int(rs[0]["g"][k]), "since_latest_round_q": int(rs[0]["s"][k]),
                 "score_pct_mixture_logit": round(float(pct(mu_mix)), 1),
                 "range90_pct": [round(float(pct(min(mug[k] - hg[k], mus[k] - hs[k]))), 1), round(float(pct(max(mug[k] + hg[k], mus[k] + hs[k]))), 1)],
                 "anchor_pct": round(float(pct(anc[k])), 1), "anchor_choice": sorted({r["anchor"] for r in rs}),
                 "configs": [r["cfg"] for r in rs], "train_rows": rs[0]["train_rows"], "train_rounds": rs[0]["train_rounds"]}
            for g in G.columns:
                o[f"contrib_{g}"] = round(float(G.at[k, g]), 6)
            o["contrib_sum_check"] = round(float(G.iloc[k].sum() + anc[k] - mu_mix), 9)   # exact additivity: must be ~0
            for g, cs in VALUES.items():
                for c in cs:
                    o[f"val_{c}"] = None if c not in Xv or pd.isna(Xv.at[k, c]) else round(float(Xv.at[k, c]), 6)
            sel = set().union(*[set(r["cols"]) for r in rs])
            o["inputs_used"] = sorted(sel)
            o["inputs_missing_at_issue"] = sorted({c[3:] for c in sel if c.startswith("mi_") and float(Xv.at[k, c]) == 1.0})
            rows.append(o)
    D = pd.DataFrame(rows)
    l1 = D[D.lead == min(leads)]
    lg = _lgus(dict(zip(l1.province_code, l1.probability)))
    OUT.mkdir(parents=True, exist_ok=True)
    D.drop(columns=["configs", "inputs_used"]).to_csv(ROWS, index=False, lineterminator="\n")
    lg.to_csv(LGUS, index=False, lineterminator="\n")
    doc = {"model": X.VERSION, "status": X.STATUS, "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "issue_quarter": issue_label, "cutoff_check": cut, "leads": list(leads), "seeds": list(X.SEEDS), "threshold": X.P_HIGH,
           "target": "FNRI HFIAS moderate+severe household food insecurity by province; HIGH at 50 %",
           "rows": json.loads(D.to_json(orient="records")), "lgu_input": str(LGU_INPUT.relative_to(BACKEND_DIR)), "lgu_input_sha256": __import__("hashlib").sha256(LGU_INPUT.read_bytes()).hexdigest(), "production_model_unchanged": "E196 (e196-lgbm-avg5-laf-1.0)"}
    LIVE.write_text(json.dumps(doc, indent=1), newline="\n")
    print(D[["province", "lead", "target_quarter", "probability", "class", "p_own_survey_gap", "p_since_latest_round", "own_survey_gap_q",
             "since_latest_round_q", "anchor_pct", "contrib_regional_accounts", "contrib_market_prices", "contrib_poverty_vulnerability",
             "contrib_agri_fish_production", "contrib_trend", "contrib_sum_check"]].to_string())
    return doc


def copy_registry() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(RESEARCH / "evidence" / "contributor_registry.json", REG)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["live", "registry"])
    ap.add_argument("--issue", default="2026-Q4")
    ap.add_argument("--leads", default="1,2")
    ap.add_argument("--reuse", action="store_true", help="reuse the saved fits of this issue")
    a = ap.parse_args()
    if a.cmd == "live":
        live(a.issue, tuple(int(x) for x in a.leads.split(",")), reuse=a.reuse)
    else:
        copy_registry()
