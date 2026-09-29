# Step 9.13 — Final Frozen Identity Summary

Evaluation identity: `clean-evaluation-v1_2_3-20260922-01`.

| Domain | Frozen SHA-256 | Current audit state |
| --- | --- | --- |
| Agent behavior aggregate | `ee914db7b8b5538c5607fdff34cff9083f6d069d50cf342964ae91c8a6446927` | MATCH |
| Benchmark V2 | `dfa9b9e5a12b0017fa68d344d01b313ebc29e583b933fbe1e93c125f55ecafd2` | MATCH; 40 cases |
| Scoring aggregate | `f742a8f8af7c8747818dadad81621c15d12d74f50538019913dfe18ab53bf59b` | MATCH |
| Step 9.11 Harness aggregate | `43a4ccda69272e9eb0d6a02eb7f3812d386d47fd7ca4aa48c0d0ece925cca455` | Legacy manifest; intentionally not current after Step 9.12b |
| Step 9.12b Harness aggregate | `56df7699114ff8f09ad7ace091fd4fc3224ff69880b3b84bf37591c5f2ad20cf` | MATCH in observer-only freeze |

The Step 9.11 Agent, Benchmark, and Scoring freezes remain immutable. The Step 9.12b change is limited to observability, but the formal runner does not yet consume the new Harness freeze.

The workspace's persisted preflight artifact remains an old FAIL artifact. The user-reported newer local PASS is useful operational context but is not present as an auditable artifact in this workspace.
