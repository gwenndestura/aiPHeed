"""
app/news  (E28)
---------------
Quarterly news collection for the FSSI, rebuilt so that every province-quarter has an auditable collection record.

Why a new package. The E27 code collected news with fetchers that could not tell a failed request from an empty one
(both returned []), never detected when a source's result cap truncated a window, kept no record of which windows
were queried, and had no notion of an authorized limit or a forecast cutoff. The stored corpus therefore cannot be
audited per province-quarter, because the attempts were never recorded. This package keeps the project's approved
sources, query themes, credible-domain policy, geocoder, XLM-RoBERTa scorer and FSSI formula, and adds:

    sources.py    source adapters that return an explicit status (OK / EMPTY / FAILED / RATE_LIMITED / MALFORMED)
    store.py      an append-only, crash-tolerant store: articles, sightings, requests, window ledger, rejections, runs
    collector.py  the query plan, recursive window splitting at the source cap, authorization and cutoff gates,
                  idempotent backfill and active-quarter incremental collection
    scoring.py    XLM-RoBERTa scoring with a versioned score store and no silent keyword fallback
    fssi.py       province-quarter FSSI from the store with the existing fssi_builder / bias_weighter
    audit.py      the machine-readable province-quarter coverage audit
"""
