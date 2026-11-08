"""
Why are E148's quarterly forecasts nearly static? Uses only labels already opened (2013 to 2019, and the 25 provinces of 2021). Reads no 2021 value of
the unscored areas. Prints no city value.

    python -m app.e150.diagnose -> data/e150/out/diagnosis.json
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from app.e147 import labels as Lb
from app.e148 import OUT as O148
from app.e148 import model as M
from app.e150 import OUT


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    S = M.Store()
    tr = M.rows_for(S, M.targets(S, ["FNRI2015", "ENNS2018", "ENNS2019"]), list(range(1, 9)), "F")
    tr["dy"] = tr["y_true"] - tr["y_anchor"]
    one = tr.sort_values("lead").groupby(["key", "survey"]).head(1)
    out = {"training_rows": int(len(tr)), "independent_outcomes": int(len(one)), "survey_rounds_as_targets": int(one["survey"].nunique()), "rows_per_outcome": round(len(tr) / len(one), 2)}
    # target variance: rounds, regions, provinces
    v = one["dy"].var()
    rnd = one.groupby("survey")["dy"].transform("mean")
    reg = one.groupby(["survey", "region"])["dy"].transform("mean")
    noise = float(np.mean(one["se_true"] ** 2 + one["se_anchor"] ** 2))
    out["change_variance"] = {"total": float(v), "between_rounds": float(rnd.var()), "between_regions_within_round": float((reg - rnd).var()), "within_region": float((one["dy"] - reg).var()), "survey_noise_mean": noise,
                              "noise_share_of_total": float(noise / v), "corr_change_with_anchor_position": float(np.corrcoef(one["dy"], one["rtm"])[0, 1])}
    # how much do inputs vary within an outcome across leads, against across outcomes?
    rows = {}
    for c in M.NOW + M.SINCE + M.SWS:
        g = tr[["key", "survey", c]].dropna()
        if g.empty:
            continue
        within = g.groupby(["key", "survey"])[c].transform(lambda s: s - s.mean())
        by = g.groupby("survey")[c].transform("mean")
        d = one[["key", "survey", c, "dy"]].dropna()
        d2 = d.assign(x=d[c] - d.groupby("survey")[c].transform("mean"), y=d["dy"] - d.groupby("survey")["dy"].transform("mean"))
        rows[c] = {"coverage": float(tr[c].notna().mean()), "share_variance_across_rounds": float(by.var() / g[c].var()) if g[c].var() > 0 else None, "share_variance_within_outcome_across_leads": float(within.var() / g[c].var()) if g[c].var() > 0 else None,
                   "distinct_values": int(g[c].round(6).nunique()), "corr_with_change_within_round": float(d2["x"].corr(d2["y"], method="spearman")) if d2["x"].std() > 0 else None}
    out["inputs"] = rows
    # model configuration consequence
    from app.e140 import model as M140
    out["config"] = {"GBC_params": {k: M140.GBC_PARAMS[k] for k in ("num_leaves", "max_depth", "min_child_samples", "learning_rate", "reg_lambda")}, "grid": M140.GBC_GRID}
    # persistence of forecasts
    Sr = pd.read_csv(O148 / "quarterly_series_lead1.csv")
    Sr = Sr.sort_values(["key", "T"])
    Sr["dmu"] = Sr.groupby("key")["mu_Q-G"].diff()
    same_model = Sr["n_train_surveys"] == Sr.groupby("key")["n_train_surveys"].shift()
    out["series"] = {"share_quarter_changes_below_0_01_logit_same_model": float((Sr.loc[same_model, "dmu"].abs() < 0.01).mean()), "mean_abs_change_logit_same_model": float(Sr.loc[same_model, "dmu"].abs().mean()), "forecast_sigma_logit": float(Sr["sigma_Q-G"].mean())}
    # labels never scored
    a = json.loads((O148.parent.parent / "e147" / "out" / "label_audit.json").read_text())
    un = sorted(set(a["areas_2021"]) - set(a["areas_2021_with_panel_features"]))
    d = pd.read_csv(Lb.DEV)
    h = d[d["fs_survey_category"] == "Food Insecure Households"]
    keys = set(S.base["key"])
    extra = h[~h["key"].isin(keys)]
    any_prev = {n: sorted(h.loc[h["province_name"] == n, "actual_year"].astype(str).unique()) for n in un}
    out["unopened_2021_areas"] = {"names": un, "earlier_any_level_years_available": any_prev}
    out["dev_rows_not_in_panel_by_year"] = extra.groupby("actual_year").size().to_dict()
    (OUT / "diagnosis.json").write_text(json.dumps(out, indent=1, default=float), newline="\n")
    print(json.dumps({k: out[k] for k in out if k != "inputs"}, indent=1, default=float))
    t = pd.DataFrame(rows).T.round(3)
    print(t.to_string())


if __name__ == "__main__":
    main()
