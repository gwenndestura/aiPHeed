"""Target and timing audit (descriptive; nothing is tuned): the exact Lead-2 information cut-off per issue date, and how
fragile the frozen T43c thresholds are (labels under nearby thresholds; not used for selection).

    python timing_audit.py   # out/timing_audit.txt, out/lead2_timing.csv
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "LEAD2_OPTIMIZATION" / "runner"))
import l2_lib as X  # noqa: E402

U, C, FM, B, E, L, np, pd = X.U, X.C, X.FM, X.B, X.E, X.L, X.np, X.pd
OUT = HERE.parent / "out"


def main():
    U.setup()
    lines = []
    lab = C.labels()
    rows = []
    for q in sorted(lab["q"].unique()):
        t = q - 2
        if t < L.qi("2022-Q4"):
            continue
        iss = E.issue(t)
        kn = C.bl_known(iss)
        r = FM.rounds("primary")
        r = r[(r["area"] == "BL") & (r["q"] == q)]
        rows.append({"origin_t": L.qs(t), "issue_date": iss, "cpi_cutoff_month": L.ym_s(L.m0_of(t)),
                     "newest_sws_quarter": L.qs(kn[-1][0]), "newest_sws_published": kn[-1][3],
                     "target_quarter": L.qs(q), "target_starts": L.origin(q).date().isoformat(),
                     "days_issue_to_target_start": (L.origin(q).date() - L.origin(t).date()).days,
                     "target_sws_published": r["published"].max(), "target_after_cutoff": r["published"].min() >= iss,
                     "cpi_target_months_after_cutoff": min(L.target_months(t, 2)) > L.m0_of(t)})
    T = pd.DataFrame(rows)
    T.to_csv(OUT / "lead2_timing.csv", index=False, lineterminator="\n")
    lines.append("Lead 2 = forecast issued on the first day of quarter t+1 (O(t)) for quarter t+2; SWS rounds published "
                 "before O(t); CPI months <= month 2 of quarter t.")
    lines.append(T.to_string(index=False))
    lines.append(f"every target's SWS rounds published after the cut-off: {bool(T['target_after_cutoff'].all())}; every "
                 f"target CPI month after the cut-off: {bool(T['cpi_target_months_after_cutoff'].all())}")
    spec = L.e40_spec()
    h = C.bl_quarters()
    w = h[(h.index >= L.qi("2021-Q1")) & (h.index <= L.qi("2022-Q4"))]
    lines.append(f"\nHunger line 11.3 = P60 of {len(w)} BL quarters 2021-22 {[round(v, 2) for v in w.values]} "
                 f"(frozen in E40 before the forecasting experiments); price thresholds = P60 of 8 quarters per province.")
    ev = h[h.index >= L.qi("2023-Q2")]
    for line_ in (10.3, 11.3, 12.3):
        lines.append(f"  descriptive: with a hunger line of {line_}, {int((ev > line_).sum())}/{len(ev)} evaluation "
                     f"quarters are hunger-HIGH; quarters within 1 point of 11.3: "
                     f"{[L.qs(q) for q, v in ev.items() if abs(v - 11.3) <= 1.0]}")
    near = lab[(lab["q"] >= L.qi("2023-Q2"))]
    fd = near["F"] - near["province_code"].map(spec["food"])
    gd = (near["F"] - near["HL"]) - near["province_code"].map(spec["gap"])
    margin = np.maximum(fd, gd)
    lines.append(f"  descriptive: province-quarters whose price condition is decided within 0.5 points of a threshold: "
                 f"{int((margin.abs() <= 0.5).sum())}/{len(near)}")
    (OUT / "timing_audit.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
