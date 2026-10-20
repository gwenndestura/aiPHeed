"""Append one provenance row (called at the moment a value is read from its source). Usage:
add_prov.py URL OUTLET PUBLISHED FIELDWORK AREA MEASURE VALUE "SOURCE TEXT" """
import csv
import sys
from datetime import date
from pathlib import Path

P = Path(__file__).resolve().parents[1] / "inputs" / "provenance.csv"
row = sys.argv[1:9] + [str(date.today())]
assert len(row) == 9, row
with P.open("a", newline="", encoding="utf-8") as f:
    csv.writer(f).writerow(row)
print(row[2], row[3], row[4], row[6])
