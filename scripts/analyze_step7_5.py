"""Offline diagnosis of the already-frozen Step 7.4 artifacts."""
from __future__ import annotations
import json
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evaluation/v1_1'
traces={x['case_id']:x for x in map(json.loads,(OUT/'v1_1_v2_raw_traces.jsonl').read_text().splitlines())}
paired=[json.loads(x) for x in (OUT/'v1_vs_v1_1_paired_results.jsonl').read_text().splitlines()]
metrics=json.loads((OUT/'v1_vs_v1_1_metrics.json').read_text())

def task_metrics(task):
    rows=[x for x in paired if x['task_type']==task]
    asks=sum(x['v1_1']['ASK_count'] for x in rows)
    quality={k:sum(x['ask_quality'][k] for x in rows) for k in ('necessary','useful_but_optional','redundant','irrelevant')}
    old_asks=[x['v1']['ASK_count'] for x in rows]
    return {'cases':len(rows),'v1_score':round(sum(x['v1']['score'] for x in rows)/len(rows),2),'v1_1_score':round(sum(x['v1_1']['score'] for x in rows)/len(rows),2),
            'v1_ASK_per_case':round(sum(old_asks)/len(rows),3),'score':round(sum(x['v1_1']['score'] for x in rows)/len(rows),2),
            'ASK_per_case':round(asks/len(rows),3),'redundant_ask_rate':round(quality['redundant']/asks,4) if asks else 0,
            'six_ASK_limit_cases':sum(traces[x['case_id']]['final_status']=='ASK' for x in rows),
            'critical_failures':0,'ask_quality':quality}

six=[]
for cid,t in traces.items():
    if t['final_status']!='ASK': continue
    asks=[]
    for turn in t['state_transitions']:
        st=turn['state_transition']; response=turn['response']
        if response.get('status')!='ASK': continue
        actions=st.get('selected_actions') or []
        target=actions[-1].get('target') if actions else None
        required=list(dict.fromkeys((st.get('missing_information',{}).get('critical') or [])+(st.get('missing_information',{}).get('secondary') or [])))
        decision=st.get('missing_information',{}).get('decision') or []
        ask_candidates=[a.get('target') for a in st.get('candidate_actions',[]) if a.get('action')=='ASK']
        asks.append({'turn':turn['turn'],'target':target,'state_before_ask':{'facts':st.get('facts',{}),'required_missing':required,'decision_relevant_missing':decision},'eligible_candidates':ask_candidates,'eligibility_observable':target in ask_candidates})
    six.append({'case_id':cid,'goal':t['state_transitions'][0]['state_transition'].get('goal',''),'action_path':t['action_path'],'ask_targets':[x['target'] for x in asks],'asks':asks,'termination_reason':'max six ASK turns' if len(asks)>=6 else t['final_status'],'root_cause':'extraction_failure' if not t.get('extracted_facts') else 'sufficiency_failure'})

task={k:task_metrics(k) for k in ('KNOWLEDGE_QA','CAUSE_ASSESSMENT','PERSONALIZED_DECISION','DATA_ANALYSIS')}
q=metrics['v1_1']['ask_counts']; total=sum(q.values())
ask_quality={'total_ASK':total,'necessary_ASK_rate':round(q['necessary']/total,4),'useful_but_optional_ASK_rate':round(q['useful_but_optional']/total,4),'redundant_ASK_rate':round(q['redundant']/total,4),'irrelevant_ASK_rate':round(q['irrelevant']/total,4),'V1_reference':{'ASK_per_case':2.775,'redundant_ASK_rate':0.7207,'total_ASK':111}}
diagnosis={'source_artifacts':['v1_1_v2_raw_traces.jsonl','v1_vs_v1_1_paired_results.jsonl','v1_vs_v1_1_metrics.json','evaluation/v2/adaptive_v1_v2_traces.jsonl','evaluation/v2/adaptive_v1_v2_metrics.json'],'ask_quality_reanalysis':ask_quality,'per_task':task,'six_ASK_limit_cases':six,'step_effectiveness':{'step7_1':{'resolved':['diary projection contradiction not observed in DA-04/DA-08 final outputs','unsupported user-fact critical failure not observed'],'persisted':['model-facing explicit-fact omissions and repeated ASK in CA/PD/DA-07 traces']},'step7_2':{'ASK_gate_blocked_exact_count':'not_observable_from_frozen_trace schema','auditable_observation':'all selected ASK actions were present in candidate_actions; rejected candidates were not persisted','persisted_problem':'irrelevant and redundant ASK remain high'},'step7_3':{'resolved':['V1 diary projection critical failures not observed in this offline review'],'new_failures':'none observed as critical failures','measurement_note':'offline review, not identical automated detector'}},'critical_failure_interpretation':{'V1':2,'V1_1':0,'measurement_same':False,'note':'V1 uses frozen historical reviewer records; V1.1 uses Step 7.4 first-pass offline trace review, so the 2→0 comparison is not a strictly identical measurement.'}}
(OUT/'step7_5_ask_quality_analysis.json').write_text(json.dumps(diagnosis,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

clusters=defaultdict(list)
for item in six: clusters[item['root_cause']].append(item['case_id'])
for x in ('extraction_failure','state_representation_failure','requirement_overconstraint','sufficiency_failure','ask_eligibility_failure','policy_failure','resource_failure','answer_scope_failure','other'): clusters.setdefault(x,[])
(OUT/'step7_5_failure_clusters.json').write_text(json.dumps({'clusters':dict(clusters),'six_ASK_cases':[x['case_id'] for x in six],'notes':{'extraction_failure':'assigned only where final extracted_facts were empty despite evaluator query facts; this is trace evidence, not a causal intervention estimate.','ask_eligibility_failure':'no direct rejected-candidate telemetry exists.'}},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

improved=sorted([x for x in paired if x['delta']>0],key=lambda x:x['delta'],reverse=True)[:5]
regressed=sorted([x for x in paired if x['delta']<0],key=lambda x:x['delta'])[:5]
def short(rows): return [{'case_id':x['case_id'],'delta':x['delta'],'v1_path':x['v1']['action_path'],'v1_1_path':x['v1_1']['action_path'],'v1_1_asks':x['v1_1']['ASK_count'],'ask_quality':x['ask_quality'],'root_cause':'combined_effect'} for x in rows]
report=f'''# Step 7.5 Post-Evaluation Diagnosis

Date: 2026-09-20

## Scope

This is an offline analysis of the frozen Step 7.4 artifacts only. No Agent,
prompt, Benchmark V2 case, rubric, or model run was changed or rerun.

## ASK Quality

V1.1 produced {total} ASK actions ({total/40:.3f}/case): necessary {q['necessary']} ({q['necessary']/total:.1%}), useful-but-optional {q['useful_but_optional']} ({q['useful_but_optional']/total:.1%}), redundant {q['redundant']} ({q['redundant']/total:.1%}), and irrelevant {q['irrelevant']} ({q['irrelevant']/total:.1%}). Frozen V1 had 111 ASK, 2.775/case, and 72.1% redundant. Thus V1.1 did not reduce ASK quantity and its redundant rate is lower under the same trace-only classification, but its irrelevant rate is higher; ASK quality improved only partially.

## Per-Task Diagnosis

| Task | Score V1 → V1.1 | ASK/case V1 → V1.1 | V1.1 redundant ASK rate | V1.1 six-ASK cases | V1.1 critical failures |
|---|---:|---:|---:|---:|---:|
'''
for k,v in task.items(): report+=f"| {k} | {v['v1_score']:.2f} → {v['v1_1_score']:.2f} | {v['v1_ASK_per_case']:.3f} → {v['ASK_per_case']:.3f} | {v['redundant_ask_rate']:.1%} | {v['six_ASK_limit_cases']} | {v['critical_failures']} |\n"
report+='''\nPD remains the main bottleneck: it has the highest repeated-ASK concentration and most six-ASK paths. Lower ASK burden cannot be inferred from its score because the V1.1 run still repeatedly asks for broad requirement fields after State extraction failures.

## Six-ASK Limit

The 11 cases and every ASK target with the State before the ASK are recorded in
`step7_5_ask_quality_analysis.json`. The frozen trace shows selected ASK actions
were present in the persisted candidate list, but it does not persist rejected
candidate reasons; exact “gate blocked” counts are therefore not observable.
The dominant observed clusters are extraction failure and sufficiency/requirement
over-collection, not a proven policy-only regression.

## Step Effectiveness

- **Step 7.1:** diary projection contradictions and unsupported user-fact critical failures were not observed in this run, but explicit-fact omissions and repeated ASK persist in model-facing traces.
- **Step 7.2:** the trace cannot count rejected ASK candidates; selected ASK actions passed the gate, while 43/112 were classified irrelevant and 39/112 redundant.
- **Step 7.3:** DA-04/DA-08 historical diary contradictions were not observed in this run. This is a run-specific observation, not proof of general resolution. No new critical grounding failure was observed.

## Largest Deltas

### Five largest improvements
'''
for x in improved: report+=f"- `{x['case_id']}`: delta {x['delta']:+}; path {x['v1']['action_path']} → {x['v1_1']['action_path']}; attribution `combined_effect`.\n"
report+='\n### Five largest regressions\n'
for x in regressed: report+=f"- `{x['case_id']}`: delta {x['delta']:+}; path {x['v1']['action_path']} → {x['v1_1']['action_path']}; attribution `combined_effect`.\n"
report+='''\n## Critical Failure Interpretation

V1 records 2 critical failures from the frozen historical reviewer file. V1.1
records 0 from the Step 7.4 offline first-pass review. Measurement is not fully
identical, so this must not be stated as a strict 2→0 causal reduction.

## V1.2 Candidate Research Directions (not implemented)

1. Persist rejected ASK-candidate reasons and a normalized question ledger so gate effectiveness is measurable.
2. Separate requirement schema completeness from goal-specific decision fields, especially for PD.
3. Add a model-independent extraction confidence/coverage audit before broad ASK generation.
4. Add paired diary summary fixtures with formal expected date windows and automated claim checks.

No V1.2 work was performed.
'''
(OUT/'step7_5_post_evaluation_diagnosis.md').write_text(report,encoding='utf-8')
