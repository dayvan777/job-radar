#!/usr/bin/env python3
"""Tiny JSON store for Job Radar. Each collection is data/<collection>.json = {doc_id: {...}}.

Usage (run from the project root):
  python3 scripts/db.py ids <collection>                 list doc ids
  python3 scripts/db.py get <collection> [doc_id]        print one doc or the whole collection
  python3 scripts/db.py set <collection> <doc_id> <json-or-@file>     replace a doc
  python3 scripts/db.py update <collection> <doc_id> <json-or-@file>  deep-merge fields (null deletes a field)
  python3 scripts/db.py delete <collection> <doc_id>
  python3 scripts/db.py event '<json>'                   append an events row (auto id, never edited)
  python3 scripts/db.py known                            all doc ids in postings, jobs, signals (for dedup)
Writes are atomic (temp file + rename). Never edit data/*.json by hand-retyping; use this script.
"""
import json, os, sys, tempfile, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")


def load(col):
    p = os.path.join(DATA, f"{col}.json")
    if not os.path.exists(p):
        return {}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save(col, obj):
    os.makedirs(DATA, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=DATA, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, os.path.join(DATA, f"{col}.json"))


def arg_json(s):
    if s.startswith("@"):
        with open(s[1:], encoding="utf-8") as f:
            return json.load(f)
    return json.loads(s)


def merge(a, b):
    for k, v in b.items():
        if v is None:
            a.pop(k, None)
        elif isinstance(v, dict) and isinstance(a.get(k), dict):
            merge(a[k], v)
        else:
            a[k] = v
    return a


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    cmd = argv[1]
    if cmd == "ids":
        print("\n".join(load(argv[2]).keys()))
    elif cmd == "get":
        d = load(argv[2])
        print(json.dumps(d.get(argv[3]) if len(argv) > 3 else d, ensure_ascii=False, indent=1))
    elif cmd in ("set", "update"):
        col, did, val = argv[2], argv[3], arg_json(argv[4])
        d = load(col)
        d[did] = val if cmd == "set" else merge(d.get(did, {}), val)
        save(col, d)
        print(f"ok {cmd} {col}/{did}")
    elif cmd == "delete":
        d = load(argv[2])
        d.pop(argv[3], None)
        save(argv[2], d)
        print(f"ok delete {argv[2]}/{argv[3]}")
    elif cmd == "event":
        row = arg_json(argv[2])
        d = load("events")
        now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        row.setdefault("at", datetime.datetime.now().astimezone().isoformat(timespec="seconds"))
        d[f"ev-{now}"] = row
        save("events", d)
        print(f"ok event ev-{now}")
    elif cmd == "known":
        ids = set()
        for c in ("postings", "jobs", "signals"):
            ids |= set(load(c).keys())
        print("\n".join(sorted(ids)))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv)
