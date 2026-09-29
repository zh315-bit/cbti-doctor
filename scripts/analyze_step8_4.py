"""Offline, frozen-rubric Step 8.4 trace analysis; never calls an Agent."""
from __future__ import annotations
import json
from collections import Counter
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'evaluation/v1_2'
# goal, facts/state, action/resource, evidence/scope, efficiency — single-reviewer frozen-rubric adjudication.
S={
'V2-KQ-01':(20,20,20,25,15),'V2-KQ-02':(15,20,5,5,10),'V2-KQ-03':(20,20,20,15,15),'V2-KQ-04':(20,20,20,15,15),'V2-KQ-05':(15,20,5,5,5),'V2-KQ-06':(20,20,15,15,10),'V2-KQ-07':(20,20,20,15,15),'V2-KQ-08':(20,20,20,15,15),'V2-KQ-09':(20,20,20,15,15),'V2-KQ-10':(20,20,20,25,15),
'V2-CA-01':(18,8,7,12,3),'V2-CA-02':(18,12,7,12,6),'V2-CA-03':(18,15,10,12,7),'V2-CA-04':(18,12,10,12,8),'V2-CA-05':(20,20,20,20,10),'V2-CA-06':(18,12,15,20,15),'V2-CA-07':(18,12,12,20,13),'V2-CA-08':(20,20,20,25,15),'V2-CA-09':(20,20,20,25,15),'V2-CA-10':(18,12,7,12,6),
'V2-PD-01':(15,10,7,8,0),'V2-PD-02':(18,12,12,15,8),'V2-PD-03':(20,20,20,15,10),'V2-PD-04':(18,15,15,12,10),'V2-PD-05':(15,10,7,8,5),'V2-PD-06':(15,10,7,8,5),'V2-PD-07':(18,10,7,10,5),'V2-PD-08':(15,10,7,8,0),'V2-PD-09':(18,15,12,10,5),'V2-PD-10':(15,10,7,8,0),'V2-PD-11':(15,10,7,8,0),'V2-PD-12':(15,10,7,8,5),
'V2-DA-01':(20,20,20,25,15),'V2-DA-02':(20,20,20,15,15),'V2-DA-03':(20,0,20,0,5),'V2-DA-04':(20,0,20,0,5),'V2-DA-05':(20,0,20,0,5),'V2-DA-06':(20,20,20,25,15),'V2-DA-07':(15,5,0,10,15),'V2-DA-08':(20,0,20,0,5)}
CRIT={'V2-DA-03':'answer_contradicts_diary_fixture','V2-DA-04':'answer_contradicts_diary_fixture','V2-DA-05':'answer_contradicts_diary_fixture','V2-DA-08':'answer_contradicts_diary_fixture'}
PREMATURE={'V2-KQ-02','V2-KQ-05','V2-DA-07'}
def norm(x): return 'sleep_time_or_sleep_onset_latency' if x in {'sleep_time','sleep_onset_latency','sleep_time_or_sleep_onset_latency'} else x
def main():
 spec=yaml.safe_load((ROOT/'evaluation/benchmarks/benchmark_v2_cases.yaml').read_text()); cases={x['case_id']:x for x in spec['cases']}; tr={x['case_id']:x for x in map(json.loads,(OUT/'v1_2_v2_raw_traces.jsonl').read_text().splitlines())}; old={x['case_id']:x for x in map(json.loads,(ROOT/'evaluation/v1_1/v1_vs_v1_1_paired_results.jsonl').read_text().splitlines())}; names=['goal_alignment','facts_state_integrity','action_resource_selection','evidence_answer_scope','interaction_efficiency']; paired=[]; q=Counter(); info=Counter(); reasons=Counter(); stops=[]
 for cid,case in cases.items():
  x=tr[cid]; dims=dict(zip(names,S[cid])); asks=[]
  known={norm(k) for k,v in (case.get('user_query_facts') or {}).items() if v not in (None,'',[],{})}; critical={norm(k) for k in case.get('critical_information') or []}; secondary={norm(k) for k in case.get('secondary_information') or []}
  for a in x['selected_actions']:
   if a['action']=='ASK':
    k=norm(a.get('target')); kind='redundant' if k in known else 'necessary' if k in critical else 'useful_but_optional' if k in secondary else 'irrelevant'; q[kind]+=1; asks.append({'target':a.get('target'),'classification':kind})
  for c in x['considered_information']:
   if c.get('candidate_action')=='ASK': info[c.get('value_level','not_measurable')]+=1
  for c in x['rejected_information']: reasons[c.get('rejection_reason','not_measurable')]+=1
  if x['stop_reason']:
   guard='harmful_rejection' if cid in PREMATURE else 'questionable_rejection' if cid.startswith('V2-KQ') else 'correct_rejection'; stops.append({'case_id':cid,'stop_reason':x['stop_reason'],'guardrail_review':guard})
  score=sum(S[cid]); oldscore=old[cid]['v1_1']['score']; delta=score-oldscore
  paired.append({'case_id':cid,'task_type':case['task_type'],'v1_1_score':oldscore,'v1_2_score':score,'delta':delta,'v1_1_ASK':old[cid]['v1_1']['ASK_count'],'v1_2_ASK':x['ASK_count'],'v1_2_rejected_candidates':x['rejected_information'],'v1_2_stop_reason':x['stop_reason'],'classification':'improved' if delta>0 else 'regressed' if delta<0 else 'unchanged','v1_2_dimension_scores':dims,'ask_quality':asks,'critical_failure':CRIT.get(cid)})
 (OUT/'v1_1_vs_v1_2_paired_results.jsonl').write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in paired)+'\n')
 n=40; total=sum(x['v1_2_score'] for x in paired); bytask={t:[x for x in paired if x['task_type']==t] for t in {x['task_type'] for x in paired}}
 metrics={'benchmark_interpretation':'development_regression_set_not_held_out','cases':40,'overall_score':round(total/n,2),'dimension_means':{k:round(sum(x['v1_2_dimension_scores'][k] for x in paired)/n,2) for k in names},'task_scores':{t:round(sum(x['v1_2_score'] for x in xs)/len(xs),2) for t,xs in bytask.items()},'ASK_per_case':round(sum(x['v1_2_ASK'] for x in paired)/n,3),'ask_counts':dict(q),'ask_rates':{k:round(v/max(sum(q.values()),1),4) for k,v in q.items()},'six_ASK_limit_cases':sum(x['final_status']=='ASK' for x in tr.values()),'RETRIEVE_per_case':round(sum(x['RETRIEVE_count'] for x in tr.values())/n,3),'READ_DIARY_per_case':round(sum(x['READ_DIARY_count'] for x in tr.values())/n,3),'turns_per_case':round(sum(x['turns'] for x in tr.values())/n,3),'steps_per_case':round(sum(x['steps'] for x in tr.values())/n,3),'premature_answer_rate':round(len(PREMATURE)/n,4),'unsupported_personalization_rate':0,'resource_skipping_failures':['V2-DA-07'],'critical_failures':dict(CRIT),'token_usage':'not_available','latency':'not_available','LLM_calls':'not_available','paired_counts':dict(Counter(x['classification'] for x in paired))}
 info_metrics={'total_considered_information_candidates':sum(info.values()),'value_counts':dict(info),'candidates_rejected':sum(reasons.values()),'rejection_reasons':dict(reasons),'candidate_rejection_rate':round(sum(reasons.values())/max(sum(info.values()),1),4),'low_value_acquisition_avoidance_rate':'not_measurable (trace records rejections but does not label a unique low-value acquisition denominator)','resource_alternatives_selected':sum('READ_DIARY' in x['action_path'] and any(c.get('resource_alternative') for c in x['considered_information']) for x in tr.values()),'bounded_answer_stop_count':len(stops),'bounded_answer_guardrail_reviews':stops}
 (OUT/'v1_2_v2_metrics.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2)+'\n'); (OUT/'v1_2_information_value_metrics.json').write_text(json.dumps(info_metrics,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'overall':metrics['overall_score'],'asks':metrics['ASK_per_case'],'info':info_metrics},ensure_ascii=False))
if __name__=='__main__': main()
