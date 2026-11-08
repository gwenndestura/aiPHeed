"""
Serving for PFI: the dashboard always gets the forecast for the next calendar quarter of the serving clock.

The stored forecast is reused while its issue quarter, its SWS data cutoff and the artifact hash are all still current.
Otherwise it is re-issued from the sealed artifact (inference only, about 0.2 s; the model is never refitted on a
request) and the first issue of each quarter is appended to the prospective register.
"""
from __future__ import annotations

import json
import threading

import pandas as pd

from app.fi9 import quarters as Q
from app.pfi import OUT, PROVINCES, VERSION
from app.pfi import engine as E
from app.pfi import sources as S

_LOCK = threading.Lock()
now = E.now


def _current(f: dict, a: dict, d: pd.Timestamp) -> bool:
    sws = S.sws_quarterly("balance_luzon", d)
    return (f.get("current_quarter") == Q.lead1(d)["current_quarter"] and f.get("artifact_sha256") == a["sha256"]
            and f.get("inputs", {}).get("sws_latest_published") == str(sws["published"].iloc[-1].date()))


def outlook() -> dict:
    d = now()
    a = E.load_artifact()
    p = OUT / "forecast.json"
    with _LOCK:
        f = json.loads(p.read_text()) if p.exists() else {}
        reissued = False
        if not _current(f, a, d):
            f = E.issue(d)
            reissued = True
    f = dict(f)
    f["served_by"] = VERSION
    f["served_on"] = d.date().isoformat()
    f["reissued_on_request"] = reissued
    return f


def evaluation() -> dict:
    p = OUT / "evaluation.json"
    if not p.exists():
        raise E.ArtifactMissing("evaluation.json not built yet: run `python -m app.pfi.engine build`")
    return json.loads(p.read_text())


def model_card() -> dict:
    a = E.load_artifact()
    lv = a["level"]
    comp = a["composite"]
    return {"version": a["version"], "artifact_sha256": a["sha256"], "built_utc": a["built_utc"], "outcome": a["outcome"],
            "level_model": {"selected": lv["selected"], "terms": lv["terms"], "coefficients": lv["beta"],
                            "residual_var_logit": lv["residual_var_logit"], "n_regions": lv["n_regions"],
                            "selection_rule": lv["selection_rule"]},
            "composite": {"direct_source": comp["direct_source"], "drift_sd_logit": comp["drift_sd_logit"],
                          "drift_note": comp["drift_note"], "direct": comp["direct"]},
            "province_covariates": a["province_covariates"], "benchmark": a["benchmark"], "state_update_2025": a["state_update_2025"],
            "bridge": a["bridge"], "projection": a["projection"], "seed": a["seed"], "n_draws": a["n_draws"],
            "commands": {"build": "python -m app.pfi.engine build", "issue": "python -m app.pfi.engine issue"}}


def lgus() -> dict:
    """The 142 LGUs with their province's forecast (inherited, labelled) and their own structural context."""
    f = outlook()
    byp = {r["province"]: r for r in f["provinces"]}
    lg = S.population()
    rows = []
    for _, r in lg.iterrows():
        p = byp[r["province_name"]]
        pov = r["poverty_incidence_2021"]
        rows.append({"lgu_psgc": r["lgu_psgc"], "lgu_name": r["lgu_name"], "lgu_type": r["lgu_type"], "province": r["province_name"],
                     "population_2024": int(r["population_2024"]),
                     "food_insecurity_forecast_pct": p["forecast"]["pct"], "forecast_class": p["forecast"]["class"],
                     "forecast_source": "province forecast applied to the LGU (no municipal food-insecurity measurement exists)",
                     "poverty_incidence_2021_pct": None if pd.isna(pov) else float(pov),
                     "poverty_source": "PSA 2021 small-area estimate (structural context, not food insecurity)"
                     if not pd.isna(pov) else "not published for this LGU"})
    by_prov = {p: sum(1 for x in rows if x["province"] == p) for p in PROVINCES}
    return {"target_quarter": f["target_quarter"], "issue_date": f["issue_date"], "count": len(rows), "by_province": by_prov,
            "note": "Each LGU shows its province's forecast. Municipal food insecurity is not measured by any survey, so LGU "
                    "values are not separate estimates; LGU poverty is structural context.", "rows": rows}


def register() -> dict:
    return {"note": "First forecast issued in each quarter, sealed by hash; scored when the next FIES wave is published.",
            "records": E.register()}

