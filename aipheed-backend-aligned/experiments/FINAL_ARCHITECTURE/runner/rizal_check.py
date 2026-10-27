"""Why the served P0H4 over-predicts Rizal (calibration-in-the-large +0.20 at Leads 1-2) and how errors change around the
2025-Q2 SWS design change. Descriptive; nothing is tuned.

    python rizal_check.py   # out/rizal_check.txt
"""
import final_lib as F

U, C, B, E, L, np, pd = F.U, F.C, F.B, F.E, F.L, F.np, F.pd
OUT = F.OUT


def main():
    U.setup()
    spec = L.e40_spec()
    ps = B.ps_frame(E.data()[0])
    ps["province"] = ps["province_code"].map(L.NAMES)
    ps["period"] = np.where(ps["q"] < L.qi("2023-Q1"), "2021-22 (threshold window)", "2023-26 (evaluation)")
    lines = ["Price-condition rate by province and period (all CPI quarters):",
             ps.groupby(["province", "period"])["y"].agg(["mean", "size"]).round(2).to_string(), "",
             "Thresholds (2021-22 P60): " + str({L.NAMES[p]: (round(spec['food'][p], 2), round(spec['gap'][p], 2))
                                                for p in spec['food']}), ""]
    D = pd.read_csv(F.EXP / "LEAD2_ONE_MODEL" / "out" / "predictions.csv", dtype={"province_code": str})
    for k in (1, 2):
        g = D[D["lead"] == k].copy()
        g["province"] = g["province_code"].map(L.NAMES)
        t = g.groupby("province").agg(mean_pi_P=("P0_price", "mean"), price_rate=("price", "mean"),
                                      mean_pi_H=("pi_H4", "mean"), mean_P=("P0H4_p3", "mean"), y=("y", "mean"),
                                      mean_S3=("S3_p", "mean"))
        lines += [f"Lead {k} (evaluation rows):", t.round(3).to_string(), ""]
    S = U.stack(1)
    v1 = S.drop_duplicates("province_code").set_index("province_code")["V1"]
    lines.append("V1 (static): " + str({L.NAMES[p]: round(float(v), 3) for p, v in v1.items()}))
    (OUT / "rizal_check.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
