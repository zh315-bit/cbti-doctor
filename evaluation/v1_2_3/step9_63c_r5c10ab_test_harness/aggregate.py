import json, sys, glob, os, collections
d = sys.argv[1]
tot = collections.Counter(); imp = {}; bad = []
for f in sorted(glob.glob(f"{d}/test_*.json")):
    r = json.load(open(f))
    imp.update(r["import_errors"])
    for tid, row in r["tests"].items():
        tot[row["outcome"]] += 1
        if row["outcome"] not in ("pass",):
            last = (row.get("detail") or "").strip().splitlines()
            bad.append((row["outcome"], tid, last[-1][:170] if last else ""))
mods = {os.path.basename(f)[:-5] for f in glob.glob(f"{d}/test_*.json")}
logs = {os.path.basename(f)[:-4] for f in glob.glob(f"{d}/test_*.log")}
print("modules with json:", len(mods), "| logs:", len(logs), "| missing json:", sorted(logs - mods))
print("exit codes:", collections.Counter(l.split("exit=")[1].strip() for l in open(f"{d}/exit_codes.txt")))
print("collected(executed) =", sum(tot.values()), dict(tot))
print("import_blockers =", len(imp)); [print("  IMPORT", k, "|", v[:120]) for k, v in sorted(imp.items())]
for b in sorted(bad): print(" ", b[0].upper(), b[1], "|", b[2])
g = f"{d}/guard.jsonl"
print("guard events:", sum(1 for _ in open(g)) if os.path.exists(g) else 0)
