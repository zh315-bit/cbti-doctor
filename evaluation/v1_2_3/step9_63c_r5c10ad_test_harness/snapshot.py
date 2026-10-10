"""Hash every repo file (excluding .venv/.git/models/__pycache__) with size+mtime_ns."""
import hashlib, json, os, sys
root = sys.argv[1]; out = sys.argv[2]
SKIP = {".venv", ".git", "models", "__pycache__", ".rag_db"}
rows = {}
for d, dirs, files in os.walk(root):
    dirs[:] = [x for x in dirs if x not in SKIP]
    for f in files:
        p = os.path.join(d, f); rel = os.path.relpath(p, root)
        if os.path.islink(p): rows[rel] = {"link": os.readlink(p)}; continue
        st = os.stat(p); h = hashlib.sha256()
        with open(p, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""): h.update(chunk)
        rows[rel] = {"sha256": h.hexdigest(), "size": st.st_size, "mtime_ns": st.st_mtime_ns}
json.dump(rows, open(out, "w"), indent=0, sort_keys=True)
print(len(rows), "files")
