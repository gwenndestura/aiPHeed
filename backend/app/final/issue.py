"""
Build one ISSUE of the served FINAL forecast from the frozen model (no refit) and write it atomically to

    data/final/issues/<issue id>/  live.json, dashboard_rows.csv, shap_live_features.csv, shap_live_summary.csv, inputs.csv,
                                   news_used.json, manifest.json

Issue ids: "YYYY-MM" (monthly, issued on the 10th; owner rule 2026-11-14) or "YYYY-Qn" (the earlier quarterly rule). inputs.csv
is the exact inference input rows (every candidate input of the five provinces, per lead), so an issue keeps its own input snapshot.

Inputs are the as-of rows of app.hcw.serve._rows (data published before the issue's information cut-off, built by the data stage).
Official values are FINAL's own: P(HIGH) = mean over the 5 seeds, forecast share = sigmoid(mean mu), class HIGH when P >= 0.50;
the explanation is LightGBM TreeSHAP (exact, additive on mu). Leads 1..max_lead only (app.final.period).

    python -m app.final.issue freeze --issue 2026-Q4     fit the frozen models once (the sealed training rows) -> data/final/model/
    python -m app.final.issue build  --issue 2027-Q1     build an issue with the frozen models
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from app.final import frozen as FZ
from app.final import period as PD
from app.paths import BACKEND_DIR

D = BACKEND_DIR / "data"
ROOT = D / "final"
ISSUES = ROOT / "issues"
MODEL = ROOT / "model" / "frozen_final.pkl"
MODEL_MANIFEST = ROOT / "model" / "model_manifest.json"
HARVEST = {"c_agri_yoy", "agri_since", "c_agri_pc"}          # combined farm-output inputs counted with harvests (served attribution)
INPUT_FILES = ["e148/out/gov_panel.parquet", "e150/out/cpi_panel.parquet", "e151/out/news_panel.parquet", "e152/out/local_panel.parquet",
               "hcw/out/cand_panel.parquet", "hfias/clean/enns_hfias.csv", "e168/live_raw/state.json"]


class IssueError(RuntimeError):
    pass


class RetrainingRequired(IssueError):
    """The training rows differ from the frozen model's (a new survey round): a controlled retrain + evaluation is required."""


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def data_version() -> dict:
    files = {f: sha256(D / f) for f in INPUT_FILES if (D / f).exists()}
    tag = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
    return {"tag": tag[:16], "files": files}


def _pct(z):
    return 100.0 / (1.0 + np.exp(-np.asarray(z, float)))


def freeze(issue_label: str, leads: list[int] | None = None, seeds: list[int] | None = None, n_jobs: int = 10) -> dict:
    """Fit the frozen models once on the training rows of `issue_label` (only allowed with the approved procedure)."""
    from joblib import Parallel, delayed
    cfg = PD.serving()
    leads = leads or list(range(1, int(cfg["validated_max_lead"]) + 1))
    seeds = seeds or list(cfg["seeds"])
    models = Parallel(n_jobs=n_jobs)(delayed(_fit_one)(issue_label, L, s) for L in leads for s in seeds)
    digest = FZ.save(models, MODEL)
    man = {"model_id": cfg["model_id"], "version": models[0].version, "fitted_for_issue": issue_label, "leads": leads, "seeds": seeds,
           "sha256": digest, "fitted_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "training_fingerprints": {f"L{m.lead}": m.train_fingerprint for m in models if m.seed == seeds[0]},
           "train_rounds": models[0].train_rounds, "n_train": {f"L{m.lead}": m.n_train for m in models if m.seed == seeds[0]}}
    MODEL_MANIFEST.write_text(json.dumps(man, indent=1), encoding="utf-8", newline="\n")
    return man


def _fit_one(issue_label, lead, seed):
    from app.hcw import serve as SV
    tr, te, AN, _ = SV._rows(lead, issue_label)
    return FZ.fit(tr, {a: AN[a][0] for a in AN}, seed, lead)


def _group(c: str) -> str:
    from app.hcw import engine as H
    b = c[3:] if c.startswith("mi_") else c
    return "rp_agprod" if b in HARVEST else H.group_of(b)


def predict_issue(issue_label: str, models: list | None = None) -> list[dict]:
    """Frozen-model predictions for every served lead and seed. Raises RetrainingRequired on a training-row change."""
    from app.hcw import serve as SV
    models = models if models is not None else FZ.load(MODEL)
    out = []
    for lead in range(1, PD.max_lead() + 1):
        ms = [m for m in models if m.lead == lead]
        if not ms:
            raise IssueError(f"no frozen model for Lead {lead}")
        tr, te, AN, issue = SV._rows(lead, PD.base_quarter(issue_label))
        fp = FZ.training_fingerprint(tr)
        if any(m.train_fingerprint != fp for m in ms):
            raise RetrainingRequired(f"Lead {lead}: the training rows changed since the model was frozen (new survey round?); "
                                     f"retrain and re-evaluate before issuing")
        for m in ms:
            q = m.predict(te, np.asarray(AN[m.anchor][1], float))
            out.append({"lead": lead, "seed": m.seed, "issue": issue, "te_raw": te, "province": te["province"].tolist(), "anchor_values": np.asarray(AN[m.anchor][1], float),
                        "g": m.model._g(q["te"]), "med": m.model.med_, **q})
    return out


def assemble(issue_label: str, R: list[dict], generated_utc: str) -> dict:
    """Served rows, SHAP tables and live.json from the per-seed predictions (pure; tested)."""
    from app.e151 import prov as Pv
    from app.hcw import serve as SV
    cfg = PD.serving()
    news = set(Pv.NEWS_ALL)
    cutoff = PD.issue_datetime(issue_label).date().isoformat()
    rows, feats, summ, prov = [], [], [], []
    for lead in sorted({r["lead"] for r in R}):
        rs = [r for r in R if r["lead"] == lead]
        tq = PD.label(PD.quarter_index(PD.base_quarter(issue_label)) + lead)
        for k, name in enumerate(rs[0]["province"]):
            p = float(np.mean([r["p"][k] for r in rs]))
            mu = float(np.mean([r["mu"][k] for r in rs]))
            half = float(np.mean([r["half"][k] for r in rs]))
            anchor = float(np.mean([r["anchor_values"][k] for r in rs]))
            gr = {v: 0.0 for v in SV.BARS.values()}; gn = dict(gr); other = pov = 0.0
            expv = change = 0.0
            per_feat = {}
            for r in rs:
                c = r["contrib"][k]
                for j, col in enumerate(r["cols"]):
                    v = float(c[j]) / len(rs)
                    grp = _group(col)
                    if grp in SV.BARS:
                        gr[SV.BARS[grp]] += v; gn[SV.BARS[grp]] += v if col in news else 0.0
                    elif grp == "poverty":
                        pov += v
                    else:
                        other += v
                    per_feat.setdefault(col, []).append((r["seed"], float(c[j]), r))
                expv += float(c[-1]) / len(rs)
                change += float(c.sum()) / len(rs)
            add_err = abs(anchor + change - mu)
            if add_err > 1e-6:
                raise IssueError(f"{name} L{lead}: explanation does not add up to the forecast ({add_err:.2e})")
            X = rs[0]["te"]
            o = {"province_code": SV.CODES[name], "province": name, "quarter": tq, "lead": lead, "issue_date": cutoff,
                 "probability": round(p, 4), "class": "HIGH" if p >= 0.5 else "LOW", "score_pct": round(float(_pct(mu)), 1),
                 "range90_low": round(float(_pct(mu - half)), 1), "range90_high": round(float(_pct(mu + half)), 1),
                 "config": " || ".join(r["cfg"] for r in rs), "model": cfg["model_id"], "value_basis": f"FINAL issue {issue_label} (frozen model)",
                 "baseline_pct": round(float(_pct(mu - change)), 4), "change_logit": round(change, 6), "expected_value_logit": round(expv, 6),
                 "shap_other": round(other, 6), "shap_poverty": round(pov, 6),
                 "own_survey_gap_q": int(X.at[k, "gap_q"]) if "gap_q" in X else None,
                 "attribution_basis": "FINAL TreeSHAP (own-survey elapsed time, mean of 5 seeds), frozen model"}
            for v in SV.BARS.values():
                o[f"shap_{v}"], o[f"shap_news_{v}"] = round(gr[v], 6), round(gn[v], 6)
            for c in SV.VALUES:
                o[f"val_{c}"] = None if c not in X or pd.isna(X.at[k, c]) else float(X.at[k, c])
            rows.append(o)
            for col, lst in per_feat.items():
                r0 = lst[0][2]
                raw = r0["te"].at[k, col] if col in r0["te"] else np.nan
                med = float(r0["med"].get(col, np.nan))
                feats.append({"province": name, "lead": lead, "quarter": tq, "feature": col, "group": _group(col),
                              "value_raw": None if pd.isna(raw) else float(raw), "value_used": med if pd.isna(raw) else float(raw),
                              "missing": bool(pd.isna(raw)), "shap_logit": float(sum(x[1] for x in lst) / len(rs)), "reference_median": med,
                              "seeds_using": len(lst), "shap_by_seed": json.dumps([round(x[1], 6) for x in lst])})
            g_scale = float(np.mean([r["g"][k] for r in rs]))
            summ.append({"province": name, "lead": lead, "quarter": tq, "anchor_logit": anchor, "anchor_names": "|".join(r["anchor"] for r in rs),
                         "expected_value_logit": expv, "inputs_shap_logit": change - expv, "mu": mu, "additivity_error": add_err,
                         "anchor_share_pct": float(_pct(anchor)), "forecast_share_pct": float(_pct(mu)),
                         "gap_q": float(X.at[k, "gap_q"]) if "gap_q" in X else None, "g_scale": g_scale, "p_high_mean_of_seeds": p,
                         "official_p_high": round(p, 4), "official_class": o["class"], "sd_mean": half / 1.645, "configs": o["config"]})
            prov.append({"province": name, "lead": lead, "target_quarter": tq, "score_pct": o["score_pct"],
                         "range90_pct": [o["range90_low"], o["range90_high"]], "p_high": o["probability"], "risk_class": o["class"],
                         "value_basis": o["value_basis"]})
    live = {"model": cfg["model_id"], "name": cfg.get("model_name", cfg["model_id"]), "created_utc": generated_utc,
            "issue_quarter": issue_label, "information_cutoff": cutoff, "target": "HFIAS moderate+severe household food insecurity, HIGH at 50 %",
            "provinces": prov, "served_leads": sorted({r["lead"] for r in R}), "seeds": sorted({r["seed"] for r in R}),
            "served_leads_rule": cfg.get("lead_basis", ""), "statistical_reliability": cfg.get("caveat", ""),
            "acceptance_basis": cfg.get("lead_basis", ""), "issue_label": PD.issue_label(issue_label),
            "base_quarter": PD.base_quarter(issue_label)}
    from app.final.serving import model_accuracy_by_lead
    live["accuracy_by_lead"] = model_accuracy_by_lead()
    seen, inputs = set(), []
    for r in R:                                                    # one copy of each lead's raw input rows (identical across seeds)
        if r["lead"] in seen or "te_raw" not in r:
            continue
        seen.add(r["lead"])
        X = r["te_raw"].copy()
        X["served_lead"] = r["lead"]
        inputs.append(X)
    return {"rows": rows, "features": feats, "summary": summ, "live": live,
            "inputs": pd.concat(inputs, ignore_index=True) if inputs else pd.DataFrame()}


def validate(issue_label: str, A: dict) -> None:
    R = pd.DataFrame(A["rows"])
    want = {(p, PD.label(PD.quarter_index(PD.base_quarter(issue_label)) + L)) for p in ("Batangas", "Cavite", "Laguna", "Quezon", "Rizal")
            for L in range(1, PD.max_lead() + 1)}
    got = set(zip(R.province, R.quarter))
    if got != want:
        raise IssueError(f"issue {issue_label}: provinces/target quarters {sorted(got)} differ from {sorted(want)}")
    if R.probability.isna().any() or not R.probability.between(0, 1).all():
        raise IssueError("probability missing or outside 0-1")
    if ((R.probability >= 0.5) != (R["class"] == "HIGH")).any():
        raise IssueError("class does not match probability")
    if not (R.range90_low <= R.score_pct).all() or not (R.score_pct <= R.range90_high).all():
        raise IssueError("forecast share outside its 90% range")


def write_issue(issue_label: str, A: dict, data_ver: dict, model_sha: str, root: Path | None = None) -> Path:
    root = root or ISSUES
    dst = root / issue_label
    if dst.exists():
        raise IssueError(f"issue {issue_label} already exists; issues are never regenerated or overwritten")
    tmp = root / f".{issue_label}.tmp"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    pd.DataFrame(A["rows"]).to_csv(tmp / "dashboard_rows.csv", index=False, lineterminator="\n")
    pd.DataFrame(A["features"]).to_csv(tmp / "shap_live_features.csv", index=False, lineterminator="\n")
    pd.DataFrame(A["summary"]).to_csv(tmp / "shap_live_summary.csv", index=False, lineterminator="\n")
    (tmp / "live.json").write_text(json.dumps(A["live"], indent=1), encoding="utf-8", newline="\n")
    if isinstance(A.get("inputs"), pd.DataFrame) and not A["inputs"].empty:
        A["inputs"].to_csv(tmp / "inputs.csv", index=False, lineterminator="\n")
    if A.get("news_used") is not None:                           # the caller states the exact stories the news inputs read
        (tmp / "news_used.json").write_text(json.dumps(A["news_used"], indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
    else:
        try:   # the stories this issue read (3 months before its cut-off: provinces, region, Balance Luzon, national) for the news panel
            from app.e168 import news_used as NU
            doc = NU.build(A["live"]["information_cutoff"])
            (tmp / "news_used.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
        except Exception:                                        # the forecast does not depend on the list; the panel falls back
            pass
    files = {f.name: sha256(f) for f in sorted(tmp.iterdir())}
    man = {"issue_quarter": issue_label, "information_cutoff": A["live"]["information_cutoff"], "generated_utc": A["live"]["created_utc"],
           "model_id": A["live"]["model"], "model_sha256": model_sha, "data_version": data_ver, "files": files}
    (tmp / "manifest.json").write_text(json.dumps(man, indent=1), encoding="utf-8", newline="\n")
    tmp.rename(dst)
    return dst


def ledger_rows(issue_dir: Path) -> list[dict]:
    """Forecast-history records for an issue directory (app.final.history.record_issue)."""
    man = json.loads((issue_dir / "manifest.json").read_text(encoding="utf-8"))
    live = json.loads((issue_dir / "live.json").read_text(encoding="utf-8"))
    R = pd.read_csv(issue_dir / "dashboard_rows.csv")
    dv = man["data_version"]["tag"] if isinstance(man.get("data_version"), dict) else str(man.get("data_version", ""))
    return [{"model_id": man["model_id"], "model_version": str(man.get("model_sha256", ""))[:16], "issue_quarter": man["issue_quarter"],
             "information_cutoff": man["information_cutoff"], "target_quarter": r["quarter"], "lead": int(r["lead"]), "province": r["province"],
             "province_code": r["province_code"], "p_high": float(r["probability"]), "risk_class": str(r["class"]),
             "share_pct": float(r["score_pct"]), "range90_pct": [float(r["range90_low"]), float(r["range90_high"])],
             "generated_utc": man["generated_utc"], "data_version": dv, "issue_dir": f"data/final/issues/{issue_dir.name}"}
            for r in R.to_dict("records")]


def check_information_rule(issue_label: str) -> None:
    """An issue may use only figures online BEFORE its cut-off (the rule the walk-forward evaluation used). The E168 live-refresh
    rule lets a figure first downloaded up to the refresh day count at the cut-off; that is refused here (audit 2026-11-14: the
    2026-Q4 issue, built by hand from the E168 refresh panels, used October CPI and September LFS published after 1 November)."""
    from app.e168 import live_data as LD
    a, p = LD._live_dates()
    cut = PD.issue_datetime(issue_label).date()
    if a is None or a.date() != cut:
        raise IssueError(f"issue {issue_label}: the data cut-off in effect is {a and a.date()}, not the issue cut-off {cut} "
                         "(set AIPHEED_LIVE_ASOF; app.final.cycle does this)")
    if p is not None and p.date() > cut:
        raise IssueError(f"issue {issue_label}: figures published up to {p.date()} would count as available at the {cut} cut-off; "
                         "only figures online before the cut-off may be used (unset AIPHEED_LIVE_PUBLISHED)")


def build(issue_label: str, now_utc: str | None = None, *, news_used: dict | None = None, live_extra: dict | None = None) -> Path:
    """`news_used` states the stories the news inputs read when they were not rebuilt for this cut-off; `live_extra` adds
    provenance fields to live.json (e.g. which issue this one supersedes)."""
    if not MODEL.exists():
        raise IssueError("no frozen model (python -m app.final.issue freeze)")
    gen = now_utc or datetime.now(timezone.utc).isoformat(timespec="seconds")
    check_information_rule(issue_label)
    R = predict_issue(issue_label)
    A = assemble(issue_label, R, gen)
    validate(issue_label, A)
    A["live"].update(live_extra or {})
    A["news_used"] = news_used
    return write_issue(issue_label, A, data_version(), sha256(MODEL))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["freeze", "build"])
    ap.add_argument("--issue", required=True)
    a = ap.parse_args()
    os.environ.setdefault("AIPHEED_LIVE_ASOF", PD.issue_datetime(a.issue).date().isoformat())
    print(json.dumps(freeze(a.issue), indent=1) if a.cmd == "freeze" else str(build(a.issue)))
