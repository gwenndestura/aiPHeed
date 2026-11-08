"""Build the E58 record served when AIPHEED_LEAD2_MODEL=e58: the E56 LightGBM food-insecurity record (probabilities,
TreeSHAP, freshness and artifacts unchanged) plus the E58 two-signal early warning per province and quarter
(experiments/E58_Rising_Stress_Early_Warning/PROTOCOL.md section 3, adopted under section 5):

    ALERT     P(HIGH food-insecurity risk) >= 0.5
    EMERGING  P(provincial food-price pressure) >= 0.5 while P(HIGH) < 0.5 (a stale or low hunger reading does not
              suppress the warning; the latest hunger reading is reported with it)
    NONE      otherwise
    direction rising / steady / easing relative to the province's latest T43 label known at the issue date

    backend/venv/Scripts/python.exe -B scripts/build_record_e58.py   -> data/e58/e58_record.json
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
EXP = BACKEND.parent / "aipheed-backend-aligned" / "experiments"
E58 = EXP / "E58_Rising_Stress_Early_Warning"
SRC = BACKEND / "data" / "e56" / "e56_record.json"
OUT = BACKEND / "data" / "e58" / "e58_record.json"
sys.path.insert(0, str(EXP / "E55_Food_Insecurity_LightGBM" / "runner"))
H_THR = 11.3


def warning(p_high, p_price, last_label, last_q, h_last, h_q):
    level = "ALERT" if p_high >= 0.5 else ("EMERGING" if p_price >= 0.5 else "NONE")
    if last_label is None:
        direction = "unknown"
    elif level != "NONE" and last_label == 0:
        direction = "rising"
    elif level == "NONE" and last_label == 1:
        direction = "easing"
    else:
        direction = "steady"
    hunger = f"the latest regional hunger reading ({h_last:.1f}% in {h_q}) is {'above' if h_last > H_THR else 'at or below'} 11.3%"
    text = {"ALERT": f"Early warning ALERT: HIGH food-insecurity risk is forecast ({p_high:.0%}); {hunger}.",
            "EMERGING": (f"Early warning EMERGING: food-price pressure is likely ({p_price:.0%}) although the forecast of HIGH "
                         f"food-insecurity risk is {p_high:.0%}; {hunger}, so the hunger condition is not yet confirmed."),
            "NONE": f"No early warning: food-price pressure {p_price:.0%}, HIGH-risk probability {p_high:.0%}."}[level]
    if direction == "rising":
        text += f" Risk is rising from the latest observed LOW ({last_q})."
    elif direction == "easing":
        text += f" Risk is easing from the latest observed HIGH ({last_q})."
    if level != "NONE":
        text += " Model warning for DA review and planning; not an official classification."
    return {"level": level, "warn": level != "NONE", "probabilityHigh": round(p_high, 4),
            "probabilityPricePressure": round(p_price, 4), "direction": direction,
            "latestKnownLabel": None if last_label is None else ("HIGH" if last_label == 1 else "LOW"),
            "latestKnownLabelQuarter": last_q, "latestHunger": round(h_last, 1), "latestHungerQuarter": h_q,
            "text": text}


def main():
    import e55_lib as F
    L = F.L
    rec = json.loads(SRC.read_text(encoding="utf-8"))
    body = {k: v for k, v in rec.items() if k != "content_sha256"}
    assert hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest() == rec["content_sha256"]
    run = sorted((E58 / "runs").glob("2026*"))[0]
    res = json.loads((run / "results.json").read_text())
    assert res["acceptance_EW"]["EW_adopted"], "EW not adopted under E58 PROTOCOL section 5"
    proto = (E58 / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]
    d = L.load()
    memo = {}

    def asof(origin_q):
        if origin_q not in memo:
            t = L.qi(origin_q)
            hs = d.cut(t).sws.groupby("q")["H"].mean().sort_index()
            memo[origin_q] = (F.t43_last(d, t), float(hs.iloc[-1]), L.qs(int(hs.index[-1])))
        return memo[origin_q]

    n = {"ALERT": 0, "EMERGING": 0, "NONE": 0}
    for code, v in rec["provinces"].items():
        last, h, hq = asof(rec["originQuarter"])
        lab, lq = last[code]
        f = v["forecast"]
        v["earlyWarning"] = warning(f["probability"], f["components"]["probabilityPricePressure"],
                                    None if lab != lab else int(lab), None if lq is None else L.qs(lq), h, hq)
        n[v["earlyWarning"]["level"]] += 1
        for q, e in v["pastDrivers"].items():
            last, h, hq = asof(e["originQuarter"])
            lab, lq = last[code]
            e["earlyWarning"] = warning(e["probability"], e["probabilityPricePressure"],
                                        None if lab != lab else int(lab), None if lq is None else L.qs(lq), h, hq)
    ew = res["rules"]["EW"]
    rec.update({
        "schema": "e58/1",
        "name": "aiPHeed provincial food-insecurity risk forecast with early warning (E56 LightGBM + E58 rule, experimental)",
        "status": "EXPERIMENTAL - development evidence, not independently validated; enabled only with AIPHEED_LEAD2_MODEL=e58",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "modelVersion": rec["modelVersion"] + f"; early-warning rule E58-EW (protocol sha {proto[:16]})",
        "earlyWarningRule": {
            "levels": {"ALERT": "P(HIGH) >= 0.5", "EMERGING": "P(price pressure) >= 0.5 and P(HIGH) < 0.5",
                       "NONE": "otherwise"},
            "rationale": "E58 diagnosis: half of E56's missed HIGH rows came from a hunger reading 3-4 quarters older than "
                         "the target suppressing a correct price signal; the warning is not suppressed by it.",
            "evaluation": {"rows": res["rows"], "onsets": res["events"]["ONSET"],
                           "onset_recall": ew["ONSET"]["recall"], "onset_recall_ci": ew["ONSET_recall_ci"],
                           "HIGH_recall": ew["HIGH"]["recall"], "accuracy": ew["HIGH"]["accuracy"],
                           "balanced_accuracy": ew["HIGH"]["balanced_accuracy"], "false_positive_rate": ew["HIGH"]["fp_rate"],
                           "E56_onset_recall": res["rules"]["C0_E56"]["ONSET"]["recall"],
                           "projection_only_onset_recall": res["rules"]["B_PROJ"]["ONSET"]["recall"]},
            "limitations": ["Development evidence on 10 already-examined quarters; about 4 independent onset episodes.",
                            "In a low-hunger period EMERGING warnings may not become HIGH food-insecurity risk: in 2021-2023, "
                            "24 of 29 price-pressure province-quarters were not T43 HIGH.",
                            "A model warning for DA review; DA confirmation is separate."],
            "counts_at_target": n},
        "sources": {**rec["sources"], "e58_protocol_sha256": proto, "e58_evaluation_run": run.name, "base_record": "e56/1"},
    })
    for v in rec["provinces"].values():
        v["warnings"] = v["warnings"] + ["Early-warning levels (E58) are model warnings for DA review, not official "
                                         "classifications; EMERGING means price pressure without confirmed hunger."]
    rec.pop("content_sha256", None)
    rec["content_sha256"] = hashlib.sha256(json.dumps(rec, sort_keys=True, default=str).encode()).hexdigest()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    print(OUT, rec["content_sha256"][:16], n)


if __name__ == "__main__":
    main()
