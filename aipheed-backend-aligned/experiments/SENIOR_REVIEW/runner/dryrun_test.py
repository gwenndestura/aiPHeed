"""Dry-run tests of seal_next.py / score_prospective.py. Nothing is written outside the given scratch directory, and the
real ledger (../prospective/) must not exist afterwards.

    python dryrun_test.py SCRATCH_DIR     # -> SCRATCH_DIR/dryrun_test.json, exit 1 on any failure

Replay: the stored development forecasts (OPTION_1 REF+news, IMPROVE_V2_LEADS REF, PERSIST, CLIM; origins 2009-Q3..
2026-Q3) are written as one "sealed" file per issue date with a ledger, then scored with the first prospective target
set to 2010-Q1. The scorer must reproduce the published OPTION_1 (REF+news) and RELIABLE_L12 0.50 (REF) R1-R7 results.
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import json
import shutil
import subprocess
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prospective_lib as P  # noqa: E402

H = P.H
HERE = Path(__file__).resolve().parent
SCORE = [sys.executable, str(HERE / "score_prospective.py")]


def run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(SCORE + args, capture_output=True, text=True, cwd=HERE)


def build_replay(dirp: Path):
    opt = pd.read_csv(P.EXP / "OPTION_1" / "out" / "forecasts_refnews.csv")
    lds = pd.read_csv(P.EXP / "IMPROVE_V2_LEADS" / "out" / "forecasts_leads.csv")
    cbf = pd.read_csv(P.CB_DIR / "out" / "forecasts.csv")
    dirp.mkdir(parents=True)
    for t in range(H.qi("2009-Q3"), H.qi("2026-Q3") + 1):
        rows = []
        for m, src in (("C-b", cbf), ("REF+news", opt), ("REF", lds)):
            for k in P.LEADS:
                p = float(src[(src["name"] == m) & (src["t"] == t) & (src["lead"] == k)]["p"].iloc[0])
                ps = float(lds[(lds["name"] == "PERSIST") & (lds["t"] == t) & (lds["lead"] == k)]["p"].iloc[0])
                cl = float(lds[(lds["name"] == "CLIM") & (lds["t"] == t) & (lds["lead"] == k)]["p"].iloc[0])
                rows.append({"issue_date": H.issue(t), "origin": H.qs(t), "lead": k, "target_quarter": H.qs(t + k),
                             "model": m, "p_high": p, "class": "HIGH" if p >= .5 else "LOW", "persist_si": ps,
                             "clim": cl})
        f = dirp / f"sealed_{H.issue(t)}.csv"
        pd.DataFrame(rows).to_csv(f, index=False)
        P.append_ledger(dirp / "SEAL_LEDGER.md", {"file": f.name, "sha256": P.sha(f), "issue": H.issue(t),
                                                  "targets": f"{H.qs(t + 1)}, {H.qs(t + 2)}", "sealed_at": "replay",
                                                  "commit": "000000000000"})


def main():
    S = Path(sys.argv[1]).resolve()
    if S.exists():
        shutil.rmtree(S)
    res = {}
    rp = S / "replay"
    build_replay(rp)
    led = str(rp / "SEAL_LEDGER.md")

    # 1. replay at 2027-03-01: reproduces the published development results; takes the single-look verdict
    r = run(["--date", "2027-03-01", "--dry-run", "--out", str(S / "score_a"), "--ledger", led, "--replay-first", "2010-Q1"])
    rep = json.loads((S / "score_a" / "score_2027-03-01.json").read_text(encoding="utf-8")) if r.returncode == 0 else {}
    opt = json.loads((P.EXP / "OPTION_1" / "out" / "results.json").read_text(encoding="utf-8"))
    l12 = json.loads((P.EXP / "RELIABLE_L12" / "out" / "results.json").read_text(encoding="utf-8"))
    cbr = json.loads((P.CB_DIR / "out" / "results_cb.json").read_text(encoding="utf-8"))
    chk = {}
    for k in ("1", "2"):
        a = rep["models"]["C-b"][k]
        b = cbr["leads"][f"L{k}"]
        chk[f"C-b L{k}"] = (a["labelled_quarters"] == b["n_quarters"]
                            and {x: v["pass"] for x, v in a["rules"].items()} == {x: v["pass"] for x, v in b["rules"].items()}
                            and all(abs(a["metrics"][x] - b["metrics"][x]) < 1e-12 for x in ("accuracy", "balanced", "auc", "brier"))
                            and a["independent_check"] == "agrees")
        a = rep["models"]["REF+news"][k]
        b = opt["leads"][f"L{k}"]
        chk[f"REF+news L{k}"] = (a["labelled_quarters"] == b["n_quarters"]
                                 and {x: v["pass"] for x, v in a["rules"].items()} == {x: v["pass"] for x, v in b["rules"].items()}
                                 and all(abs(a["metrics"][x] - b["metrics"][x]) < 1e-12 for x in ("accuracy", "balanced", "auc", "brier"))
                                 and a["independent_check"] == "agrees")
        c = rep["models"]["REF"][k]
        e = l12["candidates"]["C1"]["leads"][k]["at_050"]
        chk[f"REF L{k}"] = ([x for x, v in c["rules"].items() if not v["pass"]] == e["failed"]
                            and all(abs(c["metrics"][x] - e["metrics"][x]) < 1e-12 for x in ("accuracy", "balanced", "auc", "brier")))
    res["1 replay reproduces NEWS_V2 (C-b, main), OPTION_1 (REF+news) and RELIABLE_L12 0.50 (REF)"] = {
        "ok": r.returncode == 0 and all(chk.values()), "by_lead": chk,
        "verdict": rep.get("verdict"), "missed_seals": rep.get("missed_seals")}
    res["2 single look: verdict taken at the first 1 March with >= 40 quarters"] = {
        "ok": rep.get("verdict", {}).get("single_look") is True and rep["verdict"]["maximum_reliable_lead"] == 0}

    # 2. a later scoring does not change the verdict
    r2 = run(["--date", "2028-03-01", "--dry-run", "--out", str(S / "score_a"), "--ledger", led, "--replay-first", "2010-Q1"])
    rep2 = json.loads((S / "score_a" / "score_2028-03-01.json").read_text(encoding="utf-8")) if r2.returncode == 0 else {}
    res["3 a later scoring reports the verdict unchanged"] = {
        "ok": rep2.get("verdict", {}).get("note") == "taken earlier; unchanged"
        and rep2["verdict"]["taken_on"] == "2027-03-01"}

    # 3. few quarters: insufficient, no verdict; review trigger evaluated from 20 quarters
    r3 = run(["--date", "2012-06-01", "--dry-run", "--out", str(S / "score_b"), "--ledger", led, "--replay-first", "2010-Q1"])
    rep3 = json.loads((S / "score_b" / "score_2012-06-01.json").read_text(encoding="utf-8")) if r3.returncode == 0 else {}
    m3 = rep3.get("models", {}).get("REF+news", {})
    res["4 fewer than 40 quarters: insufficient prospective evidence, no verdict"] = {
        "ok": r3.returncode == 0 and all(m3[k]["status"] == "insufficient prospective evidence" for k in ("1", "2"))
        and "status" in rep3["verdict"], "quarters": {k: m3[k]["labelled_quarters"] for k in ("1", "2")} if m3 else None,
        "stderr": r3.stderr[-300:] if r3.returncode else ""}
    r4 = run(["--date", "2015-06-01", "--dry-run", "--out", str(S / "score_c"), "--ledger", led, "--replay-first", "2010-Q1"])
    rep4 = json.loads((S / "score_c" / "score_2015-06-01.json").read_text(encoding="utf-8")) if r4.returncode == 0 else {}
    rt = rep4.get("models", {}).get("REF+news", {}).get("1", {}).get("review_trigger")
    res["5 review trigger computed from 20 quarters (good model: no flag)"] = {
        "ok": rt is not None and rt["flag"] is False, "trigger": rt}
    bp = S / "bad"
    bp.mkdir()
    for f in sorted(rp.glob("sealed_*.csv")):
        x = pd.read_csv(f)
        x.loc[x["model"] == "REF+news", "p_high"] = 1 - x.loc[x["model"] == "REF+news", "persist_si"]
        x.to_csv(bp / f.name, index=False)
        P.append_ledger(bp / "SEAL_LEDGER.md", {"file": f.name, "sha256": P.sha(bp / f.name), "issue": x["issue_date"].iloc[0],
                                                "targets": "-", "sealed_at": "replay", "commit": "000000000000"})
    r4b = run(["--date", "2015-06-01", "--dry-run", "--out", str(S / "score_bad"), "--ledger", str(bp / "SEAL_LEDGER.md"),
               "--replay-first", "2010-Q1"])
    rep4b = json.loads((S / "score_bad" / "score_2015-06-01.json").read_text(encoding="utf-8")) if r4b.returncode == 0 else {}
    rtb = rep4b.get("models", {}).get("REF+news", {}).get("1", {}).get("review_trigger")
    res["5b review trigger fires for a model worse than persistence (p = 1 - persistence)"] = {
        "ok": rtb is not None and rtb["flag"] is True, "trigger": rtb}

    # 4. tampering is caught
    tp = S / "tamper"
    shutil.copytree(rp, tp)
    f = sorted(tp.glob("sealed_*.csv"))[10]
    x = pd.read_csv(f)
    x.loc[0, "p_high"] = 0.01
    x.to_csv(f, index=False)
    r5 = run(["--date", "2027-03-01", "--dry-run", "--out", str(S / "score_t"), "--ledger", str(tp / "SEAL_LEDGER.md"),
              "--replay-first", "2010-Q1"])
    res["6 an edited sealed file aborts the scoring"] = {"ok": r5.returncode != 0 and "does not match" in r5.stderr,
                                                         "message": r5.stderr.strip().splitlines()[-1] if r5.stderr else ""}

    # 5. a missing seal is counted, never back-filled
    mp = S / "missing"
    shutil.copytree(rp, mp)
    gone = "2015-04-01"
    (mp / f"sealed_{gone}.csv").unlink()
    lines = [ln for ln in (mp / "SEAL_LEDGER.md").read_text(encoding="utf-8").splitlines() if gone not in ln]
    (mp / "SEAL_LEDGER.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    r6 = run(["--date", "2027-03-01", "--dry-run", "--out", str(S / "score_m"), "--ledger", str(mp / "SEAL_LEDGER.md"),
              "--replay-first", "2010-Q1"])
    rep6 = json.loads((S / "score_m" / "score_2027-03-01.json").read_text(encoding="utf-8")) if r6.returncode == 0 else {}
    res["7 a missed seal is counted and its targets drop out"] = {
        "ok": gone in rep6.get("missed_seals", []) and rep6["models"]["REF+news"]["1"]["labelled_quarters"] == 61,
        "missed": rep6.get("missed_seals"), "L1_quarters": rep6.get("models", {}).get("REF+news", {}).get("1", {}).get("labelled_quarters")}

    # 6. the real configuration: the empty real ledger + the OPTION_1 2027-Q1 seal by reference
    r7 = run(["--date", "2027-03-01", "--dry-run", "--out", str(S / "score_real")])
    rep7 = json.loads((S / "score_real" / "score_2027-03-01.json").read_text(encoding="utf-8")) if r7.returncode == 0 else {}
    res["8 real setup: OPTION_1 and C-b seals verified and included (Lead 2, 2027-Q1, unlabelled); C-b is the main model; "
        "2027-01-01 counted missed"] = {
        "ok": r7.returncode == 0 and any(f.get("sha256") == P.OPT_SEAL_SHA and f["hash_ok"] for f in rep7["sealed_files"])
        and any(f.get("sha256") == P.CB_SEAL_SHA and f["hash_ok"] for f in rep7["sealed_files"])
        and rep7["models"]["REF+news"]["2"]["sealed_rows"] == 1 and rep7["models"]["C-b"]["2"]["sealed_rows"] == 1
        and rep7["models"]["C-b"]["1"].get("sealed_rows", 0) == 0 and rep7["main_model"] == "C-b"
        and rep7["missed_seals"] == ["2027-01-01"],
        "sealed_files": rep7.get("sealed_files"), "missed": rep7.get("missed_seals")}

    # 7. real-mode refusals
    refusals = {"future date": run(["--date", "2028-03-01"]), "before 2028": run(["--date", "2027-03-01"]),
                "not 1 March": run(["--date", "2028-04-01"]),
                "dry-run flags in real mode": run(["--date", "2028-03-01", "--out", str(S / "x")])}
    res["9 real-mode scoring refuses (future, before 2028, not 1 March, dry-run flags)"] = {
        "ok": all(v.returncode != 0 for v in refusals.values()),
        "messages": {k: v.stderr.strip().splitlines()[-1] for k, v in refusals.items()}}

    real = [] if not P.PROS.exists() else [x.name for x in P.PROS.iterdir() if x.name != "SEAL_LEDGER.md"]
    res["10 no seal or score file in the real prospective/ folder; the ledger holds no seal row"] = {
        "ok": not real and P.read_ledger(P.LEDGER) == [], "files": real}
    ok = all(v["ok"] for v in res.values())
    (S / "dryrun_test.json").write_text(P.dumps(res), encoding="utf-8")
    for k, v in res.items():
        print(("PASS " if v["ok"] else "FAIL ") + k)
    print("ALL PASS" if ok else "SOME FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
