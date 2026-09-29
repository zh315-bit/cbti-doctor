"""One frozen V1.2 development/regression run on Benchmark V2."""
from __future__ import annotations
import json
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
from time import perf_counter
import sys
import yaml

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT)); MAX_TURNS=6

def diary(case):
    fixture=case['diary_facts']
    return deepcopy(fixture.get('facts') or None) if fixture.get('availability')=='available' else None

def reply(target, facts):
    value=facts.get(target or '')
    templates={'bedtime':'我通常 {v} 上床。','wake_time':'我通常 {v} 起床。','sleep_time_or_sleep_onset_latency':'我通常上床后约 {v} 才睡着。','nighttime_awakenings':'我夜里通常醒 {v}。','total_sleep_time':'我估计每晚总共睡 {v}。','recent_sleep_pattern':'最近的模式是：{v}。'}
    return templates.get(target,'关于'+str(target)+'，{v}。').format(v=value) if value not in (None,'',[],{}) else '这项信息我目前不清楚。'

def state_view(state):
    return {'goal':state.goal,'task_type':state.task_type.value if state.task_type else None,'facts':deepcopy(state.facts),'fact_sources':deepcopy(state.fact_sources),'missing_information':{'critical':list(state.critical_missing),'required':list(state.required_missing),'decision':list(state.decision_missing),'secondary':list(state.secondary_missing)},'sufficiency':{'user_info':state.user_info_sufficiency,'evidence':state.evidence_sufficiency},'information_estimates':deepcopy(state.information_estimates),'considered_information':deepcopy(state.considered_information),'rejected_information':deepcopy(state.rejected_information),'candidate_actions':[asdict(x) for x in state.candidate_actions],'selected_actions':deepcopy(state.action_history),'evidence_used':deepcopy(state.evidence),'resource_status':deepcopy(state.resource_status),'stop_reason':state.stop_reason,'answer_scope':state.answer_scope}

def main():
    from adaptive_agent.service import AdaptiveSession
    from adaptive_agent.tools import SessionDiaryTool
    from evaluation.recorder import EvaluationRecorder
    from main_flask import _create_adaptive_chat_service, create_app
    spec=yaml.safe_load((ROOT/'evaluation/benchmarks/benchmark_v2_cases.yaml').read_text())
    assert spec['status']=='benchmark_v2_frozen'
    out=ROOT/'evaluation/v1_2/v1_2_v2_raw_traces.jsonl'
    if out.exists(): raise RuntimeError(f'refusing to overwrite {out}')
    service=_create_adaptive_chat_service(); service.recorder=EvaluationRecorder(ROOT/'evaluation/v1_2/recorder')
    app=create_app(service); app.config.update(TESTING=True,PROPAGATE_EXCEPTIONS=True)
    with out.open('w',encoding='utf-8') as stream:
      for case in spec['cases']:
        sid=case['case_id']; service.sessions[sid]=AdaptiveSession(); service.loop.diary_tool=SessionDiaryTool(diary(case)); messages=[case['user_query']]; turns=[]
        for turn in range(1,MAX_TURNS+1):
          started=perf_counter(); response=app.test_client().post('/api/chat',json={'session_id':sid,'message':messages[-1]}); payload=response.get_json(); state=deepcopy(service.sessions[sid].state)
          turns.append({'turn':turn,'user_turn':messages[-1],'http_status':response.status_code,'response':payload,'latency_ms':round((perf_counter()-started)*1000,2),'state_transition':state_view(state)})
          if response.status_code!=200 or payload.get('status')!='ASK': break
          messages.append(reply(state.action_history[-1].get('target') if state.action_history else None,case['follow_up_facts']))
        state=service.sessions[sid].state; path=[x['action'] for x in state.action_history]
        row={'case_id':sid,'task_type':case['task_type'],'difficulty':case['difficulty'],'language_type':case['language'],'user_turns':messages[:len(turns)],'extracted_facts':deepcopy(state.facts),'state_transitions':turns,'missing_information':state_view(state)['missing_information'],'sufficiency':state_view(state)['sufficiency'],'information_estimates':deepcopy(state.information_estimates),'considered_information':[x for t in turns for x in t['state_transition']['considered_information']],'rejected_information':[x for t in turns for x in t['state_transition']['rejected_information']],'candidate_actions':[x for t in turns for x in t['state_transition']['candidate_actions']],'selected_actions':deepcopy(state.action_history),'tool_calls':[x for x in path if x in {'RETRIEVE','READ_DIARY'}],'evidence_used':deepcopy(state.evidence),'answer_scope':state.answer_scope,'stop_reason':state.stop_reason,'final_answer':turns[-1]['response'].get('assistant',''),'action_path':path,'ASK_count':path.count('ASK'),'RETRIEVE_count':path.count('RETRIEVE'),'READ_DIARY_count':path.count('READ_DIARY'),'turns':len(turns),'steps':sum(t['response'].get('steps',0) for t in turns),'token_usage':'not_available','latency':'not_available','LLM_calls':'not_available','final_status':turns[-1]['response'].get('status','HTTP_ERROR')}
        stream.write(json.dumps(row,ensure_ascii=False,default=str)+'\n'); stream.flush(); print(sid,path,row['final_status'],flush=True)

if __name__=='__main__': main()
