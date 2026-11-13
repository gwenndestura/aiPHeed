"""
E151 quarterly news features, as of each issue date. Reads no outcome.

Every feature uses only stories published before the issue date, and topics from a BERTopic fitted before that date. The fixes against E150:
    window 3 months (rolling) instead of 12, with a 3-month lag version and a change between them
    streams at several geographic levels (province, area, CALABARZON, national, pooled), each story counted once
    event shares, not generic sentiment; problem and response reporting kept apart
    each outlet centred on its own earlier mean, so the shift from one outlet to many does not look like a change in conditions
    shrinkage toward the outlet norm when a stream has few stories

    python -m app.e151.features build -> data/e151/out/news_panel.parquet, news_monthly.csv, news_feature_audit.json
"""
from __future__ import annotations

import json
import re

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from app.e148 import panel as Pn
from app.e151 import OUT, RAW
from app.e151.corpus import NATIONAL_WORD
from app.e151.topics import EVENTS, GROUP, ORIGINS, event_probs

K = 5.0
# Topics removed by reading their keywords, applied to every fit: reasons in docs/e151. Written from the last fit's keyword list; no outcome was read.
IRRELEVANT = re.compile(r"cuisine|restaurant|festival|flood control|dpwh|arrested|police|president|duterte|marcos|robredo|aquino|vera files|fact check|\bfact\b|election|senator|stock|shares|airline|flight|movie|film", re.I)
# A topic LED by a weather hazard (one of its first three keywords) is about the hazard even when a tail keyword such as
# "flood control" matches the rule above. Fix 2026-11-11: at the 2026-10-01 origin the typhoon/flood topic carried
# "flood control" in its tail and was dropped (about half of all stories), unlike every earlier origin; no earlier topic changes.
HAZARD_LEAD = re.compile(r"\b(typhoon|super typhoon|storm|tropical storm|drought|el ni[nñ]o|monsoon|landslide)\b", re.I)


def off_topic(keywords: pd.Series) -> pd.Series:
    """Topics removed as off-topic: keyword rule IRRELEVANT, unless a weather hazard leads the keyword list."""
    k = keywords.fillna("")
    lead3 = k.map(lambda s: ", ".join(s.split(", ")[:3]))
    return k.str.contains(IRRELEVANT) & ~lead3.str.contains(HAZARD_LEAD)


GROUPS = ["market", "climate", "employment", "remittance", "poverty", "response"]
BASE_M = 36
MIN_SITE = 20
PH = re.compile(r"\b(Philippine|Philippines|Filipino|Filipinos|PH|Pinoy|Pilipino|Pilipinas|peso|pesos|P\d)\b")


def load_docs() -> pd.DataFrame:
    d = pd.read_parquet(RAW / "stories.parquet").merge(event_probs(), on="hash", how="inner")
    nat = d["geo_level"] == "national"
    ph = d["score_text"].str.contains(PH) | d["score_text"].str.contains(NATIONAL_WORD) | d["origin"].isin(["google_news_title"])
    d = d[~(nat & ~ph)].copy()                                                      # a national-level story must carry a Philippine signal
    d["eligible"] = d["pr_none"] < 0.5
    d = d[d["eligible"]].copy()
    d = d[~d.duplicated("story")].copy()                                            # one story, one count
    for g in GROUPS:
        d[f"v_{g}"] = d[[f"pr_{e}" for e, x in GROUP.items() if x == g]].sum(axis=1)
    d["v_hunger"] = d["pr_food_access"]
    d["v_net"] = d[[f"v_{g}" for g in GROUPS if g != "response"]].sum(axis=1) * d["problem"] - d["v_response"]
    return d.reset_index(drop=True)


def stream_table(d: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for j, r in enumerate(d[["geo_level", "provinces", "areas"]].itertuples(index=False)):
        rows.append((j, "all"))
        if r.geo_level == "national":
            rows.append((j, "nat"))
        if r.geo_level == "region_iva":
            rows.append((j, "reg:iva"))
        if r.geo_level in ("province", "lgu"):
            rows += [(j, "prov:" + k) for k in r.provinces.split("|") if k]
        if r.geo_level == "province_body_only":
            rows += [(j, "weak:" + k) for k in r.provinces.split("|") if k]
        if r.areas:
            rows += [(j, "area:" + a) for a in r.areas.split("|") if a]
    return pd.DataFrame(rows, columns=["j", "stream"])


def _window(d, st, i, lag_m, assign):
    cut = Pn.q_start(i)
    hi = cut - pd.DateOffset(months=lag_m)
    lo = hi - pd.DateOffset(months=3)
    base_lo = lo - pd.DateOffset(months=BASE_M)
    pub = d["published"]
    w = d[(pub >= lo) & (pub < hi)]
    b = d[(pub >= base_lo) & (pub < lo)]
    if not len(w) or len(b) < 50:
        return []
    org = [o for o in ORIGINS if pd.Timestamp(o) <= cut]
    tg, tid = assign.get(org[-1], (None, None)) if org else (None, None)
    vals = [f"v_{g}" for g in GROUPS] + ["v_hunger", "v_net"]
    glob = b[vals].mean()
    site = b.groupby("site")[vals].mean()[b.groupby("site")["id"].size() >= MIN_SITE]
    C = w[vals].copy()
    for c in vals:
        C[c] = w[c].values - w["site"].map(site[c]).fillna(glob[c]).values
    C["j"] = w.index
    C["site"] = w["site"].values
    t_share = {}
    if tg is not None:
        wg = w["id"].map(tg).values
        bg = b["id"].map(tg).values
        for g in GROUPS:
            C[f"t_{g}"] = (wg == g).astype(float) - float(np.mean(bg == g))
            t_share[g] = float(np.mean(bg == g))
        # emerging: a topic at least three times its share in the earlier base, with at least 3 stories in this window
        wt, bt = pd.Series(w["id"].map(tid).values), pd.Series(b["id"].map(tid).values)
        ws, bs = wt[wt >= 0].value_counts(), bt[bt >= 0].value_counts(normalize=True)
        emg = [t for t, n in ws.items() if n >= 3 and n / len(w) >= 3 * bs.get(t, 0.0)]
        C["emg"] = wt.isin(emg).astype(float).values
    S = st[st["j"].isin(w.index)].merge(C, on="j")
    Sb = st[st["j"].isin(b.index)].groupby("stream").size()
    rows = []
    for s, x in S.groupby("stream"):
        n = len(x)
        sh = n / (n + K)
        o = {"stream": s, "qi": i, "lag_m": lag_m, "n": n}
        for c in vals:
            o[f"e_{c[2:]}"] = float(x[c].mean()) * sh
        for g in GROUPS:
            if f"t_{g}" in x:
                o[f"tp_{g}"] = float(x[f"t_{g}"].mean()) * sh
        if "emg" in x:
            o["emerging"] = float(x["emg"].mean()) * sh
        o["intensity"] = float(np.log((n + 1) / (Sb.get(s, 0) * 3 / BASE_M + 1)))
        p = x["site"].value_counts(normalize=True).values
        o["diversity"] = float(np.exp(-np.sum(p * np.log(p))))
        rows.append(o)
    return rows


def target_panel() -> pd.DataFrame:
    """Upgrade 1: per-province readings of the sentences that name the province. Same 3-month window, 36-month base and shrinkage as the other streams."""
    p = RAW / "province_targets.parquet"
    if not p.exists():
        return pd.DataFrame()
    t = pd.read_parquet(p)
    L = t[["l_hard", "l_resp", "l_none"]].values
    pr = np.exp(L - L.max(axis=1, keepdims=True))
    pr = pr / pr.sum(axis=1, keepdims=True)
    t["hard"], t["resp"] = pr[:, 0], pr[:, 1]
    t = t.merge(pd.read_parquet(RAW / "stories.parquet", columns=["id", "published"]), on="id")
    rows = []
    for k, g in t.groupby("key"):
        for i in range(Pn.FIRST, Pn.LAST + 1):
            cut = Pn.q_start(i)
            for lag in (0, 3, 6):
                hi = cut - pd.DateOffset(months=lag)
                lo = hi - pd.DateOffset(months=3)
                w = g[(g["published"] >= lo) & (g["published"] < hi)]
                b = g[(g["published"] >= lo - pd.DateOffset(months=BASE_M)) & (g["published"] < lo)]
                n = len(w)
                if not n:
                    continue
                sh = n / (n + K)
                early = t[t["published"] < lo]
                bh, br = (b["hard"].mean(), b["resp"].mean()) if len(b) >= 5 else (early["hard"].mean(), early["resp"].mean()) if len(early) else (w["hard"].mean(), w["resp"].mean())
                rows.append({"stream": "prov:" + k, "qi": i, "lag_m": lag, "tg_n": n, "tg_hard": float(w["hard"].mean() - bh) * sh, "tg_resp": float(w["resp"].mean() - br) * sh, "tg_net": float((w["hard"].mean() - bh) - (w["resp"].mean() - br)) * sh})
    return pd.DataFrame(rows)


def build(without_top=False):
    d = load_docs()
    top = d["site"].value_counts()
    if without_top:
        d = d[d["site"] != top.index[0]].reset_index(drop=True)
    st = stream_table(d)
    assign = {}
    rep = pd.read_csv(OUT / "topic_report.csv")
    rep["irrelevant"] = off_topic(rep["keywords"])
    rep.to_csv(OUT / "topic_report.csv", index=False, lineterminator="\n")
    for o in ORIGINS:
        a = pd.read_parquet(RAW / f"topic_assign_{o}.parquet")
        drop = set(rep[(rep["origin"] == o) & rep["irrelevant"]]["topic"])
        a.loc[a["topic"].isin(drop), "t_group"] = None
        a = a.set_index("id")
        assign[o] = (a["t_group"].to_dict(), a["topic"].to_dict())
    jobs = [(i, lag) for i in range(Pn.FIRST, Pn.LAST + 1) for lag in (0, 3, 6)]
    res = Parallel(n_jobs=10)(delayed(_window)(d, st, i, lag, assign) for i, lag in jobs)
    P = pd.DataFrame([r for x in res for r in x])
    tp = target_panel()
    if len(tp):
        P = P.merge(tp, on=["stream", "qi", "lag_m"], how="left")
    if without_top:
        P.to_parquet(OUT / "news_panel_no_top_outlet.parquet", index=False)
        return
    P.to_parquet(OUT / "news_panel.parquet", index=False)
    # monthly relative frequency, national and pooled, for the report and construct checks; a description only
    m = d.assign(month=d["published"].dt.to_period("M").astype(str))
    M_ = m.groupby("month")[[f"v_{g}" for g in GROUPS] + ["v_hunger", "v_net"]].mean().join(m.groupby("month").size().rename("n"))
    for c in [f"v_{g}" for g in GROUPS]:
        M_[c + "_r3"] = M_[c].rolling(3).mean()
    M_.to_csv(OUT / "news_monthly.csv", lineterminator="\n")
    q = P[P["lag_m"] == 0]
    a = {"largest_outlet": {"site": top.index[0], "share": float(top.iloc[0] / len(d))}, "eligible_stories": int(len(d)), "panel_rows": int(len(P)), "streams": int(P["stream"].nunique()), "median_stories_per_quarter": {k: float(q[q["stream"].str.startswith(k)]["n"].median()) for k in ("all", "nat", "area:", "prov:", "reg:")},
         "calabarzon_median_stories_per_quarter": {k: float(q[q["stream"] == "prov:" + k]["n"].median()) if len(q[q["stream"] == "prov:" + k]) else 0 for k in ("batangas", "cavite", "laguna", "quezon", "rizal")},
         "quarters_covered_of_56": {k: int((q["stream"] == "prov:" + k).sum()) for k in ("batangas", "cavite", "laguna", "quezon", "rizal")}, "events": EVENTS,
         "share_of_eligible_with_problem_above_half": float((d["problem"] > 0.5).mean()), "mean_problem": float(d["problem"].mean()), "mean_plan": float(d["plan"].mean()), "mean_by_event": {e: float(d[f"pr_{e}"].mean()) for e in EVENTS}, "top_event_share": d[[f"pr_{e}" for e in EVENTS if e != "none"]].idxmax(axis=1).str[3:].value_counts(normalize=True).round(3).to_dict()}
    (OUT / "news_feature_audit.json").write_text(json.dumps(a, indent=1, default=float), newline="\n")
    print(json.dumps(a, indent=1, default=float))


if __name__ == "__main__":
    build()
    build(without_top=True)
