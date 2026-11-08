"""
E133 prospective seal (protocol section 8): every E133 model's forecast for 2026-Q4 .. 2027-Q3 for the 4 SWS areas,
issued 2026-11-01 with all information published by then, plus labelled model-based provincial estimates from the
E133 candidate (HFM-X, frozen selection rule). Write-once.

    python -I runner/e133_seal.py
"""
from __future__ import annotations

import hashlib
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e133_run as R  # noqa: E402

sys.path.insert(0, str(R.EXP / "E131_Objectives_Resolution" / "runner"))
import e131_provincial as PV  # noqa: E402

X, L = R.X, R.L
SEALED = HERE.parent / "sealed"
AREA = SEALED / "E133_PROSPECTIVE_SEAL.csv"
PROV = SEALED / "E133_PROVINCIAL_MODEL_BASED_SEAL.csv"
ISSUE = date(2026, 11, 1)
CANDIDATE = "HFM-X"
MODELS = ["HFM", "HFM-NS", "HFM-NS-DES", "HFM-TREND", "HFM-X", "HFM-X-B30", "HFM-X-PH1", "HFM-X-PH2"]


def main():
    if AREA.exists() or PROV.exists():
        sys.exit("refusing to overwrite an existing E133 seal")
    rr = X.rounds()
    qa = X.asof(rr, ISSUE)
    assert L.qs(int(qa["qi"].max())) == "2026-Q3"
    drv = {"rice": R.Drivers("rice"), "b30": R.Drivers("b30"), "oni": R.Drivers("rice", "oni_quarter_mean")}
    e132 = pd.read_csv(R.EXP / "E132_Final_Methodology" / "sealed" / "E132_PROSPECTIVE_SEAL.csv")
    rows = []
    for k in L.LEADS:
        T = L.qs(L.qi("2026-Q4") - 1 + k)
        res = R.predict(qa, ISSUE, L.qi(T), drv)
        for j, a in enumerate(X.AREAS):
            s = qa[qa.area == a].sort_values("qi")
            seas = e132[(e132.area == a) & (e132.target == T)]["SEAS-LLM"].iloc[0]
            rec = {"area": a, "issue": ISSUE.isoformat(), "lead": k, "target": T, "y_latest": float(s["y"].iloc[-1]),
                   "latest_quarter": L.qs(int(s["qi"].iloc[-1])), "PERSIST": float(s["y"].iloc[-1])}
            for m in MODELS:
                f, sd = float(res[m][0][j]), float(res[m][1][j])
                rec[m], rec[f"{m}_lo80"], rec[f"{m}_hi80"] = f, f - X.Z80 * sd, f + X.Z80 * sd
            rec["ENS133"] = (rec["HFM-NS-DES"] + float(seas)) / 2
            fx = res["HFM-X"][2]
            rec.update({f"HFM-X_beta_{g}": fx.beta.get(g) for g in R.ALL_GROUPS})
            rows.append(rec)
    S = pd.DataFrame(rows)
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    S.insert(0, "sealed_utc", stamp)
    S.insert(1, "candidate", f"{CANDIDATE} (frozen selection rule: highest Lead-2 within-tolerance share, P-DASH, S-U)")
    SEALED.mkdir(exist_ok=True)
    AREA.write_bytes(S.to_csv(index=False, lineterminator="\n").encode("utf-8"))
    bl = S[S.area == "balance_luzon"].rename(columns={CANDIDATE: "f", f"{CANDIDATE}_lo80": "lo80", f"{CANDIDATE}_hi80": "hi80"})
    rr_tab = pd.read_csv(R.EXP / "E131_Objectives_Resolution" / "out" / "x3c_relative_risk.csv")
    prov = PV.provincial_estimates(bl[["target", "lead", "f", "lo80", "hi80"]], rr_tab)
    prov["label"] = prov["label"].str.replace("Balance Luzon hunger forecast", f"Balance Luzon {CANDIDATE} hunger forecast")
    prov.insert(0, "sealed_utc", stamp)
    PROV.write_bytes(prov.to_csv(index=False, lineterminator="\n").encode("utf-8"))
    (SEALED / "E133_SEAL_SHA256.txt").write_text(
        "".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in (AREA, PROV)), encoding="utf-8")
    print(S[["area", "lead", "target", "y_latest", "HFM-NS-DES", "HFM-X", "HFM-X_lo80", "HFM-X_hi80", "HFM-X-B30"]].round(2).to_string(index=False))
    print(prov[["province", "target", "estimate", "lo80", "hi80"]].round(2).to_string(index=False))
    print((SEALED / "E133_SEAL_SHA256.txt").read_text())


if __name__ == "__main__":
    main()
