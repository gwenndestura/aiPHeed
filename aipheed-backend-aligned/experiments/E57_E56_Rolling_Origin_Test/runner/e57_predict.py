"""E57 step 1 (PROTOCOL section 2): run the frozen E56 procedure at every eligible rolling origin and SEAL the forecasts
before any label is read. Also writes the as-of baseline inputs (persistence, known-label majority/climatology,
province climatology), which use only labels known at each origin.

    backend/venv/Scripts/python.exe -B runner/e57_predict.py  -> sealed/predictions.csv (+ .sha256)
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

sys.dont_write_bytecode = True
E57 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(E57.parent / "E56_LightGBM_Optimization" / "runner"))
import e56_lib as G  # noqa: E402

E, F, L, np, pd = G.E, G.F, G.L, G.np, G.pd
ORIGINS = list(range(L.qi("2023-Q4"), L.qi("2026-Q1") + 1))
SEALED = E57 / "sealed" / "predictions.csv"


def verify():
    want = (E57 / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]
    got = hashlib.sha256((E57 / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if got != want:
        raise SystemExit("PROTOCOL.md changed after freezing")


def known_labels(d, t):
    """T43 labels known at O(t): quarters <= t-1 whose SWS rounds were all posted before O(t), CPI from d.cut(t)."""
    r = pd.read_csv(L.SWS_FILE)
    r["q"] = r["quarter"].map(L.qi)
    r["published"] = pd.to_datetime(r["published"])
    complete = {q for q, g in r.groupby("q") if (g["published"] < L.origin(t)).all()}
    Y = F.t43_labels(d.cut(t))
    return Y[Y["q"].isin(complete) & (Y["q"] <= t - 1) & Y["T43"].notna()]


def main():
    verify()
    if SEALED.exists():
        raise SystemExit("already sealed; predictions are written once")
    d, X, B = E.load()
    space = G.search_space()
    rows = []
    for t in ORIGINS:
        tr0, te0 = F.frame(d, X, B, t, None)               # eligibility without the poverty column (D-0 note in report)
        assert E.ok(tr0, te0) and F.hunger(d, X, t) is not None, L.qs(t)
        fx = G.tuned_forecast(d, X, B, t, space)
        kl = known_labels(d, t)
        last = F.t43_last(d, t)
        maj = float(kl["T43"].mean() >= 0.5)
        clim = float(kl["T43"].mean())
        h_last = float(d.cut(t).sws.groupby("q")["H"].mean().sort_index().iloc[-1])
        for i, p in enumerate(L.PROVS):
            kp = kl[kl["province_code"] == p]
            rows.append({"origin_quarter": L.qs(t), "issue_date": str(L.origin(t).date()), "target": L.qs(t + 2),
                         "t": t, "province_code": p, "province": L.NAMES[p],
                         "E56_p": float(fx["p"][i]), "E56_p_price": float(fx["p_price"][i]),
                         "E56_p_hunger": float(fx["p_hunger"]), "E56_config": int(fx["cfg"]["id"]),
                         "E56_pov_in_config": fx["cfg"]["pov"] == "AS",
                         "ofw_inputs_missing": bool(pd.isna(fx["te"].iloc[i].get("remit_usd_yoy"))),
                         "PERSIST_p": last[p][0], "PERSIST_from": None if last[p][1] is None else L.qs(last[p][1]),
                         "MAJORITY_p": maj, "CLIM_p": clim, "PROVCLIM_p": float(kp["T43"].mean()) if len(kp) else clim,
                         "known_label_quarters": int(kl["q"].nunique()), "H_last_known": h_last})
        print("sealed origin", L.qs(t), "config", fx["cfg"]["id"], flush=True)
    SEALED.parent.mkdir(exist_ok=True)
    pd.DataFrame(rows).to_csv(SEALED, index=False, float_format="%.12g")
    (SEALED.parent / "predictions.csv.sha256").write_text(hashlib.sha256(SEALED.read_bytes()).hexdigest() + "  predictions.csv\n")
    print("sealed", len(rows), "forecasts")


if __name__ == "__main__":
    main()
