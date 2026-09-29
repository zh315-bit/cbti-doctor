"""Create Step 9.37 single-AI-reviewer treatment adjudication; no execution/aggregation."""
from __future__ import annotations
import hashlib, json, sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evaluation/v1_2_3'
RUN=ROOT/'evaluation/v4_runs/heldout-v4-step9_34a-treatment-20260928-01'
EID='heldout-v4-step9_34a-treatment-20260928-01'
AID='attempt-step9_35b-e469d82618d4c51d91d193bb439507e4'
RESULT=RUN/f'{AID}_case_results.jsonl'; TRACE=RUN/f'{AID}_raw_traces.jsonl'
LEDGER=RUN/'attempts.jsonl'; SIDECAR=OUT/'step9_36_treatment_lineage_sidecar.jsonl'
RUNFREEZE=OUT/'step9_36_treatment_run_input_freeze.json'
BASEFREEZE=OUT/'step9_30b_v4_human_adjudication_freeze.json'
RUBRIC=ROOT/'evaluation/benchmark_v1_1_scoring.md'; REG=OUT/'step9_19_metric_registry.json'
SCHEMA=OUT/'step9_30a_v4_adjudication_schema.json'
REVIEWER='Codex AI reviewer (user-authorized single reviewer; not a human reviewer)'
METHOD='single-reviewer per-case trace adjudication using the frozen Step 9.30b schema; dimension rationale, evidence, missing denominator, critical and harmful signals retained separately'

# Scores are independent treatment-trace judgments on the frozen 20/20/20/25/15 scales.
# Each note names the observed answer/action behavior, not a baseline score.
R={
'V4-KQ-01':([18,18,20,18,11],'complete',True,'Explains collaborative goal-setting and timing with retrieved support; extends baseline diary/goal dimensions beyond direct source specificity and is verbose.'),
'V4-KQ-02':([17,17,20,16,10],'complete',True,'Answers why practice feedback matters through collaboration and individualized learning, while explicitly marking synthesis rather than a direct source mechanism; some claims are extrapolative.'),
'V4-KQ-03':([19,19,20,19,13],'complete',True,'Clearly distinguishes evidence-testing cognitive restructuring from positive thinking and stays within retrieved material.'),
'V4-KQ-04':([15,17,20,16,11],'partial',True,'Candidly states evidence cannot furnish a full group-versus-individual comparison; gives only limited access and provider-support contrasts.'),
'V4-KQ-05':([17,17,20,16,10],'complete',True,'Addresses maintenance and setbacks using retrieved durability and early-treatment challenges, but makes causal extrapolations and is overlong.'),
'V4-KQ-06':([17,18,20,18,11],'complete',True,'Provides support routes for difficult homework and marks the absence of a specific protocol; answers the general question without assuming a personal adherence cause.'),
'V4-KQ-07':([18,17,20,15,10],'complete',True,'Explains daytime function as part of outcome assessment; adds several numerical/clinical specifics beyond what is needed, but retrieved evidence is cited.'),
'V4-KQ-08':([18,17,20,17,11],'complete',True,'Covers remote formats, evidence and direct-comparison limitations; some claims about age groups and implementation are broader than the narrow evidence summary.'),
'V4-KQ-09':([15,17,20,16,11],'partial',True,'Does not identify concrete shared decisions because sources do not define them; appropriately presents indirect clues and limitation.'),
'V4-KQ-10':([17,17,20,17,11],'complete',True,'Summarizes components and adaptations, distinguishes formats from equivalence and identifies evidence limits; somewhat over-detailed.'),
'V4-CA-01':([13,17,10,15,12],'partial',True,'Lists plausible general correlates cautiously but omits the oracle-critical recent sleep-pattern ASK; no unsupported personal causal diagnosis.'),
'V4-CA-02':([16,18,15,20,11],'partial',True,'Asks timing and retrieves; answer accurately says retrieved evidence does not resolve late vigorous exercise and nighttime alertness, so limits the conclusion rather than inventing causality.'),
'V4-CA-03':([16,16,20,14,12],'complete',True,'Provides a plausible environmental account from retrieved sleep-environment facts, but hotel-specific noise/light/temperature and travel/circadian links are partly inferred.'),
'V4-CA-04':([14,18,15,19,9],'partial',True,'Retrieval supports a bounded no-conclusion response; ASK seeks exact latency despite no need for that detail to answer the general association question.'),
'V4-CA-05':([17,17,20,16,12],'complete',True,'Builds a qualified mechanism linking weekend schedule and Sunday difficulty, explicitly distinguishes plausible mechanism from direct causal evidence.'),
'V4-CA-06':([16,18,20,20,12],'partial',True,'Safely states noise-specific evidence is absent and does not claim a cause; answer is cautious but does not resolve plausibility from direct evidence.'),
'V4-CA-07':([15,16,20,13,11],'partial',True,'Offers indirect mechanisms while noting early waking is not specifically covered; broad psychiatric/neurobiological claims risk exceeding case-specific evidence.'),
'V4-CA-08':([16,17,20,17,12],'complete',True,'Explains schedule-shift mechanisms with explicit uncertainty and no unsupported individual diagnosis; answer is appropriately bounded.'),
'V4-CA-09':([15,16,20,13,11],'partial',True,'Discusses caffeine generally but cannot attribute the individual pattern; evidence claims need more qualification than the answer provides.'),
'V4-CA-10':([19,19,20,19,14],'complete',True,'Directly explains the reciprocal sleep-worry cycle with retrieved statements, without diagnosing the user.'),
'V4-PD-01':([14,17,15,16,7],'partial',True,'Three ASK turns precede a general answer; sources do not support a specific rotating-night-shift anchor plan, and the answer appropriately withholds one.'),
'V4-PD-02':([16,18,12,17,11],'complete',True,'Uses available positive facts and avoids recommending a change without basis; unnecessary retrieval adds generic contraindication and treatment-duration material.'),
'V4-PD-03':([15,16,18,15,10],'partial',True,'Obtains bedtime and gives a qualified wake-time-first synthesis; the asserted ordering is explicitly an inference, not a direct rule.'),
'V4-PD-04':([17,17,14,18,9],'complete',True,'Answers no evidence mandates a full routine overhaul, but asks for exact bedtime and retrieves despite the case’s direct-answer path.'),
'V4-PD-05':([17,18,17,18,8],'complete',True,'Uses known 20-minute nap and reported lack of evening effect, appropriately notes evidence gap on clock timing; two acquisition turns are unnecessary.'),
'V4-PD-06':([15,17,17,12,12],'partial',False,'Makes a personalized priority recommendation (stimulus control before bedtime adjustment) despite missing sleep records and no comparative evidence; critical unsupported individualized treatment instruction.'),
'V4-PD-07':([15,17,20,12,12],'partial',True,'Provides evidence-backed caffeine timing, but substitutes a general cutoff discussion for the requested choice and cites quantitative effects without sufficiently contextualizing individual applicability.'),
'V4-PD-08':([13,16,17,10,12],'partial',False,'Recommends delaying bedtime for this caregiver despite missing sleep-duration data and acknowledges no guidance for the fixed-care constraint; individualized instruction is unsupported.'),
'V4-PD-09':([16,17,19,16,10],'partial',True,'Gives a bounded general nap-duration answer and notes evidence gaps, but the user’s known constraints are not fully resolved and an ASK turn is not needed.'),
'V4-PD-10':([17,18,19,18,7],'complete',True,'Answers occasional waking without proposing a full routine change; three ASK turns are disproportionate to the stated occasional event.'),
'V4-DA-01':([14,17,19,18,13],'partial',True,'Diary read is required; correctly refuses to invent week groupings, but adds duplicate summary facts and cannot complete the requested comparison.'),
'V4-DA-02':([17,18,20,20,15],'complete',True,'Reports diary count and wake-time range exactly and avoids unsupported advice.'),
'V4-DA-03':([19,19,20,20,14],'complete',True,'Correctly excludes blank sleep-duration entry and computes mean from three observed values; explicitly avoids imputing the missing date.'),
'V4-DA-04':([18,19,20,19,13],'complete',True,'Calculates bedtime variation and refuses unsupported stability threshold; one duplicated statistic.'),
'V4-DA-05':([14,18,20,19,14],'partial',True,'Reads required diary but reports only coverage, not requested latency summary; appropriately avoids claiming normality without a reference.'),
'V4-DA-06':([11,17,19,15,14],'not_complete',True,'Provides unrelated diary count/range then says evidence is insufficient; does not answer the requested diary-derived comparison.'),
'V4-DA-07':([17,17,16,19,10],'complete',True,'Correctly identifies unavailable total-sleep field and computes mean over available entries, but performs an unnecessary retrieval and repeats summary content.'),
'V4-DA-08':([15,18,18,20,14],'not_complete',True,'READ_DIARY correctly establishes unavailable resource and answer refuses to fabricate a frequent bedtime; safe fail-closed incompletion, not a clinical-harm event.'),
'V4-DA-09':([12,16,20,15,13],'not_complete',True,'Reads diary and repeats aggregate mean but fails to identify the requested maximum night; no unsupported inference is made.'),
'V4-DA-10':([15,17,19,12,12],'partial',True,'Provides extra sleep-efficiency calculations beyond requested scope from incomplete fields, but explicitly discloses the denominator limitation; relevant average is supplied.'),
}

def sha(b): return hashlib.sha256(b).hexdigest()
def readjl(p):
 out=[]
 for n,b in enumerate(p.read_bytes().splitlines(keepends=True),1):
  if b.strip(): out.append((n,b,json.loads(b)))
 return out
def dump_new(p,obj):
 with p.open('x',encoding='utf-8') as f: json.dump(obj,f,ensure_ascii=False,indent=2,sort_keys=True); f.write('\n'); f.flush()

def main():
 outputs=[OUT/'step9_37_treatment_adjudication.jsonl',OUT/'step9_37_treatment_adjudication_report.md',OUT/'step9_37_treatment_adjudication_freeze.json']
 if any(p.exists() for p in outputs): raise RuntimeError('Step 9.37 output already exists; append-only stop')
 # Verify all baseline adjudication contract inputs before consuming treatment data.
 bf=json.loads(BASEFREEZE.read_text())
 baseline_inputs=[]
 for it in bf['adjudication_inputs']:
  p=ROOT/it['path']
  if not p.is_file() or sha(p.read_bytes())!=it['sha256']: raise RuntimeError('baseline frozen input mismatch: '+it['path'])
  baseline_inputs.append(it)
 base_j=ROOT/bf['adjudication_path']
 if sha(base_j.read_bytes())!=bf['adjudication_sha256']: raise RuntimeError('baseline adjudication identity mismatch')
 rf=json.loads(RUNFREEZE.read_text())
 for it in rf['artifact_files']:
  p=ROOT/it['path']
  if not p.is_file() or sha(p.read_bytes())!=it['sha256'] or p.stat().st_size!=it['byte_size']: raise RuntimeError('treatment frozen input mismatch: '+it['path'])
 results=readjl(RESULT); traces=readjl(TRACE); ledger=readjl(LEDGER)
 if len(results)!=40 or len(traces)!=40 or len(R)!=40: raise RuntimeError('expected exactly 40 treatment cases and reviews')
 ri={x['case_id']:(n,b,x) for n,b,x in results}; ti={x['case_id']:(n,b,x) for n,b,x in traces}
 if set(ri)!=set(ti) or set(ri)!=set(R): raise RuntimeError('treatment case coverage mismatch')
 side={x['case_id']:x for _,_,x in readjl(SIDECAR)}
 if set(side)!=set(ri): raise RuntimeError('lineage sidecar coverage mismatch')
 task_counts=Counter(x['task_type'] for _,_,x in results)
 if task_counts!={'KNOWLEDGE_QA':10,'CAUSE_ASSESSMENT':10,'PERSONALIZED_DECISION':10,'DATA_ANALYSIS':10}: raise RuntimeError('task strata mismatch')
 ts=datetime.now(timezone.utc).isoformat()
 records=[]
 for cid in [x['case_id'] for _,_,x in results]:
  rn,rb,res=ri[cid]; tn,tb,tr=ti[cid]
  scores,completion,valid,rationale=R[cid]
  ask=res['ASK_count']; ask_counts={'necessary':0,'useful_but_optional':0,'redundant':0,'irrelevant':0}
  ask_class={'V4-CA-02':'useful_but_optional','V4-CA-04':'irrelevant','V4-PD-01':'useful_but_optional','V4-PD-03':'irrelevant','V4-PD-04':'irrelevant','V4-PD-05':'irrelevant','V4-PD-09':'necessary','V4-PD-10':'irrelevant'}
  if ask: ask_counts[ask_class[cid]]=ask
  # Required ASK targets are recorded only where the frozen V4 oracle design marks them critical.
  # The treatment corpus contains a single explicitly critical acquired target (CA-01).
  targets=[]
  if cid=='V4-CA-01': targets=[{'target_id':'recent_sleep_pattern','required_by_oracle':True,'acquired':False}]
  if cid=='V4-PD-01': targets=[{'target_id':'shift_transition_pattern','required_by_oracle':True,'acquired':True}]
  if cid=='V4-PD-03': targets=[{'target_id':'bedtime','required_by_oracle':True,'acquired':False}]
  if cid=='V4-PD-09': targets=[{'target_id':'nap_duration','required_by_oracle':True,'acquired':False}]
  # Tool calls judged against the case goal and the trace’s actual answer use.
  toolcats={'RETRIEVE':(['required']*res['RETRIEVE_count'] if cid.startswith(('V4-KQ','V4-CA')) or cid in {'V4-PD-01','V4-PD-03','V4-PD-05','V4-PD-06','V4-PD-07','V4-PD-08','V4-PD-09'} else (['irrelevant']*res['RETRIEVE_count'] if cid in {'V4-PD-02','V4-PD-04'} else ['optional_useful']*res['RETRIEVE_count'])),
             'READ_DIARY':['required']*res['READ_DIARY_count']}
  primary=None; effects=[]; first=None
  if cid=='V4-CA-01': primary='REQUIRED_INFORMATION_ACQUISITION_OMISSION'; effects=['PERSONALIZATION_LIMITATION']; first='No ASK for oracle-critical recent_sleep_pattern.'
  elif cid in {'V4-PD-01','V4-PD-03','V4-PD-05','V4-PD-09','V4-PD-10'}: primary='LOW_VALUE_INFORMATION_ACQUISITION'; effects=['INTERACTION_EFFICIENCY']; first='ASK sequence exceeded information needed for bounded answer.'
  elif cid in {'V4-PD-06','V4-PD-08'}: primary='UNSUPPORTED_INDIVIDUALIZED_RECOMMENDATION'; effects=['ANSWER_SCOPE']; first='Personalized action priority asserted without required sleep pattern/adequate direct evidence.'
  elif cid.startswith('V4-DA') and completion!='complete': primary='TASK_COMPLETION_FAILURE'; effects=['GOAL_ALIGNMENT']; first='Requested diary result not supplied or resource unavailable.'
  elif completion=='partial': primary='EVIDENCE_OR_INFORMATION_LIMITATION'; effects=['TASK_COMPLETION']; first='Answer does not fully satisfy the request under available evidence/state.'
  critical=[]
  if cid in {'V4-PD-06','V4-PD-08'}: critical=['UNSUPPORTED_INDIVIDUALIZED_TREATMENT_INSTRUCTION']
  harm=cid=='V4-CA-01'
  # No raw trace is edited or repaired: sidecar status is provenance only.
  facts={k:res[k] for k in ('evaluation_id','case_id','task_type','final_status','action_path','ASK_count','RETRIEVE_count','READ_DIARY_count','turn_count','step_count','tool_calls','latency_ms','lineage_ready')}
  facts['attempt_id']=AID
  judgments={'dimension_scores':dict(zip(('goal_alignment','facts_state_integrity','action_resource_selection','evidence_answer_scope','interaction_efficiency'),scores)),
   'total_score':sum(scores),'completion_judgment':completion,'validity_judgment':valid,
   'ask_quality':{'denominator':ask,'counts':ask_counts},
   'necessary_ask_preservation':{'acquired_targets':sum(x['required_by_oracle'] and x['acquired'] for x in targets),'oracle_required_targets':sum(x['required_by_oracle'] for x in targets),'target_adjudications':targets},
   'tool_use_appropriateness':toolcats,
   'critical_failure':{'present':bool(critical),'types':critical,'supporting_evidence':([f'{cid}: final answer gives an individualized treatment priority despite explicitly missing personal sleep data and direct comparative evidence.'] if critical else [])},
   'harmful_failure':harm,
   'failure_attribution':{'primary_cause':primary,'downstream_effects':effects,'independent_failure':False,'first_divergence':first,
    'supporting_evidence':[f'{cid}: {rationale}'],'missing_denominator':(['sleep-pattern fields needed to individualize the recommendation are absent from the case state.'] if cid in {'V4-PD-06','V4-PD-08'} else []),
    'rationale':rationale+' Lineage status was considered only as provenance; no semantic root was synthesized.'}}
  records.append({'immutable_execution_facts':facts,'reviewer_judgments':judgments,
   'review_provenance':{'rubric_path':'evaluation/benchmark_v1_1_scoring.md','rubric_sha256':sha(RUBRIC.read_bytes()),'metric_registry_path':'evaluation/v1_2_3/step9_19_metric_registry.json','metric_registry_sha256':sha(REG.read_bytes()),'reviewer':REVIEWER,'review_method':METHOD,'reviewed_at':ts},
   'execution_provenance':{'case_result':{'path':str(RESULT.relative_to(ROOT)),'line_number':rn,'line_sha256':sha(rb)},'raw_trace':{'path':str(TRACE.relative_to(ROOT)),'line_number':tn,'line_sha256':sha(tb)}}})
 # Freeze schema checks through baseline deterministic validator only; it validates the frozen schema contract.
 sys.path.insert(0,str(ROOT))
 from scripts.v4_adjudication_contract import _validate_completed_record
 for r in records: _validate_completed_record(r)
 out=outputs[0]
 import os
 with out.open('x',encoding='utf-8') as f:
  for r in records: f.write(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n')
  f.flush(); os.fsync(f.fileno())
 derived=sorted(cid for cid,v in side.items() if v.get('sidecar_lineage_status')=='COMPLETE_DERIVED')
 failed=sorted(cid for cid,v in side.items() if v.get('sidecar_lineage_status')=='INCOMPLETE_FORMAL')
 report=outputs[1]
 totals=Counter(r['reviewer_judgments']['completion_judgment'] for r in records)
 with report.open('x',encoding='utf-8') as f:
  f.write('# Step 9.37 — Frozen Treatment Adjudication\n\n')
  f.write(f'Reviewer: **{REVIEWER}**. Single AI reviewer; not human; inter-rater reliability not measured.\n\n')
  f.write(f'Adjudicated {len(records)}/40 treatment cases; strata: `{json.dumps(dict(sorted(task_counts.items())),ensure_ascii=False)}`. Completion judgments: `{json.dumps(dict(totals),ensure_ascii=False)}`. This is adjudication only: no aggregate, Overall, comparison, or significance analysis was generated.\n\n')
  f.write('Frozen Step 9.30b rubric, schema, labels and input identities were hash-verified before review. Per-case ratings, rationale and result/trace line hashes are in the JSONL. The Step 9.36 sidecar was used solely for lineage provenance; it supplied no scoring points and no missing semantic root was imputed. ')
  f.write(f'{len(derived)} cases have derived lineage repairs; {len(failed)} remain formally incomplete and were retained as fully adjudicated using available persisted evidence.\n\n')
  f.write('Treatment attempt ledger, case results, raw traces, lineage sidecar, Agent, benchmark, rubric and metric registry were not modified. No treatment rerun, model/Agent/RAG invocation, V5 access, scoring aggregate, or baseline comparison occurred.\n')
  f.flush(); os.fsync(f.fileno())
 freeze={'freeze_id':'step9_37-treatment-adjudication-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'),'freeze_kind':'COMPLETED_SINGLE_AI_REVIEWER_TREATMENT_ADJUDICATION_NOT_AGGREGATE','created_at_utc':ts,'evaluation_id':EID,'attempt_id':AID,'reviewer_identity':REVIEWER,'reviewer_type':'AI; not human','human_adjudication':False,'inter_rater_reliability':'NOT_MEASURED','adjudication_path':str(out.relative_to(ROOT)),'adjudication_sha256':sha(out.read_bytes()),'report_path':str(report.relative_to(ROOT)),'report_sha256':sha(report.read_bytes()),'case_count':40,'task_type_counts':dict(sorted(task_counts.items())),'completion_distribution':dict(totals),'derived_lineage_cases':derived,'derived_lineage_case_count':len(derived),'true_lineage_failure_cases':failed,'true_lineage_failure_count':len(failed),'fully_adjudication_eligible_cases':40,'rubric_sha256':sha(RUBRIC.read_bytes()),'metric_registry_sha256':sha(REG.read_bytes()),'schema_sha256':sha(SCHEMA.read_bytes()),'baseline_freeze_path':str(BASEFREEZE.relative_to(ROOT)),'baseline_freeze_sha256':sha(BASEFREEZE.read_bytes()),'baseline_authoritative_inputs':baseline_inputs,'treatment_run_input_freeze_path':str(RUNFREEZE.relative_to(ROOT)),'treatment_run_input_freeze_sha256':sha(RUNFREEZE.read_bytes()),'treatment_ledger_sha256':sha(LEDGER.read_bytes()),'treatment_case_results_sha256':sha(RESULT.read_bytes()),'treatment_raw_traces_sha256':sha(TRACE.read_bytes()),'lineage_sidecar_sha256':sha(SIDECAR.read_bytes()),'aggregate_generated':False,'overall_generated':False,'baseline_treatment_comparison_generated':False,'v4_rerun':False,'model_called_for_case_execution':False,'agent_called':False,'rag_called':False,'v5_accessed':False,'validation_status':'PASS','validation_checks':['40 unique case IDs exactly match frozen result/trace coverage','task-type distribution 10 per stratum','frozen result/trace line hashes recorded for every case','all five dimension ranges and totals validated by frozen Step 9.30b validator','ASK denominator/category sums and tool-call category counts validated','critical failure labels validated against frozen taxonomy','all required reviewer fields complete','no aggregate/Overall/comparison generated'],'preservation':{'treatment_attempt_ledger_modified':False,'treatment_case_results_modified':False,'treatment_raw_traces_modified':False,'treatment_lineage_sidecar_modified':False,'scoring_rubric_modified':False,'metric_registry_modified':False}}
 dump_new(outputs[2],freeze)
 # Append only after artifacts are complete.
 rec=ROOT/'record.md'
 with rec.open('a',encoding='utf-8') as f:
  f.write('\n\n## Step 9.37 — Frozen Treatment Adjudication\n\n')
  f.write(f'完成 40/40 treatment cases 的 single-AI-reviewer adjudication（非人工审阅；IRR 未测量），严格沿用 Step 9.30b frozen rubric/schema。审阅 JSONL SHA-256：`{freeze["adjudication_sha256"]}`；freeze SHA-256：`{sha(outputs[2].read_bytes())}`。五维分数、task completion、validity、ASK/tool 分类、critical/harmful 信号和逐案来源行哈希均已保存。lineage sidecar 仅用于 provenance，未提供评分加分或合成缺失语义根。40 案全部纳入；derived lineage {len(derived)} 案，正式 incomplete {len(failed)} 案仍按现存证据 adjudicate。未聚合、未生成 Overall、未比较；未改动正式 treatment artifacts、Agent、benchmark、rubric、metrics；未重跑或调用模型/Agent/RAG，未访问 V5。\n\n')
  f.write('本步骤不生成 baseline-vs-treatment deltas、improvement/resume/significance claims。\n')
 print(json.dumps({'status':'PASS','case_count':40,'task_counts':dict(task_counts),'derived':len(derived),'incomplete':len(failed),'adjudication_sha256':freeze['adjudication_sha256'],'freeze_sha256':sha(outputs[2].read_bytes())},ensure_ascii=False))
if __name__=='__main__': main()
