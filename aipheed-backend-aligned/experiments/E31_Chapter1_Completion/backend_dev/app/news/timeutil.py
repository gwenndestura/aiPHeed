"""Philippine-time quarter arithmetic for the news collector (E28). Every boundary is a Philippine calendar boundary."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

PH = ZoneInfo("Asia/Manila")


def parse_quarter(q: str) -> tuple[int, int]:
    y, n = str(q).split("-Q")
    y, n = int(y), int(n)
    if not 1 <= n <= 4:
        raise ValueError(f"bad quarter {q!r}")
    return y, n


def qstr(y: int, n: int) -> str:
    return f"{y}-Q{n}"


def quarter_start(q: str) -> date:
    y, n = parse_quarter(q)
    return date(y, 3 * (n - 1) + 1, 1)


def quarter_end_excl(q: str) -> date:
    y, n = parse_quarter(q)
    return date(y + 1, 1, 1) if n == 4 else date(y, 3 * n + 1, 1)


def quarter_of_date(d: date) -> str:
    return qstr(d.year, (d.month - 1) // 3 + 1)


def next_quarter(q: str) -> str:
    y, n = parse_quarter(q)
    return qstr(y + 1, 1) if n == 4 else qstr(y, n + 1)


def quarters_between(a: str, b: str) -> list[str]:
    out, q = [], a
    if parse_quarter(a) > parse_quarter(b):
        return out
    while True:
        out.append(q)
        if q == b:
            return out
        q = next_quarter(q)


def month_windows(q: str) -> list[tuple[date, date]]:
    """The three calendar-month windows [start, end) of a quarter."""
    s = quarter_start(q)
    out = []
    for i in range(3):
        m = s.month + i
        a = date(s.year, m, 1)
        b = date(s.year + 1, 1, 1) if m == 12 else date(s.year, m + 1, 1)
        out.append((a, b))
    return out


def split_window(a: date, b: date) -> tuple[tuple[date, date], tuple[date, date]] | None:
    """Halve [a, b) on a day boundary, or None when it is a single day."""
    days = (b - a).days
    if days <= 1:
        return None
    mid = a + timedelta(days=days // 2)
    return (a, mid), (mid, b)


def ph_midnight(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=PH)


def to_ph(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=PH)          # a naive timestamp is Philippine local time (project convention)
    return ts.astimezone(PH)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
