"""LEAD2_DEPLOY: day-by-day replay of the deployable SWS-release re-issue (backend app.ml.inference.sws_reissue) over
the walk-forward history, run twice per day (repeated scheduler runs). Each origin's quarter-start P0H4 forecasts
(Leads 1-4) are recorded on their own issue date; the re-issue then only sees what the store says was published.

Checks: the re-issued Lead-2+ probabilities and issue dates equal P0H4-U (FORECAST_RESEARCH S-AB) row for row; no
duplicates; quarter-start rows unchanged; every row's SWS reading was published before its issue date. Reports the
deployment-timing effect (P0H4 quarter-start -> P0H4 + re-issue) separately from any model change.

    python deploy_replay.py     # ../out/deploy_replay.json, ../out/deploy_replay_history.csv
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd

import lt_lib as T

BACKEND = T.EXP.parent.parent / "backend"
sys.path.insert(0, str(BACKEND))
from app.ml.inference import sws_reissue as RI  # noqa: E402

F, M, KEY = T.F, T.M, T.KEY
NAMES = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal",
         "PH040500000": "Batangas"}


def main():
    C = pd.read_csv(T.OUT / "candidates.csv", dtype={"province_code": str})
    S = T.stack()
    C = C.merge(S[KEY + ["psa_newest_month"]], on=KEY)
    tmp = Path(tempfile.mkdtemp())
    sws, hist = tmp / "sws.csv", tmp / "history.csv"
    shutil.copy(BACKEND / "data" / "ch1_reissue" / "sws_rounds.csv", sws)
    r = RI.load_sws(sws)
    qs = []
    for x in C.itertuples():
        iss = RI.origin(int(x.t))
        ph = RI.pi_hunger(r, iss, int(x.t) + int(x.lead)) or {}
        qs.append({"province_code": x.province_code, "province": NAMES[x.province_code], "quarter": RI.qlabel(int(x.q)),
                   "issue_date": iss.isoformat(), "lead": int(x.lead), "pi_hunger": x.pi_H_A, "pi_price": x.P0_price,
                   "probability": x.P0H4_p3, "sws_newest_q": ph.get("sws_q_used"),
                   "sws_newest_published": ph.get("sws_published_used"), "h_last": ph.get("h_last"),
                   "psa_newest_month": x.psa_newest_month, "model": "P0H4"})
    Q = pd.DataFrame(qs)
    first, last = RI.origin(int(C["t"].min())), RI.window_cap(int(C["t"].max())) + timedelta(days=3)
    day, runs, added = first, 0, []
    while day <= last:
        todays = Q[Q["issue_date"] == day.isoformat()]
        if len(todays):
            RI.record_quarter_start(todays, path=hist, recorded_at=day.isoformat())
        for _ in range(2):                                       # repeated scheduler runs on the same day
            s = RI.reissue(day, sws_path=sws, path=hist, log_path=None, recorded_at=day.isoformat())
            added.append(s["rows_added"])
            runs += 1
        day += timedelta(days=1)
    before = hashlib.sha256(hist.read_bytes()).hexdigest()
    again = [RI.reissue(d, sws_path=sws, path=hist, log_path=None)["rows_added"] for d in (first, last, last + timedelta(days=400))]
    H = RI.load_history(hist)
    res = {"days": (last - first).days + 1, "runs": runs, "rows_added_total": int(sum(added)),
           "second_same_day_runs_adding_rows": int(sum(added[1::2])), "extra_runs_added": int(sum(again)),
           "history_unchanged_by_extra_runs": hashlib.sha256(hist.read_bytes()).hexdigest() == before,
           "history_rows": int(len(H)), "duplicate_ids": int(H["forecast_id"].duplicated().sum())}
    allB = H[H["issue_schedule"] == "B"]
    res["reissue_rows_written"] = int(len(allB))
    res["superseded_reissues"] = int(len(allB) - len(allB.drop_duplicates(["origin_quarter", "province_code", "lead"])))
    B = allB.sort_values("issue_date").groupby(["origin_quarter", "province_code", "lead"]).tail(1).copy()   # in force
    B["t"] = B["origin_quarter"].map(RI.qindex)
    B = B.merge(C[KEY + ["q", "y", "C0_p", "pi_H_AB"]].assign(target_quarter=lambda d: d["q"].map(RI.qlabel)),
                on=["t", "lead", "province_code", "target_quarter"], how="left")
    B["fr_issue"] = [F.issue(int(t), "B") for t in B["t"]]
    res["reissued_rows"] = int(len(B))
    res["expected_rows_leads_2_4"] = int((C["lead"] >= 2).sum())
    res["max_abs_vs_P0H4U_probability"] = float((B["probability"] - B["C0_p"]).abs().max())
    res["max_abs_vs_P0H4U_pi_H"] = float((B["pi_hunger"] - B["pi_H_AB"]).abs().max())
    res["issue_dates_equal_S_AB"] = bool((B["issue_date"] == B["fr_issue"]).all())
    res["triggers"] = B.drop_duplicates("origin_quarter")["trigger"].value_counts().to_dict()
    has = H["sws_published_used"].notna()
    res["sws_used_published_before_issue"] = bool((H.loc[has, "sws_published_used"].astype(str) < H.loc[has, "issue_date"]).all())
    res["rows_without_sws_reading"] = int((~has).sum())
    res["quarter_start_rows_intact"] = int((H["issue_schedule"] == "A").sum()) == len(Q)
    # deployment-timing effect at Lead 2: quarter-start (served P0H4) vs the same model re-issued
    g = C[C["lead"] == 2].merge(B[["t", "lead", "province_code", "probability"]], on=KEY, how="left")
    res["lead2"] = {}
    for name, col in (("P0H4 quarter-start (served)", "P0H4_p3"), ("P0H4 + SWS re-issue (deployable)", "probability")):
        d = F.evaluate(g.assign(PERS=g["PERS_AB"]), col, "PERS")
        dv = g["q"] <= F.DEV_LAST
        res["lead2"][name] = {"metrics": d["metrics"], "failed": d["failed"], "acc_thirds": d["acc_thirds"], "loqo_min": d["loqo_min"],
                              "later_quarters": M.cls(g.loc[~dv, "y"], g.loc[~dv, col]),
                              "brier_vs_persist_p": d["brier_vs_persist"]["p_less"], "brier_vs_clim_p": d["brier_vs_clim"]["p_less"]}
    res["lead2_brier_change"] = M.boot_diff(g["q"], (g["probability"] - g["y"]) ** 2, (g["P0H4_p3"] - g["y"]) ** 2)
    H.to_csv(T.OUT / "deploy_replay_history.csv", index=False, lineterminator="\n", float_format="%.6g")
    (T.OUT / "deploy_replay.json").write_text(json.dumps(res, indent=1, default=float))
    shutil.rmtree(tmp, ignore_errors=True)
    print(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main()
