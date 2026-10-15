"""E31 step 4: the operational outputs as of the authorized limit (information cutoff 2026-10-14 23:59:59 PHT).

  NOWCAST  2026-Q4 (lead 0; the quarter is under way): PCF21 with every input released by the cutoff
           (SWS through September 2026, D through 2026-Q3). Supporting news = 2026-Q4 articles published by the cutoff.
  FORECAST 2027-Q1 (lead 1): same origin. Supporting news = 2026-Q4 articles published by the cutoff (PARTIAL window).

PCF21 itself uses no news (its inputs are SWS hunger and PSA food CPI), so 'n_articles_used_by_model' is 0 and the
news window is the evidence shown beside the estimate, governed by app/news/alignment.py. Lead 0 has never been
evaluated on development data: its evidence status is NOT_EVALUATED, and lead 1 is NOT_ESTABLISHED (E25/E28).
Nothing here is a seal: the ledger's seals for 2026-Q4 / 2027-Q1 (origin 2026-10-01) stay as they are.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
EXP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXP / "runner"))
sys.path.insert(0, str(EXP / "backend_dev"))
import guard31  # noqa: E402

guard31.install()
import pandas as pd  # noqa: E402

from app.news.alignment import evidence_window, provenance, select  # noqa: E402
from app.quarterly import pcf_engine as P  # noqa: E402
from app.quarterly.cycle import reference_probabilities  # noqa: E402

BD = EXP / "backend_dev"
INP = BD / "data" / "inputs"
STORE = BD / "data" / "news_e31"
CUTOFF = "2026-10-14T23:59:59+08:00"
ORIGIN = pd.Timestamp("2026-10-15T00:00:00")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def news_version() -> dict:
    return {"store": "news_e31 (Google News RSS titles; E28 collector + E31 date limit)",
            "articles_jsonl_sha256": sha(STORE / "articles.jsonl"), "scores_jsonl_sha256": sha(STORE / "scores.jsonl"),
            "source_policy": "v1"}


def main(generated_at: datetime | None = None):
    generated_at = generated_at or datetime.now(timezone.utc)
    rounds = pd.read_csv(INP / "sws_rounds.csv")
    S1 = pd.read_csv(INP / "s1_labels.csv", dtype={"province_code": str})
    dq = pd.read_csv(INP / "d_quarterly_panel.csv", dtype={"province_code": str})
    dn = pd.read_csv(INP / "dnow_panel.csv", dtype={"province_code": str})
    Dm, Nm = P.panels_from_tables(dq, dn)
    ev = {"T1": {"0": {"status": "NOT_EVALUATED", "basis": "lead 0 (same-quarter estimate) was never evaluated"},
                 "1": {"status": "NOT_ESTABLISHED", "basis": "development quarters only (E25/E28); one unseen quarter "
                                                             "(2026-Q3) scored in E31"}}}
    fc = P.forecast(ORIGIN, P.qk("2026-Q4"), [0, 1], rounds, S1, Dm, Nm, ev)
    arts = [json.loads(l) for l in open(STORE / "articles.jsonl", encoding="utf-8") if l.strip()]
    nv = news_version()
    out = {"record": "E31 operational outputs", "information_cutoff": CUTOFF, "origin": ORIGIN.isoformat(),
           "inputs_sha256": {f: sha(INP / f) for f in ("sws_rounds.csv", "s1_labels.csv", "d_quarterly_panel.csv",
                                                      "dnow_panel.csv")},
           "engine": "PCF21 (app/quarterly/pcf_engine.py)", "engine_sha256": sha(BD / "app" / "quarterly" / "pcf_engine.py"),
           "threshold": fc["threshold"], "threshold_labels": fc["threshold_labels"],
           "sws_rounds_used": fc["sws_rounds_used"], "outputs": []}
    for lead, mode in (("0", "nowcast"), ("1", "forecast")):
        blk = fc["leads"][lead]
        tq = blk["target_quarter"]
        w = evidence_window(tq, mode, CUTOFF)
        shown, why = select(arts, w)
        refs = reference_probabilities(S1, fc["threshold"], "2026-Q4", max(int(lead), 1))
        prov = provenance(w, generated_at, nv, [])           # the model used no article
        prov["n_articles_used_by_model"] = prov.pop("n_articles_used")
        prov["supporting_news"] = {"n_articles_in_window": len(shown),
                                   "n_province_attributed": sum(1 for a in shown if a.get("geo_province_code")),
                                   "excluded": why}
        out["outputs"].append({"mode": mode.upper(), "lead": int(lead), "target_quarter": tq, "provenance": prov,
                               "H": blk["H"], "D_model": blk["D_model"], "layers": blk["layers"],
                               "provinces": blk["provinces"],
                               "references": {"persistence": refs["persistence"],
                                              "calibrated_persistence": refs["calibrated_persistence"],
                                              "climatology": refs["climatology"],
                                              "last_label_quarter": refs["last_label_quarter"]}})
    body = json.dumps(out, indent=1, default=float).encode("utf-8")
    (BD / "data" / "e31").mkdir(parents=True, exist_ok=True)
    (BD / "data" / "e31" / "operational_outputs.json").write_bytes(body)
    for o in out["outputs"]:
        print(o["mode"], o["target_quarter"], "tau", round(out["threshold"], 3), "H", round(o["H"]["mu_H"], 2),
              {v["province"][:3]: round(v["risk"]["p_high"], 3) for v in o["provinces"].values()},
              "news", o["provenance"]["supporting_news"]["n_articles_in_window"],
              o["provenance"]["news_evidence_window"]["coverage"])


if __name__ == "__main__":
    main()
