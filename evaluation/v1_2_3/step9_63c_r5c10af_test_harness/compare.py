import json, sys
a = json.load(open(sys.argv[1])); b = json.load(open(sys.argv[2]))
added = sorted(set(b) - set(a)); removed = sorted(set(a) - set(b))
changed = sorted(k for k in set(a) & set(b) if a[k].get("sha256") != b[k].get("sha256"))
touched = sorted(k for k in set(a) & set(b) if a[k].get("sha256") == b[k].get("sha256") and a[k].get("mtime_ns") != b[k].get("mtime_ns"))
for name, lst in [("ADDED", added), ("REMOVED", removed), ("CONTENT_CHANGED", changed), ("MTIME_ONLY", touched)]:
    print(f"{name}: {len(lst)}"); [print("  ", x) for x in lst[:50]]
