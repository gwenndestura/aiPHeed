"""
app/quarterly/periods.py
------------------------
Quarter arithmetic for the quarterly update, in Philippine time.

Every period boundary in aiPHeed is a Philippine calendar boundary (Asia/Manila,
UTC+8, no daylight saving). A forecast for target quarter T is supported by the
news of the quarter immediately before it (the reference quarter, T-1), and only
by articles published on or before the declared information cutoff.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

PH_TZ = "Asia/Manila"
MONTHS = {1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June", 7: "July",
          8: "August", 9: "September", 10: "October", 11: "November", 12: "December"}


@dataclass(frozen=True, order=True)
class Quarter:
    year: int
    q: int

    @classmethod
    def parse(cls, text: str) -> "Quarter":
        y, n = str(text).strip().upper().split("-Q")
        y, n = int(y), int(n)
        if not 1 <= n <= 4:
            raise ValueError(f"bad quarter {text!r}")
        return cls(y, n)

    def __str__(self) -> str:
        return f"{self.year}-Q{self.q}"

    @property
    def index(self) -> int:
        return self.year * 4 + self.q - 1

    def shift(self, k: int) -> "Quarter":
        i = self.index + k
        return Quarter(i // 4, i % 4 + 1)

    def next(self) -> "Quarter":
        return self.shift(1)

    def prev(self) -> "Quarter":
        return self.shift(-1)

    def start(self) -> pd.Timestamp:
        """00:00:00 PHT on the quarter's first day."""
        return pd.Timestamp(self.year, 3 * (self.q - 1) + 1, 1, tz=PH_TZ)

    def end(self) -> pd.Timestamp:
        """23:59:59.999999 PHT on the quarter's last day (start of next quarter minus 1 microsecond)."""
        return self.next().start() - pd.Timedelta(microseconds=1)

    def months_label(self) -> str:
        m0 = 3 * (self.q - 1) + 1
        return f"{MONTHS[m0]}–{MONTHS[m0 + 2]} {self.year}"

    def display(self) -> str:
        return f"Q{self.q} {self.year} ({self.months_label()})"

    @classmethod
    def of(cls, ts) -> "Quarter":
        ts = to_ph(ts)
        return cls(ts.year, (ts.month - 1) // 3 + 1)


def to_ph(ts) -> pd.Timestamp:
    """Timestamp in Asia/Manila. A naive value is read as Philippine local time."""
    t = pd.Timestamp(ts)
    return t.tz_localize(PH_TZ) if t.tzinfo is None else t.tz_convert(PH_TZ)
