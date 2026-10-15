"""
app/services/report_data_e31.py
-------------------------------
GET /api/v1/report/data for the Visualization page, from the E31 record (the same numbers as the map, the ranking
and the E31 PDF). The frontend lays the blocks out (lib/chartReport.ts); every number and sentence comes from here.

  type=trend  province estimates over a quarter range, each point labelled with its mode
  type=shap   the driver breakdown of one province-quarter. The served engine is additive, so this is its exact
              decomposition (S1 - tau = (H - tau) + 2D), labelled as such; it is not a SHAP approximation of a
              different model.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.ml.inference import e31_engine as E31
from app.services import reference as ref

MODE_SHORT = {"BACKTEST": "backtest", "RETROSPECTIVE_BLIND": "frozen forecast, scored", "NOWCAST": "nowcast",
              "FORECAST": "forecast"}


def _rows_for(quarters, code):
    out = []
    for q in quarters:
        r = E31.quarter_row(q, "nowcast")
        if r and code in r["provinces"]:
            out.append((q, r["mode"], r["provinces"][code]))
    return out


def _common(rec: dict) -> list:
    return [{"kind": "paragraph", "style": "note", "text": rec["disclaimer"]},
            {"kind": "paragraph", "text": "Estimates are P(S1 = H + 2D above its threshold): H is regional SWS "
                                          "hunger shared by all five provinces; D is provincial relative food "
                                          "inflation. No lead time is validated; values are indicative."}]


def trend(scope: str, pid: str | None, q_from: str | None, q_to: str | None) -> dict:
    rec = E31.record()
    quarters = [q for q in E31.E31Engine("nowcast").available_quarters()
                if (q_from is None or q >= q_from) and (q_to is None or q <= q_to)]
    codes = ([ref.province_code(pid)] if scope == "province" and pid else [m["code"] for m in ref.PROVINCES.values()])
    names = {m["code"]: m["name"] for m in ref.PROVINCES.values()}
    series, table = [], []
    for c in codes:
        rows = {q: (mode, v) for q, mode, v in _rows_for(quarters, c)}
        series.append({"name": names[c], "values": [round(rows[q][1]["p_high"] * 100, 1) if q in rows else None
                                                     for q in quarters]})
        for q in quarters:
            if q in rows:
                mode, v = rows[q]
                table.append([names[c], q, MODE_SHORT[mode], f"{100 * v['p_high']:.0f}%",
                              v.get("observed_label") or "-"])
    blocks = [{"kind": "heading", "level": 1, "text": "Estimated food-insecurity risk over time"}, *_common(rec),
              {"kind": "figure", "label": "Figure 1", "title": "P(S1 above threshold), percent",
               "chart": {"type": "line", "quarters": quarters, "series": series, "yMin": 0, "yMax": 100, "yStep": 20,
                         "lines": [{"value": 50, "label": "50%"}]},
               "note": "Backtests are development evidence; 2026-Q3 was frozen before its outcome and then scored; "
                       "2026-Q4 is a nowcast (cutoff " + rec["information_cutoff"][:10] + ") and 2027-Q1 a forecast."},
              {"kind": "table", "label": "Table 1", "title": "Estimates by quarter and mode",
               "columns": [{"label": "Province", "align": "left", "width": 90}, {"label": "Quarter", "align": "left", "width": 60},
                           {"label": "Mode", "align": "left", "width": 140}, {"label": "Estimate", "align": "right", "width": 60},
                           {"label": "Observed", "align": "center", "width": 60}],
               "rows": table, "note": "Observed = the released label where the outcome is known."}]
    return {"type": "trend", "title": "aiPHeed trend report", "subtitle": f"{quarters[0]} to {quarters[-1]}" if quarters else "",
            "generatedDate": datetime.now(timezone.utc).date().isoformat(),
            "metadata": [["Record", rec["content_sha256"][:16]], ["Information cutoff", rec["information_cutoff"]],
                         ["Engine", rec["served_engine"]["name"]]], "blocks": blocks}


def drivers(pid: str, quarter: str) -> dict:
    rec = E31.record()
    c = ref.province_code(pid)
    r = E31.quarter_row(quarter, "nowcast")
    if r is None or c not in r["provinces"]:
        raise KeyError(f"no estimate for {pid} in {quarter}")
    v = r["provinces"][c]
    ds = v.get("drivers") or []
    tot = sum(abs(d["contribution"]) for d in ds) or 1.0
    bars = [{"label": d["factor"], "pct": round(100 * abs(d["contribution"]) / tot),
             "direction": "increases_risk" if d["contribution"] >= 0 else "protective"} for d in ds]
    blocks = [{"kind": "heading", "level": 1, "text": f"What drives the estimate: {v['province']}, {quarter}"},
              *_common(rec),
              {"kind": "paragraph", "text": f"Mode: {MODE_SHORT[r['mode']]} (lead {r['lead']}); estimate "
                                            f"{100 * v['p_high']:.0f}% ({v['signal']}); threshold {r['threshold']:.2f}."},
              {"kind": "figure", "label": "Figure 1", "title": "Share of the margin over the threshold",
               "chart": {"type": "bars", "bars": bars}, "note": v.get("driver_method")},
              {"kind": "table", "label": "Table 1", "title": "Driver contributions (S1 points)",
               "columns": [{"label": "Driver", "align": "left", "width": 230}, {"label": "Input value", "align": "right", "width": 70},
                           {"label": "Contribution", "align": "right", "width": 70}, {"label": "Scope", "align": "left", "width": 120}],
               "rows": [[d["factor"], f"{d['value']:.2f}", f"{d['contribution']:+.2f}", d["kind"]] for d in ds],
               "note": "Associations used by the model, not causes. Contributions sum to S1 - threshold."}]
    return {"type": "shap", "title": "aiPHeed driver report", "subtitle": f"{v['province']} {quarter}",
            "generatedDate": datetime.now(timezone.utc).date().isoformat(),
            "metadata": [["Record", rec["content_sha256"][:16]], ["Information cutoff", r["information_cutoff"]],
                         ["Mode", MODE_SHORT[r["mode"]]]], "blocks": blocks}
