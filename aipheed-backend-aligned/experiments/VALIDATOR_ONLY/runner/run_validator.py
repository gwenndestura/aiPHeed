"""VALIDATOR_ONLY (PROTOCOL_VALIDATOR_ONLY.md): one LightGBM on T43c with no input computed from PSA food CPI or SWS.

    python run_validator.py freeze   # records the protocol SHA-256 (refuses if already frozen with another hash)
    python run_validator.py score    # out/predictions.csv, out/results.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
VO = HERE.parent
EXP = VO.parent
OUT = VO / "out"
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(EXP / "FINAL_ARCHITECTURE" / "runner"))
import final_lib as F  # noqa: E402

O, X, U, C, FM, B, L, np, pd = F.O, F.X, F.U, F.C, F.FM, F.B, F.L, F.np, F.pd
sys.path.insert(0, str(EXP / "LEAD2_ONE_MODEL" / "runner"))
import run_one as R1  # noqa: E402

PROTOCOL = VO / "PROTOCOL_VALIDATOR_ONLY.md"
SHA_FILE = HERE / "PROTOCOL_SHA256.txt"
FOOD_CPI = ["A1_food", "A1_gap", "A_mom", "O_food_yoy", "O_rice_yoy", "W_cereal_yoy"]
SWS = ["H1", "h_last", "h_change", "h_mean4", "h_max4", "h_margin", "h_run", "NCR_last", "NCR_change", "VIS_last",
       "VIS_change", "MIN_last", "MIN_change", "true_horizon", "NG_gap_price"]
V0 = ["A2", "A3", "V1", "C1", "C2", "C3", "C4", "E1", "E2", "N1", "G_pri_yoy", "W_rice_yoy", "W_rice_mom",
      "W_crude_yoy", "W_urea_yoy", "lead"]
ARMS = {"V0": V0, "V1": [c for c in V0 if c not in ("A2", "W_crude_yoy")]}
KEY = ["t", "lead", "province_code"]


class NoOffset(F.FOne):
    """The S3 model on an explicit column list without the food-CPI structural offset."""

    def __init__(self, cfg: dict, cols: list[str]):
        super().__init__(cfg, cols)
        self.use_offset = False


def forecast(S: pd.DataFrame, t: int, cols: list[str], name: str) -> pd.DataFrame:
    orig = F.FOne
    F.FOne = lambda cfg, c: NoOffset(cfg, c)          # F.forecast builds the model through F.FOne
    try:
        return F.forecast(S, t, cols, name)
    finally:
        F.FOne = orig


def _check():
    sha = FM.sha256(PROTOCOL)
    assert SHA_FILE.exists() and SHA_FILE.read_text().strip() == sha, "protocol changed or not frozen"
    s3 = set(O.cols("S3"))
    for arm, cols in ARMS.items():
        assert not set(cols) & set(FOOD_CPI + SWS), arm
        assert set(cols) <= s3, arm
    assert set(V0) | set(FOOD_CPI) | set(SWS) == s3, "every S3 column is either kept or removed by name"


def phase_freeze():
    sha = FM.sha256(PROTOCOL)
    if SHA_FILE.exists():
        assert SHA_FILE.read_text().strip() == sha, "already frozen with another hash"
    else:
        SHA_FILE.write_text(sha + "\n", encoding="utf-8", newline="\n")
    print("frozen", sha[:8])


def _diff(D, a, b, k):
    g = D[D["lead"] == k]
    y = g["y"].astype(int).to_numpy()
    t = FM.boot_diff(g, (g[a] - y) ** 2, (g[b] - y) ** 2)
    return {"diff": t["diff"], "ci90": t["ci90"], "p_two": t["p_two"]}


def phase_score():
    _check()
    U.setup()
    t0 = time.time()
    S = F.build(O.A4.RL._K())
    fr = []
    for t in O.A4.RL._origins():
        parts = [forecast(S, t, cols, n).set_index(KEY + ["target_q"]) for n, cols in ARMS.items()]
        fr.append(pd.concat(parts, axis=1).reset_index())
        print("origin", L.qs(t), round(time.time() - t0), "s", flush=True)
    P = pd.concat(fr, ignore_index=True).drop(columns=["target_q"])
    D = pd.read_csv(EXP / "FINAL_ARCHITECTURE" / "out" / "predictions.csv", dtype={"province_code": str})
    n0 = len(D)
    D = D[KEY + ["q", "y", "ALWAYS-LOW_p", "PERSIST-SI_p", "CLIM_p", "P0H4_p3", "C_p"]].merge(P, on=KEY, how="left")
    assert len(D) == n0 and D[[f"{n}_p" for n in ARMS]].notna().all().all(), "rows differ"
    D.to_csv(OUT / "predictions.csv", index=False, lineterminator="\n", float_format="%.6g")
    res = {"protocol_sha256": FM.sha256(PROTOCOL), "arms": {}}
    for n, col in [*((a, f"{a}_p") for a in ARMS), ("P0H4", "P0H4_p3"), ("S3", "C_p")]:
        rep = R1.report(D, col)
        if n in ARMS:
            rep["vs"] = {b: {k: _diff(D, col, bc, k) for k in (1, 2, 3)}
                         for b, bc in (("P0H4", "P0H4_p3"), ("S3", "C_p"), ("ALWAYS-LOW", "ALWAYS-LOW_p"),
                                       ("PERSIST-SI", "PERSIST-SI_p"), ("CLIM", "CLIM_p"))}
        res["arms"][n] = rep
        for k in (1, 2, 3):
            m, v = rep["leads"][k]["metrics"], rep["leads"][k]["verdict"]
            print(f"{n:5s} L{k} acc {m['accuracy']:.3f} bal {m['balanced_accuracy']:.3f} R {m['recall']:.2f} "
                  f"Brier {m['brier']:.3f} AUC {m.get('auc') if m.get('auc') is None else round(m['auc'], 2)} "
                  f"verdict {v}", flush=True)
        print(f"      max reliable lead {rep.get('max_promising_lead')}", flush=True)
    FM.write_json(OUT / "results.json", res)


if __name__ == "__main__":
    {"freeze": phase_freeze, "score": phase_score}[sys.argv[1]]()
