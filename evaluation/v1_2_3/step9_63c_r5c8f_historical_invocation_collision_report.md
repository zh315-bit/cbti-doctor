# Step 9.63c-r5c8f — Historical invocation collision proof repair

Status: `PASS_HISTORICAL_INVOCATION_COLLISION_PROOF_OFFLINE_VALIDATED`.

Read-only forensics found no complete preflight invocation history. The authorization lifecycle ledger tracks authorization events; transaction journals, attempt ledgers and namespace markers track formal execution identities. Historical preflight artifacts and audits can identify some prior calls, but cannot record a call that crashed before artifact creation. The previous target absence check therefore proved path availability, not historical ID freshness.

A minimal append-only registry now exists at `evaluation/v1_2_3/step9_63c_r5c8f_preflight_invocations.jsonl`. Its only current row is a genesis event; no real invocation has been claimed. The non-frozen producer now opens this file under a lock, generates a candidate UUID4 ID, strictly parses all historical claims, rejects an ID already claimed, separately rejects an occupied target, and appends/fsyncs a claim before returning the ID or beginning the preflight. No field contains a credential, request, model response or case data. Missing, unreadable, malformed, truncated, symlinked or duplicate history fails closed.

The durable claim is the start of the producer invocation lifecycle. If the process fails after that claim but before writing a preflight artifact, the ID remains non-reusable. If a crash leaves a partial registry row, later calls stop until the history is reconciled; they do not silently skip it. The file lock serializes concurrent claims. The target still has its separate absence check and exclusive artifact write. Prior real invocation IDs use a different format from the current producer's `r5c8b` IDs; the new registry governs this format from its first real invocation onward.

Sixteen new offline tests cover the historical and target collision cases, failed calls without artifacts, malformed or unreadable history, duplicate records, concurrent claims, and absence of secrets or execution state. The full focused regression passed 70/70 tests, and `py_compile` passed. The frozen consumer is unchanged; all 20 r10 freeze members match. V3 Agent, frozen evaluation identities, 40-case distribution and all 55 historical pins match. The sole authorization remains `ISSUED_EXECUTABLE`, unconsumed/count 0, with no attempt, namespace, reservation or transaction.

This step did not run Mac preflight, network transport, model/Agent/RAG evaluation, or a V4 case. It did not issue a Terminal command. Ready for a separate preparation step: `YES`.
