"""
Versioned source (credible-domain) policy (E29, decision D8).

v1 is the E28 baseline (rss_fetcher.CREDIBLE_DOMAINS + subdomains). v2 is a PROPOSED transparent rule (v1 + *.gov.ph +
outlets the project's own query bank targets). `config/source_policy.json` names the active version; it stays v1 until
D8 is answered. Every collected article and every FSSI manifest records the policy version that admitted it, so a
policy change never silently changes an earlier panel.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

POLICY_PATH = Path(__file__).resolve().parents[2] / "config" / "source_policy.json"


def load(path: Path | None = None) -> dict:
    return json.loads(Path(path or POLICY_PATH).read_text(encoding="utf-8"))


def _v1(domain: str) -> bool:
    from app.news.collector import _credible

    return _credible(domain)


def credible_fn(version: str | None = None, path: Path | None = None) -> Callable[[str], bool]:
    cfg = load(path)
    version = version or cfg["active"]
    v = cfg["versions"][version]
    adds = {a["domain"] for a in v.get("additions", [])}
    suffixes = tuple(v.get("suffix_rules", []))
    never = set(v.get("never", []))

    def fn(domain: str) -> bool:
        d = (domain or "").lower()
        if d in never:
            return False
        if _v1(d):
            return True
        parts = d.split(".")
        if any(".".join(parts[i:]) in adds for i in range(len(parts))):
            return True
        return bool(suffixes) and d.endswith(suffixes)

    fn.version = version  # type: ignore[attr-defined]
    return fn


def additions_only_fn(version: str, path: Path | None = None) -> Callable[[str], bool]:
    """True only for domains a version ADDS to v1 (used by the shadow pass that measures a proposed policy)."""
    full = credible_fn(version, path)
    return lambda d: full(d) and not _v1(d)
