# Step 9.63c-r5c10aa — Proposed native unittest collection command

**Design only. Do not execute under Step r5c10aa.** From `/Volumes/Elements/cbti-doctor-main`, a separately approved collection-only step could run:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -I -B - <<'PY'
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path('tests').resolve()))
loader = unittest.TestLoader()
suite = loader.loadTestsFromName('test_step9_63b_mac_local_preflight')

def cases(node):
    for item in node:
        if isinstance(item, unittest.TestSuite):
            yield from cases(item)
        else:
            yield item

ids = [case.id() for case in cases(suite)]
for test_id in ids:
    print(test_id)
print(f'COLLECTED={len(ids)} IMPORT_ERRORS={len(loader.errors)}')
if loader.errors or len(ids) != 8 or len(set(ids)) != 8:
    for error in loader.errors:
        print(error, file=sys.stderr)
    raise SystemExit(1)
PY
```

This imports the test module and constructs `TestCase` objects to enumerate IDs. It does **not** call `suite.run`, `TextTestRunner`, a test method, `setUp` or `tearDown`. The source has no module/class setup hook, custom constructor or module-level transport import; `unittest.main()` is protected by `if __name__ == '__main__'`. `-I -B` isolates user-site/PYTHONPATH and prevents bytecode writes. The eight IDs are an **expected count from static source**, not a current collection result. `loader.errors` is checked because `unittest.TestLoader` can return a `_FailedTest` instead of raising on import error. A later execution must preserve before/after hashes of the target, r10 freeze and historical Trace files and report actual counts; it may not run methods or substitute a fake r11 identity.

The proposal validates native `unittest` discovery, not pytest-specific collection. Given the project's documented and CI-native `unittest` workflow, this is the smaller first verification path; an isolated pytest installation remains a separate choice only if pytest-specific behavior is required.
