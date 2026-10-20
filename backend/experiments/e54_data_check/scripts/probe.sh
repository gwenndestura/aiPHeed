#!/bin/sh
# E54 data check: fetch each URL once, save the raw body and the HTTP status (no parsing, nothing executed).
# usage: sh probe.sh <out_dir> <name> <url>
out="$1/$2"
mkdir -p "$out"
code=$(curl -sS -L --max-time 60 -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) aiPHeed-research-data-check" \
  -o "$out/body" -w "%{http_code} %{content_type} %{size_download}" "$3" 2>"$out/curl_error.txt")
printf '%s\t%s\t%s\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$2" "$code" "$3" | tee -a "$1/../probe_log.tsv"
