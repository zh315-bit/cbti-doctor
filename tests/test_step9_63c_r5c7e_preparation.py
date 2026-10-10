from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from scripts import preflight_step9_63c_r5c7_mac_local as preflight

ROOT = Path(__file__).resolve().parents[1]


class Step963cR5c7ePreparationTests(unittest.TestCase):
    def test_r5c7e_artifact_is_preserved_as_historical_evidence(self):
        path = ROOT / "evaluation/v1_2_3/step9_63c_r5c7e_preflight-step9_63c-r10-7decee88a4c8439fb3f30ffb68240b31_mac_local_final_preclearance.json"
        self.assertTrue(path.is_file())
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),
                         "f07d8380e0d445938e0a4bd7b212380459a983ccfe8f04bc49ab2996b43cf4b7")

    def test_r10_authorization_archive_matches_record_and_is_not_live(self):
        # Step 9.63c-r5c10ad AR-5: previously asserted the live r10 snapshot was
        # ISSUED_EXECUTABLE. Under the r11-only resolver r10 is archival evidence only:
        # assert its recorded bytes and recorded unconsumed content, and that the live
        # snapshot fails closed without touching those bytes.
        archive = {
            "evaluation/v1_2_3/step9_63c_r5c5b_runner_freeze_r10.json":
                "d24244235e51e7bf6c8567880c654fe3fd73b87fa1bfe1ab0f10dfdc94db2693",
            "evaluation/v1_2_3/step9_63c_r5c6_r10_v3_authorization_manifest.json":
                "beac52d1ed3bc11efa02b1a924a8abc7b210171bf5cc1b7910011a6ef9741241",
        }
        digests = lambda: {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in archive}
        self.assertEqual(digests(), archive)
        self.assertEqual((preflight.AUTH_SHA256, preflight.EXPECTED_RUNNER_SHA256),
                         tuple(archive.values())[::-1])
        auth = json.loads((ROOT / "evaluation/v1_2_3/step9_63c_r5c6_r10_v3_authorization_manifest.json")
                          .read_text(encoding="utf-8"))
        self.assertEqual((auth["runner_freeze_revision"], auth["runner_freeze_sha256"]),
                         ("r10", archive["evaluation/v1_2_3/step9_63c_r5c5b_runner_freeze_r10.json"]))
        self.assertEqual((auth["authorization_status"], auth["consumed"],
                          auth["authorization_consumption_count"]), ("ISSUED_NOT_CONSUMED", False, 0))
        with self.assertRaises(RuntimeError) as raised:
            preflight._snapshot()
        self.assertIn(str(raised.exception),
                      ("current runner identity pointer is missing or unsafe", "R10_FREEZE_MISMATCH"))
        self.assertEqual(digests(), archive)


if __name__ == "__main__":
    unittest.main()
