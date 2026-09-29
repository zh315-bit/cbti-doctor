"""Controlled V1.2.1 mechanism validation; no model or benchmark execution."""
from __future__ import annotations
import json
from dataclasses import asdict
from pathlib import Path
import unittest

from adaptive_agent.candidates import build_candidates
from adaptive_agent.policy import HeuristicDecisionPolicy
from adaptive_agent.requirements import RequirementSet
from adaptive_agent.state import AdaptiveAgentState, TaskType
from adaptive_agent.state_update import apply_diary_result
from adaptive_agent.sufficiency import SufficiencyEstimator
from adaptive_agent.tools import DiaryResult

ROOT=Path(__file__).resolve().parents[1]; TRACE=ROOT/'evaluation/v1_2_1/step8_7_mechanism_traces.jsonl'

def decide(name, state, req, expect):
    SufficiencyEstimator().update(state, req); state.candidate_actions=build_candidates(state, req)
    action=HeuristicDecisionPolicy().choose(state)
    row={'scenario':name,'validity_critical_missing':state.validity_critical_missing,'preconditions_considered':state.preconditions_considered,'information_estimates':state.information_estimates,'considered_information':state.considered_information,'rejected_information':state.rejected_information,'candidate_actions':[asdict(x) for x in state.candidate_actions],'selected_action':asdict(action),'stop_reason':state.stop_reason,'diary_projection':state.diary_projection}
    row['pass']=expect(row); return row

class PreconditionsMechanismTests(unittest.TestCase):
    def test_controlled_scenarios(self):
        R=RequirementSet; S=AdaptiveAgentState; T=TaskType
        rows=[
          decide('A_evidence_absent',S(goal='解释睡眠概念',task_type=T.KNOWLEDGE_QA),R((),(),True),lambda x:x['selected_action']['action']=='RETRIEVE' and x['preconditions_considered'][0]['type']=='EVIDENCE'),
          decide('B_evidence_present',S(goal='解释睡眠概念',task_type=T.KNOWLEDGE_QA,evidence=['source']),R((),(),True),lambda x:x['selected_action']['action']=='ANSWER'),
          decide('C_evidence_optional',S(goal='描述作息',task_type=T.KNOWLEDGE_QA),R((),(),False),lambda x:not x['preconditions_considered'] and x['selected_action']['action']=='ANSWER'),
          decide('D_diary_authorized',S(goal='分析记录',task_type=T.DATA_ANALYSIS,diary_authorized=True,diary_available=True),R((),(),False,resources=('sleep_diary',)),lambda x:x['selected_action']['action']=='READ_DIARY'),
          decide('E_diary_unavailable',S(goal='分析记录',task_type=T.DATA_ANALYSIS,diary_available=False),R((),(),False,resources=('sleep_diary',)),lambda x:x['selected_action']['action']=='ANSWER' and x['preconditions_considered'][0]['status']=='unavailable'),
          decide('F_diary_unauthorized',S(goal='分析记录',task_type=T.DATA_ANALYSIS,diary_authorized=False),R((),(),False,resources=('sleep_diary',)),lambda x:x['selected_action']['action']=='ANSWER'),
          decide('G_diary_optional',S(goal='讨论睡眠习惯',task_type=T.PERSONALIZED_DECISION,diary_authorized=True,diary_available=True),R((),(),False),lambda x:not x['preconditions_considered']),
          decide('H_critical_state',S(goal='调整起床时间',task_type=T.PERSONALIZED_DECISION),R(('wake_time',),(),False),lambda x:x['selected_action']['action']=='ASK' and any(p.get('type') in {'VALIDITY_CRITICAL_STATE','CRITICAL_STATE'} for p in x['preconditions_considered'])),
          decide('I_detail_optional',S(goal='描述作息',task_type=T.PERSONALIZED_DECISION),R((),('caffeine',),False),lambda x:x['selected_action']['action']=='ANSWER'),
          decide('J_cost_cannot_override_evidence',S(goal='解释睡眠概念',task_type=T.KNOWLEDGE_QA,action_history=[{'action':'ASK','target':'a'}]*5),R((),(),True),lambda x:x['selected_action']['action']=='RETRIEVE'),
          decide('K_diminishing_cannot_override_resource',S(goal='分析记录',task_type=T.DATA_ANALYSIS,diary_authorized=True,diary_available=True,action_history=[{'action':'ASK','target':'a'}]*5),R((),(),False,resources=('sleep_diary',)),lambda x:x['selected_action']['action']=='READ_DIARY'),
          decide('L_stop_cannot_bypass_evidence',S(goal='解释睡眠概念',task_type=T.KNOWLEDGE_QA),R((),(),True),lambda x:x['selected_action']['action']!='ANSWER'),
        ]
        fixtures={
          'normal':[{'date':f'2026-01-0{i}','total_sleep_time':400+i} for i in range(1,8)],
          'missing':[{'date':'2026-01-01','total_sleep_time':None}],
          'nonconsecutive':[{'date':'2026-01-01'},{'date':'2026-01-05'}],
          'range':[{'date':'2026-01-01','wake_time':{'uncertainty':'range','low':'07:00','high':'08:00'}}],
          'distinct':[{'date':'2026-01-01','note':'a'},{'date':'2026-01-01','note':'b'}],
        }
        for name,entries in fixtures.items():
            state=S(action_history=[{'action':'READ_DIARY'}]); apply_diary_result(state,DiaryResult({'recent_sleep_pattern':entries},True,source_entry_count=len(entries),source_dates=tuple(str(e['date']) for e in entries)))
            rows.append({'scenario':'projection_'+name,'diary_projection':state.diary_projection,'facts':state.facts,'provenance':state.fact_sources,'pass':state.diary_projection['projection_status']=='valid' and len(state.facts.get('recent_sleep_pattern',[]))==len(entries)})
        for name,result in [('cardinality',DiaryResult({'recent_sleep_pattern':[{'date':'2026-01-01'}]},True,source_entry_count=2)),('date',DiaryResult({'recent_sleep_pattern':[{'date':'bad'}]},True,source_entry_count=1,source_dates=('2026-01-01',)))]:
            state=S(action_history=[{'action':'READ_DIARY'}]); apply_diary_result(state,result)
            rows.append({'scenario':'fail_closed_'+name,'diary_projection':state.diary_projection,'facts':state.facts,'pass':state.diary_projection['projection_status']=='invalid' and not state.facts})
        TRACE.parent.mkdir(parents=True,exist_ok=True); TRACE.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows),encoding='utf-8')
        self.assertEqual(len(rows),19)

if __name__=='__main__': unittest.main()
