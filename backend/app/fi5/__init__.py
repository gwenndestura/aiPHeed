"""aiPHeed FI5: five-domain food insecurity forecasting system (Objectives 1-4).

Independent of FIRI v2. The outcome is SWS involuntary hunger (Balance Luzon, the SWS area that contains
CALABARZON); explanatory evidence is organised in exactly five domains (market and prices, climate stress,
employment, OFW remittances, poverty and social vulnerability), and news-derived signals sit inside the domain they
describe rather than in a separate news group.

Pipeline (each step caches its output under data/fi5):

    sources   raw government series + release-date rules -> one long vintage table
    nlp       XLM-RoBERTa zero-shot domain/stress labels -> BERTopic -> bias-corrected FSSI
    target    SWS quarterly hunger -> HIGH/LOW label (above the five-year average)
    features  as-of (release-date aware) five-domain feature rows for any issue date
    models    LightGBM + four baselines
    evaluate  walk-forward expanding-window evaluation per lead, audits, reliability
    rankings  142 city/municipality priority rankings
    explain   SHAP -> one or two plain-language sentences
    pipeline  CLI that runs everything and writes data/fi5/out
"""

VERSION = "fi5-1.0"
