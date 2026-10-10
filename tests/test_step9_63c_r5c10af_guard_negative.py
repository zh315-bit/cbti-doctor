"""Step 9.63c-r5c10af: negative tests for the test side-effect guard (v3 candidate).

The guard under test is ``evaluation/v1_2_3/step9_63c_r5c10af_test_harness/guard``.
Its scenarios run against a throw-away temporary tree that plays the protected
repository; the real repository is never a target. Each scenario is first run with no
guard at all to prove it really changes something, then with the guard.

Because the guard (correctly) refuses to start Python children whose environment
differs from its own, this module cannot spawn the scenarios while it runs under that
very guard. The harness therefore runs the catalogue first, outside any guard
(``CBTI_GUARD_NEGATIVE_RESULTS``); this module verifies that the results are bound to
the exact guard and catalogue bytes in the repository. Run outside a guard it executes
the catalogue itself. Under a guard with no results it fails; it never skips.

Requested coverage (user decision, Step 9.63c-r5c10ae review):
  a  hard links: creating one from a repository file is blocked; writing through an
     existing one is blocked
  b  rename/replace blocked when either end is in the repository
  c  symlinks: deleting the link itself is allowed; writing through it is blocked
  d  every write entry point: os.open, shutil.copy*, Path.write_text, builtin open, ...
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HARNESS = REPO / "evaluation/v1_2_3/step9_63c_r5c10af_test_harness"
GUARD_DIR = HARNESS / "guard"
SCENARIOS_PATH = HARNESS / "guard_negative_scenarios.py"
# Historical evidence that must stay byte-identical.
V1_GUARD = (REPO / "evaluation/v1_2_3/step9_63c_r5c10ab_test_harness/guard/sitecustomize.py",
            "1376cf088cfbb7441829430a2e62924c73c606851af37b93764d0f1f9201fcbd")
V2_GUARD = (REPO / "evaluation/v1_2_3/step9_63c_r5c10ad_test_harness/guard/sitecustomize.py",
            "b85280bd79ec78e0ca8c6e7ef04bf580ba84fcfd9e2aef1d999395a59fea9f23")
# The standard library itself refuses rmtree on a symlink, so this scenario has no effect
# without a guard; it is a SAFE-class scenario kept for completeness.
DOCUMENTED_INEFFECTIVE = {"c15_rmtree_symlink_without_slash"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_scenarios():
    spec = importlib.util.spec_from_file_location("guard_negative_scenarios", SCENARIOS_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses resolve annotations through sys.modules
    spec.loader.exec_module(module)
    return module


SCEN = load_scenarios()
_REPORT: dict | None = None


def report() -> dict:
    global _REPORT
    if _REPORT is not None:
        return _REPORT
    results = os.environ.get("CBTI_GUARD_NEGATIVE_RESULTS")
    if results:
        data = json.loads(Path(results).read_text(encoding="utf-8"))
    elif "CBTI_GUARD_ROOT" not in os.environ:
        rows = SCEN.run_catalogue(str(GUARD_DIR))
        data = {"rows": rows, "guard_sitecustomize_sha256": sha256(GUARD_DIR / "sitecustomize.py"),
                "scenario_catalogue_sha256": sha256(SCENARIOS_PATH)}
    else:
        raise AssertionError("running under a guard without CBTI_GUARD_NEGATIVE_RESULTS; "
                             "run the suite through the r5c10af harness (run_all.sh)")
    _REPORT = data
    return data


class GuardNegativeCatalogueTests(unittest.TestCase):
    def setUp(self):
        self.report = report()
        self.rows = {row["id"]: row for row in self.report["rows"]}

    def test_results_are_bound_to_current_guard_and_catalogue_bytes(self):
        self.assertEqual(self.report["guard_sitecustomize_sha256"], sha256(GUARD_DIR / "sitecustomize.py"))
        self.assertEqual(self.report["scenario_catalogue_sha256"], sha256(SCENARIOS_PATH))
        self.assertEqual({row["id"] for row in self.report["rows"]}, {s.id for s in SCEN.SCENARIOS})

    def test_every_asserted_scenario_passes(self):
        for scenario in SCEN.SCENARIOS:
            if scenario.expect == "LIMIT":
                continue
            with self.subTest(scenario=scenario.id, expect=scenario.expect):
                row = self.rows[scenario.id]
                self.assertEqual(row["verdict"], "PASS",
                                 f"{row['verdict']}: guarded={row['guarded']}")

    def test_scenarios_have_an_effect_without_the_guard(self):
        ineffective = {sid for sid, row in self.rows.items() if not row["scenario_effective_without_guard"]}
        self.assertEqual(ineffective, DOCUMENTED_INEFFECTIVE)

    def test_blocked_scenarios_were_blocked_by_the_guard_not_by_the_os(self):
        for sid, row in self.rows.items():
            if row["expect"] == "BLOCK":
                with self.subTest(scenario=sid):
                    guarded = row["guarded"]
                    self.assertTrue(guarded["outcome"] == "BLOCKED" or guarded["guard_blocked_events"] > 0, guarded)
                    self.assertFalse(guarded["repo_changed"] or guarded["out_changed"])

    def test_allowed_scenarios_stay_silent(self):
        allowed = [row for row in self.rows.values() if row["expect"] == "ALLOW"]
        self.assertGreaterEqual(len(allowed), 10)
        for row in allowed:
            with self.subTest(scenario=row["id"]):
                self.assertEqual(row["guarded"]["outcome"], "ALLOWED")
                self.assertEqual(row["guarded"]["guard_blocked_events"], 0)
                self.assertFalse(row["guarded"]["repo_changed"])

    # ---- the four requested families, by name -----------------------------------------
    def expect(self, mapping: dict[str, str]):
        for sid, expected in mapping.items():
            with self.subTest(scenario=sid):
                self.assertIn(sid, self.rows)
                self.assertEqual(self.rows[sid]["expect"], expected)
                self.assertEqual(self.rows[sid]["verdict"], "PASS")

    def test_a_hard_links(self):
        self.expect({"a1_link_from_repo_file": "BLOCK", "a2_link_into_repo": "BLOCK",
                     "a3_write_via_existing_hardlink": "BLOCK", "a4_append_via_existing_hardlink": "BLOCK",
                     "a5_truncate_via_existing_hardlink": "BLOCK", "a6_chmod_via_existing_hardlink": "BLOCK",
                     "a7_utime_via_existing_hardlink": "BLOCK", "a8_pathlib_write_via_existing_hardlink": "BLOCK",
                     "a9_unlink_the_hardlink_name_itself": "ALLOW", "a10_write_unrelated_multilink_file": "ALLOW"})

    def test_b_rename_replace_either_end(self):
        self.expect({"b1_rename_source_in_repo": "BLOCK", "b2_rename_target_in_repo": "BLOCK",
                     "b3_replace_source_in_repo": "BLOCK", "b4_replace_target_in_repo": "BLOCK",
                     "b5_pathlib_rename_source_in_repo": "BLOCK", "b6_pathlib_replace_target_in_repo": "BLOCK",
                     "b7_shutil_move_source_in_repo": "BLOCK", "b8_shutil_move_target_in_repo": "BLOCK",
                     "b9_rename_directory_in_repo": "BLOCK", "b10_rename_source_dir_fd_in_repo": "BLOCK",
                     "b11_rename_target_dir_fd_in_repo": "BLOCK", "b12_rename_into_repo_via_symlinked_dir": "BLOCK",
                     "b13_rename_outside_to_outside": "ALLOW", "b14_rename_the_symlink_itself": "ALLOW"})

    def test_c_symlinks(self):
        self.expect({"c1_remove_symlink_itself": "ALLOW", "c2_unlink_symlink_itself": "ALLOW",
                     "c3_pathlib_unlink_symlink_itself": "ALLOW", "c4_write_through_symlink": "BLOCK",
                     "c5_os_open_through_symlink": "BLOCK", "c6_write_text_through_symlink": "BLOCK",
                     "c7_copy_onto_symlink": "BLOCK", "c8_new_file_through_symlinked_dir": "BLOCK",
                     "c9_overwrite_through_symlinked_dir": "BLOCK", "c10_delete_through_symlinked_dir": "BLOCK",
                     "c11_dotdot_after_symlink_write": "BLOCK", "c12_dotdot_after_symlink_remove": "BLOCK",
                     "c13_trailing_slash_rmdir_through_symlink": "BLOCK", "c16_relative_symlink_write": "BLOCK",
                     "c17_create_symlink_inside_repo": "BLOCK", "c18_create_symlink_pointing_into_repo": "ALLOW",
                     "c19_read_through_symlink": "ALLOW", "c20_chmod_through_symlink": "BLOCK"})

    def test_d_write_entry_points(self):
        self.expect({"d1_open_w": "BLOCK", "d2_open_a": "BLOCK", "d3_open_x_new": "BLOCK", "d4_open_r_plus": "BLOCK",
                     "d5_open_wb": "BLOCK", "d6_io_open_w": "BLOCK",
                     "d7_os_open_wronly": "BLOCK", "d8_os_open_creat": "BLOCK", "d9_os_open_rdwr": "BLOCK",
                     "d10_os_open_trunc": "BLOCK", "d11_os_open_append": "BLOCK", "d12_os_open_excl": "BLOCK",
                     "d13_shutil_copy": "BLOCK", "d14_shutil_copyfile": "BLOCK", "d15_shutil_copy2": "BLOCK",
                     "d16_shutil_copy_into_repo_dir": "BLOCK", "d17_shutil_copyfileobj": "BLOCK",
                     "d18_shutil_copytree": "BLOCK", "d19_shutil_copymode": "BLOCK", "d20_shutil_copystat": "BLOCK",
                     "d21_pathlib_write_text": "BLOCK", "d22_pathlib_write_bytes": "BLOCK", "d23_pathlib_open_w": "BLOCK",
                     "d24_pathlib_touch_new": "BLOCK", "d25_pathlib_touch_existing": "BLOCK", "d26_pathlib_mkdir": "BLOCK",
                     "d27_os_makedirs": "BLOCK", "d28_os_mkdir": "BLOCK", "d29_os_truncate_path": "BLOCK",
                     "d30_os_chmod_path": "BLOCK", "d31_os_chmod_fd": "BLOCK", "d32_os_fchmod_fd": "BLOCK",
                     "d33_os_utime_path": "BLOCK", "d34_os_utime_fd": "BLOCK", "d35_os_chown_path": "BLOCK",
                     "d36_os_remove": "BLOCK", "d37_os_unlink": "BLOCK", "d38_pathlib_unlink": "BLOCK",
                     "d39_os_rmdir": "BLOCK", "d40_shutil_rmtree": "BLOCK", "d41_os_symlink_dst_in_repo": "BLOCK",
                     "d42_os_mkfifo": "BLOCK", "d43_os_mknod_fifo": "BLOCK", "d44_sqlite3_connect_write": "BLOCK",
                     "d45_dir_fd_open_create": "BLOCK", "d46_dir_fd_open_overwrite": "BLOCK", "d47_dir_fd_mkdir": "BLOCK",
                     "d48_dir_fd_unlink": "BLOCK", "d49_dir_fd_mkfifo": "BLOCK", "d50_relative_path_after_chdir": "BLOCK",
                     "d51_dotdot_relative_from_out": "BLOCK", "d53_tempfile_inside_repo": "BLOCK",
                     "d54_logging_file_handler": "BLOCK", "d55_read_repo_file": "ALLOW", "d56_write_outside": "ALLOW",
                     "d57_delete_outside_tree": "ALLOW", "d58_rename_ancestor_of_repo": "BLOCK",
                     "d59_rmtree_ancestor_of_repo": "SAFE", "d60_chmod_ancestor_of_repo": "BLOCK"})

    def test_case_insensitive_aliases_are_blocked_or_explicitly_skipped(self):
        for sid in ("d52_case_variant_of_root", "d61_rmdir_ancestor_alias_case"):
            with self.subTest(scenario=sid):
                row = self.rows[sid]
                self.assertIn(row["verdict"], ("PASS", "SKIPPED"))
                if row["verdict"] == "SKIPPED":
                    self.assertEqual(row["guarded"]["skipped"], "filesystem is case-sensitive")

    def test_child_process_escape_routes(self):
        self.expect({"e1_child_python_inherits_guard": "BLOCK", "e2_child_isolated_flag": "BLOCK",
                     "e3_child_no_site_flag": "BLOCK", "e4_child_ignore_env_flag": "BLOCK",
                     "e5_child_clustered_flags": "BLOCK", "e6_child_scrubbed_environment": "BLOCK",
                     "e7_child_environment_without_guard_path": "BLOCK",
                     "e8_parent_environ_mutated_then_inherit": "BLOCK", "e9_exec_isolated_python": "BLOCK",
                     "e10_posix_spawn_isolated_python": "BLOCK", "e11_shell_subprocess": "BLOCK",
                     "e12_non_python_binary": "BLOCK", "e13_child_python_writes_outside": "ALLOW"})

    def test_known_limits_are_reported_not_hidden(self):
        limits = [row for row in self.rows.values() if row["expect"] == "LIMIT"]
        self.assertEqual([row["id"] for row in limits], ["f1_ctypes_libc_write"])
        self.assertIn(limits[0]["verdict"], ("LIMIT_BYPASSED", "LIMIT_NOT_REPRODUCED"))


class HistoricalGuardEvidenceTests(unittest.TestCase):
    def test_v1_and_v2_guards_are_unchanged(self):
        for path, expected in (V1_GUARD, V2_GUARD):
            with self.subTest(path=path.relative_to(REPO).as_posix()):
                self.assertEqual(sha256(path), expected)

    def test_v3_candidate_is_a_separate_file(self):
        self.assertNotEqual(sha256(GUARD_DIR / "sitecustomize.py"), V1_GUARD[1])
        self.assertNotEqual(sha256(GUARD_DIR / "sitecustomize.py"), V2_GUARD[1])


class OracleTests(unittest.TestCase):
    """The pass/fail oracle itself, on synthetic outcomes."""

    def row(self, **kwargs):
        base = {"outcome": "BLOCKED", "repo_changed": False, "out_changed": False, "guard_blocked_events": 1}
        return {**base, **kwargs}

    def scenario(self, expect):
        return SCEN.Scenario("x", "x", expect, "pass")

    def test_verdicts(self):
        verdict = SCEN.verdict
        self.assertEqual(verdict(self.scenario("BLOCK"), self.row(), {}), "PASS")
        self.assertEqual(verdict(self.scenario("BLOCK"), self.row(outcome="ALLOWED", repo_changed=True, guard_blocked_events=0), {}), "BYPASS")
        self.assertEqual(verdict(self.scenario("BLOCK"), self.row(outcome="OS_ERROR", guard_blocked_events=0), {}), "NOT_BLOCKED")
        self.assertEqual(verdict(self.scenario("BLOCK"), self.row(out_changed=True), {}), "BYPASS")
        self.assertEqual(verdict(self.scenario("ALLOW"), self.row(), {}), "FALSE_POSITIVE")
        self.assertEqual(verdict(self.scenario("ALLOW"), self.row(outcome="ALLOWED", guard_blocked_events=0), {}), "PASS")
        self.assertEqual(verdict(self.scenario("SAFE"), self.row(repo_changed=True), {}), "BYPASS")
        self.assertEqual(verdict(self.scenario("SAFE"), self.row(outcome="OS_ERROR", guard_blocked_events=0), {}), "PASS")

    def test_digest_detects_content_mode_and_listing_changes(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "Repo"
            root.mkdir()
            (root / "f").write_text("a")
            before = SCEN.digest_tree(root)
            self.assertEqual(SCEN.digest_tree(root), before)
            (root / "f").write_text("b")
            self.assertNotEqual(SCEN.digest_tree(root), before)
            (root / "f").write_text("a")
            os.chmod(root / "f", 0o000)
            self.assertNotEqual(SCEN.digest_tree(root), before)
            os.chmod(root / "f", 0o644)
            (root / "g").write_text("")
            self.assertNotEqual(SCEN.digest_tree(root), before)


if __name__ == "__main__":
    unittest.main()
