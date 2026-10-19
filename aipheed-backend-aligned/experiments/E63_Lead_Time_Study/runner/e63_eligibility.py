"""E63 step 0 (score-free, run before PROTOCOL.md is frozen): which origins are eligible at each lead, and the lead-2
identity check of the generalised inputs. Reads no T43 label value: label availability is checked from the SWS round
list and CPI completeness only.

    backend/venv/Scripts/python.exe -B runner/e63_eligibility.py -> tables/eligibility.csv, out/eligibility.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e63_lib as H  # noqa: E402

L, M, P2, np, pd = H.L, H.M, H.P2, H.np, H.pd


def identity_check(raw):
    """At h = 2 the generalised inputs must equal the E56 originals exactly."""
    d, x, ev = raw
    allo = list(range(H.FIRST_ORIGIN, H.LAST_FEATURE_ORIGIN + 1))
    X0, B0 = M.features(d, x, allo, ev), P2.bases(d, allo)
    _, X2, B2 = H.inputs_h(raw, 2)
    X2 = X2[X0.columns]
    fx = pd.testing.assert_frame_equal(X0.reset_index(drop=True), X2.reset_index(drop=True), check_exact=True)
    fb = pd.testing.assert_frame_equal(B0.reset_index(drop=True), B2.reset_index(drop=True), check_exact=True)
    return fx is None and fb is None


def main():
    raw = H.load_raw()
    d = raw[0]
    ident = identity_check(raw)
    print("lead-2 inputs identical to E56:", ident)
    have = H.label_exists(d)
    rows = []
    for h in H.LEADS:
        _, X, B = H.inputs_h(raw, h)
        for t in range(H.FIRST_ORIGIN, H.LAST_TARGET - h + 1):
            e = H.eligible(d, X, B, t, h)
            rows.append({"lead": h, "origin_quarter": L.qs(t), "issue_date": str(L.origin(t).date()),
                         "target": L.qs(t + h), "label_can_exist": (t + h) in have, **e,
                         "in_study": bool(e["ok"] and (t + h) in have)})
    R = pd.DataFrame(rows)
    out = H.E63 / "tables" / "eligibility.csv"
    R.to_csv(out, index=False)
    summ = {"lead2_inputs_identical_to_E56": ident, "label_quarters": [L.qs(q) for q in sorted(have)]}
    for h in H.LEADS:
        g = R[(R["lead"] == h) & R["in_study"]]
        summ[f"lead{h}"] = {"origins": g["origin_quarter"].tolist(), "targets": g["target"].tolist(),
                            "n_quarters": int(len(g)), "n_rows": int(5 * len(g))}
        print(f"lead {h}: {len(g)} origins {g['origin_quarter'].tolist()[:1]}..{g['origin_quarter'].tolist()[-1:]}"
              f" targets {g['target'].tolist()}")
    common = set.intersection(*[set(summ[f"lead{h}"]["targets"]) for h in H.LEADS])
    summ["common_targets"] = sorted(common, key=L.qi)
    print("common targets:", summ["common_targets"])
    (H.E63 / "out" / "eligibility.json").write_text(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main()
