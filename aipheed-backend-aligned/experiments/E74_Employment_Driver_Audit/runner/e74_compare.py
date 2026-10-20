"""E74: every FIRI v2 indicator compared on one footing (its exact push on the index, the measurement the dashboard
bars are built from), across all 95 served province-quarters and for the 2027-Q1 forecast. Reads out/trace_rows.json.
Pure post-processing; no model code. Writes out/driver_comparison.json and tables/DRIVER_COMPARISON.md."""
import json
from collections import Counter, defaultdict
from pathlib import Path

E74 = Path(__file__).resolve().parents[1]
rows = json.loads((E74 / "out" / "trace_rows.json").read_text())
META = {"A1": ("E56 LightGBM P(food-price pressure), Lead 2", "province", "model output used as an index indicator"),
        "A2": ("PSA headline CPI vs usual level", "province", "index indicator"),
        "A3": ("PSA wholesale rice price change", "province", "index indicator"),
        "V1": ("PSA SAE 2021 poverty + POPCEN 2024 density", "province (static)", "index indicator (vulnerability)"),
        "C1": ("PAGASA El Nino alert/advisory", "national", "index indicator"),
        "C2": ("PAGASA typhoons within 300 km", "province", "index indicator"),
        "C3": ("PSA palay/corn production drop", "province", "index indicator"),
        "C4": ("PSA fisheries production drop", "province", "index indicator"),
        "E1": ("PSA LFS unemployment-rate change", "national", "index indicator"),
        "E2": ("BSP OFW remittance decline", "national", "index indicator"),
        "N1": ("FSSI-v3 news index", "province", "index indicator (signal)"),
        "H1": ("SWS regional hunger outlook", "regional (Balance Luzon)", "observed outcome evidence")}
ROLE = {"A1": "ACCESS", "A2": "ACCESS", "A3": "ACCESS", "E1": "ACCESS", "E2": "ACCESS", "C3": "AVAILABILITY",
        "C4": "AVAILABILITY", "C1": "STABILITY", "C2": "STABILITY", "V1": "VULNERABILITY", "H1": "OUTCOME", "N1": "NEWS"}
EVIDENCE = {"E1": "No provincial employment series exists; employment news does not track LFS (E73, rho -0.17); weight = equal default (untested); inside the LightGBM the same input has a negative TreeSHAP",
            "E2": "Missing for every 2026 issue; remittance news does not track BSP (E73)",
            "C2": "Climate news tracks PAGASA typhoons (E73, rho 0.35 [0.06, 0.60])",
            "C1": "The one El Nino in the data (2023-24) came with disinflation (E65)",
            "A1": "Price model 0.72 Lead-2 on its own price label (E70); the CPI projection alone is as good",
            "H1": "Direct outcome, regional only; against OCTA the index tracks hunger only through H1 (rho 0.73 with, 0.06 without)",
            "N1": "News adds no forecast value; bias correction not validated (E73)",
            "C4": "Fish-kill news does not track fisheries production (E73)",
            "V1": "Static; contributing factors did not reproduce the subsistence ordering (E71)",
            "A2": "-", "A3": "-", "C3": "-"}
stat = defaultdict(lambda: {"usable": 0, "abs_push": [], "largest": 0, "pos": 0, "neg": 0})
for r in rows:
    pu = r["indicator_push"]
    big = max(pu, key=lambda k: abs(pu[k])) if pu else None
    for k in META:
        s = stat[k]
        if r["indicator_score"].get(k) is not None and k in pu:
            s["usable"] += 1
            s["abs_push"].append(abs(pu[k]))
            s["pos"] += pu[k] > 0
            s["neg"] += pu[k] < 0
        s["largest"] += int(big == k)
fc = [r for r in rows if r["kind"] == "forecast"]
table = []
for k, (src, level, kind) in META.items():
    s = stat[k]
    f27 = {r["province"]: round(r["indicator_push"].get(k, 0.0), 4) if k in r["indicator_push"] else None for r in fc}
    vals = {r["province"]: r["indicator_x"].get(k) for r in fc}
    table.append({"indicator": k, "source": src, "level": level, "type": kind, "role": ROLE[k],
                  "usable_rows": s["usable"], "rows": len(rows), "missing_or_untestable": len(rows) - s["usable"],
                  "mean_abs_push_when_usable": round(sum(s["abs_push"]) / len(s["abs_push"]), 4) if s["abs_push"] else None,
                  "raises_rows": s["pos"], "lowers_rows": s["neg"], "largest_single_push_rows": s["largest"],
                  "push_2027Q1": f27, "same_value_all_provinces_2027Q1": (None if all(v is None for v in vals.values())
                                                         else len({v for v in vals.values() if v is not None}) == 1),
                  "independent_evidence": EVIDENCE[k]})
by_q = defaultdict(list)
for r in rows:
    by_q[r["target"]].append(r)
persist = {q: Counter(max(x["indicator_push"], key=lambda k: abs(x["indicator_push"][k])) for x in v) for q, v in sorted(by_q.items())}
out = {"rows": len(rows), "table": table, "largest_push_by_quarter": {q: dict(c) for q, c in persist.items()},
       "e56_treeshap_2027Q1": json.loads((E74 / "out" / "e56_treeshap_groups_2027Q1.json").read_text()),
       "verdict": ("No defensible overall ranking: the indicators are on one scale only as pushes on this index, but they "
                   "differ in geography (national, regional, provincial), in weight basis (evidence vs default) and in "
                   "missingness, and none except climate news and the regional hunger outcome has independent support. "
                   "Present them as contributing evidence, not ranked causes.")}
(E74 / "out" / "driver_comparison.json").write_text(json.dumps(out, indent=1))
L = ["# E74 driver comparison (generated by runner/e74_compare.py)\n",
     f"All {len(rows)} served FIRI v2 province-quarters (2022-Q3 … 2027-Q1). Push = exact contribution to FIRI − 0.5.\n",
     "| Indicator | Source | Level | Type | Usable rows | Mean abs push | Raises / lowers | Largest single push (rows) | 2027-Q1 push (Cav, Lag, Que, Riz, Bat) | Same value all provinces | Independent evidence |",
     "|---|---|---|---|---|---|---|---|---|---|---|"]
for t in table:
    p = t["push_2027Q1"]
    p27 = ", ".join("—" if p.get(x) is None else f"{p[x]:+.3f}" for x in ("cavite", "laguna", "quezon", "rizal", "batangas"))
    L.append(f"| {t['indicator']} | {t['source']} | {t['level']} | {t['type']} | {t['usable_rows']}/{t['rows']} | "
             f"{t['mean_abs_push_when_usable'] if t['mean_abs_push_when_usable'] is not None else '—'} | {t['raises_rows']} / {t['lowers_rows']} | "
             f"{t['largest_single_push_rows']} | {p27} | {'missing' if t['same_value_all_provinces_2027Q1'] is None else t['same_value_all_provinces_2027Q1']} | {t['independent_evidence']} |")
L.append("\n**Largest single push by quarter:** " + "; ".join(f"{q}: {', '.join(f'{k} {n}' for k, n in c.items())}" for q, c in persist.items()))
L.append("\n**Verdict:** " + out["verdict"])
(E74 / "tables").mkdir(exist_ok=True)
(E74 / "tables" / "DRIVER_COMPARISON.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("\n".join(L))
