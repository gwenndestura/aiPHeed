"""
Temporal alignment of news evidence (E31): which articles may support a FORECAST and which a NOWCAST.

Policy (testable; every prediction record carries the window it used):

  FORECAST of target quarter T at lead k (k >= 1)
      evidence quarter E = T - k (lead 1: the quarter immediately before T, the study's 3-month lead time);
      eligible = articles whose Philippine publication time lies in E AND is on or before the information cutoff;
      the cutoff must not be later than the start of T (a forecast is made before its target begins). A cutoff
      inside E gives a PARTIAL evidence window, which is labelled as such.

  NOWCAST of target quarter T (lead 0; T under way or ended)
      evidence quarter E = T itself;
      eligible = articles published in T on or before the nowcast cutoff (for example 2026-10-10 23:59:59 PHT);
      the cutoff must be at or after the start of T. The previous quarter's news is never used as a stand-in.

  Both modes: nothing published after the cutoff, nothing outside E, nothing before the study window, nothing after
  the authorized limit. A violation raises AlignmentViolation; it is never silently filtered at prediction time.

Limitation recorded in every window: publication time is the publisher's date. The time an article became
retrievable through the search index is unknown for historical quarters (articles may have been indexed later), so a
historical replay can only enforce publication time, not retrieval time.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta

from app.news.timeutil import PH, parse_quarter, ph_midnight, quarter_end_excl, quarter_start, to_ph

STUDY_START = ph_midnight(date(2021, 1, 1))
MODES = ("forecast", "nowcast")


class AlignmentViolation(ValueError):
    pass


def shift_quarter(q: str, k: int) -> str:
    y, n = parse_quarter(q)
    i = y * 4 + (n - 1) + k
    return f"{i // 4}-Q{i % 4 + 1}"


@dataclass(frozen=True)
class EvidenceWindow:
    mode: str
    target_quarter: str
    lead: int
    evidence_quarter: str
    window_start_ph: str
    window_end_excl_ph: str       # min(end of evidence quarter, cutoff + 1 second)
    information_cutoff_ph: str
    coverage: str                 # FULL (the whole evidence quarter) or PARTIAL (cutoff inside it)
    days_covered: int
    days_in_quarter: int
    limitation: str = ("publication time enforced; historical search-index retrieval time unknown")

    def to_dict(self) -> dict:
        return asdict(self)


def _parse_cutoff(cutoff) -> datetime:
    """A cutoff is an instant (second resolution). A bare date (date object or 'YYYY-MM-DD') means the end of that
    Philippine calendar day, 23:59:59."""
    if isinstance(cutoff, str):
        cutoff = date.fromisoformat(cutoff) if len(cutoff) == 10 else datetime.fromisoformat(cutoff)
    if isinstance(cutoff, date) and not isinstance(cutoff, datetime):
        cutoff = ph_midnight(cutoff) + timedelta(days=1) - timedelta(seconds=1)
    return to_ph(cutoff).replace(microsecond=0)


def evidence_window(target_quarter: str, mode: str, cutoff, lead: int | None = None,
                    authorized_limit_excl: datetime | None = None) -> EvidenceWindow:
    """The news evidence window for one prediction. lead defaults to 1 (forecast) or 0 (nowcast)."""
    if mode not in MODES:
        raise AlignmentViolation(f"unknown mode {mode!r}")
    c = _parse_cutoff(cutoff)
    t_start = ph_midnight(quarter_start(target_quarter))
    t_end = ph_midnight(quarter_end_excl(target_quarter))
    if mode == "forecast":
        k = 1 if lead is None else int(lead)
        if k < 1:
            raise AlignmentViolation("a forecast needs lead >= 1; lead 0 is a nowcast")
        if c > t_start:
            raise AlignmentViolation(f"forecast cutoff {c.isoformat()} is after the start of target {target_quarter} "
                                     f"({t_start.isoformat()}): that would use target-quarter information")
        e = shift_quarter(target_quarter, -k)
    else:
        k = 0 if lead is None else int(lead)
        if k != 0:
            raise AlignmentViolation("a nowcast has lead 0")
        if c < t_start:
            raise AlignmentViolation(f"nowcast cutoff {c.isoformat()} is before target {target_quarter} starts: "
                                     f"there is no same-quarter news yet; issue a forecast instead")
        e = target_quarter
    e_start = ph_midnight(quarter_start(e))
    e_end = ph_midnight(quarter_end_excl(e))
    if e_start < STUDY_START:
        raise AlignmentViolation(f"evidence quarter {e} is before the study window (2021-Q1)")
    if c < e_start:
        raise AlignmentViolation(f"cutoff {c.isoformat()} precedes the evidence quarter {e}")
    end = min(e_end, c + timedelta(seconds=1))
    if authorized_limit_excl is not None:
        end = min(end, to_ph(authorized_limit_excl))
    days_q = (e_end - e_start).days
    days_c = min(days_q, int(-(-(end - e_start).total_seconds() // 86400)))   # days touched by the window
    return EvidenceWindow(mode=mode, target_quarter=target_quarter, lead=k, evidence_quarter=e,
                          window_start_ph=e_start.isoformat(), window_end_excl_ph=end.isoformat(),
                          information_cutoff_ph=c.isoformat(), coverage="FULL" if end >= e_end else "PARTIAL",
                          days_covered=days_c, days_in_quarter=days_q)


def _pub(a: dict) -> datetime:
    return to_ph(datetime.fromisoformat(a["published_ph"]))


def is_eligible(a: dict, w: EvidenceWindow) -> bool:
    p = _pub(a)
    return (a.get("quarter") == w.evidence_quarter
            and datetime.fromisoformat(w.window_start_ph) <= p < datetime.fromisoformat(w.window_end_excl_ph)
            and p <= datetime.fromisoformat(w.information_cutoff_ph))


def select(articles, w: EvidenceWindow) -> tuple[list[dict], dict]:
    """Eligible articles for the window, with a count of every reason the others were left out."""
    out, why = [], {"other_quarter": 0, "after_cutoff": 0, "eligible": 0}
    for a in articles:
        if a.get("quarter") != w.evidence_quarter:
            why["other_quarter"] += 1
        elif not is_eligible(a, w):
            why["after_cutoff"] += 1
        else:
            out.append(a)
            why["eligible"] += 1
    return out, why


def assert_aligned(used, w: EvidenceWindow) -> None:
    """Raise if any article actually used by a prediction violates its window (the automated safeguard)."""
    bad = [a.get("article_key") for a in used if not is_eligible(a, w)]
    if bad:
        raise AlignmentViolation(f"{len(bad)} article(s) outside the {w.mode} window for {w.target_quarter} "
                                 f"(evidence {w.evidence_quarter}, cutoff {w.information_cutoff_ph}): {bad[:5]}")


def provenance(w: EvidenceWindow, generated_at: datetime, news_version: dict, used_keys) -> dict:
    """The block stored with every prediction: target, mode, generation time, information cutoff, news version and a
    hash of the exact article set used."""
    keys = sorted(used_keys)
    return {"mode": w.mode, "target_quarter": w.target_quarter, "lead": w.lead,
            "generated_at": to_ph(generated_at).isoformat(), "information_cutoff": w.information_cutoff_ph,
            "news_evidence_window": w.to_dict(), "news_version": news_version,
            "n_articles_used": len(keys),
            "articles_used_sha256": hashlib.sha256(json.dumps(keys).encode()).hexdigest()}
