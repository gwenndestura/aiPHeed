"""
Append-only news store (E28).

Files (JSON lines, one record per line, each line flushed and fsync'd so an interruption can lose at most the line
being written; a torn last line is skipped on load and counted):

    articles.jsonl    one record per unique article (first sighting); never rewritten
    sightings.jsonl   every later sighting of a known article (other query, province, source or run)
    requests.jsonl    every search request: query, window, status, counts, attempts, timestamps
    windows.jsonl     the window ledger: final status of each (source, query, province, window); latest line wins
    rejected.jsonl    items refused at intake, with the reason and a SHA-256 of the link only (no title or text, so an
                      item published after the authorized limit is never stored in readable form)
    runs.jsonl        one line at the start and one at the end of every run

Article identity. `article_key` = SHA-256 of (publisher domain | normalised title | Philippine publication date). The
same story found by several queries, several sources (Google link vs GDELT URL) or several runs maps to one key.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import unicodedata
from pathlib import Path

FILES = ("articles", "sightings", "requests", "windows", "rejected", "runs")


def norm_title(t: str) -> str:
    t = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().casefold()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", t)).strip()


def article_key(domain: str, title: str, ph_date: str) -> str:
    return hashlib.sha256(f"{(domain or '').lower()}|{norm_title(title)}|{ph_date}".encode()).hexdigest()


def sha(s: str) -> str:
    return hashlib.sha256((s or "").encode()).hexdigest()


def window_id(source: str, query_id: str, province: str, start: str, end: str) -> str:
    return f"{source}|{query_id}|{province}|{start}|{end}"


class NewsStore:
    def __init__(self, root: Path | str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.torn_lines: dict[str, int] = {}
        self.articles: dict[str, dict] = {}
        self.windows: dict[str, dict] = {}
        for rec in self._read("articles"):
            self.articles.setdefault(rec["article_key"], rec)
        for rec in self._read("windows"):
            self.windows[rec["window_id"]] = rec

    # ---- low-level
    def path(self, name: str) -> Path:
        return self.root / f"{name}.jsonl"

    def _read(self, name: str) -> list[dict]:
        p = self.path(name)
        if not p.exists():
            return []
        out, torn = [], 0
        with open(p, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    torn += 1           # an interrupted write; the record it held is re-collected on the next run
        if torn:
            self.torn_lines[name] = torn
        return out

    def read(self, name: str) -> list[dict]:
        return self._read(name)

    def _append(self, name: str, rec: dict) -> None:
        with open(self.path(name), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())

    # ---- typed writers
    def add_article(self, rec: dict) -> bool:
        """True if new. A known key is recorded as a sighting; the stored article is never modified."""
        k = rec["article_key"]
        if k in self.articles:
            return False
        self.articles[k] = rec
        self._append("articles", rec)
        return True

    def add_sighting(self, rec: dict) -> None:
        self._append("sightings", rec)

    def log_request(self, rec: dict) -> None:
        self._append("requests", rec)

    def set_window(self, rec: dict) -> None:
        self.windows[rec["window_id"]] = rec
        self._append("windows", rec)

    def reject(self, rec: dict) -> None:
        self._append("rejected", rec)

    def log_run(self, rec: dict) -> None:
        self._append("runs", rec)

    def window_done(self, wid: str) -> bool:
        w = self.windows.get(wid)
        return bool(w) and w["status"] in ("COMPLETE", "TRUNCATED_AT_MIN_WINDOW", "SPLIT")
