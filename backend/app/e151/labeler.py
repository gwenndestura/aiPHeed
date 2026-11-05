"""
E151 event labels after the label check (deviation D3). Reads no outcome. Runs in the backend venv.

Three readers of each story, each put on its own scale using stories published before the first forecast date (2015-01-01):
    nli      XLM-RoBERTa zero-shot logits
    sim      cosine between the story's multilingual embedding and a description of the event
    lex      seed phrases per event, in English and Filipino, title counted twice (the seed idea of Balashankar et al. 2023)

    python -m app.e151.labeler -> data/e151/raw/labels.parquet
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

from app.e151 import RAW

EV = ["food_access", "purchasing", "supply", "agri_loss", "income", "climate", "displacement", "ofw", "assistance", "recovery"]
REF_END = "2015-01-01"
LEX = {
    "food_access": r"hunger|hungry|gutom|nagugutom|starv\w*|malnutrition|malnourish\w*|undernourish\w*|stunt\w*|wasting|food insecur\w*|food security|feeding program|walang makain|no food|nutrition|community pantr\w*|food poverty",
    "purchasing": r"inflation|implasyon|price (hike|increase|spike|rise|surge)s?|prices? (rise|rose|rising|soar\w*|surge\w*|climb\w*|jump\w*|up)|high(er)? prices?|mahal|presyo|cost of living|afford\w*|wage|sahod|purchasing power|price cap|suggested retail|sugar price|rice price|gas prices?|fuel prices?|oil price",
    "supply": r"shortage\w*|kakulangan|hoard\w*|rice supply|food supply|supply of|buffer stock|imports?\b|importation|smuggl\w*|cartel|NFA|tariff\w*|rationing|food terminal",
    "agri_loss": r"crop damage|damage to agri\w*|agricultur\w* damage|agri damage|agri losses|crop loss\w*|farm loss\w*|palay|harvest|fish kill|red tide|African swine fever|\bASF\b|bird flu|avian|pests?\b|army ?worm|rice tungro|fisherfolk|mangingisda|fish catch|shrinking catch|livestock|poultry",
    "income": r"unemploy\w*|jobless|layoffs?|laid off|retrench\w*|job loss\w*|lost (their )?jobs?|livelihoods?|kabuhayan|poverty|kahirapan|mahirap|underemploy\w*|informal workers?|displaced workers?",
    "climate": r"typhoon|bagyo|tropical (storm|depression)|storm signal|signal no|landfall|PAGASA|floods?|flooding|baha|flash flood|landslide|drought|tagtuyot|el ni.o|la ni.a|monsoon|habagat|amihan|LPA|low pressure|storm surge|calamity|state of calamity|death toll",
    "displacement": r"displaced|evacuat\w*|evacuees?|bakwit|homeless|lost (their )?homes?|relocat\w*|bunkhouse|tents?\b|sheltered",
    "ofw": r"\bOFWs?\b|overseas Filipino\w*|remittance\w*|repatriat\w*|migrant workers?|deployment ban|POEA|OWWA|DMW\b|kasambahay|domestic helpers?",
    "assistance": r"food packs?|relief|ayuda|cash aid|cash assistance|financial assistance|subsid\w*|DSWD|4Ps|pantawid|donat\w*|distribut\w*|livelihood aid|aid to|P20 rice|rice program|Red Cross|volunteers|assistance|gift|fuel subsidy",
    "recovery": r"prices? (fell|fall|drop\w*|eas\w*|declin\w*)|inflation (eas\w*|slow\w*|fell|drop\w*|cool\w*)|recover\w*|rehabilit\w*|rebuild\w*|resilien\w*|back on its feet|surplus|bumper|output (rose|grew|up)|boost\w*",
}
OFFTOPIC = r"election|elections|candidate|campaign|senator\b.*\bsaid|vote[rs]?|rally|SONA|Binay|impeach\w*|\bPSEi\b|stocks?\b|stock market|peso\b.*\bdollar|airline|flights?|Cebu Pacific|Philippine Airlines|\bfilm\b|movie|concert|recipe|restaurant|bank\b|corruption|blue ribbon|dynast\w*|hero\b|anniversary|memorial"
FOREIGN = r"\b(Germany|German|Europe|EU|UK|Britain|British|Brexit|US|U\.S\.|United States|American[s]?|Biden|Trump|China|Chinese|Japan|Japanese|Korea|Indonesia|Vietnam|Thailand|India|Pakistan|Bangladesh|Ivory Coast|Africa|Turkey|Turkish|Iran|Iraq|Israel|Hamas|Gaza|OPEC|Somalia|Yemen|Sudan|Ukraine|Russia)\b"
PH = r"\b(Philippines?|Filipinos?|PH|Pinoy|Pilipin\w*|Manila|Luzon|Visayas|Mindanao|Duterte|Marcos|Aquino|DA\b|DSWD|DOLE|PAGASA|NDRRMC|Cebu|Davao|Tacloban|Batangas|Cavite|Laguna|Quezon|Rizal|OFWs?)\b"
RX = {k: re.compile(v, re.I) for k, v in LEX.items()}
RX_OFF, RX_FOR, RX_PH = re.compile(OFFTOPIC, re.I), re.compile(FOREIGN), re.compile(PH)
DESC = {"food_access": "families are going hungry, malnutrition, not enough food to eat", "purchasing": "food prices and inflation rise and households cannot afford food", "supply": "shortage of rice and food supply, imports, buffer stocks", "agri_loss": "crop damage, farm and fishery losses, harvest failure", "income": "job losses, unemployment, lost livelihoods and poverty", "climate": "typhoon, flood, drought, El Nino storm warning and damage", "displacement": "people displaced and evacuated from their homes", "ofw": "overseas Filipino workers, remittances, repatriation", "assistance": "government food aid, relief goods, cash assistance, subsidies", "recovery": "prices fall, supply improves, communities recover and rebuild", "offtopic": "politics, elections, stock market, business, airlines, entertainment and crime"}


def lex_scores(title: pd.Series, text: pd.Series) -> pd.DataFrame:
    o = {}
    for k, r in RX.items():
        o[k] = title.map(lambda s: 2 * len(r.findall(s or ""))) + text.map(lambda s: len(r.findall(s or "")))
    return pd.DataFrame(o).astype(float)


def build(sample_cols=False) -> pd.DataFrame:
    from sentence_transformers import SentenceTransformer
    d = pd.read_parquet(RAW / "stories.parquet", columns=["id", "story", "published", "title", "score_text", "hash", "geo_level"])
    E = np.load(RAW / "embeddings.npy")
    ev = pd.read_parquet(RAW / "events.parquet")
    ev = ev.drop_duplicates("hash").set_index("hash")
    ref = (d["published"] < REF_END).values
    nli = ev.reindex(d["hash"])[[f"l_{k}" for k in EV]].values
    nz = (nli - np.nanmean(nli[ref], axis=0)) / np.nanstd(nli[ref], axis=0)
    m = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2", device="cpu")
    D = m.encode([DESC[k] for k in EV + ["offtopic"]], normalize_embeddings=True)
    S = E @ D.T
    sz = (S - S[ref].mean(axis=0)) / S[ref].std(axis=0)
    L = lex_scores(d["title"], d["score_text"]).values
    lz = np.log1p(L)
    lz = (lz - lz[ref].mean(axis=0)) / lz[ref].std(axis=0)
    out = d[["id", "story", "hash", "published", "geo_level"]].copy()
    for j, k in enumerate(EV):
        out["nz_" + k], out["sz_" + k], out["lz_" + k] = nz[:, j], sz[:, j], lz[:, j]
        out["lx_" + k] = L[:, j]
    out["sz_offtopic"] = sz[:, len(EV)]
    out["off_lex"] = d["title"].map(lambda s: len(RX_OFF.findall(s or ""))).values
    out["for_lex"] = d["score_text"].map(lambda s: len(RX_FOR.findall((s or "")[:300]))).values
    out["ph_lex"] = d["score_text"].map(lambda s: len(RX_PH.findall((s or "")[:300]))).values
    rl = pd.read_parquet(RAW / "relevance.parquet").drop_duplicates("hash").set_index("hash")
    pr = ev.reindex(d["hash"])[["l_problem_now", "l_plan_or_warning"]].values
    w = (pr - np.nanmean(pr[ref], axis=0)) / np.nanstd(pr[ref], axis=0)
    out["z_problem"], out["z_plan"] = w[:, 0], w[:, 1]
    r = rl.reindex(d["hash"])[["l_offtopic", "l_foreign", "l_weather"]].values
    r = (r - np.nanmean(r[ref], axis=0)) / np.nanstd(r[ref], axis=0)
    out["z_offtopic"], out["z_foreign"], out["z_weather"] = r[:, 0], r[:, 1], r[:, 2]
    out.to_parquet(RAW / "labels_raw.parquet", index=False)
    return out


if __name__ == "__main__":
    print(build().shape)
