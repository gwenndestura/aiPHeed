"""FI6-N processing: archive articles -> classified, geolocated, deduplicated events -> quarterly domain features.

    python -m app.fi6.news_events build      # parse, geo, flags, severity, XLM-R (cached), events, features, audits
    python -m app.fi6.news_events kit        # 200-article human annotation kit for the archive labels

Steps (each documented in docs/fi6/NEWS_INVESTIGATION.md):
  1. one row per (site, wp_id); text = title + lead (excerpt); publication date = the site's `date` (PHT)
  2. geography (rule-based gazetteer with namesake masks): geo_level lgu / province / region / national
  3. restated-statistic flag: reports of an official release the model already uses (CPI inflation, LFS
     unemployment, BSP remittances, PSA poverty) and reports of the SWS hunger survey itself (the outcome)
  4. severity: P damage (millions), hectares, families/persons affected or evacuated, workers laid off
  5. event type (transparent keyword rules per domain)
  6. XLM-R zero-shot (cached): five domains on gated articles; then direction (harder / easier for families to
     get enough food) and evidence type (hardship, disruption, warning, government response) on relevant ones
  7. events: same domain, cosine >= 0.85 within 10 days -> one event; independent sources counted
  8. quarterly features (as-of quarter end, z-scored on earlier quarters only by the feature builder)
"""
from __future__ import annotations

import argparse
import html
import json
import re

import numpy as np
import pandas as pd

from app.fi5.nlp import DOMAINS, EMBED_MODEL, GATE, XLMR_MODEL, _model_revision, _nli
from app.fi6.news_archive import RAW
from app.fi6.paths import FI6
from app.paths import BACKEND_DIR as BACKEND

NA = FI6 / "news_archive"
ARTICLES = NA / "articles.parquet"
SCORES = NA / "xlmr_scores_archive.parquet"
EVENTS = NA / "events.parquet"
FEATURES = NA / "news_features_quarterly.csv"
PROVINCE_SIGNAL = NA / "fssi_archive_province_quarter.csv"
AUDIT = NA / "audit.json"

TEMPLATE = "This news is about {}."
DOMAIN_LABELS = {"market": "food prices or food supply", "climate": "typhoons, floods or drought damaging crops",
                 "employment": "jobs or job losses", "remittance": "overseas Filipino workers or remittances",
                 "poverty": "poverty, hunger or food aid for families"}
STAGE2 = {"harder": "This news is about something that makes it harder for families to get enough food.",
          "easier": "This news is about something that makes it easier for families to get enough food.",
          "hardship": "This news reports families or people lacking food or going hungry.",
          "disruption": "This news reports damage or disruption that has already happened.",
          "warning": "This news warns of a possible future problem.",
          "response": "This news is about a government programme or assistance."}
REL_T = 0.30
LOCAL = ["lgu", "province", "region", "body_mention"]
# WordPress search matched the anchor somewhere in the article body: weaker evidence than a title/lead mention, kept
# as its own geo level ("body_mention") instead of being discarded or promoted.
ANCHOR_PROVINCE = {"Batangas": "Batangas", "Lipa": "Batangas", "Cavite": "Cavite", "Dasmarinas": "Cavite", "Bacoor": "Cavite",
                   "Imus": "Cavite", "Laguna": "Laguna", "Calamba": "Laguna", '"Los Banos"': "Laguna",
                   '"Quezon province"': "Quezon", "Lucena": "Quezon", "Tayabas": "Quezon", "Sariaya": "Quezon",
                   "Infanta": "Quezon", "Gumaca": "Quezon", "Mauban": "Quezon", '"Rizal province"': "Rizal",
                   "Antipolo": "Rizal", "Cainta": "Rizal", "CALABARZON": "", '"Southern Tagalog"': ""}
EVENT_COS, EVENT_DAYS = 0.85, 10

PROVINCE_RX = {
    "Batangas": r"\bbatangas\b", "Cavite": r"\bcavite\b", "Laguna": r"\blaguna\b(?! de bay)",
    "Quezon": r"\bquezon province\b|\bprovince of quezon\b|\blalawigan ng quezon\b|\bquezon,? (?:governor|gov\.|provincial)\b",
    "Rizal": r"\brizal province\b|\bprovince of rizal\b|\blalawigan ng rizal\b|\brizal,? (?:governor|gov\.|provincial)\b",
}
MASKS = r"quezon city|manuel (?:l\. )?quezon|quezon avenue|quezon ave|quezon memorial|quezon blvd|jose rizal|rizal park|rizal avenue|rizal memorial|rizal stadium|rizal technological|rizal medical"
REGION_RX = r"\bcalabarzon\b|\bsouthern tagalog\b|\bregion iv-?a\b|\bregion 4-?a\b|\blaguna de bay\b|\blaguna lake\b"
AMBIGUOUS_LGU = {"san juan", "san pablo", "santa rosa", "santa cruz", "san jose", "san mateo", "rosario", "mabini",
                 "taytay", "lemery", "san luis", "san nicolas", "santo tomas", "tanauan", "alaminos", "victoria",
                 "infanta", "general luna", "padre burgos", "plaridel", "buenavista", "candelaria", "dolores",
                 "san antonio", "san andres", "quezon", "pila", "bay", "real", "lopez", "perez", "mendez", "laurel",
                 "teresa", "rodriguez", "magdalena", "alfonso", "famy", "morong", "baras", "talisay", "balete",
                 "san pascual", "kalayaan", "santa maria", "sampaloc", "magallanes", "cuenca", "pagsanjan", "calauan",
                 "liliw", "silang", "naic", "tanza", "general trias", "carmona", "agdangan", "unisan", "pitogo",
                 "jomalig", "luisiana", "majayjay", "nagcarlan", "ibaan", "lobo", "taysan", "tuy", "lian", "indang",
                 "amadeo", "ternate", "noveleta", "kawit", "rizal", "malvar", "taal", "bauan", "calaca", "balayan",
                 "nasugbu", "catanauan", "mulanay", "atimonan", "macalelon", "polillo", "burdeos", "panukulan",
                 "patnanungan", "guinayangan", "calauag", "tagkawayan", "tiaong", "lucban", "general nakar", "paete",
                 "pakil", "pangil", "mabitac", "siniloan", "cardona", "pililla", "jalajala", "tanay", "angono"}
RESTATED = {
    "cpi_release": r"\binflation\b.*\b(rate|eases|slows|accelerat|quicken|steady|rises|hits|at \d)|\b(psa|pso)\b.*\binflation\b|inflation.{0,25}\d+(\.\d+)?%",
    "lfs_release": r"\bunemployment rate\b|\bjobless rate\b|\blabor force survey\b",
    "bsp_remittance_release": r"\b(cash|personal|ofw) remittances?\b.*\b(grew|rose|fell|up|down|hit|reach|record|growth|slow|steady)\b|\bbsp\b.*\bremittance|remittance(s)? growth|remittances?.{0,40}\d+(\.\d+)?%|remittances? (reach|hit|up|rise|climb)",
    "psa_poverty_release": r"\bpoverty (incidence|rate|threshold)\b|\bpsa\b.*\bpoor\b",
    "sws_hunger_release": r"\bsws\b|social weather|self-rated (poverty|hunger)|\bhunger (rate|incidence)\b.*\bsurvey\b",
}
EVENT_RULES = {
    "market": {"price_increase": r"price.{0,20}\b(hike|increase|up|soar|spike|surge|jump|rise|rising|higher)|tumaas|taas.presyo|mahal",
               "shortage": r"shortage|kakulangan|scarc|hoard|supply (gap|problem|crunch)",
               "price_decrease": r"price.{0,20}\b(drop|fall|down|lower|cut|decline|stabili)|bumaba|rollback",
               "import_supply": r"\bimport|\bnfa\b|buffer stock|supply"},
    "climate": {"typhoon": r"typhoon|bagyo|storm|signal no", "flood": r"flood|baha|lubog|monsoon|habagat",
                "drought": r"drought|el ni[nñ]o|tagtuyot|dry spell|water shortage", "crop_damage": r"crop|palay|farm|agri|damage|pinsala|losses",
                "fisheries": r"fish|isda|fisher|mangingisda|fish kill"},
    "employment": {"layoff_closure": r"layoff|laid off|retrench|closure|shut ?down|tanggal|nawalan ng trabaho|job loss",
                   "livelihood_loss": r"livelihood|kabuhayan|income loss|stranded|no work",
                   "job_recovery": r"job fair|hiring|jobs created|employment (rise|up|recover)"},
    "remittance": {"repatriation_displacement": r"repatriat|stranded ofw|displaced|evacuat|war|conflict|crisis",
                   "deployment_ban": r"deployment ban|ban on deployment|moratorium",
                   "remittance_change": r"remittance"},
    "poverty": {"hunger_report": r"hunger|hungry|gutom|nagugutom|malnutrition|malnourished|wasting|stunting|walang makain",
                "displacement": r"evacuat|displaced|lumikas|homeless|nawalan ng tirahan",
                "assistance": r"relief|food packs?|ayuda|assistance|4ps|pantawid|feeding|cash aid|dswd"},
}
PESO_RX = re.compile(r"(?:₱|php|p)\s?(\d+(?:[.,]\d+)?)\s?-?\s?(billion|bilyon|million|milyon|b\b|m\b)", re.I)
FAM_RX = re.compile(r"(\d[\d,]{0,9})\s+(families|households|individuals|persons|residents|pamilya)\b", re.I)
HA_RX = re.compile(r"(\d[\d,]{0,9}(?:\.\d+)?)\s*(hectares|ha)\b", re.I)


# Not event reporting: multi-story roundups (mention every province in passing), and non-news sections.
EXCLUDE_TITLE = re.compile(r"(?:newscast|news ?round-?up|top stories|rappler talk|\[podcast\]|^in photos|quiz|horoscope|"
                           r"lotto result|recipe|(?:movie|film|book|album|music) review|^review:|"
                           r"newsbreak:? (?:morning|evening) brief|what you need to know today)", re.I)
EXCLUDE_PATH = re.compile(r"/(?:sports|entertainment|life-and-style|lifestyle|movies|music|technology|tech|quiz|celebrities|"
                          r"showbiz|travel|food-drink|food|culture|culture-desk|the-wrap|video|books|arts|fashion|hustle|brandrap|bulletin-board)/", re.I)


def clean(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", html.unescape(s or ""))
    return re.sub(r"\s+", " ", s).replace("[…]", "").replace("[&hellip;]", "").strip()


def load_raw() -> pd.DataFrame:
    rows = []
    for f in sorted(RAW.glob("*.jsonl")):
        with open(f, encoding="utf-8") as fh:
            rows += [json.loads(l) for l in fh if l.strip()]
    d = pd.DataFrame(rows)
    q = d.groupby(["site", "wp_id"])["query"].apply(lambda x: "|".join(sorted(set(x)))).rename("queries")
    d = d.drop_duplicates(["site", "wp_id"]).merge(q, on=["site", "wp_id"])
    d["title"] = d["title"].map(clean)
    d["lead"] = d["excerpt"].map(clean).str.slice(0, 600)
    d["published"] = pd.to_datetime(d["date"], errors="coerce")
    d["modified"] = pd.to_datetime(d["modified"], errors="coerce")
    d["retrieved"] = pd.to_datetime(d["retrieved_utc"], errors="coerce").dt.tz_localize(None)
    d = d.dropna(subset=["published"])
    d["quarter"] = d["published"].dt.to_period("Q").astype(str).str.replace("Q", "-Q")
    d["text"] = (d["title"] + ". " + d["lead"]).str.slice(0, 700)
    d["excluded"] = d["title"].str.contains(EXCLUDE_TITLE) | d["link"].fillna("").str.contains(EXCLUDE_PATH)
    return d.drop(columns=["excerpt", "date"]).reset_index(drop=True)


def geo(text: str, lgus: pd.DataFrame) -> dict:
    t = re.sub(MASKS, " ", text.lower())
    provs = {p for p, rx in PROVINCE_RX.items() if re.search(rx, t)}
    lgu_hits = []
    for name, prov in zip(lgus["n"], lgus["province_name"]):
        if re.search(rf"\b{re.escape(name)}\b", t):
            if name not in AMBIGUOUS_LGU or prov in provs:
                lgu_hits.append(name)
                provs.add(prov)
    region = bool(re.search(REGION_RX, t))
    level = "lgu" if lgu_hits else ("province" if provs else ("region" if region else "national"))
    return {"geo_level": level, "provinces": "|".join(sorted(provs)), "lgus": "|".join(sorted(set(lgu_hits)))}


def flags(text: str) -> dict:
    t = text.lower()
    out = {f"restates_{k}": bool(re.search(rx, t)) for k, rx in RESTATED.items()}
    out["restated_statistic"] = any(out.values())
    for d, rules in EVENT_RULES.items():
        hits = [k for k, rx in rules.items() if re.search(rx, t)]
        out[f"etype_{d}"] = hits[0] if hits else ""
    pesos = 0.0
    for v, u in PESO_RX.findall(text):
        x = float(v.replace(",", ""))
        pesos += x * (1000 if u.lower().startswith(("b", "bil")) else 1)
    out["damage_pmillion"] = pesos if re.search(r"damage|loss|pinsala|lugi", t) else 0.0
    out["families_affected"] = float(sum(float(v.replace(",", "")) for v, w in FAM_RX.findall(text)
                                         if re.search(r"affect|evacuat|displac|lumikas|apektado", t)))
    out["hectares"] = float(sum(float(v.replace(",", "")) for v, _ in HA_RX.findall(text)))
    return out


def score(texts: pd.Series) -> pd.DataFrame:
    """XLM-R zero-shot on title + lead, cached by text hash."""
    import hashlib

    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    keys = texts.map(lambda s: hashlib.sha1(s.encode("utf-8")).hexdigest())
    have = _cache()
    todo = pd.DataFrame({"key": keys, "text": texts}).drop_duplicates("key")
    todo = todo[~todo["key"].isin(set(have["key"]))].reset_index(drop=True)
    if len(todo):
        torch.set_num_threads(20)
        tok = AutoTokenizer.from_pretrained(XLMR_MODEL)
        model = AutoModelForSequenceClassification.from_pretrained(XLMR_MODEL).eval()
        rev = _model_revision()
        parts = [have] if len(have) else []
        for i in range(0, len(todo), 400):
            c = todo.iloc[i:i + 400].reset_index(drop=True)
            prem = [t for t in c["text"] for _ in DOMAINS]
            hyp = [TEMPLATE.format(DOMAIN_LABELS[d]) for _ in c["text"] for d in DOMAINS]
            p1 = _nli(tok, model, prem, hyp).reshape(len(c), len(DOMAINS))
            res = pd.DataFrame(p1, columns=[f"p_{d}" for d in DOMAINS])
            res.insert(0, "key", c["key"])
            for h in STAGE2:
                res[f"p_{h}"] = np.nan
            rel = np.where(p1.max(axis=1) >= REL_T)[0]
            if len(rel):
                prem = [c.at[k, "text"] for k in rel for _ in STAGE2]
                hyp = [STAGE2[h] for _ in rel for h in STAGE2]
                p2 = _nli(tok, model, prem, hyp).reshape(len(rel), len(STAGE2))
                for j, h in enumerate(STAGE2):
                    res.loc[rel, f"p_{h}"] = p2[:, j]
            res["model_rev"] = rev
            parts.append(res)
            pd.concat(parts, ignore_index=True).to_parquet(SCORES, index=False)
            print(f"xlmr archive {min(i + 400, len(todo))}/{len(todo)}", flush=True)
        have = pd.concat(parts, ignore_index=True)
    return pd.DataFrame({"key": keys}).merge(have, on="key", how="left")


def build_events(a: pd.DataFrame) -> pd.DataFrame:
    from sentence_transformers import SentenceTransformer

    rel = a[a["relevant"]].sort_values("published").reset_index(drop=True)
    emb = SentenceTransformer(EMBED_MODEL, device="cpu").encode(rel["text"].tolist(), batch_size=128, normalize_embeddings=True)
    days = rel["published"].values.astype("datetime64[D]").astype(np.int64)
    dom = rel[[f"is_{d}" for d in DOMAINS]].to_numpy()
    ev = np.full(len(rel), -1)
    for i in range(len(rel)):
        w = np.where((days >= days[i] - EVENT_DAYS) & (np.arange(len(rel)) < i))[0]
        if len(w):
            s = emb[w] @ emb[i]
            ok = w[(s >= EVENT_COS) & (dom[w] & dom[i]).any(axis=1)]
            if len(ok):
                ev[i] = ev[ok[np.argmax(emb[ok] @ emb[i])]]
                continue
        ev[i] = i
    rel["event_id"] = ev
    rel["n_sources_event"] = rel.groupby("event_id")["site"].transform("nunique")
    return rel


def quarterly_features(a: pd.DataFrame, rel: pd.DataFrame) -> pd.DataFrame:
    """Per quarter: risk-event shares per domain (coverage-normalised), climate damage, displaced families."""
    usable = rel[~rel["restated_statistic"]]
    harder = usable["p_harder"].fillna(0) > usable["p_easier"].fillna(0)
    rows = []
    a_local = a[a["geo_level"].isin(LOCAL)]
    for q in sorted(a["quarter"].unique()):
        denom_local = int(a_local[a_local["quarter"] == q].drop_duplicates(["site", "wp_id"]).shape[0])
        denom_all = int(a[a["quarter"] == q].shape[0])
        r = {"quarter": q, "articles_all": denom_all, "articles_calabarzon": denom_local,
             "sites": int(a[a["quarter"] == q]["site"].nunique())}
        uq = usable[usable["quarter"] == q]
        hq = harder[usable["quarter"] == q]
        for d in DOMAINS:
            scope = uq["geo_level"].isin(LOCAL) if d not in ("remittance", "market") else \
                pd.Series(True, index=uq.index)
            e = uq[scope & uq[f"is_{d}"] & hq]
            n_ev = e["event_id"].nunique()
            den = denom_all if d in ("remittance", "market") else denom_local
            r[f"events_{d}"] = int(n_ev)
            r[f"risk_share_{d}"] = n_ev / den if den >= 30 else np.nan
        loc = rel[(rel["quarter"] == q) & rel["geo_level"].isin(LOCAL)].drop_duplicates("event_id")
        r["climate_damage_log"] = float(np.log1p(loc[loc["is_climate"]]["damage_pmillion"].sum())) if denom_local >= 30 else np.nan
        r["displaced_families_log"] = float(np.log1p(loc["families_affected"].sum())) if denom_local >= 30 else np.nan
        r["hardship_events"] = int(loc[loc["p_hardship"].fillna(0) >= 0.9]["event_id"].nunique())
        rows.append(r)
    return pd.DataFrame(rows)


def province_signal(a: pd.DataFrame, rel: pd.DataFrame, k: float = 10.0) -> pd.DataFrame:
    """Objective 1 output: per province-quarter risk-event share (shrunk toward the region for thin cells)."""
    rows = []
    usable = rel[~rel["restated_statistic"] & (rel["p_harder"].fillna(0) > rel["p_easier"].fillna(0))]
    for q in sorted(a["quarter"].unique()):
        reg_den = max(int(a[(a["quarter"] == q) & (a["geo_level"] != "national")].shape[0]), 1)
        reg = usable[(usable["quarter"] == q) & (usable["geo_level"] != "national")]["event_id"].nunique() / reg_den
        for p in PROVINCE_RX:
            den = int(a[(a["quarter"] == q) & a["provinces"].str.contains(p)].shape[0])
            n = usable[(usable["quarter"] == q) & usable["provinces"].str.contains(p)]["event_id"].nunique()
            lam = den / (den + k)
            rows.append({"quarter": q, "province": p, "articles": den, "risk_events": int(n),
                         "risk_share_raw": n / den if den else np.nan, "risk_share_corrected": lam * (n / den if den else 0) + (1 - lam) * reg,
                         "shrink_weight": lam})
    return pd.DataFrame(rows)


TODO = NA / "to_score.parquet"
OV_MODEL = BACKEND / "models_ov" / "xlmr_large_xnli"


def _cache() -> pd.DataFrame:
    files = [f for f in [SCORES, *sorted(NA.glob("xlmr_scores_archive_part_*.parquet"))] if f.exists()]
    return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True).drop_duplicates("key") if files else \
        pd.DataFrame(columns=["key"])


def _ov_nli(cm, tok, prem: list[str], hyp: list[str], batch: int = 32) -> np.ndarray:
    """OpenVINO (Intel Arc iGPU) NLI, fp32: identical to the PyTorch CPU result (checked 2026-11-02, max diff 0.0000)."""
    ids = tok(prem, hyp, truncation=True, max_length=96)
    order = np.argsort([len(x) for x in ids["input_ids"]], kind="stable")
    out = np.empty(len(prem))
    for j in range(0, len(order), batch):
        idx = order[j:j + batch]
        b = tok.pad({"input_ids": [ids["input_ids"][i] for i in idx], "attention_mask": [ids["attention_mask"][i] for i in idx]},
                    return_tensors="np")
        lg = cm({"input_ids": b["input_ids"], "attention_mask": b["attention_mask"]})[0][:, [0, 2]]
        e = np.exp(lg - lg.max(1, keepdims=True))
        out[idx] = (e / e.sum(1, keepdims=True))[:, 1]
    return out


def score_worker(part: tuple[float, float], backend: str = "torch", threads: int | None = None):
    """Score a fixed slice of the not-yet-scored texts. backend: torch (CPU) or openvino-GPU (Arc iGPU)."""
    todo = pd.read_parquet(TODO)
    have = set(_cache()["key"])
    todo = todo[~todo["key"].isin(have)].sort_values("key").reset_index(drop=True)
    todo = todo.iloc[int(round(part[0] * len(todo))):int(round(part[1] * len(todo)))].reset_index(drop=True)
    target = NA / f"xlmr_scores_archive_part_{backend}_{part[0]:.2f}_{part[1]:.2f}.parquet"
    parts = [pd.read_parquet(target)] if target.exists() else []
    if backend == "torch":
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        torch.set_num_threads(threads or 18)
        tok = AutoTokenizer.from_pretrained(XLMR_MODEL)
        model = AutoModelForSequenceClassification.from_pretrained(XLMR_MODEL).eval()
        nli = lambda p, h: _nli(tok, model, p, h)
        rev = _model_revision()
    else:
        import openvino as ov
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained(str(OV_MODEL))
        cm = ov.Core().compile_model(str(OV_MODEL / "openvino_model.xml"), backend.split("-")[1], {"INFERENCE_PRECISION_HINT": "f32"})
        nli = lambda p, h: _ov_nli(cm, tok, p, h)
        rev = "openvino-export-of-" + XLMR_MODEL
    for i in range(0, len(todo), 200):
        c = todo.iloc[i:i + 200].reset_index(drop=True)
        p1 = nli([t for t in c["text"] for _ in DOMAINS], [TEMPLATE.format(DOMAIN_LABELS[d]) for _ in c["text"] for d in DOMAINS])
        p1 = p1.reshape(len(c), len(DOMAINS))
        res = pd.DataFrame(p1, columns=[f"p_{d}" for d in DOMAINS])
        res.insert(0, "key", c["key"])
        for h in STAGE2:
            res[f"p_{h}"] = np.nan
        rel = np.where(p1.max(axis=1) >= REL_T)[0]
        if len(rel):
            p2 = nli([c.at[k, "text"] for k in rel for _ in STAGE2], [STAGE2[h] for _ in rel for h in STAGE2]).reshape(len(rel), len(STAGE2))
            for j, h in enumerate(STAGE2):
                res.loc[rel, f"p_{h}"] = p2[:, j]
        res["model_rev"] = rev
        parts.append(res)
        pd.concat(parts, ignore_index=True).to_parquet(target, index=False)
        print(f"[{backend} {part}] {min(i + 200, len(todo))}/{len(todo)}", flush=True)


def prepare() -> pd.DataFrame:
    a, _ = _prepared()
    import hashlib
    t = a.loc[a["to_score"], ["text"]].copy()
    t["key"] = t["text"].map(lambda s: hashlib.sha1(s.encode("utf-8")).hexdigest())
    t.drop_duplicates("key").to_parquet(TODO, index=False)
    return t


def _prepared():
    from app.fi5.paths import LGU_REFERENCE

    raw = load_raw()
    excluded = raw[raw["excluded"]]
    a = raw[~raw["excluded"]].reset_index(drop=True)
    lg = pd.read_csv(LGU_REFERENCE)
    lg["n"] = lg["lgu_name"].str.lower().str.replace("ñ", "n").str.replace(" city", "", regex=False)
    lg = lg[lg["n"].str.len() >= 4]
    textn = a["text"].str.replace("ñ", "n").str.replace("Ñ", "N")
    g = pd.DataFrame([geo(t, lg) for t in textn])
    f = pd.DataFrame([flags(t) for t in a["text"]])
    a = pd.concat([a, g, f], axis=1)
    anchored = a["queries"].map(lambda qs: sorted({ANCHOR_PROVINCE[q] for q in qs.split("|") if q in ANCHOR_PROVINCE}))
    bm = (a["geo_level"] == "national") & anchored.map(len).gt(0)
    a.loc[bm, "geo_level"] = "body_mention"
    a.loc[bm, "provinces"] = anchored[bm].map(lambda x: "|".join(p for p in x if p))
    a["gate"] = a["text"].map(lambda s: bool(GATE.search(s)))
    # score only what can matter: gated and (CALABARZON-located, or national driver queries)
    a["to_score"] = a["gate"] & ((a["geo_level"] != "national") | a["queries"].str.contains(
        "OFW|remittances|repatriation|deployment ban|rice|food prices|layoffs|retrenchment|El Nino|damage|hunger|malnutrition|gutom|bigas"))
    return a, excluded


def build() -> dict:
    a, excluded = _prepared()
    sc = score(a.loc[a["to_score"], "text"])
    sc.index = a.index[a["to_score"]]
    for c in [c for c in sc.columns if c.startswith("p_")]:
        a[c] = sc[c]
    for d in DOMAINS:
        a[f"p_{d}"] = a[f"p_{d}"].fillna(0.0)
        a[f"is_{d}"] = a[f"p_{d}"] >= REL_T
    a["relevant"] = a[[f"is_{d}" for d in DOMAINS]].any(axis=1)
    a["evidence"] = np.select([~a["relevant"], a["p_hardship"] >= 0.9, a["p_response"] >= 0.5,
                               a["p_disruption"] >= 0.5, a["p_warning"] >= 0.5], ["irrelevant", "observed_hardship",
                              "government_response", "ongoing_disruption", "potential_risk"], "background")
    a["direction"] = np.where(~a["relevant"], "n/a", np.where(a["p_harder"] - a["p_easier"] > 0.2, "increases_risk",
                              np.where(a["p_easier"] - a["p_harder"] > 0.2, "reduces_risk", "unclear")))
    rel = build_events(a)
    a = a.merge(rel[["site", "wp_id", "event_id", "n_sources_event"]], on=["site", "wp_id"], how="left")
    keep = [c for c in a.columns if c not in ("text",)]
    a[keep].to_parquet(ARTICLES, index=False)
    rel.drop(columns=["text"]).to_parquet(EVENTS, index=False)
    feats = quarterly_features(a, rel)
    feats.to_csv(FEATURES, index=False, lineterminator="\n")
    province_signal(a, rel).to_csv(PROVINCE_SIGNAL, index=False, lineterminator="\n")
    audit = {
        "articles": int(len(a)), "excluded_roundups_and_non_news_sections": int(len(excluded)),
        "by_site": a["site"].value_counts().to_dict(),
        "first_published": str(a["published"].min().date()), "last_published": str(a["published"].max().date()),
        "published_after_retrieval": int((a["published"] > a["retrieved"] + pd.Timedelta(days=1)).sum()),
        "modified_differs_share": float((a["modified"].dt.date != a["published"].dt.date).mean()),
        "geo_level": a["geo_level"].value_counts().to_dict(), "gated": int(a["gate"].sum()), "scored": int(a["to_score"].sum()),
        "relevant": int(a["relevant"].sum()), "events": int(rel["event_id"].nunique()),
        "multi_source_events": int((rel.drop_duplicates("event_id")["n_sources_event"] > 1).sum()),
        "restated_statistic_articles": int(a["restated_statistic"].sum()),
        "restated_by_type": {k: int(a[f"restates_{k}"].sum()) for k in RESTATED},
        "domain_counts": {d: int(a[f"is_{d}"].sum()) for d in DOMAINS},
        "evidence": a["evidence"].value_counts().to_dict(), "direction": a["direction"].value_counts().to_dict(),
        "quarters_with_feature": {d: int(feats[f"risk_share_{d}"].notna().sum()) for d in DOMAINS},
    }
    AUDIT.write_text(json.dumps(audit, indent=1, default=str))
    return audit


def kit(n: int = 200, seed: int = 20261103) -> pd.DataFrame:
    a = pd.read_parquet(ARTICLES)
    a = a[a["to_score"]]
    parts = [a[a[f"is_{d}"]].sample(min(25, int(a[f"is_{d}"].sum())), random_state=seed) for d in DOMAINS]
    parts.append(a[~a["relevant"]].sample(min(40, int((~a["relevant"]).sum())), random_state=seed))
    s = pd.concat(parts).drop_duplicates(["site", "wp_id"])
    s = pd.concat([s, a.drop(s.index).sample(max(0, n - len(s)), random_state=seed)]).sample(frac=1, random_state=seed).head(n)
    s.insert(0, "item", np.arange(1, len(s) + 1))
    sheet = s[["item", "published", "site", "title", "lead", "link"]].copy()
    for c in ["relevant(0/1)", *[f"{d}(0/1)" for d in DOMAINS], "event_type(free text)", "direction(increases/reduces/unclear)",
              "evidence(risk/disruption/hardship/response/background)", "province(s) affected", "restates_official_statistic(0/1)"]:
        sheet[c] = ""
    out = FI6 / "nlp_validation"
    sheet.to_csv(out / "archive_annotation_sheet.csv", index=False, encoding="utf-8-sig", lineterminator="\n")
    s[["item", "site", "wp_id", "relevant", "evidence", "direction", "geo_level", "provinces", "restated_statistic",
       *[f"is_{d}" for d in DOMAINS], *[f"etype_{d}" for d in DOMAINS]]].to_csv(out / "archive_model_key.csv", index=False, lineterminator="\n")
    return sheet


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["prepare", "worker", "build", "kit"])
    ap.add_argument("--part", default="0:1")
    ap.add_argument("--backend", default="torch", help="torch (CPU) or openvino-GPU (Intel Arc iGPU)")
    ap.add_argument("--threads", type=int, default=None)
    a = ap.parse_args()
    if a.cmd == "prepare":
        print(len(prepare()), "texts to score")
    elif a.cmd == "worker":
        lo, hi = (float(x) for x in a.part.split(":"))
        score_worker((lo, hi), a.backend, a.threads)
    else:
        print(json.dumps(build(), indent=1, default=str) if a.cmd == "build" else kit().shape)
