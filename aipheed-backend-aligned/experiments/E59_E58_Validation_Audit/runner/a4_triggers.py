"""E59 audit step 4: the five trigger groups, traced from data to model to explanation to API.

For each of the 10 evaluated origins plus the 2026-Q4 and 2027-Q1 issue dates, the configuration E56 selected is refitted
(exactly as served; probabilities checked against the E58 record) and the LightGBM booster is inspected:
  * inputs offered to the trees (configuration feature set), per group;
  * inputs actually used in a split (split count > 0), per group;
  * the TreeSHAP group contributions served in the E58 record (status contributes / no_effect / insufficient_data);
  * which groups also enter the regional hunger component (I7 ridge), which is not LightGBM.

    backend/venv/Scripts/python.exe -B runner/a4_triggers.py  -> out/triggers.json, out/trigger_use_by_origin.csv
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
A = Path(__file__).resolve().parents[1]
EXP = A.parent
BACKEND = EXP.parents[1] / "backend"
sys.path.insert(0, str(EXP / "E56_LightGBM_Optimization" / "runner"))
import e56_lib as G  # noqa: E402

E, F, L, np, pd = G.E, G.F, G.L, G.np, G.pd
FIVE = ["market", "climate", "fish_kill", "employment", "ofw_remittance"]
SEL = sorted((EXP / "E56_LightGBM_Optimization" / "runs").glob("2026*"))[0] / "selections.json"


def main():
    sel = json.loads(SEL.read_text())
    rec = json.loads((BACKEND / "data" / "e58" / "e58_record.json").read_text(encoding="utf-8"))
    d, X, B = E.load()
    space = G.search_space()
    rows = []
    for oq, s in sel.items():
        t = L.qi(oq)
        c = s["cfg"]
        tr, te = F.frame(d, X, B, t, "AS")
        fit = tr.dropna(subset=[f"base_{c['m']}", f"gbase_{c['m']}", "F_true", "G_true"])
        mdl = G.PriceLGB2(G.cols_for(c), c).fit(fit)
        hc = F.hunger(d, X, t)
        p = hc["p"] * mdl.predict(te)
        # served probability for this origin's target (pastDrivers or forecast)
        q = L.qs(t + 2)
        served = [v["forecast"]["probability"] if rec["targetQuarter"] == q else v["pastDrivers"][q]["probability"]
                  for v in [rec["provinces"][pp] for pp in L.PROVS]]
        imp = dict(zip(mdl.feat, mdl.model.booster_.feature_importance("split"))) if mdl.const is None else {}
        for g in FIVE + ["news_volume", "poverty"]:
            cols = [k for k in mdl.feat if (F.group_of(k) == g if g in FIVE else (k == "news_n" if g == "news_volume" else F.group_of(k) == "poverty"))]
            used = [k for k in cols if imp.get(k, 0) > 0]
            shap_status = []
            for pp in L.PROVS:
                v = rec["provinces"][pp]
                e = v if rec["targetQuarter"] == q else v["pastDrivers"][q]
                if g in FIVE:
                    shap_status.append(e["triggerStatus"][g]["status"])
            rows.append({"origin": oq, "target": q, "config": c["id"], "feature_set": c["feat"], "group": g,
                         "inputs_offered": len(cols), "inputs_used_in_splits": len(used), "used_inputs": ";".join(used),
                         "splits": int(sum(imp.get(k, 0) for k in cols)),
                         "served_contributes_provinces": shap_status.count("contributes") if g in FIVE else None,
                         "served_insufficient_provinces": shap_status.count("insufficient_data") if g in FIVE else None,
                         "repro_max_abs_diff": float(np.max(np.abs(np.array(served) - p)))})
    T = pd.DataFrame(rows)
    hunger_inputs = {g: F.P2.HUNGER_GROUPS.get(g, []) for g in F.P2.ALL_GROUPS}
    summ = {}
    for g, gg in T.groupby("group"):
        summ[g] = {"origins": int(len(gg)), "origins_offered": int((gg["inputs_offered"] > 0).sum()),
                   "origins_used_in_trees": int((gg["inputs_used_in_splits"] > 0).sum()),
                   "total_splits": int(gg["splits"].sum()),
                   "served_entries_contributes": None if gg["served_contributes_provinces"].isna().all() else int(gg["served_contributes_provinces"].sum()),
                   "served_entries": int(len(gg) * 5),
                   "hunger_component_inputs": hunger_inputs.get(g if g != "news_volume" else "news", [])}
    res = {"by_group": summ, "max_reproduction_diff": float(T["repro_max_abs_diff"].max()),
           "price_offset_note": "Every forecast's starting point (offset) is the base-effect projection of provincial food "
                                "CPI inflation, attributed to Market / Prices; the trees add the trigger effects on top.",
           "hunger_component": "I7 ridge on regional means of " + ", ".join(sorted({c for v in hunger_inputs.values() for c in v}))
                               + " (not LightGBM; not in the TreeSHAP bars)",
           "ew_rule_inputs": "EW uses P_price (LightGBM price part: offset + trees) and P(HIGH) = P_price x P_hunger; it adds "
                             "no input of its own"}
    T.to_csv(A / "out" / "trigger_use_by_origin.csv", index=False)
    (A / "out" / "triggers.json").write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps(res, indent=1, default=float))
    print(T.pivot_table(index="origin", columns="group", values="splits", aggfunc="sum").to_string())


if __name__ == "__main__":
    main()
