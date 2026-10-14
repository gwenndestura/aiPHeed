"""
app/quarterly/registry.py
-------------------------
Source registry and immutable snapshot store for the quarterly update.

* Every input file is REGISTERED with its SHA-256 computed from the bytes (never typed), its observation
  period, its publication/availability time, its retrieval time and its authorization. A file whose bytes
  change no longer verifies, so a silent overwrite is detected.
* INGEST copies the bytes into a content-addressed snapshot (snapshots/<sha256>/<name>). Ingesting the same
  bytes twice is a no-op, so reruns never duplicate records. A new file for an existing source_id becomes a
  new VINTAGE; earlier vintages are kept, so every historical forecast can name the exact inputs it used.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

KINDS = ("news", "indicator", "label", "static", "model")


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


@dataclass
class SourceEntry:
    source_id: str
    kind: str
    path: str
    sha256: str
    observation_start: str | None          # "YYYY-QN"
    observation_end: str | None
    available_at: str | None               # ISO publication / availability time; None = unknown (= unavailable)
    retrieved_at: str | None
    authorized: bool = False
    authorized_by: str | None = None
    authorization_ref: str | None = None
    vintage: int = 1
    revision_note: str | None = None
    required_columns: list[str] = field(default_factory=list)
    granularity: str | None = None          # "province-quarter", "region-quarter", "lgu", "article", ...

    def verify(self, root: Path | None = None) -> bool:
        p = Path(self.path) if root is None else (root / self.path)
        return p.exists() and sha256_file(p) == self.sha256


class Registry:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.entries: list[SourceEntry] = []
        if self.path.exists():
            self.entries = [SourceEntry(**e) for e in json.loads(self.path.read_text(encoding="utf-8"))["sources"]]

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"sources": [asdict(e) for e in self.entries]}, indent=2) + "\n",
                             encoding="utf-8")

    def register(self, source_id: str, kind: str, path: str | Path, *, observation_start=None, observation_end=None,
                 available_at=None, retrieved_at=None, authorized=False, authorized_by=None, authorization_ref=None,
                 required_columns=(), granularity=None, revision_note=None) -> SourceEntry:
        if kind not in KINDS:
            raise ValueError(f"unknown kind {kind}")
        digest = sha256_file(path)
        same = [e for e in self.entries if e.source_id == source_id]
        for e in same:
            if e.sha256 == digest:
                return e                                   # idempotent: identical bytes already registered
        vintage = max((e.vintage for e in same), default=0) + 1
        if same and not revision_note:
            raise ValueError(f"{source_id}: new bytes for an existing source need a revision_note (vintage {vintage})")
        e = SourceEntry(source_id, kind, str(path), digest, observation_start, observation_end, available_at,
                        retrieved_at or datetime.now(timezone.utc).isoformat(), bool(authorized), authorized_by,
                        authorization_ref, vintage, revision_note, list(required_columns), granularity)
        self.entries.append(e)
        return e

    def latest(self, source_id: str) -> SourceEntry | None:
        same = [e for e in self.entries if e.source_id == source_id]
        return max(same, key=lambda e: e.vintage) if same else None

    def by_kind(self, kind: str) -> list[SourceEntry]:
        ids = {e.source_id for e in self.entries if e.kind == kind}
        return [self.latest(i) for i in sorted(ids)]


class SnapshotStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.manifest = self.root / "manifest.jsonl"

    def ingest(self, entry: SourceEntry) -> dict:
        src = Path(entry.path)
        if sha256_file(src) != entry.sha256:
            raise ValueError(f"{entry.source_id}: file bytes differ from the registered SHA-256")
        dest = self.root / "snapshots" / entry.sha256 / src.name
        rec = {"source_id": entry.source_id, "vintage": entry.vintage, "sha256": entry.sha256,
               "snapshot": str(dest.relative_to(self.root)), "kind": entry.kind}
        if dest.exists() and sha256_file(dest) == entry.sha256:
            return {**rec, "new": False}
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
        with open(self.manifest, "a", encoding="utf-8") as f:
            f.write(json.dumps({**rec, "ingested_at": datetime.now(timezone.utc).isoformat()}) + "\n")
        return {**rec, "new": True}

    def records(self) -> list[dict]:
        if not self.manifest.exists():
            return []
        return [json.loads(l) for l in self.manifest.read_text(encoding="utf-8").splitlines() if l.strip()]
