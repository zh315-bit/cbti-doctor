"""Offline Step 8.1 design analysis over frozen Step 7.4/7.5 artifacts."""
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evaluation/v1_2'
OUT.mkdir(exist_ok=True)
old=json.loads((ROOT/'evaluation/v1_1/step7_5_ask_quality_analysis.json').read_text())
metrics=json.loads((ROOT/'evaluation/v1_1/v1_vs_v1_1_metrics.json').read_text())
quality=old['ask_quality_reanalysis']
total=quality['total_ASK']
counts=metrics['v1_1']['ask_counts']
iv_counts={'HIGH':counts['necessary'],'MEDIUM':counts['useful_but_optional'],'LOW':0,'NONE':counts['redundant']+counts['irrelevant']}
retro={'framework':'ordinal_information_value_v1_2_design','input_ASK':total,'mapping':{'necessary':{'information_value':'HIGH','reason':'counterfactual value can change next action or core answer scope'},'useful_but_optional':{'information_value':'MEDIUM','reason':'may change personalization/scope, but does not always block a bounded answer'},'redundant':{'information_value':'NONE','reason':'semantic equivalent already present in State/provenance'},'irrelevant':{'information_value':'NONE','reason':'does not affect current goal or safe answer'}},'information_value_counts':iv_counts,'rates':{k:round(v/total,4) for k,v in iv_counts.items()},'cost_model':{'ASK':'MEDIUM initially; increases with prior ASK count, repeated target, and cognitive burden','RETRIEVE':'MEDIUM; tool/latency and evidence relevance cost','READ_DIARY':'LOW when available and relevant, HIGH/unavailable when missing','ANSWER':'risk cost, increasing with uncertainty, personalization, and grounding exposure'},'stop_rule':'stop acquisition when no remaining fact has HIGH value, or MEDIUM value that changes answer scope enough to justify its cost and answer risk'}
(OUT/'step8_1_information_value_analysis.json').write_text(json.dumps(retro,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

pd='''# PD Failure Patterns from Frozen V1.1 Traces

This analysis uses only the 9 PD six-ASK-limit traces in the frozen Step 7.4
raw artifacts. It does not introduce case-specific rules.

## Pattern 1: Requirements Completeness Masquerades as Decision Value

The agent keeps requesting total sleep, awakenings, and recent pattern after a
bounded directional answer is already possible. These fields can be useful for
a full prescription, but are not automatically worth another user turn for a
narrow direction question. Their default value is LOW or MEDIUM, not HIGH.

## Pattern 2: Extraction Failure Expands the Remaining Set

When explicit facts do not enter State, every downstream field appears missing.
The information-value layer cannot rescue a missing fact that was never
represented; it only sees a falsely large uncertainty set. This is a combined
Step 7.1 plus sufficiency failure.

## Pattern 3: No Diminishing-Return Threshold

The sixth ASK can pass the same eligibility shape as the first because the
current policy has no increasing acquisition threshold. V1.2 should require
progressively stronger counterfactual impact as prior ASK count and cognitive
burden rise; it should not use a fixed maximum-ASK rule.

## Pattern 4: Resource/Answer Alternatives Are Not Compared at Value Level

A diary or bounded answer can sometimes dominate another ASK. The decision must
compare READ_DIARY, RETRIEVE, ASK, and ANSWER using value, cost, and answer-risk,
not only whether a requirement remains missing.

## Pattern 5: Detail Improvement Is Treated as Personalization Necessity

Some follow-up facts enrich an answer without changing its direction or safety
scope. These should be LOW value and omitted once the bounded answer is adequate.
'''
(OUT/'step8_1_pd_failure_patterns.md').write_text(pd,encoding='utf-8')

report=f'''# Step 8.1 Information Value Design Report

Date: 2026-09-20

## Scope

Design and offline analysis only. No Agent behavior, Benchmark V2, rubric, or
historical result was modified. No Agent or Benchmark V2 rerun was performed.

## Proposed Ordinal Information Value

Each remaining fact receives `HIGH`, `MEDIUM`, `LOW`, or `NONE` from six
interpretable dimensions: decision impact, current uncertainty, answer-scope
impact, acquisition cost, resource alternatives, and redundancy.

The core counterfactual test is: *if a plausible value of this fact were known,
could the next action or bounded answer scope change?* Decision-changing facts
default to HIGH; answer-scope-changing facts to MEDIUM/HIGH; detail-only facts
to LOW; redundant or irrelevant facts to NONE. Approximate/range values lower
uncertainty but do not automatically create a refinement ASK.

Retrospective classification of the 112 V1.1 ASK actions:

| Prior label | Proposed value | Count |
|---|---:|---:|
| necessary | HIGH | {iv_counts['HIGH']} |
| useful-but-optional | MEDIUM | {iv_counts['MEDIUM']} |
| redundant | NONE | {counts['redundant']} |
| irrelevant | NONE | {counts['irrelevant']} |

No action was classified LOW in the coarse retrospective because the frozen
trace labels do not preserve enough semantic detail to distinguish every
detail-improving ASK from an irrelevant one. V1.2 should add that distinction
before implementation.

## Proposed Acquisition Cost

`ASK` starts at MEDIUM and rises with previous ASK count, repeated target,
cognitive burden, and unresolved prior answers. `RETRIEVE` is MEDIUM for tool
and latency cost. `READ_DIARY` is LOW when available/relevant and unavailable
otherwise. `ANSWER` has non-zero risk cost: uncertainty, grounding, and
personalization risk increase when the answer is more specific.

The decision is not “minimize ASK”; it is to compare information value against
acquisition cost and answer risk. A later ASK must clear a higher ordinal
threshold than an earlier ASK, without hard-coding a fixed maximum count.

## Stop Rule

Stop gathering when no remaining fact has HIGH value, or when MEDIUM value does
not change answer scope enough to justify its cost and answer risk. Missing
information may remain while ANSWER is selected with a bounded limitation.

## Frozen V1.1 Evidence

V1.1 had {total} ASK ({total/40:.3f}/case), 34.8% redundant and 38.4%
irrelevant under Step 7.5's trace-only labels. PD remained the bottleneck at
5.333 ASK/case and 9 six-ASK-limit cases. This supports designing an
information-value layer, but does not prove that the proposed model improves
behavior.

## Candidate V1.2 Flow

```text
Goal → State → Sufficiency → Remaining Information
     → Information Value (HIGH/MEDIUM/LOW/NONE)
     → Cost and answer-risk comparison
     → ASK / RETRIEVE / READ_DIARY / ANSWER
```

V1.1 primarily asks whether a field is missing and decision-relevant. V1.2
would add counterfactual value, explicit acquisition cost, resource alternatives,
diminishing returns, and a stop rule before candidate generation/selection.
This is a design proposal only.

## Relationship to Calibrate-Then-Act

The design is conceptually inspired by Calibrate-Then-Act: estimate whether
additional information is worth acquiring before acting, and account for
uncertainty and action cost. CBTI-Doctor currently implements interpretable
heuristics, State/provenance, sufficiency, and bounded answers. It does not
implement CTA, calibrated expected utility, learned probabilities, or a
validated calibration procedure. The proposed ordinal values remain heuristic.

## V1.2 Evaluation Plan

Benchmark V2 is now a development/regression set, not final independent
evidence. After V1.2 development is frozen, create and freeze a held-out
Benchmark V3, or preregister a leakage-resistant protocol. Compare V1.1 vs V1.2
on task score, ASK/case, redundant/irrelevant/necessary/useful ASK rates,
six-ASK-limit cases, critical failures, premature-answer rate, and resource use.
Do not create V3 in Step 8.1.

## Limitations

The retrospective labels are coarse and inherited from Step 7.5. The frozen
trace does not expose rejected ASK candidates, so gate-blocking and marginal
value cannot be measured directly. No causal claim, calibration claim, or
general superiority claim is supported.
'''
(OUT/'step8_1_design_report.md').write_text(report,encoding='utf-8')
