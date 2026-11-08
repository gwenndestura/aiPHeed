"""Prospective seal for S3 (FINAL_ARCHITECTURE candidate C): its forecasts issued 2026-10-01 (origin 2026-Q3) for every
lead 1..K, written before any 2026-Q4 SWS outcome exists, with a SHA-256. Not served; for prospective scoring only.

    python seal_s3.py   # out/sealed_prospective_S3.csv (+ .sha256)
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "FINAL_ARCHITECTURE" / "runner"))
import final_lib as F  # noqa: E402

O, U, FM, L, pd = F.O, F.U, F.FM, F.L, F.pd
OUT = HERE.parent / "out"


def main():
    U.setup()
    K = O.A4.RL._K()
    t = L.qi("2026-Q3")
    S = F.build(K)
    f = F.forecast(S, t, F.CANDS["C"], "S3")
    f = f.assign(issue_date=F.E.issue(t), quarter=f["target_q"].map(L.qs),
                 province=f["province_code"].map(L.NAMES), cls=(f["S3_p"] >= .5).map({True: "HIGH", False: "LOW"}))
    f = f[["province_code", "province", "issue_date", "lead", "quarter", "S3_p", "cls", "S3_cfg"]].sort_values(["lead", "province_code"])
    path = OUT / "sealed_prospective_S3.csv"
    assert not path.exists(), "a seal is never rewritten"
    f.to_csv(path, index=False, lineterminator="\n", float_format="%.6g")
    sha = FM.sha256(path)
    (OUT / "sealed_prospective_S3.csv.sha256").write_text(sha + "\n", encoding="utf-8", newline="\n")
    print(len(f), "forecasts sealed", sha[:8], f[f["lead"] <= 2][["province", "quarter", "S3_p", "cls"]].to_string(index=False))


if __name__ == "__main__":
    main()
