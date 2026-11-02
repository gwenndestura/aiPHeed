"""Score sealed Lead-2 forecasts (backend/seals/PREREG_LEAD2.md) once their outcome is published.

Additive research tooling: never imported by backend/app.

    python -B scripts/score_seal.py --seal seals/2026-10-15_2027-Q1.json   # one seal, after its target is published
    python -B scripts/score_seal.py --summary                              # PREREG section 6-7 over on-time seals

Refuses to score a seal whose bytes do not match the ledger, when the pre-registration changed, or before the target
quarter's SWS result (a non-commissioned Balance Luzon round of the target quarter) and the quarter's last CPI month
are published. Scores are written once to seals/scores/<seal>.score.json and never overwritten.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import seal_lead2 as SL  # noqa: E402

SCORES = SL.SEALS / "scores"
ADDENDUM = SL.SEALS / "PREREG_LEAD2_ADDENDUM_1.md"
MIN_CLAIM_QUARTERS = 8                                                # PREREG section 7
CANDIDATES = ("C0_P0H4", "C1_M0", "C2_M2")
PRIMARY = ("C1_M0", "D0")


def addendum_rules(c1: dict, c2: dict) -> dict:
    """PREREG_LEAD2_ADDENDUM_1 section 2, from a province's sealed C1_M0 and C2_M2 parts: (probability, HIGH/LOW)."""
    h, p2 = c2["hunger"], c2["price"]
    pbar = (c1["price"] + p2) / 2
    return {"A1": (h * p2, "HIGH" if (h >= 0.5 and p2 >= 0.45) else "LOW"),
            "A2": (h * pbar, "HIGH" if h * pbar >= 0.5 else "LOW")}


def outcome_published(target_q: int, rounds, today: dt.date) -> bool:
    """The target quarter's SWS result exists: a Balance Luzon round of that quarter published on or before today
    (`rounds` holds non-commissioned rounds only), and the quarter's last CPI month is available by today."""
    g = rounds[(rounds["area"] == "BL") & (rounds["q"] == target_q)]
    sws = bool(len(g)) and all(SL.as_date(p) <= today for p in g["published"])
    last_month = (target_q // 4) * 12 + (target_q % 4) * 3 + 2
    return sws and SL.cpi_month_available(last_month, today)


def _qi(s: str) -> int:
    return int(s[:4]) * 4 + int(s[-1]) - 1


def score_one(seal_path: Path, today: dt.date) -> dict:
    SL.prereg_sha()
    seal = SL.verify_seal(seal_path)
    if seal["preregSha256"] != SL.prereg_sha():
        raise SL.SealError("seal was made under a different pre-registration")
    out = SCORES / (seal_path.stem + ".score.json")
    if out.exists():
        raise SL.SealError(f"{out.name} exists; scores are written once")
    sys.path.insert(0, str(SL.PRICE_RUNNER))
    import price_refit as PR
    SI = PR.SI
    X = SI.setup()
    tq = _qi(seal["target"])
    if not outcome_published(tq, SI.R.rounds(), today):
        raise SL.SealError(f"the {seal['target']} SWS result (or its last CPI month) is not published yet")
    lab = X.C.labels()
    lab = lab[lab["q"] == tq].set_index("province_code")
    missing = [p for p in SL.PROVINCES if p not in lab.index]
    if missing:
        raise SL.SealError(f"no T43c label yet for {seal['target']} {missing}: update the input data first")
    rows = []
    for p in SL.PROVINCES:
        y = int(lab.loc[p, "y"])
        r = {"province_code": p, "y": y, "hunger": int(lab.loc[p, "hunger"]), "price": int(lab.loc[p, "price"])}
        for c, cand in seal["candidates"].items():                   # C0-C2 (PREREG) or C3_M3 (addendum 2)
            v = cand[p]
            r[f"{c}_prob"] = v["probability"]
            r[f"{c}_min"] = min(v["hunger"], v["price"])
            for d in ("D0", "D1", "M3-D0", "M3-E1"):
                if d in v:
                    r[f"{c}_{d}_correct"] = int((v[d] == "HIGH") == bool(y))
        if {"C1_M0", "C2_M2"} <= set(seal["candidates"]):
            for a, (prob, cls) in addendum_rules(seal["candidates"]["C1_M0"][p], seal["candidates"]["C2_M2"][p]).items():
                r[f"{a}_prob"], r[f"{a}_high"] = prob, int(cls == "HIGH")
        for k, b in (("post", "atPostIssue"), ("served", "atServedIssue"), ("m3", "atIssue")):
            if b in seal["baselines"]:
                base = seal["baselines"][b]
                r[f"PERSIST-SI_{k}"], r[f"CLIM_{k}"] = base["PERSIST-SI"][p], base["CLIM"]
        rows.append(r)
    res = {"seal": seal_path.name, "sealSha256": SL.sha256_file(seal_path), "target": seal["target"],
           "method": seal.get("method", "P0H4 / M0 / M2"), "timing": seal["timing"], "scoredOn": today.isoformat(),
           "rows": rows}
    SCORES.mkdir(exist_ok=True)
    with open(out, "x", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, indent=1)
    return res


def summary() -> dict:
    """PREREG sections 6-7 over every scored on-time seal (late seals reported separately)."""
    import pandas as pd
    SL.prereg_sha()
    scored = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(SCORES.glob("*.score.json"))] if SCORES.exists() else []
    for s in scored:
        SL.verify_seal(SL.SEALS / s["seal"])
    on_all = [s for s in scored if s["timing"] == "on-time"]
    late = [f"{s['target']} ({s.get('method', 'P0H4 / M0 / M2')})" for s in scored if s["timing"] != "on-time"]
    on = [s for s in on_all if not s["seal"].endswith("_M3.json")]
    on3 = [s for s in on_all if s["seal"].endswith("_M3.json")]
    nq, nq3 = len({s["target"] for s in on}), len({s["target"] for s in on3})
    out = {"onTimeQuarters": nq, "onTimeQuartersM3": nq3, "lateSeals": late, "minimumForAnyClaim": MIN_CLAIM_QUARTERS,
           "primary": f"{PRIMARY[0]} under {PRIMARY[1]}",
           "hypothesesTested": ["M0 D0 (primary)", "D1", "A1", "A2", "M3-D0", "M3-E1"]}
    if max(nq, nq3) < MIN_CLAIM_QUARTERS:
        out["status"] = (f"no claim: {nq} (P0H4/M0/M2) and {nq3} (M3) resolved on-time quarter(s), {MIN_CLAIM_QUARTERS} "
                         "required (Lead 2 stays experimental)")
        return out
    sys.path.insert(0, str(SL.PRICE_RUNNER))
    import price_refit as PR
    P = PR.SI.P
    if nq3 >= MIN_CLAIM_QUARTERS:                                     # addendum 2: M3
        SL.prereg_sha(SL.SEALS / "PREREG_LEAD2_ADDENDUM_2.md")
        g3 = pd.DataFrame([{**r, "q": _qi(s["target"]), "target": s["target"]} for s in on3 for r in s["rows"]])
        g3 = g3.assign(**{"PERSIST-SI_p": g3["PERSIST-SI_m3"], "CLIM_p": g3["CLIM_m3"], "ALWAYS-LOW_p": 0.0},
                       _e1=(g3["C3_M3_prob"] >= 0.45).astype(int))
        d0, e1 = P.official_rules(g3, "C3_M3_prob"), P.official_rules(g3, "_e1")
        r_e1 = {**{k: v for k, v in e1["rules"].items() if not k.startswith("R5")},
                **{k: v for k, v in d0["rules"].items() if k.startswith("R5")}}
        out["M3"] = {"M3-D0": {"failed": d0["failed"], "passesAll": d0["passesAll"]},
                     "M3-E1": {"failed": [k.split()[0] for k, v in r_e1.items() if not v["pass"]],
                               "passesAll": all(v["pass"] for v in r_e1.values())},
                     "status": "interim (R1 needs 10 quarters)" if nq3 < 10 else "final under addendum 2"}
    if nq < MIN_CLAIM_QUARTERS:
        out["status"] = f"P0H4/M0/M2: no claim ({nq} quarters); M3 reported separately"
        return out
    g = pd.DataFrame([{**r, "q": _qi(s["target"]), "target": s["target"]} for s in on for r in s["rows"]])
    res = {}
    for c in CANDIDATES:
        k = "served" if c == "C0_P0H4" else "post"
        base = g.assign(**{"PERSIST-SI_p": g[f"PERSIST-SI_{k}"], "CLIM_p": g[f"CLIM_{k}"], "ALWAYS-LOW_p": 0.0})
        d0 = P.official_rules(base, f"{c}_prob")
        d1c = P.official_rules(base, f"{c}_min")                       # classification rules on both-parts
        r1 = {**{k2: v for k2, v in d1c["rules"].items() if not k2.startswith("R5")},
              **{k2: v for k2, v in d0["rules"].items() if k2.startswith("R5")}}
        res[c] = {"D0": {"failed": d0["failed"], "passesAll": d0["passesAll"]},
                  "D1": {"failed": [k2.split()[0] for k2, v in r1.items() if not v["pass"]],
                         "passesAll": all(v["pass"] for v in r1.values())}}
    SL.prereg_sha(ADDENDUM)
    base = g.assign(**{"PERSIST-SI_p": g["PERSIST-SI_post"], "CLIM_p": g["CLIM_post"], "ALWAYS-LOW_p": 0.0})
    for a in ("A1", "A2"):                                            # addendum 1: decisions + product probability
        dc, pc = P.official_rules(base, f"{a}_high"), P.official_rules(base, f"{a}_prob")
        ra = {**{k2: v for k2, v in dc["rules"].items() if not k2.startswith("R5")},
              **{k2: v for k2, v in pc["rules"].items() if k2.startswith("R5")}}
        res[a] = {"failed": [k2.split()[0] for k2, v in ra.items() if not v["pass"]],
                  "passesAll": all(v["pass"] for v in ra.values()), "origin": "addendum 1 (chosen by exploration)"}
    out["hypothesesTested"] = 3
    out["results"] = res
    out["status"] = ("interim (R1 needs 10 quarters)" if nq < 10 else
                     "primary passes all seven rules" if res[PRIMARY[0]][PRIMARY[1]]["passesAll"] else
                     "primary does not pass: Lead 2 stays experimental")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--seal")
    ap.add_argument("--summary", action="store_true")
    a = ap.parse_args(argv)
    try:
        if a.summary:
            print(json.dumps(summary(), indent=1, default=str))
        elif a.seal:
            r = score_one(Path(a.seal), dt.date.today())
            print(json.dumps({k: v for k, v in r.items() if k != "rows"}, indent=1))
        else:
            ap.error("--seal FILE or --summary")
    except SL.SealError as e:
        print(f"SCORE REFUSED: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
