"""E58 step 2 (score-free, labels only): rising-event definitions and their counts, in the evaluation rows and in the
training labels known at each origin (feasibility of a dedicated rising-event classifier).

Events (PROTOCOL section 2):
  ONSET  province T43 HIGH at the target quarter AND its latest T43 label known at the issue date was LOW
  RISEP  food-price stress rising: target-quarter food YoY or food-minus-headline YoY >= 1.0 point above the latest
         complete quarter known at the issue date (1.0 = half-width of the BSP 3 +/- 1% inflation target band)
  HIGH   T43 HIGH at the target (the E56 target)

    backend/venv/Scripts/python.exe -B runner/e58_event_counts.py  -> tables/event_counts.json, data/events.csv
"""
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
E58 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(E58.parent / "E56_LightGBM_Optimization" / "runner"))
import e56_lib as G  # noqa: E402

F, L, np, pd = G.F, G.L, G.np, G.pd
RISE_PTS = 1.0


def events_for(d, t, p, Y):
    """Event labels for province p, target t+2, issued at O(t)."""
    last, lq = F.t43_last(d, t)[p]
    tgt = Y[(Y["province_code"] == p) & (Y["q"] == t + 2)]
    if not len(tgt) or pd.isna(tgt["T43"].iloc[0]):
        return None
    c = d.cut(t)
    Fk = L.quarter_F(c)
    Hk = L.quarter_F(c, "all_items").rename(columns={"F": "HL"})
    K = Fk.merge(Hk, on=["province_code", "q"])
    K = K[(K["province_code"] == p)].sort_values("q")
    k = K.iloc[-1]
    y = tgt.iloc[0]
    return {"t": t, "province_code": p, "target": L.qs(t + 2), "HIGH": int(y["T43"]),
            "ONSET": int(y["T43"] == 1 and last == 0), "last_known_T43": last,
            "RISEP": int((y["F"] - k["F"] >= RISE_PTS) or ((y["F"] - y["HL"]) - (k["F"] - k["HL"]) >= RISE_PTS)),
            "last_complete_cpi_quarter": L.qs(int(k["q"]))}


def main():
    d = L.load()
    Y = F.t43_labels(d)
    rows = []
    for t in range(L.qi("2021-Q4"), L.qi("2026-Q1") + 1):
        for p in L.PROVS:
            e = events_for(d, t, p, Y)
            if e:
                rows.append(e)
    Ev = pd.DataFrame(rows)
    (E58 / "data").mkdir(exist_ok=True)
    Ev.to_csv(E58 / "data" / "events.csv", index=False)
    evalr = Ev[(Ev["t"] >= L.qi("2023-Q4"))]
    out = {"evaluation_rows": int(len(evalr)),
           "evaluation_counts": {k: int(evalr[k].sum()) for k in ("HIGH", "ONSET", "RISEP")},
           "onset_by_quarter": evalr.groupby("target")["ONSET"].sum().astype(int).to_dict(),
           "risep_by_quarter": evalr.groupby("target")["RISEP"].sum().astype(int).to_dict(),
           "training_onsets_known_at_origin": {}}
    for t in range(L.qi("2023-Q4"), L.qi("2026-Q1") + 1):
        known = Ev[Ev["t"] + 2 <= t - 1]                      # targets whose outcome quarter is <= t-1
        out["training_onsets_known_at_origin"][L.qs(t)] = {"rows": int(len(known)), "ONSET": int(known["ONSET"].sum()),
                                                            "RISEP": int(known["RISEP"].sum())}
    (E58 / "tables").mkdir(exist_ok=True)
    (E58 / "tables" / "event_counts.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
