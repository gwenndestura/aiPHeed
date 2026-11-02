"""Export the sealed M3 mid-quarter update (PREREG_LEAD2 addendum 2; seal backend/seals/2026-11-01_2027-Q1_M3.json) for
the backend, with the driver (SHAP) values of the same model run.

The price part is refitted exactly as seal_lead2_m3.child did (run_m3.m0_m3 CPI cutoff for every origin, world prices
as served, uni_lib.select + UniPrice U2): no configuration is re-chosen and nothing is retrained differently. The export
refuses to write unless the refit reproduces the sealed configuration, training size, price and hunger parts.

    python -B export_m3.py

Writes backend/m3_update/rows_m3.csv (the rows.csv columns, one Lead-2 row per province) and
backend/m3_update/evaluation_m3.json (M3's development metrics from out/results.json). Nothing in backend/data,
backend/seals or the served P0H4 export changes.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_m3 as M  # noqa: E402

PR, U, L, E, SI, pd, np = M.PR, M.U, M.L, M.E, M.SI, M.pd, M.np
REPO = HERE.parents[3]
SEAL = REPO / "backend" / "seals" / "2026-11-01_2027-Q1_M3.json"
DEST = REPO / "backend" / "m3_update"
ISSUE, ORIGIN, LEAD = "2026-11-01", "2026-Q3", 2
FAMS = ("A1", "A2", "A3", "V1", "C1", "C2", "C3", "C4", "E1", "E2", "N1", "H1")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    seal = json.loads(SEAL.read_text(encoding="utf-8"))
    ledger = (REPO / "backend" / "seals" / "LEDGER.md").read_text(encoding="utf-8")
    seal_sha = sha(SEAL)
    if seal_sha not in ledger:
        raise SystemExit("M3 seal does not match its ledger hash")
    sealed = seal["candidates"]["C3_M3"]
    import export_l2 as XL                                         # GROUPS / EXTRA_GROUPS / VALUE_COLS, read-only
    PR.frozen_ok()
    U.setup()
    t = L.qi(ORIGIN)
    # ---- price part: the seal child's exact setup
    U.world_features = PR.world_features_at
    L.m0_of = M.m0_m3
    S = U.stack(PR.K)
    cutoff = L.ym_s(M.m0_m3(t))
    tr = U.train_rows(S, t)
    cc = U.cols("U2", True)
    cfg, _ = U.select(tr, cc, True)
    if f"u{cfg['id']}" != seal["inputs"]["priceFit"]["cfg"] or len(tr) != seal["inputs"]["priceFit"]["nTrain"]:
        raise SystemExit(f"refit differs from the seal: cfg u{cfg['id']}, nTrain {len(tr)}")
    if cutoff != seal["inputs"]["cpiCutoff"]:
        raise SystemExit(f"CPI cutoff {cutoff} != sealed {seal['inputs']['cpiCutoff']}")
    mdl = U.UniPrice(cfg, cc, True).fit(tr)
    te = S[(S["t"] == t) & (S["lead"] == LEAD)].sort_values("province_code").reset_index(drop=True)
    price = mdl.predict(te)
    sv = mdl.shap(te)
    L.m0_of = PR.M0_SERVED                                          # restored before the hunger part, as run_m3 does
    # ---- hunger part at the M3 issue date
    X = SI.setup()
    h, info = SI.h4_at(X, ISSUE, t, LEAD)
    rows = []
    target = L.qs(t + LEAD)
    lead_days = (dt.date(2027, 1, 1) - dt.date.fromisoformat(ISSUE)).days
    for i, x in te.iterrows():
        p = x["province_code"]
        s = sealed[p]
        if abs(price[i] - s["price"]) > 1e-6 or abs(h - s["hunger"]) > 1e-6 or abs(h * price[i] - s["probability"]) > 1e-6:
            raise SystemExit(f"{p}: refit {h:.6f} x {price[i]:.6f} differs from the seal {s}")
        fam = {f: 0.0 for f in FAMS}
        for j, c in enumerate(cc):
            f = U.FAMILY_OF.get(c, c)
            if f in fam:
                fam[f] += float(sv[i, j])
        prob = float(h * price[i])
        row = {"province_code": p, "province": U.C.PROV_NAME[p], "quarter": target, "issue_date": ISSUE, "lead": LEAD,
               "pi_hunger": float(h), "pi_price": float(price[i]), "probability": prob,
               "class": "HIGH" if prob >= 0.5 else "LOW", "observed": "", "observed_hunger_condition": "",
               "observed_price_condition": "", "sws_newest_q": info["newestSwsQ"],
               "sws_newest_published": info["newestSwsPublished"], "h_last": info["h_last"], "psa_newest_month": cutoff,
               "news_latest_published": x["news_latest_published"], "lead_days": lead_days,
               "A1_food": x["A1_food"], "A1_gap": x["A1_gap"], "A_mom": x["A_mom"],
               **{f"shap_{f}": fam[f] for f in FAMS},
               **{f"avail_{g}": int(bool(pd.Series([x[c] for c in cs]).notna().any()))
                  for g, cs in {**XL.GROUPS, **XL.EXTRA_GROUPS}.items()},
               **{f"val_{c}": x[c] for c in XL.VALUE_COLS},
               "model": "P0H4-M3", "seal_sha256": seal_sha}
        if not (str(row["sws_newest_published"]) < ISSUE and str(row["news_latest_published"])[:10] < ISSUE):
            raise SystemExit(f"{p}: an input was published on or after {ISSUE}")
        rows.append(row)
    head = (REPO / "backend" / "data" / "ch1_engine" / "rows.csv").read_text(encoding="utf-8").splitlines()[0].split(",")
    if set(head) != set(rows[0]):
        raise SystemExit(f"columns differ from rows.csv: {set(head) ^ set(rows[0])}")
    DEST.mkdir(exist_ok=True)

    def fmt(v):
        return f"{v:.6g}" if isinstance(v, (float, np.floating)) and not pd.isna(v) else ("" if v is None or (
            isinstance(v, float) and pd.isna(v)) else v)
    with open(DEST / "rows_m3.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=head, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: fmt(r[k]) for k in head})
    res = json.loads((M.OUT / "results.json").read_text(encoding="utf-8"))["models"]["M3_midquarter"]
    add2 = REPO / "backend" / "seals" / "PREREG_LEAD2_ADDENDUM_2.md"
    ev = {"model": ("P0H4-M3, the mid-quarter update of Lead 2: the served P0H4 (same LightGBM price part, same hunger "
                    "part), issued on the first day of the second month of the quarter before the target, with the newest "
                    "SWS Balance Luzon reading and every origin's CPI cutoff at that date"),
          "issue_date": ISSUE, "target": target, "lead": LEAD, "seal_sha256": seal_sha,
          "seal_timing": seal["timing"], "prereg_addendum_2_sha256": add2.read_text(encoding="utf-8").rsplit(
              "PREREG-SHA256: ", 1)[1].strip(),
          "development": {"n": 65, "n_quarters": 13, "period": "2023-Q2..2026-Q3", **res},
          "development_label": ("EXPLORATORY: the fifth Lead-2 variant scored on these rows; judged only on sealed "
                                "on-time 2027+ forecasts (PREREG_LEAD2 addendum 2, at least 8 quarters)"),
          "plan_sha256": json.loads((M.OUT / "results.json").read_text(encoding="utf-8"))["planSha256"],
          "source": "aipheed-backend-aligned/experiments/LEAD2_MIDQUARTER_UPDATE (run_m3.py, export_m3.py)"}
    (DEST / "evaluation_m3.json").write_text(json.dumps(ev, indent=1, default=str) + "\n", encoding="utf-8", newline="\n")
    print("exported", len(rows), "rows to", DEST)
    for r in rows:
        print(f"  {r['province']:9s} hunger {r['pi_hunger']:.4f} price {r['pi_price']:.4f} prob {r['probability']:.4f} "
              f"{r['class']} | shap A1 {r['shap_A1']:+.3f} E1 {r['shap_E1']:+.3f} C4 {r['shap_C4']:+.3f}")


if __name__ == "__main__":
    main()
