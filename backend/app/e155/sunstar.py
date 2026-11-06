"""
E155 SunStar headlines from its public daily sitemaps (robots allows; about one request per second). Only the URL, edition, section and slug are kept. No article page is fetched.

    python -m app.e155.sunstar -> data/e155/raw/sunstar/<date>.txt, sunstar.parquet
"""
from __future__ import annotations

import re
import subprocess
import time

import pandas as pd

from app.paths import BACKEND_DIR

RAW = BACKEND_DIR / "data" / "e155" / "raw" / "sunstar"
UA = "Mozilla/5.0 (aiPHeed thesis research; polite)"
LOC = re.compile(r"<loc>([^<]+)</loc>")


def day(d: pd.Timestamp) -> str:
    f = RAW / f"{d:%Y-%m-%d}.txt"
    if f.exists():
        return "have"
    u = f"https://www.sunstar.com.ph/sitemap/sitemap-daily-{d:%Y-%m-%d}.xml"
    for a in range(3):
        try:
            raw = subprocess.run(["curl", "-s", "-m", "60", "-A", UA, u], check=True, capture_output=True).stdout.decode("utf-8", "ignore")
        except subprocess.CalledProcessError:
            time.sleep(5)
            continue
        if "<urlset" in raw or "<loc>" in raw:
            f.write_text("\n".join(LOC.findall(raw)) + "\n", encoding="utf-8", newline="\n")
            return "ok"
        if "Just a moment" in raw:
            return "challenge"
        time.sleep(5)
    return "fail"


def build() -> pd.DataFrame:
    rows = []
    for f in sorted(RAW.glob("*.txt")):
        for u in f.read_text(encoding="utf-8").split():
            m = re.match(r"https://www\.sunstar\.com\.ph/([^/]+)/([^/]+)/([^/?#]+)", u)
            if m:
                rows.append({"date": f.stem, "edition": m.group(1), "section": m.group(2), "slug": m.group(3), "title": m.group(3).replace("-", " ")})
    d = pd.DataFrame(rows)
    d.to_parquet(RAW.parent / "sunstar.parquet", index=False)
    return d


def main(part: int = 0, parts: int = 1):
    RAW.mkdir(parents=True, exist_ok=True)
    bad = 0
    for d in pd.date_range("2013-01-01", "2026-09-30", freq="D")[part::parts]:
        s = day(d)
        if s in ("ok", "fail"):
            time.sleep(1.0)
        if s == "challenge":
            bad += 1
            print("bot check met; stopping without bypassing", d.date(), flush=True)
            break
        if d.day == 1 and d.month == 1:
            print(d.date(), s, flush=True)
    if part:
        print("done", flush=True)
        return
    t = build()
    print("articles", len(t), "editions", t["edition"].value_counts().head(12).to_dict(), flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    import sys
    main(*(int(x) for x in sys.argv[1:3])) if len(sys.argv) > 2 else main()
