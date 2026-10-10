"""Collection-only: load every tests/test_*.py via unittest; never call run()."""
import ast, importlib, json, sys, unittest
from pathlib import Path
root = Path.cwd(); out = sys.argv[1]
files = sorted((root / "tests").glob("test_*.py"))
syntax_fail = []
static = {}
for f in files:
    try:
        tree = ast.parse(f.read_text(encoding="utf-8"))
        static[f.stem] = sum(1 for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test"))
    except SyntaxError as e:
        syntax_fail.append((f.name, str(e)))
sys.path.insert(0, str(root / "tests")); sys.path.insert(0, str(root))
result = {"files": len(files), "syntax_failures": syntax_fail, "modules": {}}
for f in files:
    loader = unittest.TestLoader()
    try:
        suite = loader.loadTestsFromModule(importlib.import_module(f.stem))
    except BaseException as exc:
        result["modules"][f.stem] = {"collected": 0, "static_defs": static.get(f.stem),
                                     "import_error": f"{type(exc).__name__}: {exc}"}
        continue
    def walk(s):
        for t in s:
            if isinstance(t, unittest.TestSuite): yield from walk(t)
            else: yield t
    tests = list(walk(suite))
    errs = [e.strip().splitlines()[-1] for e in loader.errors]
    real = [t.id() for t in tests if not t.id().startswith("unittest.loader._FailedTest")]
    result["modules"][f.stem] = {"collected": len(real), "static_defs": static.get(f.stem),
                                 "import_error": errs[0] if errs else None}
json.dump(result, open(out, "w"), indent=1)
blocked = {k: v for k, v in result["modules"].items() if v["import_error"]}
print("files", len(files), "syntax_failures", len(syntax_fail))
print("collected_methods", sum(v["collected"] for v in result["modules"].values()))
print("import_blockers", len(blocked))
for k, v in blocked.items(): print("  BLOCKED", k, "static_defs=", v["static_defs"], "|", v["import_error"][:150])
mism = {k: (v["collected"], v["static_defs"]) for k, v in result["modules"].items() if not v["import_error"] and v["collected"] != v["static_defs"]}
print("collected!=static (non-blocked):", mism)
