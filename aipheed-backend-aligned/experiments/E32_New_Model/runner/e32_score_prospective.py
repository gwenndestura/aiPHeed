"""E32 final test, part 2 (run ONLY after the outcomes are released and authorized): score the frozen 2026-Q4 /
2027-Q1 predictions. Verifies the frozen record's hash, then needs an authorized outcome file

    inputs/AUTHORIZED_OUTCOMES.csv  columns: target_quarter, province_code, H, D, H_round, H_posted, D_months

with H = the definition-A Balance Luzon round(s) of the quarter and D = province food YoY minus the five-province
mean over the quarter's three months (E25 construction). Each forecast is scored against the tau it was frozen with.
"""
import hashlib, json, sys
from pathlib import Path
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e32_common as C  # noqa: E402
pd = C.pd


def main():
    f = C.E32 / "frozen" / "E32_PROSPECTIVE.json"
    want = (C.E32 / "frozen" / "E32_PROSPECTIVE.sha256").read_text().split()[0]
    if hashlib.sha256(f.read_bytes()).hexdigest() != want:
        raise SystemExit("frozen record changed: refused")
    src = C.E32 / "inputs" / "AUTHORIZED_OUTCOMES.csv"
    if not src.exists():
        print("PENDING: no authorized outcome file; nothing scored (expected until the SWS December 2026 round)")
        return
    rec = json.loads(f.read_text(encoding="utf-8"))
    o = pd.read_csv(src, dtype={"province_code": str})
    res = {}
    for k, blk in rec["leads"].items():
        g = o[o["target_quarter"] == blk["target_quarter"]].set_index("province_code")
        if len(g) != 5:
            res[blk["target_quarter"]] = "PENDING"
            continue
        y = {p: int(g.loc[p, "H"] + 2 * g.loc[p, "D"] > blk["tau"]) for p in g.index}
        res[blk["target_quarter"]] = {a: {"brier": sum((pr[p] - y[p]) ** 2 for p in y) / 5,
                                          "accuracy": sum(int(pr[p] >= .5) == y[p] for p in y) / 5}
                                      for a, pr in blk["arms_p_high"].items()} | {"labels": y}
    C.write_json(C.E32 / "runs" / "e32_prospective_scores.json", res)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
