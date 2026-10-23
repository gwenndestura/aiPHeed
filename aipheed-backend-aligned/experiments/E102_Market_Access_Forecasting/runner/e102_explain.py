"""E102 explanation diagnostics (after scoring; explanation only, never used to select an arm): FB2 vs SERVED domain
weights at the last origin and mean absolute SHAP (= push) shares by domain over the evaluated Lead-2 rows; logistic
M3 coefficients at the last origin. Writes ../out/explain.json."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e102_lib as L  # noqa: E402
import e102_run as RUN  # noqa: E402

R, E101, np, pd, TS, qi, qs = L.R, L.E101, L.np, L.pd, L.TS, L.qi, L.qs


def weights_and_shares(rows, lead):
    reg_hist, shares, w_last = [], {d: [] for d in R.DOMS}, None
    for t in sorted({x["t"] for x in rows}):
        known = {qs(q): h for q, h in TS._posted(TS.issue_of(t)).items()}
        w, _, _ = R.evidence_weights([(dm, tq) for (tt, dm, tq) in reg_hist if tt < t], known, list(R.DOMS))
        cur = [x for x in rows if x["t"] == t]
        for x in cur:
            av = [d for d in R.DOMS if x["dom"].get(d) is not None]
            if len(av) < R.MIN_DOMAINS or t > qi(RUN.EVAL_END[lead]):
                continue
            ww = {d: (w or {}).get(d, 1.0) if w else 1.0 for d in av}
            tot = sum(ww.values())
            push = {d: ww[d] / tot * (x["dom"][d] - 0.5) for d in av}
            s = sum(abs(v) for v in push.values()) or 1.0
            for d in R.DOMS:
                shares[d].append(abs(push.get(d, 0.0)) / s)
        if w is not None:
            tot = sum(w.get(d, 1.0) for d in R.DOMS)
            w_last = {d: round(w.get(d, 1.0) / tot, 4) for d in R.DOMS}
        reg_hist.append((t, {d: RUN.mean([x["dom"][d] for x in cur]) for d in R.DOMS}, qs(t + lead)))
    return w_last, {d: round(float(np.mean(v)), 3) for d, v in shares.items()}


def main():
    RUN.verify()
    H = R.load_history()
    LV = R.level_indicator()
    rel101 = E101.rel_scores(LV)
    S63 = pd.read_csv(E101.E63, dtype={"province_code": str})
    a1_63 = {(int(r.lead), int(r.t), r.province_code): float(r.E56_p_price) for r in S63.itertuples()}
    cpi = L.load_cpi()
    PNL = L.panel(cpi, list(range(qi("2021-Q2"), qi("2026-Q3") + 1)))
    pct = {k: L.percentiles({key: v[k] for key, v in PNL.items()}) for k in ("REL", "PERS")}
    out = {"note": "explanation only, computed after scoring"}
    for lead in (1, 2):
        rows = E101.lead_rows(H, lead, a1_63, rel101)
        fb2 = []
        for x in rows:
            y = {**x, "dom": dict(x["dom"])}
            y["dom"]["A"] = RUN.mean([x["s"]["A1"], pct["REL"].get((x["t"], x["code"])), pct["PERS"].get((x["t"], x["code"]))])
            fb2.append(y)
        ws, ss = weights_and_shares(rows, lead)
        wf, sf = weights_and_shares(fb2, lead)
        out[f"lead{lead}"] = {"SERVED": {"weights_last_origin": ws, "mean_abs_shap_share": ss},
                              "FB2": {"weights_last_origin": wf, "mean_abs_shap_share": sf}}
    # M3 coefficients at the last evaluated origin, Lead 2
    res = json.loads((RUN.OUT / "results.json").read_text(encoding="utf-8"))
    feats = {qi(q): f for q, f in res["leads"]["2"]["features"].items()}
    t = qi(RUN.EVAL_END[2])
    cols = RUN.MODEL_COLS["M3"]
    tr = L.training_pairs(feats, 2, t, cols)
    from sklearn.linear_model import LogisticRegression
    X = tr[cols].to_numpy(float)
    mu, sd = X.mean(0), X.std(0)
    sd[sd == 0] = 1
    m = LogisticRegression(C=1.0, max_iter=1000).fit((X - mu) / sd, tr["y"].to_numpy(int))
    out["M3_lead2_last_origin"] = {"training_pairs": int(len(tr)), "HIGH_in_training": int(tr["y"].sum()),
                                   "standardised_coefficients": dict(zip(cols, [round(float(c), 3) for c in m.coef_[0]]))}
    (RUN.OUT / "explain.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
