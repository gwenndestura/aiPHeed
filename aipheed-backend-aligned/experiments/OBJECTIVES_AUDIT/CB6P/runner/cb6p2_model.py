"""C-B6P2 (../PREREGISTRATION_P2.md, hash checked): C-B6P + S_last, y_last (province's last known Eq. 3 score).

    python cb6p2_model.py fit     # C-B6P replication + C-B6P2 -> ../out/cb6p2_fits.csv
    python cb6p2_model.py score   # acceptance -> ../out/cb6p2_results.json
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import hashlib
import json
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cb6p_model as M  # noqa: E402

H, V = M.H, M.V
PLAN = M.HERE / "PREREGISTRATION_P2.md"
OUT = M.OUT
NAME = "C-B6P2"
EXTRA = ["S_last", "y_last"]
M.COLS = {"C-B6P": M.COLS["C-B6P"], NAME: M.COLS["C-B6P"] + EXTRA}
M.GROUPS = {**M.GROUPS, "province_history": EXTRA}
_orig_train, _orig_prov = M.train_rows, M._prov_rows


def check() -> str:
    b = PLAN.read_bytes().replace(b"\r\n", b"\n")
    body, last = b.rstrip(b"\n").rsplit(b"\n", 1)
    h = hashlib.sha256(body + b"\n").hexdigest()
    assert last.startswith(b"PLAN-SHA256: ") and last.split()[1].decode() == h, "C-B6P2 pre-registration changed"
    return h


def s_last(d, lab, L, thr, t, max_q=None) -> dict:
    kb = V.known_labels(d, t, lab)
    kb = kb[kb["area"] == "BL"].sort_values("q")
    if max_q is not None:
        kb = kb[kb["q"] <= max_q]
    base = float(kb["H"].iloc[-1]) if len(kb) else np.nan
    Lk = L[L["q"].isin(kb["q"]) & (L["last_m"] <= M.m_avail(t))].sort_values("q")
    out = {"BL": base}
    for p in M.PROVS:
        s = Lk[Lk["province"] == p]
        out[p] = float(s["S"].iloc[-1]) if len(s) else base
    return out


def _add(R: pd.DataFrame) -> pd.DataFrame:
    SL = M._G["SL"]
    v = [SL.get((int(t), p), np.nan) for t, p in zip(R["t"], R["province"])]
    R = R.copy()
    R["S_last"] = v
    R["y_last"] = (R["S_last"] > M._G["thr"]).astype(float).where(R["S_last"].notna())
    return R


def _prov(R, Dm):
    return _add(_orig_prov(R, Dm))


def _train(t):
    return _add(_orig_train(t))


def _init():
    M._init()
    d, lab, L, thr, S = M._G["d"], M._G["lab"], M._G["L"], M._G["thr"], M._G["T"]
    SL = {}
    for t in sorted(S["t"].unique()):
        for k, v in s_last(d, lab, L, thr, int(t)).items():
            SL[(int(t), k)] = v
    M._G["SL"] = SL
    M._prov_rows, M.train_rows = _prov, _train


def fit():
    pre = check()
    _init()
    d, lab, L, thr = M._G["d"], M._G["lab"], M._G["L"], M._G["thr"]
    ok = all(s_last(d, lab, L, thr, t) == s_last(d, lab, L, thr, t, max_q=t - 1)
             for t in range(M.FIRST, H.qi("2026-Q3") + 1))
    print({"S_last_leakage_unchanged": ok}, flush=True)
    assert ok
    with Pool(8, initializer=_init) as pool:
        F = pd.concat(pool.map(M._origin, list(range(M.FIRST, H.qi("2026-Q3") + 1))), ignore_index=True)
    st = pd.read_csv(OUT / "cb6p_fits.csv")
    key = ["t", "lead", "province"]
    a = F[F["name"] == "C-B6P"].set_index(key)["p"]
    b = st[st["name"] == "C-B6P"].set_index(key)["p"].reindex(a.index)
    rep = float((a - b).abs().max())
    chk = {"prereg_sha256": pre, "S_last_leakage_unchanged": ok, "C-B6P_replication_max_abs_diff": rep}
    print(chk)
    assert rep < 1e-9, "C-B6P replication differs"
    (OUT / "cb6p2_checks.json").write_text(json.dumps(chk, indent=1), encoding="utf-8")
    F[F["name"] == NAME].to_csv(OUT / "cb6p2_fits.csv", index=False)


def score():
    pre = check()
    L = pd.read_csv(OUT / "cb6p_labels.csv")
    F = pd.concat([pd.read_csv(OUT / "cb6p_fits.csv"), pd.read_csv(OUT / "cb6p2_fits.csv")], ignore_index=True)
    R6 = pd.read_csv(M.AUD / "out" / "cb6_fits.csv")[["t", "lead", "q", "p"]].rename(columns={"p": "C-B6-R"})
    W0 = F.pivot_table(index=["t", "lead", "q", "province"], columns="name", values="p").reset_index()
    W0 = W0.merge(R6, on=["t", "lead", "q"], how="left").merge(L[["province", "q", "y"]], on=["province", "q"])
    W0 = W0[W0["q"] >= M.Q0]
    arms = [NAME, "C-B6P", "C-B6-R", "PERSIST", "LOGIT"]
    res = {"prereg_sha256": pre, "checks": json.loads((OUT / "cb6p2_checks.json").read_text(encoding="utf-8")),
           "leads": {}, "algorithm3": {}}
    fam = {}
    for k in M.LEADS:
        W = W0[W0["lead"] == k].dropna(subset=arms)
        Lk = {a: M.metrics(W["y"], W[a]) for a in arms}
        if k <= 2:
            Lk["vs_C-B6P"] = M.paired(W, NAME, "C-B6P")
            for b in ("C-B6-R", "PERSIST", "LOGIT"):
                fam[(k, b)] = M.paired(W, NAME, b)
            s = F[(F["name"] == NAME) & (F["lead"] == k) & (F["q"] >= M.Q0)]
            grp = pd.DataFrame({g: sum(s[f"shap_{c}"].fillna(0) for c in cs).abs() for g, cs in M.GROUPS.items()})
            sh = grp.div(grp.sum(axis=1).replace(0, np.nan), axis=0) * 100
            Lk["shap_share_pct_mean"] = {g: float(sh[g].mean()) for g in M.GROUPS}
            Lk["quarters_where_provinces_differ"] = int(W.assign(c=W[NAME] >= .5).groupby("q")["c"].nunique().gt(1).sum())
        res["leads"][str(k)] = Lk
    hp = M.holm({key: v["p_one_sided"] for key, v in fam.items()})
    res["holm_family_6"] = [{"lead": k, "comparator": b, **v, "p_holm": hp[(k, b)],
                             "significant": bool(v["diff"] < 0 and hp[(k, b)] < .05)} for (k, b), v in fam.items()]
    for a in arms:
        mx = 0
        for k in M.LEADS:
            if res["leads"][str(k)][a]["accuracy"] >= .75 and mx == k - 1:
                mx = k
        res["algorithm3"][a] = mx
    l1, l2 = res["leads"]["1"], res["leads"]["2"]
    res["acceptance"] = {
        "brier_below_C-B6P_p_lt_0.10_both": all(x["vs_C-B6P"]["diff"] < 0 and x["vs_C-B6P"]["p_one_sided"] < .10 for x in (l1, l2)),
        "accuracy_ge_C-B6P_both": all(x[NAME]["accuracy"] >= x["C-B6P"]["accuracy"] for x in (l1, l2)),
        "leakage": res["checks"]["S_last_leakage_unchanged"]}
    res["acceptance"]["passes"] = all(res["acceptance"].values())
    (OUT / "cb6p2_results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    for k in ("1", "2"):
        for a in arms:
            m = res["leads"][k][a]
            print(f"L{k} {a:8s} acc {m['accuracy']:.3f} bal {m['balanced']:.3f} P {m['precision']:.3f} R {m['recall']:.3f} "
                  f"F1 {m['f1']:.3f} AUC {m['auc']:.3f} Brier {m['brier']:.4f}")
        v = res["leads"][k]["vs_C-B6P"]
        print(f"   vs C-B6P dBrier {v['diff']:+.4f} p {v['p_one_sided']:.3f}; provinces differ in",
              res["leads"][k]["quarters_where_provinces_differ"], "quarters")
        print("   SHAP %:", {g: round(x, 1) for g, x in res["leads"][k]["shap_share_pct_mean"].items()})
    for f in res["holm_family_6"]:
        print(f"   L{f['lead']} vs {f['comparator']:7s} dBrier {f['diff']:+.4f} Holm {f['p_holm']:.3f} sig {f['significant']}")
    print("Algorithm 3:", res["algorithm3"])
    print("Acceptance:", res["acceptance"])


if __name__ == "__main__":
    {"fit": fit, "score": score}[sys.argv[1]]()
