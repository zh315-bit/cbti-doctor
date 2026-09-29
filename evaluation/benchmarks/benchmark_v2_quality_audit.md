# Benchmark V2 Quality Audit

## Audit scope

This is a static design audit of `benchmark_v2_cases.yaml`. No Agent, RAG, Flask route, tool interface, model or benchmark run was invoked.

## Static validation result

| Check | Result | Notes |
|---|---|---|
| YAML parseability | PASS | Parsed as a mapping with one 40-case list. |
| Required per-case fields | PASS | All 40 cases contain every field declared in `case_required_fields`. |
| Unique IDs | PASS | 40 unique `V2-*` IDs. |
| Task quota | PASS | KQ 10, CA 10, PD 12, DA 8. |
| Difficulty quota | PASS | Easy 10, Medium 20, Hard 10. |
| Language distribution | PASS | zh_brief 10, zh_colloquial 9, zh_distributed 7, mixed_zh_en 5, en 9. |
| Resource distribution | PASS | Eight diary-required DA cases, one diary-optional/not-authorized PD case, two data-dependent unavailable-resource cases; all non-diary cases retain unavailable fixtures by design. |
| Action-path diversity | PASS | Contains all seven requested path forms, with alternatives where order is non-unique. |
| Information-sufficiency diversity | PASS | Includes answer-ready, one/multiple critical gaps, secondary-only gaps, conflicting facts, excess facts, evidence gap, diary required/optional/unavailable. |

## Leakage audit

**PASS with documented safeguards.**

- `user_query_facts` are evaluator-only oracle fields; the channel rules prohibit direct State injection.
- Every `initial_session_facts` mapping is empty, so evaluator knowledge cannot be mistaken for session knowledge.
- `follow_up_facts` are hidden until an actual ASK; they are not answer context.
- Diary facts are stored separately and must be released by `READ_DIARY`; unavailable fixtures contain empty facts.
- Evidence is empty in every Case. No case embeds retrieved answer text as an expected fact.

## Ground-truth and path audit

**PASS, with intentional flexibility.**

- No case requires a unique ASK field when multiple reasonable goal-relevant questions exist.
- Exact sleep-window, dosage, clinical diagnosis, or medical threshold assertions are never required outputs.
- Data-analysis cases require resource reads before data claims; unavailable cases require a limitation rather than invented analysis.
- Conflicting fact cases require clarification or explicit uncertainty rather than selecting a preferred value.
- Knowledge cases do not become diary tasks merely because they mention diaries or timing terms.

## Duplicate and overfitting review

**PASS.**

The review compared case goal, task type, user framing, resource contract, requested answer scope and expected action family against V1.1. V2 has no copied case ID or verbatim V1.1 query. Similar clinical domains are intentional because CBT-I evaluation must include recurring real task families, but each V2 scenario changes at least the goal boundary, language framing, available information, resource contract, or decision ambiguity.

The set does not name existing source code fields as test targets, prescribe YAML-order expectations, or present deliberately malformed language. Some ordinary natural-language sentences may exercise fact extraction or provenance indirectly; that is accepted real-task coverage, not reverse-engineering of a known failure fixture.

## Remaining design limitations

1. This is still a synthetic, manually authored set and is not representative of clinical prevalence or outcome efficacy.
2. The expectation language must be calibrated by future independent reviewers before automatic scoring is attempted.
3. `analysis_focus` in DA-07 is an evaluator-level clarification concept; any future runner must map it through ordinary user text rather than direct State mutation.
4. V2 has not yet been run, scored, or calibrated; no V2 performance conclusion exists.

## Freeze recommendation

**Recommend freezing Benchmark V2 Evaluation Set as `design_only_unrun` after acceptance.** Freeze the YAML and this audit before any V2 Agent run. Any later edit must create a new named dataset version/changelog rather than overwrite the accepted V2 cases.
