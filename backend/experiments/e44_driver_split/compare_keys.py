"""Compare keys_before.json and keys_after.json: same keys, order and value types; print the changed values."""
import json
from pathlib import Path

H = Path(__file__).resolve().parent
b = json.loads((H / "keys_before.json").read_text(encoding="utf-8"))
a = json.loads((H / "keys_after.json").read_text(encoding="utf-8"))
for k in [x for x in b if x != "forecast_index"]:
    print(f"== {k}")
    print("  top-level keys  before:", b[k]["top_level_keys"])
    print("  top-level keys  after: ", a[k]["top_level_keys"])
    print("  trigger keys    before:", b[k]["trigger_keys"])
    print("  trigger keys    after: ", a[k]["trigger_keys"])
    print("  identical keys, order and value types:", b[k]["shape"] == a[k]["shape"]
          and b[k]["top_level_keys"] == a[k]["top_level_keys"] and b[k]["trigger_keys"] == a[k]["trigger_keys"])
    print("  pct before:", b[k]["pct"], "| after:", a[k]["pct"])
print("forecast index before:", b["forecast_index"])
print("forecast index after: ", a["forecast_index"], "| unchanged:", a["forecast_index"] == b["forecast_index"])
