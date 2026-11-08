"""
Automatic monthly refresh of the served E168 forecast (10th of each month, app.tasks.scheduler): newest public figures
and news up to the last complete month, frozen E168 procedure, validated, promoted, served.

    python -m app.e168.live_refresh run [--as-of YYYY-MM-01] [--published YYYY-MM-DD] [--skip-news] [--no-promote] [--force]

Cut-off: the first day of the current month, so the newest period used is the last complete month (on 8 November:
October). Figures for periods up to that month that are already online on the refresh day are used.
    python -m app.e168.live_refresh status

Steps (each one logged in data/e168/live_raw/refresh_log.jsonl; a failed step stops the run and what is served stays):
    1 government   app.e168.live_data.fetch: PSA production, CPI and LFS; NASA POWER rainfall and soil; NOAA ONI;
                   IBTrACS cyclones; World Bank remittances
    2 news         publisher archives collected from the last collected day to today (app.fi6.news_archive), corpus,
                   story embeddings, XLM-R event and relevance scores for the new stories only (OpenVINO python),
                   event labels, topic assignment with the topic model fitted before the issue origin, news panel
    3 panels       the live issue quarter's rows of the government, CPI and news panels recomputed at the cut-off;
                   every other row is kept exactly as it was (the training and validation rows never change)
    4 forecast     app.e168.regenerate.stage(issue, as_of): Leads 1-3, SHAP groups, checks -> data/e168/issues/<issue>_<as_of>/
    5 promote      app.e168.regenerate.promote with the owner gate (O1-O7) re-checked; approver recorded as the
                   automatic refresh under the owner's standing instruction (2026-11-08). Skipped when nothing the
                   forecast reads has changed since the served issue.

Release rule for a live figure: usable under the training rule, or already in the public download on or before the
cut-off (app.e168.live_data.first_seen). The model, its training rows, inputs, target and thresholds are unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

import pandas as pd

from app.e168 import live_data as LD
from app.paths import BACKEND_DIR

D = BACKEND_DIR / "data"
STATE = LD.LIVE / "state.json"
LOG = LD.LIVE / "refresh_log.jsonl"
NEWS_LIVE = LD.LIVE / "news"
APPROVER = "automatic live refresh (standing instruction of the owner, Angel Melindo, 2026-11-08)"
PANELS = {"gov": D / "e148" / "out" / "gov_panel.parquet", "cpi": D / "e150" / "out" / "cpi_panel.parquet",
          "news": D / "e151" / "out" / "news_panel.parquet"}
CAL_KEYS = ["batangas", "cavite", "laguna", "quezon", "rizal"]


def _py() -> str:
    return sys.executable


def _ov_python() -> str | None:
    for p in (os.getenv("AIPHEED_OV_PYTHON"), r"C:\Users\admin\aipheed_fi5_xpu\Scripts\python.exe"):
        if p and os.path.exists(p):
            return p
    return None


def _ov_model() -> str | None:
    for p in (os.getenv("AIPHEED_OV_MODEL"), str(BACKEND_DIR / "models_ov" / "xlmr_large_xnli"),
              r"C:\Users\admin\aipheed_final\backend\models_ov\xlmr_large_xnli"):
        if p and os.path.exists(os.path.join(p, "openvino_model.xml")):
            return p
    return None


def _state() -> dict:
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def _save_state(s: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(s, indent=1), newline="\n")


def today_ph() -> str:
    from app.quarterly.target import now_ph
    return now_ph().date().isoformat()


def month_start(day: str) -> str:
    """The cut-off for figures and news: the first day of the month of `day` (the month in progress is not used)."""
    return pd.Timestamp(day).replace(day=1).date().isoformat()


def _run(args: list[str], as_of: str, python: str | None = None, timeout: int = 7200, published: str | None = None) -> str:
    env = {**os.environ, "AIPHEED_LIVE_ASOF": as_of, "AIPHEED_LIVE_PUBLISHED": published or os.getenv("AIPHEED_LIVE_PUBLISHED") or as_of,
           "PYTHONPATH": str(BACKEND_DIR), "PYTHONIOENCODING": "utf-8"}
    p = subprocess.run([python or _py(), *args], cwd=str(BACKEND_DIR), env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError(f"{' '.join(args[:3])} failed: {(p.stderr or p.stdout)[-1500:]}")
    return p.stdout[-3000:]


# -------------------------------------------------------------------------------------------------------------- news
def news_collect(as_of: str, published: str | None = None) -> dict:
    from app.fi6 import news_archive as NA
    st = _state()
    until = st.get("news_collected_until", NA.LAST_DAY[:10])
    after = (pd.Timestamp(until) - timedelta(days=2)).strftime("%Y-%m-%dT00:00:00")      # 2-day overlap for late indexing
    before = (pd.Timestamp(published or as_of) + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00")   # stored now, used from next month
    NA.collect(list(NA.SITES), (after, before))
    raw = NA_load_new()
    st["news_collected_until"] = published or as_of
    _save_state(st)
    return {"window": [after, before], "new_articles_total": int(len(raw)),
            "newest_published": str(raw["published"].max()) if len(raw) else None}


def NA_load_new() -> pd.DataFrame:
    """Collected articles that the FI6 archive build does not hold yet, in the columns the E151 corpus reads."""
    from app.fi6 import news_events as NE
    a = pd.read_parquet(D / "fi6" / "news_archive" / "articles.parquet", columns=["site", "wp_id"])
    have = set(a["site"] + ":" + a["wp_id"].astype(str))
    r = NE.load_raw()
    r = r[~r["excluded"]]
    r = r[~(r["site"] + ":" + r["wp_id"].astype(str)).isin(have)]
    out = r[["site", "wp_id", "title", "lead", "published", "link", "query_kind"]].copy()
    out["wp_id"] = out["wp_id"].astype("int64")
    out["published"] = pd.to_datetime(out["published"]).dt.tz_localize(None)
    NEWS_LIVE.mkdir(parents=True, exist_ok=True)
    out.to_parquet(NEWS_LIVE / "fi6_new_articles.parquet", index=False)
    return out


def news_pipeline(as_of: str, published: str | None = None) -> dict:
    out = {"collect": news_collect(as_of, published)}
    _run(["-m", "app.e151.corpus", "build"], as_of)
    _run(["-c", "from app.e151 import topics as T; T.embed()"], as_of)
    ovp, ovm = _ov_python(), _ov_model()
    if not (ovp and ovm):
        raise RuntimeError("OpenVINO python or XLM-R model not found (set AIPHEED_OV_PYTHON and AIPHEED_OV_MODEL)")
    out["score"] = _run(["-m", "app.e168.news_score", ovm], as_of, python=ovp).strip().splitlines()[-1]
    _run(["-c", "from app.e151 import labeler as L; L.build()"], as_of)
    _run(["-c", "from app.e168 import live_refresh as R; R.assign_topics()"], as_of)
    old = pd.read_parquet(PANELS["news"])
    _run(["-c", "from app.e151 import features as F; F.build()"], as_of)
    d = pd.Timestamp(as_of)
    out["panel"] = _splice("news", old, pd.read_parquet(PANELS["news"]), d.year * 4 + (d.month - 1) // 3)
    s = pd.read_parquet(D / "e151" / "raw" / "stories.parquet", columns=["published"])
    out["stories"], out["newest_story"] = int(len(s)), str(s["published"].max())
    return out


def assign_topics() -> None:
    """Topic of every story under the latest origin's topic model, fitted only on stories published before that origin
    (as app.e151.topics.fit). Earlier origins' assignments do not change: their fits are untouched."""
    import numpy as np

    from app.e151 import OUT, RAW
    from app.e151 import topics as T
    origin = T.ORIGINS[-1]
    d = pd.read_parquet(RAW / "stories.parquet")
    E = np.load(RAW / "embeddings.npy")
    d["first"] = ~d.duplicated("story")
    R, meta = T._fit(origin, d, E, T.event_probs())
    rep = pd.read_csv(OUT / "topic_report.csv")
    rep = pd.concat([rep[rep["origin"] != origin], R], ignore_index=True)
    rep.to_csv(OUT / "topic_report.csv", index=False, lineterminator="\n")
    print(json.dumps(meta))


# ------------------------------------------------------------------------------------------------------------ panels
def _splice(name: str, old: pd.DataFrame, new: pd.DataFrame, live_qi: int) -> dict:
    """Keep every non-live row exactly as before; take the recomputed live-quarter rows."""
    keep = old[old["qi"] != live_qi]                     # (a new quarter simply adds its rows)
    out = pd.concat([keep, new[new["qi"] == live_qi]], ignore_index=True)[old.columns]
    tmp = PANELS[name].with_suffix(".tmp")
    out.to_parquet(tmp, index=False)
    tmp.replace(PANELS[name])
    return {"rows": int(len(out)), "live_rows": int((out["qi"] == live_qi).sum())}


def rebuild_panels() -> dict:
    """Run with AIPHEED_LIVE_ASOF set: recompute the live issue quarter's panel rows at the cut-off."""
    import numpy as np
    from joblib import Parallel, delayed

    from app.e147 import features as Fe
    from app.e148 import panel as Pn
    from app.e150 import panel as P150
    asof = pd.Timestamp(os.environ["AIPHEED_LIVE_ASOF"])
    i = asof.year * 4 + (asof.month - 1) // 3
    res = {"cutoff": str(Pn.q_start(i).date())}
    # government panel: the GOV columns of the live rows; static columns (quarterly remittances, regional unemployment) kept
    G = pd.read_parquet(PANELS["gov"])
    live = G[G["qi"] == i].copy()
    if live.empty:                          # first refresh of a new quarter: start from the previous quarter's rows
        live = G[G["qi"] == G["qi"].max()].copy()
        live["qi"] = i
        live[["remit_q_yoy", "unemp_region"]] = np.nan     # not carried forward; recomputed below
    rows = Parallel(n_jobs=8)(delayed(Fe.gov_row)(k.replace(" ", ""), Pn.q_start(i)) for k in live["key"])
    for c in Fe.GOV:
        live[c] = [r.get(c, np.nan) for r in rows]
    if live["remit_q_yoy"].isna().all() or live["unemp_region"].isna().all():
        live = _static_columns(live, i, G)
    res["gov"] = _splice("gov", G, live, i)
    # CPI panel
    old = pd.read_parquet(PANELS["cpi"])
    new = P150.cpi_panel()
    res["cpi"] = _splice("cpi", old, new, i)
    return res


def _static_columns(live: pd.DataFrame, i: int, G: pd.DataFrame) -> pd.DataFrame:
    """Quarterly remittances and regional unemployment for a new live quarter, by the rules of app.e148.panel.build_gov."""
    import numpy as np

    from app.e147 import features as Fe
    from app.e148 import panel as Pn
    from app.fi5.target import qindex
    q = pd.read_csv(BACKEND_DIR.parent / "aipheed-backend-aligned" / "experiments" / "CORRECTED_PIPELINE" / "out" / "remittances_quarterly_corrected.csv")
    q["qi"] = q["quarter"].map(qindex)
    s = q.set_index("qi")["remit_usd_bn"]
    live["remit_q_yoy"] = 100 * (s[i - 2] / s[i - 6] - 1) if (i - 2) in s.index and (i - 6) in s.index else np.nan
    ref = G[G["qi"] == i - 4].set_index("key")["unemp_region"] if (i - 4) in set(G["qi"]) else pd.Series(dtype=float)
    ru = Pn._region_unemp()
    y = i // 4 - 1 if i % 4 >= 1 else i // 4 - 2
    reg = Fe.base_rows().drop_duplicates("key").set_index("key")["region"].to_dict()
    names = {"CALABARZON": "Region IV-A"}
    live["unemp_region"] = [ru.get(names.get(reg.get(k, ""), ""), {}).get(y, ref.get(k, np.nan)) for k in live["key"]]
    return live


# ---------------------------------------------------------------------------------------------------------- forecast
def _fingerprint(i: int) -> str:
    """What the live forecast reads for the five provinces at the live quarter."""
    h = hashlib.sha256()
    for name, p in PANELS.items():
        d = pd.read_parquet(p)
        d = d[d["qi"] == i]
        col = "key" if "key" in d else "stream"
        d = d[d[col].astype(str).str.replace("prov:", "").str.replace(" ", "").str.lower().isin(CAL_KEYS) | (col == "stream")]
        h.update(name.encode())
        h.update(d.sort_values(list(d.columns[:3])).round(9).to_csv(index=False).encode())
    return h.hexdigest()


def run(as_of: str | None = None, skip_news: bool = False, promote: bool = True, force: bool = False, published: str | None = None) -> dict:
    """`as_of` is the cut-off (default: the first day of the current month, so the newest period is the last complete
    month); `published` is the day the figures were checked online (default: today)."""
    from app.e168 import regenerate as RG
    from app.quarterly.target import forecast_target
    published = published or today_ph()
    as_of = as_of or month_start(published)
    os.environ["AIPHEED_LIVE_PUBLISHED"] = published
    issue = forecast_target(f"{as_of}T12:00:00")["calendar_quarter"]
    i = int(issue[:4]) * 4 + int(issue[-1]) - 1
    lock = LD.LIVE / ".refresh.lock"
    LD.LIVE.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        if time.time() - lock.stat().st_mtime < 6 * 3600:
            return {"status": "already running"}
        lock.unlink()
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    rec = {"started_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "as_of": as_of, "published_by": published,
           "issue_quarter": issue, "steps": {}}
    try:
        t = time.time()
        rec["steps"]["government"] = LD.fetch(published)
        if not skip_news:
            rec["steps"]["news"] = news_pipeline(as_of, published)
        rec["steps"]["panels"] = json.loads(_run(["-c", "import json; from app.e168 import live_refresh as R; print(json.dumps(R.rebuild_panels()))"], as_of).strip().splitlines()[-1])
        fp = _fingerprint(i)
        st = _state()
        if not force and st.get("served_fingerprint") == fp:
            rec["status"] = "unchanged: no new figure or story reaches the forecast; the served issue stays"
        else:
            rev = 1                                                 # a later re-issue for the same cut-off is a new revision
            while (RG.ISSUES / RG.folder_name(issue, as_of, rev)).exists():
                rev += 1
            out = _run(["-c", f"import json; from app.e168 import regenerate as RG; print(json.dumps(RG.stage('{issue}', '{as_of}', {rev})))"], as_of)
            rec["steps"]["stage"] = json.loads(out.strip().splitlines()[-1])
            if promote and rec["steps"]["stage"].get("status") == "staged":
                rec["steps"]["promote"] = RG.promote(rec["steps"]["stage"]["folder"], APPROVER)
                st.update(served_fingerprint=fp, served_folder=rec["steps"]["stage"]["folder"], served_cutoff=as_of, served_published_by=published)
            rec["status"] = "promoted" if "promote" in rec["steps"] else rec["steps"]["stage"].get("status", "staged")
        st["last_check"] = published
        _save_state(st)
        rec["seconds"] = round(time.time() - t, 1)
    except Exception as e:                                          # noqa: BLE001 - recorded; the served issue stays
        rec["status"] = "failed"
        rec["error"] = f"{type(e).__name__}: {e}"[:2000]
    finally:
        os.close(fd)
        lock.unlink(missing_ok=True)
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, default=str) + "\n")
    return rec


def status() -> dict:
    st = _state()
    last = None
    if LOG.exists():
        lines = [l for l in LOG.read_text(encoding="utf-8").splitlines() if l.strip()]
        last = json.loads(lines[-1]) if lines else None
    return {"state": st, "last_run": {k: last.get(k) for k in ("as_of", "status", "seconds", "error")} if last else None,
            "sources": LD.status()["first_seen"]}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "status"])
    ap.add_argument("--as-of")
    ap.add_argument("--skip-news", action="store_true")
    ap.add_argument("--no-promote", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--published", help="day the figures were checked online (default today)")
    a = ap.parse_args()
    if a.cmd == "run":
        print(json.dumps(run(a.as_of, a.skip_news, not a.no_promote, a.force, a.published), indent=1, default=str))
    else:
        print(json.dumps(status(), indent=1, default=str))
