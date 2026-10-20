"""Strip an HTML file to text and print sentences containing any keyword (case-insensitive).
usage: python -I grep_html.py <html> <max> kw1 [kw2 ...]"""
import html
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

raw = open(sys.argv[1], encoding="utf-8", errors="replace").read()
raw = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", raw)
txt = html.unescape(re.sub(r"(?s)<[^>]+>", " ", raw))
txt = re.sub(r"\s+", " ", txt)
kws = [k.lower() for k in sys.argv[3:]]
seen, n = set(), 0
for s in re.split(r"(?<=[.!?])\s+", txt):
    if any(k in s.lower() for k in kws) and s not in seen:
        seen.add(s)
        print("-", s[:400])
        n += 1
        if n >= int(sys.argv[2]):
            break
