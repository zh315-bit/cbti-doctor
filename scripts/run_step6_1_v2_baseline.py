"""Run frozen Benchmark V2 through the existing Adaptive /api/chat path only."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
from time import perf_counter
from typing import Any
import traceback

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
MAX_TURNS = 6


def diary_payload(case: dict[str, Any]) -> dict[str, Any] | None:
    fixture = case['diary_facts']
    if fixture.get('availability') != 'available':
        return None
    return deepcopy(fixture.get('facts') or None)


def follow_up(target: str | None, facts: dict[str, Any]) -> str:
    target = target or ''
    value = facts.get(target)
    if target == 'bedtime' and value:
        return f'我通常 {value} 上床。'
    if target == 'wake_time' and value:
        return f'我通常 {value} 起床。'
    if target == 'sleep_time_or_sleep_onset_latency' and value:
        return f'我通常上床后约 {value} 才睡着。'
    if target == 'nighttime_awakenings' and value is not None:
        return f'我夜里通常醒 {value}。'
    if target == 'total_sleep_time' and value:
        return f'我估计每晚总共睡 {value}。'
    if target == 'recent_sleep_pattern' and value:
        return f'最近的模式是：{value}。'
    if value:
        return f'关于{target}，{value}。'
    return '这项信息我目前不清楚。'


def snapshot(state: Any) -> dict[str, Any]:
    from dataclasses import asdict
    return {
        'goal': state.goal,
        'task_type': state.task_type.value if state.task_type else None,
        'facts': deepcopy(state.facts),
        'missing_information': {'critical': list(state.critical_missing), 'secondary': list(state.secondary_missing), 'decision': list(state.decision_missing)},
        'sufficiency': {'user_info': state.user_info_sufficiency, 'evidence': state.evidence_sufficiency},
        'candidate_actions': [asdict(item) for item in state.candidate_actions],
        'selected_actions': deepcopy(state.action_history),
        'evidence_used': deepcopy(state.evidence),
        'resource_status': deepcopy(state.resource_status),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    from adaptive_agent.service import AdaptiveSession
    from adaptive_agent.tools import SessionDiaryTool
    from evaluation.recorder import EvaluationRecorder
    from main_flask import _create_adaptive_chat_service, create_app

    spec = yaml.safe_load((ROOT / 'evaluation/benchmarks/benchmark_v2_cases.yaml').read_text())
    if spec.get('status') != 'benchmark_v2_frozen':
        raise RuntimeError('Benchmark V2 must be frozen before an Agent run.')
    output = ROOT / args.output
    output.mkdir(parents=True, exist_ok=True)
    service = _create_adaptive_chat_service()
    service.recorder = EvaluationRecorder(output / 'recorder')
    app = create_app(service); app.config.update(TESTING=True, PROPAGATE_EXCEPTIONS=True)
    trace_file = output / 'adaptive_v1_v2_traces.jsonl'
    if trace_file.exists():
        raise RuntimeError(f'Refusing to overwrite existing baseline trace: {trace_file}')
    with trace_file.open('w', encoding='utf-8') as out:
        for case in spec['cases']:
            case_id = case['case_id']; service.sessions[case_id] = AdaptiveSession()
            service.loop.diary_tool = SessionDiaryTool(diary_payload(case))
            messages, turns = [case['user_query']], []
            for turn in range(1, MAX_TURNS + 1):
                started = perf_counter()
                try:
                    response = app.test_client().post('/api/chat', json={'session_id': case_id, 'message': messages[-1]})
                    payload = response.get_json(silent=True) or {'raw_http_body': response.get_data(as_text=True)[:4000]}
                    status = response.status_code
                except Exception as exc:
                    payload, status = {'exception': str(exc), 'traceback': traceback.format_exc()}, 0
                state = deepcopy(service.sessions[case_id].state)
                turns.append({'turn': turn, 'user_turn': messages[-1], 'http_status': status, 'response': payload,
                              'latency_ms': round((perf_counter()-started)*1000, 2), 'state_transition': snapshot(state)})
                if status != 200 or payload.get('status') != 'ASK': break
                target = state.action_history[-1].get('target') if state.action_history else None
                messages.append(follow_up(target, case['follow_up_facts']))
            state = service.sessions[case_id].state
            path = [entry['action'] for entry in state.action_history]
            result = {
                'case_id': case_id, 'task_type': case['task_type'], 'difficulty': case['difficulty'], 'language_type': case['language'],
                'user_turns': messages[:len(turns)], 'extracted_facts': deepcopy(state.facts), 'state_transitions': turns,
                'missing_information': {'critical': list(state.critical_missing), 'secondary': list(state.secondary_missing), 'decision': list(state.decision_missing)},
                'sufficiency': {'user_info': state.user_info_sufficiency, 'evidence': state.evidence_sufficiency},
                'candidate_actions': [item for turn in turns for item in turn['state_transition']['candidate_actions']],
                'selected_actions': deepcopy(state.action_history), 'tool_calls': [a for a in path if a in {'RETRIEVE','READ_DIARY'}],
                'evidence_used': deepcopy(state.evidence), 'final_answer': turns[-1]['response'].get('assistant','') if turns else '',
                'action_path': path, 'ASK_count': path.count('ASK'), 'RETRIEVE_count': path.count('RETRIEVE'), 'READ_DIARY_count': path.count('READ_DIARY'),
                'turns': len(turns), 'steps': sum(t['response'].get('steps',0) for t in turns),
                'token_usage': getattr(service.loop.answer_generator, 'last_token_usage', None),
                'latency_ms': round(sum(t['latency_ms'] for t in turns),2), 'LLM_calls': 'not_available',
                'critical_failure': None, 'failure_type': [], 'final_status': turns[-1]['response'].get('status','HTTP_ERROR') if turns else 'HTTP_ERROR',
            }
            out.write(json.dumps(result, ensure_ascii=False, default=str)+'\n'); out.flush()
            print(json.dumps({'case_id':case_id,'path':path,'status':result['final_status']},ensure_ascii=False),flush=True)

if __name__ == '__main__': main()
