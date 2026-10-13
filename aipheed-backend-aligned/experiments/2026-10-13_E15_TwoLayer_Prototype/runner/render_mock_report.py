"""E15: render TWO_LAYER_MOCK_REPORT.md (static) from a run's two_layer_output.json. Reads only E15 files.
Usage: python -B runner/render_mock_report.py <run_dir_name>"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard  # noqa: E402

guard.install()
import two_layer as TL  # noqa: E402

RUN = guard.EXP / "runs" / sys.argv[1]


def f(x, nd=1, sign=False):
    if x is None:
        return "—"
    return f"{x:+.{nd}f}" if sign else f"{x:.{nd}f}"


def main():
    res = json.loads((RUN / "two_layer_output.json").read_text(encoding="utf-8"))
    qs = res["quarters"]
    last = qs[-1]
    reg, prov, leg = last["regional_layer"], last["provincial_layer"], last["legacy_layer"]
    L = []
    a = L.append
    a(f"# aiPHeed Two-Layer View: Development Mock ({last['quarter']})")
    a("")
    a(f"> **Development prototype.** It is built from eligible data through {res['data_through']} and is **not "
      "connected to the dashboard or the production API**. It shows measured values, not forecasts. "
      f"Source run: `runs/{RUN.name}/`.")
    a("")
    a("## 1. Regional context: hunger in Balance Luzon (one value for the region)")
    a("")
    t = reg["trend"]
    a("| Item | Value |")
    a("|---|---|")
    a(f"| Hunger, {last['quarter']} | **{f(reg['level_pct'])}% of families** |")
    a(f"| Scope | {reg['scope']} (wider than CALABARZON) |")
    for r in reg["rounds"]:
        a(f"| Round | {r['round']}: {f(r['value_pct'])}%, published {r['published']} "
          f"({r['date_status']}, {r['series']} series) |")
    if t:
        a(f"| Change | {f(t['change_pct_points'], sign=True)} points against {t['compared_with_quarter']} "
          f"({t['quarters_apart']} quarter{'s' if t['quarters_apart'] > 1 else ''} earlier) |")
    a("")
    a("## 2. Provincial layer: relative food-price pressure")
    a("")
    a(f"Unweighted five-province mean food inflation, {last['quarter']}: "
      f"**{f(prov['five_province_mean_F_pct_unweighted'], 2)}%**. D is each province's food inflation minus this mean.")
    a("")
    a("| Rank (1 = highest) | Province | Food inflation, YoY % | D, points | Tied with |")
    a("|---|---|---|---|---|")
    for p in sorted(prov["provinces"], key=lambda p: (p["relative_pressure_rank"] or 9, p["province"])):
        a(f"| {p['relative_pressure_rank'] or '—'} | {p['province']} | {f(p['food_inflation_yoy_pct'], 2)} | "
          f"{f(p['relative_pressure_D_pp'], 2, sign=True)} | {', '.join(p['tied_with']) or '—'} |")
    a("")
    a("**Ranking by quarter** (1 = highest relative pressure; — means no rank, because a province is missing):")
    a("")
    recent = qs[-4:]
    a("| Province | " + " | ".join(q["quarter"] for q in recent) + " |")
    a("|---|" + "---|" * len(recent))
    for name in sorted(TL.PROVINCES.values()):
        cells = []
        for q in recent:
            p = next(x for x in q["provincial_layer"]["provinces"] if x["province"] == name)
            cells.append(f"{p['relative_pressure_rank'] or '—'} ({f(p['relative_pressure_D_pp'], 1, sign=True)})")
        a(f"| {name} | " + " | ".join(cells) + " |")
    a("")
    a("## 3. Regional hunger by quarter, 2021–2025")
    a("")
    a("| Quarter | Hunger, % | Change, points (against) | Rounds | Series | Last published |")
    a("|---|---|---|---|---|---|")
    for q in qs:
        r = q["regional_layer"]
        tr = r["trend"]
        ch = f"{f(tr['change_pct_points'], sign=True)} ({tr['compared_with_quarter']})" if tr else "—"
        a(f"| {q['quarter']} | {f(r['level_pct'])} | {ch} | {len(r['rounds'])} | "
          f"{', '.join(sorted({x['series'] for x in r['rounds']})) or 'no round'} | {r['latest_publication_date'] or '—'} |")
    a("")
    a("## 4. Legacy composite (secondary)")
    a("")
    a(f"*{leg['label']}.* {leg['formula']}; {leg['rule']}, threshold {leg['threshold_display']}. "
      f"H_A (production-series rounds) = {f(leg['H_A_production_rounds_pct'])}. Status: {leg['status']}.")
    a("")
    a("| Province | S1 | Legacy label |")
    a("|---|---|---|")
    for p in leg["provinces"]:
        a(f"| {p['province']} | {f(p['S1'], 2)} | {p['label'] or '—'} |")
    a("")
    n_all = sum(1 for q in qs for p in q["legacy_layer"]["provinces"] if p["label"])
    n_high = sum(1 for q in qs for p in q["legacy_layer"]["provinces"] if p["label"] == "HIGH")
    a(f"Across 2021–2025 the legacy label is HIGH in {n_high} of {n_all} province-quarters. It is unavailable in "
      "quarters without a production-series SWS round.")
    a("")
    a("## 5. Caveats (always shown)")
    a("")
    for c in res["caveats"]:
        a(f"- {c}")
    a("")
    a("## 6. What this view deliberately does not show")
    a("")
    a("- **No province is described in terms of household hunger or need.** No provincial outcome exists to support that.")
    a("- **The regional hunger value is never repeated as a provincial value.**")
    a("- **No D or rank is shown for a quarter with a missing province.** Missing values are never filled with 0.")
    a("- **No forecast is shown.** Forecasts await the prospective protocol (`PROSPECTIVE_VALIDATION_PROTOCOL.md`).")
    a("")
    txt = "\n".join(L)
    bad = TL.wording_violations({"report": txt})
    if bad:
        raise SystemExit(f"E15: banned wording in the report: {bad}")
    out = guard.EXP / "TWO_LAYER_MOCK_REPORT.md"
    if out.exists():
        raise FileExistsError(out)
    out.write_text(txt, encoding="utf-8", newline="\n")
    print(out)


if __name__ == "__main__":
    main()
