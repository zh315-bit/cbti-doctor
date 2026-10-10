# Step 9.63c-r5c10o — exact two-file change and SHA-256 audit

Approved pre-patch hashes matched r5c10n exactly. Files changed by this step: **2 test files only**; unapproved changes introduced by this step: **0**. The working tree had unrelated pre-existing changes; these are not counted as step changes or claimed repaired.

| File | Before SHA-256 | After SHA-256 | r10 member |
|---|---|---|---|
| `tests/test_v1_2_mechanism_validation.py` | `2d5d8fcc4919b798b907903bdd61bf8d3cb987351195b61b397ac379fa3739b5` | `e079a059b22388d0d40abbf7962e0fa3e25e4c3d565069133496b82676f6d2d9` | No |
| `tests/test_v1_2_1_mechanism_validation.py` | `2d92acdfe7923c631d950d1f4bf1efc99ae333f41f3981c12371d6def8ed8307` | `cd8b2c5bcb657ef3dd848cedbfc27034c03a1c4a8ccb41fa9452805e103f6cf2` | No |

Exact change sites (the repository `git diff --` for these two paths is the corresponding unified diff):

| File | Removed | Added |
|---|---|---|
| V1.2 | Fixed `TRACE_PATH` under `evaluation/v1_2/`; `mkdir` and fixed-path `write_text` | `tempfile` import; `isolated_trace_path()` resolving and rejecting any repository-contained target; method-local `TemporaryDirectory` write using the identical JSONL expression; `test_historical_trace_path_rejected` |
| V1.2.1 | Fixed `TRACE` under `evaluation/v1_2_1/`; `mkdir` and fixed-path `write_text` | Same local-only pattern, retaining the identical JSONL expression; `test_historical_trace_path_rejected` |

Original scenario construction, selected-action checks and final 18/19-case assertions remain in place. Static diff and pre/post source aggregate show no production code or frozen-member edit. The current r10 member aggregate is unchanged pre/post: `f6f20d9dad339ffef49a4e23179705c7857fe0ce0b882cb9a013d59c9e1b1197`. Production Python aggregate is unchanged pre/post: `bb5e9616afaaf3dc98f4b7514f66a2f67b683e91a0b4d269394159c945a6a2ad`. `git diff --check` passed for the two files.

```diff
diff --git a/tests/test_v1_2_mechanism_validation.py b/tests/test_v1_2_mechanism_validation.py
@@ imports and target @@
 from pathlib import Path
+import tempfile
 import unittest
 ROOT = Path(__file__).resolve().parents[1]
-TRACE_PATH = ROOT / "evaluation/v1_2/step8_3_mechanism_traces.jsonl"
+def isolated_trace_path(directory: str) -> Path:
+    path = (Path(directory) / "step8_3_mechanism_traces.jsonl").resolve()
+    if path == ROOT or ROOT in path.parents:
+        raise ValueError("trace output must be outside the repository")
+    return path
@@ write and negative guard @@
-        TRACE_PATH.parent.mkdir(parents=True, exist_ok=True)
-        TRACE_PATH.write_text("".join(json.dumps(trace, ensure_ascii=False) + "\n" for trace in traces), encoding="utf-8")
+        with tempfile.TemporaryDirectory(prefix="v12-mechanism-") as directory:
+            trace_path = isolated_trace_path(directory)
+            trace_path.write_text("".join(json.dumps(trace, ensure_ascii=False) + "\n" for trace in traces), encoding="utf-8")
         self.assertEqual(len(traces), 18)
         self.assertTrue(all("information_value" in trace and "selected_action" in trace for trace in traces))
+    def test_historical_trace_path_rejected(self):
+        with self.assertRaisesRegex(ValueError, "outside the repository"):
+            isolated_trace_path(str(ROOT / "evaluation/v1_2"))

diff --git a/tests/test_v1_2_1_mechanism_validation.py b/tests/test_v1_2_1_mechanism_validation.py
@@ imports and target @@
 from pathlib import Path
+import tempfile
 import unittest
-ROOT=Path(__file__).resolve().parents[1]; TRACE=ROOT/'evaluation/v1_2_1/step8_7_mechanism_traces.jsonl'
+ROOT=Path(__file__).resolve().parents[1]
+def isolated_trace_path(directory: str) -> Path:
+    path=(Path(directory)/'step8_7_mechanism_traces.jsonl').resolve()
+    if path == ROOT or ROOT in path.parents:
+        raise ValueError('trace output must be outside the repository')
+    return path
@@ write and negative guard @@
-        TRACE.parent.mkdir(parents=True,exist_ok=True); TRACE.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows),encoding='utf-8')
+        with tempfile.TemporaryDirectory(prefix='v121-mechanism-') as directory:
+            trace_path=isolated_trace_path(directory)
+            trace_path.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows),encoding='utf-8')
         self.assertEqual(len(rows),19)
+    def test_historical_trace_path_rejected(self):
+        with self.assertRaisesRegex(ValueError,'outside the repository'):
+            isolated_trace_path(str(ROOT/'evaluation/v1_2_1'))
```
