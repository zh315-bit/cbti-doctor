# Step 9.32 — Architecture Repair Design & Paired Evaluation Preregistration

**Status: DESIGN ONLY; no Agent implementation, paired evaluation, model call, or V5 creation.**

## Baseline identity

- Baseline Agent aggregate SHA-256: `4e2bffea0d7eaa9299074a960df84a1806b3ae9d4930662929abc58ca5b2ae79`; current 26-entry candidate inventory matches the Step 9.26 final candidate freeze.
- Candidate manifest: `evaluation/v1_2_3/step9_26_final_candidate_freeze.json` (`2de40b76bf0ad6d6c3be68294fb8b390d8c6e675c328ac59e22ec78ec010282e`); final candidate manifest: `evaluation/v1_2_3/step9_19_final_candidate_manifest.json`.
- Reconstruction snapshot: `evaluation/v1_2_3/step9_32_baseline_agent_snapshot.tar.gz`, SHA-256 `f00eb91a8020dbff5e87c4dc5d7c58c02ebeaf713acb8451057de4a60a7dd88a`, 101 files. It contains non-secret frozen source/config/RAG assets and excludes `.env`/secret values. Since this workspace has no Git commit object, the snapshot is the reconstructable old Agent, not a Git branch/ref.
- Config hash: `11323b934e451e6fc39b12e84d82387d83ba4e98c2df148452cf113566b210e5`. RAG config/corpus/index hash: `58467abc2abafce62e8d71713684802f64a35946accf35c08007e67b0edd60a5`. Model profile: `deepseek-flash` at `https://api.deepseek.com`; temperature remains baseline default/unset, no seed relied upon, thinking disabled, timeout 120 s, max_retries=1. Credential value and presence were not read or captured.

## Architecture repair package

### R1 — evidence path independent of personal fact completeness

Keep `USER_FACTS`, `EXTERNAL_EVIDENCE`, and `DIARY_DATA` as distinct dependencies. Required evidence retrieval/diary reading remains actionable when unrelated personal fields are unknown; personal incompleteness constrains personalization only. A successful result satisfies only its matching dependency and carries provenance into answer context. An unavailable/failed resource is recorded once and yields a bounded answer, never fabricated evidence.

### R2 — value-gated precondition and safe fallback

Always fail closed for safety-critical and execution-critical gates. A decision-critical field is hard only when plausible values change an action materially and no safe bounded fallback exists. Soft/detail fields are ASKed only when the target is genuinely unknown, not already asked/unavailable, and resolving it changes safety, execution, direction, next action, or material answer scope. Independent required retrieval may proceed without waiting for unrelated optional facts, but cannot replace a necessary safety/execution ASK.

### R3 — asserted fact and unavailable-target state

Canonical statuses are ASSERTED, DERIVED, RETRIEVED, UNKNOWN, UNAVAILABLE, NOT_APPLICABLE, INVALID. Preserve provenance/time/scope through every downstream layer. Retrieved evidence cannot satisfy a personal fact requirement by default. UNAVAILABLE persists; semantic-target/alias matching prevents duplicate or adjacent re-asks. Conflicts are retained and marked invalid/conflicted, not silently last-write-wins; clarification is asked only when material under R2.

### Ordering and boundaries

Normalize facts/statuses → resolve requirements and independent dependencies → classify hard gates/materiality → estimate information value → generate independent candidates → select/execute actions → update the matching dependency/provenance → build validated answer context. The machine-readable design specifies each trigger, required state, blocking condition, safe fallback and invariant boundary.

### Step 9.33 implementation scope

12 production modules are proposed: input understanding, State, requirements, dependency resolver, preconditions, information value, candidates, acquisition gate, policy, state update, runner and answer generation. Exact functions, rationale, R1/R2/R3 ownership, and frozen files that must not be touched are enumerated in `step9_32_repair_design.json`. No code was changed in Step 9.32.

## Synthetic regression suite design

Ten new fixture categories are preregistered: independent required evidence with missing personal context; material missing fact; immaterial missing fact; missing safety gate; asserted fact retention; unavailable target; unavailable resource; evidence projection; evidence-not-required; and conflicting facts. The examples are newly formulated and do not use V4 IDs, text, or near-paraphrases. Plan status is `PLANNED_NOT_RUN`.

## Paired old-vs-new preregistration

Baseline is the frozen pre-Step-9.33 Agent snapshot; treatment is the separately frozen R1+R2+R3 Agent. Both arms must use identical V4 bytes/order, model configuration, RAG corpus, tools, runner, rubric, metric registry, reviewer protocol and environment. A fresh baseline arm is required; the previous official V4 result alone is not substituted for a matched run.

Primary M1–M5: low-value ASK rate; task completion; harmful-failure count; necessary-ASK preservation; critical-failure count. Secondary metrics: validity, overall/task means (KQ/CA/PD/DA), acquisition/tool/turn/step rates and mean latency. Definitions and denominators inherit the frozen registry. Hypotheses H1–H7 are directional and have no invented effect-size thresholds. Binary outcomes use paired discordance and McNemar only where assumptions/sample size warrant; scores use per-case paired deltas and descriptive summaries. All counts include numerators/denominators.

One attempt, no retries: preserve partial append-only traces; infrastructure faults remain distinct from Agent outcomes; no rerun or overwrite. If any required pair is incomplete, report it as incomplete/exploratory and do not claim resume comparative eligibility. The baseline temperature is preserved as currently unset/default; no seed is assumed.

Resume comparative claim eligibility is **NO now**. A qualified development comparison may become eligible only with protocol integrity, no critical-failure increase, no necessary-ASK regression, at least one primary target improvement, identical conditions, complete denominators, and no cherry-picking. This does not permit clinical or generalization claims.

## V4/V5 boundary and integrity

V4 is **DEVELOPMENT / POSTMORTEM / PAIRED REGRESSION EVIDENCE**, not unseen after repair-informed development. V5 is a future sealed unseen holdout; it is not created or inspected here. Step 9.32 did not modify Agent, V4 data/results/adjudication/aggregate, rubric or registry; it made no model/Agent/RAG calls and ran no evaluation.
