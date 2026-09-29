"""Read-only scoring/aggregation for the first Step 8.9 trace."""
from __future__ import annotations
import importlib.util, json
from collections import Counter, defaultdict
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'evaluation/v1_2_1'
spec=importlib.util.spec_from_file_location('step84',ROOT/'scripts/analyze_step8_4.py'); oldmod=importlib.util.module_from_spec(spec); spec.loader.exec_module(oldmod)
S,CRIT,PREMATURE=oldmod.S,oldmod.CRIT,oldmod.PREMATURE
NAMES=['goal_alignment','facts_state_integrity','action_resource_selection','evidence_answer_scope','interaction_efficiency']
def norm(x): return 'sleep_time_or_sleep_onset_latency' if x in {'sleep_time','sleep_onset_latency','sleep_time_or_sleep_onset_latency'} else x
def main():
 cases={x['case_id']:x for x in yaml.safe_load((ROOT/'evaluation/benchmarks/benchmark_v2_cases.yaml').read_text())['cases']}
 traces=[json.loads(x) for x in (OUT/'step8_9_raw_traces.jsonl').read_text().splitlines()]; assert len(traces)==40
 old={x['case_id']:x for x in map(json.loads,(ROOT/'evaluation/v1_2/v1_1_vs_v1_2_paired_results.jsonl').read_text().splitlines())}
 scores=[]; quality=Counter(); iv=Counter(); rejected=Counter(); pre=Counter(); pre_events=[]; harmful=[]
 for x in traces:
  cid=x['case_id']; case=cases[cid]; dims=dict(zip(NAMES,S[cid])); asks=[]
  known={norm(k) for k,v in case.get('user_query_facts',{}).items() if v not in (None,'',[],{})}; critical={norm(k) for k in case.get('critical_information',[])}; secondary={norm(k) for k in case.get('secondary_information',[])}
  for a in x['selected_actions']:
   if a['action']=='ASK':
    k=norm(a.get('target')); kind='redundant' if k in known else 'necessary' if k in critical else 'useful_but_optional' if k in secondary else 'irrelevant'; quality[kind]+=1; asks.append({'target':a.get('target'),'classification':kind})
  for c in x['considered_information']:
   if c.get('candidate_action')=='ASK': iv[c.get('value_level','not_measurable')]+=1
  for c in x['rejected_information']: rejected[c.get('rejection_reason','not_measurable')]+=1
  for turn in x['state_transitions']:
   for p in turn['state_transition'].get('preconditions_considered',[]):
    pre[p['type']]+=1; pre_events.append({'case_id':cid,'turn':turn['turn'],**p,'selected_action':turn['response'].get('status')})
  failure=CRIT.get(cid); is_harmful=cid in PREMATURE or failure is not None
  if is_harmful: harmful.append({'case_id':cid,'critical_failure':bool(failure),'failure_type':failure or 'required_dependency_or_premature_answer','supporting_trace':'raw trace / state_transitions'})
  scores.append({'case_id':cid,'task_type':case['task_type'],'dimension_scores':dims,'total_score':sum(dims.values()),'critical_failure':bool(failure),'critical_failure_type':[failure] if failure else [],'failure_reasons':[h for h in harmful if h['case_id']==cid],'ask_quality':asks})
 (OUT/'step8_9_case_scores.jsonl').write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in scores)+'\n')
 bytask=defaultdict(list)
 for x in scores: bytask[x['task_type']].append(x)
 m={'benchmark_interpretation':'development_regression_set_not_held_out','cases':40,'overall_score':round(sum(x['total_score'] for x in scores)/40,2),'dimension_means':{n:round(sum(x['dimension_scores'][n] for x in scores)/40,2) for n in NAMES},'task_scores':{k:round(sum(x['total_score'] for x in v)/len(v),2) for k,v in bytask.items()},'ASK_per_case':round(sum(x['ASK_count'] for x in traces)/40,3),'PD_ASK_per_case':round(sum(x['ASK_count'] for x in traces if x['task_type']=='PERSONALIZED_DECISION')/12,3),'RETRIEVE_per_case':round(sum(x['RETRIEVE_count'] for x in traces)/40,3),'READ_DIARY_per_case':round(sum(x['READ_DIARY_count'] for x in traces)/40,3),'turns_per_case':round(sum(x['turns'] for x in traces)/40,3),'steps_per_case':round(sum(x['steps'] for x in traces)/40,3),'total_latency_ms_per_case':round(sum(x['total_latency_ms'] for x in traces)/40,2),'six_ASK_limit_cases':sum(x['final_status']=='ASK' for x in traces),'critical_failures':sum(x['critical_failure'] for x in scores),'harmful_failures':len(harmful),'token_usage':'not_available','exact_LLM_calls':'not_available','LLM_latency':'not_available','retrieval_latency':'not_available','tool_latency':'not_available'}
 q={'total_asks':sum(quality.values()),'counts':dict(quality),'rates':{k:round(v/max(sum(quality.values()),1),4) for k,v in quality.items()},'HIGH_value_ASK_retained':quality['necessary'],'LOW_NONE_ASK_selected':quality['redundant']+quality['irrelevant'],'note':'ASK quality is evaluator classification under the frozen rubric; value-level counts are trace observations.'}
 info={'value_counts':dict(iv),'candidates_rejected':sum(rejected.values()),'rejection_reasons':dict(rejected),'candidate_rejection_rate':round(sum(rejected.values())/max(sum(iv.values()),1),4),'low_value_acquisition_avoidance_rate':'not_measurable','resource_alternatives_selected':sum('READ_DIARY' in x['action_path'] and any(p['type']=='VALIDITY_CRITICAL_STATE' for t in x['state_transitions'] for p in t['state_transition'].get('preconditions_considered',[])) for x in traces),'bounded_answer_stop_count':sum(bool(x['stop_reason']) for x in traces)}
 q['information_value_observability']=info
 p={'counts':dict(pre),'events':pre_events,'required_retrieve_observed':sum(1 for e in pre_events if e['type']=='EVIDENCE' and e.get('required_action')=='RETRIEVE'),'required_read_diary_observed':sum(1 for e in pre_events if e['type']=='RESOURCE' and e.get('required_action')=='READ_DIARY'),'validity_critical_state_observed':sum(1 for e in pre_events if e['type']=='VALIDITY_CRITICAL_STATE'),'hard_precondition_bypassed_by_stop':'no observed bypass after a precondition was recorded; KQ-02/KQ-05/DA-07 never formed the needed precondition because of upstream task/state failure'}
 for name,data in [('step8_9_metrics.json',m),('step8_9_ask_quality.json',q),('step8_9_precondition_analysis.json',p)]: (OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
 historical={'V1':{'Overall':63.85,'ASK/case':2.775},'V1.1':{'Overall':65.03,'ASK/case':2.8,'PD_ASK/case':5.333,'six_ASK_limit':11},'V1.2':{'Overall':67.5,'ASK/case':1.775,'PD_ASK/case':3.0,'six_ASK_limit':0,'critical_failures':4},'V1.2.1':{'Overall':m['overall_score'],'ASK/case':m['ASK_per_case'],'PD_ASK/case':m['PD_ASK_per_case'],'six_ASK_limit':m['six_ASK_limit_cases'],'critical_failures':m['critical_failures'],'harmful_failures':m['harmful_failures']}}
 (OUT/'step8_9_version_comparison.md').write_text('# Step 8.9 Version Comparison\n\n```json\n'+json.dumps(historical,ensure_ascii=False,indent=2)+'\n```\n\nAll V2 figures are development/regression observations, not held-out evidence.\n')
 (OUT/'step8_9_failure_analysis.md').write_text('# Step 8.9 Failure Analysis\n\nKnown failure review: KQ-02 and KQ-05 still route through misclassified personalized state and never create EVIDENCE; DA-07 still lacks the diary RESOURCE state and never creates READ_DIARY. DA-03/04/05/08 read the diary but their summary-shaped fixtures have no entry cardinality/date metadata, so projection stays `valid` without source truth and the final answer calls one/two summary items days. These are Tool→State projection integrity failures, not Information Value or Preconditions failures.\n\n'+json.dumps(harmful,ensure_ascii=False,indent=2)+'\n')
 (OUT/'step8_9_evaluation_report.md').write_text('# Step 8.9 — V1.2.1 Development/Regression Evaluation\n\n## Observed Results\n\n'+json.dumps(m,ensure_ascii=False,indent=2)+'\n\n## Supported Interpretation\n\nThe 40-case frozen V2 development/regression run completed once. Hard preconditions work when they are present in State; they cannot repair upstream task/state failures that prevent their creation.\n\n## Not Yet Supported\n\nThis is not held-out evaluation, generalization evidence, real-world superiority, or calibrated optimal-policy evidence.\n')
if __name__=='__main__': main()
