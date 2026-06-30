import csv
import json
import os
from datetime import date, datetime


def _json_default(obj):
    """Make json.dump() tolerate datetimes and anything else unexpected."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    return str(obj)


def save_json(data, filepath):
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=_json_default)
    print(f"  -> wrote {filepath} ({len(data)} records)")


def save_csv(data, filepath, fieldnames=None):
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)

    if not data:
        # Still write an empty file with headers if we know the schema,
        # so downstream tools don't choke on a missing file.
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            if fieldnames:
                csv.DictWriter(f, fieldnames=fieldnames).writeheader()
        print(f"  -> wrote {filepath} (0 records)")
        return

    if fieldnames is None:
        # Union of all keys, in first-seen order, across every record.
        fieldnames = []
        seen = set()
        for row in data:
            for k in row.keys():
                if k not in seen:
                    seen.add(k)
                    fieldnames.append(k)

    with open(filepath, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in data:
            clean_row = {}
            for k in fieldnames:
                v = row.get(k)
                if isinstance(v, (datetime, date)):
                    v = v.isoformat()
                elif isinstance(v, (dict, list)):
                    v = json.dumps(v, ensure_ascii=False, default=_json_default)
                clean_row[k] = v
            writer.writerow(clean_row)
    print(f"  -> wrote {filepath} ({len(data)} records)")
