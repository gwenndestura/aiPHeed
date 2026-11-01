"""LEAD2_POST_SWS_PRICE (PROTOCOL.md + PROTOCOL_AMENDMENT_1.md): walk-forward refit of the served P0 price arm with the
CPI cutoff as a parameter. Parameterised copies only; every original module is imported read-only and nothing on disk
outside out/ is written. The served and post-SWS runs are separate processes (no in-memory cache crosses).

    python -B price_refit.py served   # cutoff = e41_lib.m0_of (served): parity (amendment 1 a and b) + leakage audit
    python -B price_refit.py post     # cutoff = newest CPI month at O'(t), every origin: leakage audit + perturbation
"""
from __future__ import annotations

import dataclasses
import hashlib
import importlib.util
import json
import math
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOTD = HERE.parent
EXP = ROOTD.parent
OUT = ROOTD / "out"
LOG: list[str] = []


def say(*a):
    s = " ".join(str(x) for x in a)
    LOG.append(s)
    print(s, flush=True)


def frozen_ok():
    for f in ("PROTOCOL", "PROTOCOL_AMENDMENT_1"):
        want = (ROOTD / f"{f}_SHA256.txt").read_text().split()[0]
        if hashlib.sha256((ROOTD / f"{f}.md").read_bytes()).hexdigest() != want:
            raise SystemExit(f"{f}.md changed after freezing")


def _issue_module():
    """LEAD2_POST_SWS_ISSUE/runner/score.py, imported read-only for O'(t) and the CPI availability rule."""
    spec = importlib.util.spec_from_file_location("post_sws_issue_score", EXP / "LEAD2_POST_SWS_ISSUE" / "runner" / "score.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


SI = _issue_module()                                                # also puts LEAD2_OPTIMIZATION/runner on sys.path
import l2_lib as X  # noqa: E402

U, L, E, B, np, pd = X.U, X.L, X.E, X.B, X.np, X.pd
M0_SERVED = L.m0_of                                                 # the original function object, kept untouched
K = int(json.loads((U.OUT / "testability_unified.json").read_text())["K"])
ORIGINS = [L.qi(q) for q in json.loads((U.OUT / "testability_unified.json").read_text())["eligible_origins"]]


# =============================================================================================== cutoff parameter
def m0_post(t: int) -> int:
    """Newest CPI month available at O'(t) (month M available from the first day of M+2)."""
    m = SI.cpi_newest(SI.post_issue(int(t)))
    if m < M0_SERVED(int(t)):
        raise SystemExit(f"O'({L.qs(int(t))}) gives a CPI cutoff before the served one")
    return m


def world_features_at(t: int, w: pd.DataFrame | None = None, m0f=None) -> dict:
    """Copy of uni_lib.world_features with the cutoff function as a parameter (default: the served m0_of), so the
    World Bank columns stay as served whatever e41_lib.m0_of is."""
    m0f = M0_SERVED if m0f is None else m0f
    w = U.pinksheet() if w is None else w
    m0 = m0f(t)
    w = w[w.index <= m0]

    def yoy(c):
        return float(100 * (w.loc[m0, c] / w.loc[m0 - 12, c] - 1)) if m0 in w.index and m0 - 12 in w.index else np.nan
    mom = (float(100 * (math.log(w.loc[m0, "rice_thai5"]) - math.log(w.loc[m0 - 3, "rice_thai5"])))
           if m0 in w.index and m0 - 3 in w.index else np.nan)
    return {"W_rice_yoy": yoy("rice_thai5"), "W_rice_mom": mom,
            "W_cereal_yoy": float(np.nanmean([yoy("rice_thai5"), yoy("wheat_hrw"), yoy("maize")])),
            "W_crude_yoy": yoy("crude_avg"), "W_urea_yoy": yoy("urea")}


def install(mode: str):
    U.world_features = world_features_at                            # identical to served in both modes (pinned)
    L.m0_of = M0_SERVED if mode == "served" else m0_post            # the one change (post mode only)


def issue_date(mode: str, t: int) -> pd.Timestamp:
    return L.origin(t) if mode == "served" else SI.post_issue(t)


# =============================================================================================== P0 arm (copy)
def p0_origin(S: pd.DataFrame, t: int, d=None):
    """l2_lib.forecast_origin restricted to arm P0 (= l2_lib.price_prob('P0'): uni_lib.select + UniPrice, U2, mono)."""
    tr = U.train_rows(S, t, d)
    te = S[S["t"] == t]
    if not B.eligible(tr) or not len(te):
        return None, None
    if not ((tr["t"] < t).all() and (tr["q"] <= t - 1).all()):
        raise SystemExit(f"LEAKAGE: training row at or after origin {L.qs(t)}")
    cc = U.cols("U2", True)
    cfg, _ = U.select(tr, cc, True)
    out = te[["t", "lead", "province_code", "target_q"]].copy()
    out["P0_price"] = U.UniPrice(cfg, cc, True).fit(tr).predict(te)
    out["P0_cfg"] = f"u{cfg['id']}"
    info = {"origin": L.qs(t), "nTrain": int(len(tr)), "trainOrigins": [L.qs(int(tr["t"].min())), L.qs(int(tr["t"].max()))],
            "trainTargetMax": L.qs(int(tr["q"].max())), "cfg": out["P0_cfg"].iloc[0]}
    return out, info


# =============================================================================================== leakage audit
def leakage(mode: str, origins) -> list[dict]:
    d0 = E.data()[0]
    rows, prev = [], None
    for t in sorted(int(x) for x in origins):
        o = issue_date(mode, t)
        m = L.m0_of(t)
        avail = pd.Timestamp(year=(m + 2) // 12, month=(m + 2) % 12 + 1, day=1)
        dc = d0.cut(t)
        newest = int(max(dc.idx["ym"].max(), dc.yoy["ym"].max()))
        r = {"origin": L.qs(t), "issue": str(o.date()), "cpiCutoff": L.ym_s(m), "cpiCutoffServed": L.ym_s(M0_SERVED(t)),
             "cutoffAvailableFrom": str(avail.date()), "newestCpiInCut": L.ym_s(newest), "newestEqualsCutoff": newest == m}
        if not avail <= o:
            raise SystemExit(f"LEAKAGE: CPI {r['cpiCutoff']} not available at {r['issue']} ({r['origin']})")
        if newest > m:
            raise SystemExit(f"LEAKAGE: Data.cut({r['origin']}) holds CPI {r['newestCpiInCut']} > cutoff {r['cpiCutoff']}")
        if prev is not None and o < prev:
            raise SystemExit(f"LEAKAGE: issue date of {r['origin']} earlier than that of an earlier origin")
        prev = o
        rows.append(r)
    return rows


# =============================================================================================== parity (amendment 1)
def parity_stored(P: pd.DataFrame) -> dict:
    st = pd.read_csv(EXP / "FINAL_ARCHITECTURE" / "out" / "predictions.csv", dtype={"province_code": str}, keep_default_na=False)
    raw = pd.read_csv(EXP / "FINAL_ARCHITECTURE" / "out" / "predictions.csv", dtype={"province_code": str, "P0_price": str})
    st["P0_price_str"] = raw["P0_price"]
    out = {}
    for k in (1, 2):
        s = st[st["lead"] == k][["t", "province_code", "P0_price", "P0_price_str", "P0_cfg"]]
        m = s.merge(P[P["lead"] == k], on=["t", "province_code"], suffixes=("_stored", ""), how="left")
        miss = int(m["P0_price"].isna().sum())
        fmt = m["P0_price"].map(lambda v: f"{v:g}" if pd.notna(v) else "")
        eq = int((fmt == m["P0_price_str"]).sum())
        diff = (m["P0_price"] - m["P0_price_stored"].astype(float)).abs()
        out[f"lead{k}"] = {"rows": int(len(m)), "missing": miss, "equalAt6sig": eq, "maxAbsDiff": float(diff.max()),
                           "cfgEqual": int((m["P0_cfg"] == m["P0_cfg_stored"]).sum())}
    out["pass"] = all(out[f"lead{k}"]["missing"] == 0 and out[f"lead{k}"]["equalAt6sig"] == out[f"lead{k}"]["rows"]
                      and out[f"lead{k}"]["maxAbsDiff"] <= 5e-7 for k in (2,))
    return out


def parity_code(S: pd.DataFrame, P: pd.DataFrame, lead2_origins: list[int]) -> dict:
    """Copy vs the original l2_lib.forecast_origin(add_fe(S), t, ('P0',)) at the first, middle and last Lead-2 origin."""
    pick = [lead2_origins[0], lead2_origins[len(lead2_origins) // 2], lead2_origins[-1]]
    Sf = X.add_fe(S[S["t"] <= max(pick)])
    res = []
    for t in pick:
        f = X.forecast_origin(Sf, t, ("P0",), True)
        m = f.merge(P[P["t"] == t], on=["t", "lead", "province_code"], suffixes=("_orig", ""))
        res.append({"origin": L.qs(t), "rows": int(len(m)), "rowsOrig": int(len(f)),
                    "maxAbsDiff": float((m["P0_price"] - m["P0_price_orig"]).abs().max()),
                    "cfgEqual": bool((m["P0_cfg"] == m["P0_cfg_orig"]).all())})
    return {"origins": res, "pass": all(r["maxAbsDiff"] <= 1e-9 and r["cfgEqual"] and r["rows"] == r["rowsOrig"] for r in res)}


# =============================================================================================== perturbation (post)
def perturbation(P: pd.DataFrame) -> dict:
    """CPI months after m0'(t*) replaced by random values; P0_price'(t*) must not move (to 1e-12). Both sides are built
    through the same explicit-data path (uni_lib.stack(K, d, x, last_origin)); the unperturbed side is also compared
    with the main run."""
    t = L.qi("2023-Q4")
    d0, x0 = E.data()
    m = L.m0_of(t)
    rng = np.random.default_rng(2036)
    idx, yoy = d0.idx.copy(), d0.yoy.copy()
    a, b = idx["ym"] > m, yoy["ym"] > m
    idx.loc[a, "index"] = rng.uniform(50, 300, int(a.sum()))
    yoy.loc[b, "yoy"] = rng.uniform(-20, 40, int(b.sum()))
    dp = dataclasses.replace(d0, idx=idx, yoy=yoy)
    db = dataclasses.replace(d0)
    pb, _ = p0_origin(U.stack(K, d=db, x=x0, last_origin=t), t, db)
    pp, _ = p0_origin(U.stack(K, d=dp, x=x0, last_origin=t), t, dp)
    mm = pb.merge(pp, on=["t", "lead", "province_code"], suffixes=("", "_pert")).merge(
        P[P["t"] == t][["t", "lead", "province_code", "P0_price"]], on=["t", "lead", "province_code"], suffixes=("", "_main"))
    out = {"origin": L.qs(t), "cutoff": L.ym_s(m), "monthsPerturbed": f"> {L.ym_s(m)} ({int(a.sum())} index, {int(b.sum())} YoY values)",
           "maxAbsDiffPerturbed": float((mm["P0_price"] - mm["P0_price_pert"]).abs().max()),
           "maxAbsDiffVsMainRun": float((mm["P0_price"] - mm["P0_price_main"]).abs().max()), "rows": int(len(mm))}
    out["pass"] = out["maxAbsDiffPerturbed"] <= 1e-12
    return out


# =============================================================================================== main
def main(mode: str):
    if mode not in ("served", "post"):
        raise SystemExit("mode must be 'served' or 'post'")
    frozen_ok()
    OUT.mkdir(exist_ok=True)
    U.setup()
    install(mode)
    res = {"mode": mode, "K": K, "origins": [L.qs(t) for t in ORIGINS],
           "protocolSha256": hashlib.sha256((ROOTD / "PROTOCOL.md").read_bytes()).hexdigest(),
           "amendment1Sha256": hashlib.sha256((ROOTD / "PROTOCOL_AMENDMENT_1.md").read_bytes()).hexdigest()}
    t0 = time.time()
    S = U.stack(K)
    say(mode, "stack", len(S), "rows,", round(time.time() - t0), "s")
    res["leakageAudit"] = {"rows": leakage(mode, S["t"].unique()), "passed": True}
    say("leakage audit passed for", len(res["leakageAudit"]["rows"]), "origins")
    fr, info = [], []
    for t in ORIGINS:
        f, i = p0_origin(S, t)
        if f is not None:
            fr.append(f)
            info.append(i)
        say("origin", L.qs(t), "done", round(time.time() - t0), "s")
    P = pd.concat(fr, ignore_index=True)
    res["fits"] = info
    P.to_csv(OUT / f"p0_price_{mode}.csv", index=False, lineterminator="\n", float_format="%.12g")
    st = pd.read_csv(EXP / "FINAL_ARCHITECTURE" / "out" / "predictions.csv", dtype={"province_code": str})
    l2o = sorted(int(x) for x in st[st["lead"] == 2]["t"].unique())
    if mode == "served":
        res["parityStored"] = parity_stored(P)
        say("parity vs stored file:", json.dumps(res["parityStored"]))
        res["parityCode"] = parity_code(S, P, l2o)
        say("parity vs original code:", json.dumps(res["parityCode"]))
        res["parityPass"] = bool(res["parityStored"]["pass"] and res["parityCode"]["pass"])
    else:
        res["perturbation"] = perturbation(P)
        say("perturbation:", json.dumps(res["perturbation"]))
    res["seconds"] = round(time.time() - t0)
    (OUT / f"refit_{mode}.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    (OUT / f"log_refit_{mode}.txt").write_text("\n".join(LOG) + "\n", encoding="utf-8")
    if mode == "served" and not res["parityPass"]:
        raise SystemExit("PARITY FAILED: M2 is not scored")
    if mode == "post" and not res["perturbation"]["pass"]:
        raise SystemExit("PERTURBATION FAILED: M2 is not scored")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")
