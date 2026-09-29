"""Bounded live acceptance run through the real Flask HTTP /api/chat route.

Uses configured LLM and RAG. Only diary data and follow-up user answers are fixtures.
Run: .venv/bin/python scripts/validate_step4.py --tag baseline
"""
import argparse
from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import sys
from threading import Thread
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tag', required=True)
    parser.add_argument('--offline', action='store_true', help='Real Flask route, synthetic model/tool outputs; not live acceptance')
    args = parser.parse_args()
    from main_flask import create_app, _create_adaptive_chat_service
    from adaptive_agent.tools import SessionDiaryTool
    from adaptive_agent.service import AdaptiveSession
    from evaluation.recorder import EvaluationRecorder
    from werkzeug.serving import make_server

    output = ROOT / 'evaluation' / 'runs' / ('step4-' + args.tag)
    output.mkdir(parents=True, exist_ok=True)
    service = _create_adaptive_chat_service()
    if args.offline:
        from adaptive_agent.input_understanding import Understanding
        from adaptive_agent.state import TaskType
        from adaptive_agent.tools import RetrievalResult

        class FixtureUnderstanding:
            def understand(self, text, prior):
                if '刺激控制' in text:
                    return Understanding('解释刺激控制及减少不必要卧床的原因', TaskType.KNOWLEDGE_QA, {})
                if '日记' in text:
                    return Understanding('分析最近7天的睡眠日记', TaskType.DATA_ANALYSIS, {})
                facts = {}
                if '每天11点' in text:
                    facts = {'bedtime': '23:00', 'sleep_onset_latency': 60}
                elif '早上7:00' in text:
                    facts = {'wake_time': '07:00'}
                elif '总睡眠时间' in text:
                    facts = {'total_sleep_time': 360}
                elif '每晚醒1次' in text:
                    facts = {'nighttime_awakenings': 1}
                elif '最近两周' in text:
                    facts = {'recent_sleep_pattern': text}
                return Understanding('判断是否应该早点上床', TaskType.PERSONALIZED_DECISION, facts)

        class FixtureRetrieval:
            def retrieve(self, query):
                return RetrievalResult(('MOCK evidence: fixture only, not medical evidence',), detail='explicit mock retrieval')

        class FixtureAnswer:
            def answer(self, state, limitation=None):
                return 'MOCK answer: ' + (limitation or state.goal)

        service.loop.understander = FixtureUnderstanding()
        service.loop.retrieval_tool = FixtureRetrieval()
        service.loop.answer_generator = FixtureAnswer()
    service.recorder = EvaluationRecorder(output)
    app = create_app(service)
    server = None
    if not args.offline:
        server = make_server('127.0.0.1', 0, app)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
    observations = []

    # Observe existing boundaries without changing extraction, candidates or policy.
    def observe_method(owner, method, label):
        original = getattr(owner, method)
        def wrapped(*inputs, **kwargs):
            result = original(*inputs, **kwargs)
            observations.append({'event': label, 'inputs': deepcopy(inputs),
                                 'result': deepcopy(result)})
            return result
        setattr(owner, method, wrapped)

    observe_method(service.loop.understander, 'understand', 'understanding')
    observe_method(service.loop.retrieval_tool, 'retrieve', 'retrieval')
    observe_method(service.loop.policy, 'choose', 'decision')
    observe_method(service.loop, 'run_turn', 'loop_result')

    def encode(value):
        if hasattr(value, '__dataclass_fields__'):
            return asdict(value)
        raise TypeError(type(value).__name__)

    def request(case, message):
        observations.clear()
        prior = deepcopy(service.sessions.get(case))
        data = json.dumps({'session_id': case, 'message': message}).encode()
        try:
            if args.offline:
                response = app.test_client().post('/api/chat', json=json.loads(data))
                result, status = response.get_json(), response.status_code
            else:
                with urlopen(Request(f'http://127.0.0.1:{server.server_port}/api/chat',
                                     data=data, headers={'Content-Type': 'application/json'}),
                             timeout=600) as response:
                    result = json.load(response)
                    status = response.status
        except Exception as exc:
            result, status = {'error': type(exc).__name__}, 0
        state = deepcopy(service.sessions.get(case))
        requirements = None
        if state and state.state.task_type:
            requirements = service.loop.requirements[state.state.task_type]
        trace = dict(mode='offline' if args.offline else 'live', case=case, message=message, http_status=status, response=result,
                     prior=prior, requirements=requirements, observations=observations,
                     updated=state)
        with (output / 'http-traces.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(trace, ensure_ascii=False, default=encode) + '\n')
        print(json.dumps({'case': case, 'http_status': status, 'response': result},
                         ensure_ascii=False), flush=True)
        return result

    try:
        case = 'case1'
        result = request(case, '我每天11点上床，一个小时才能睡着，我应该早点上床吗？')
        replies = {
            'bedtime': '我每晚23:00上床。',
            'sleep_onset_latency': '我上床后需要60分钟才能睡着。',
            'wake_time': '我每天早上7:00起床。',
            'total_sleep_time': '我每晚实际总睡眠时间是6小时。',
            'nighttime_awakenings': '我每晚醒1次，大约30分钟。',
            'recent_sleep_pattern': '最近两周每天23:00上床，约60分钟入睡，7:00起床，每晚睡6小时，夜里醒1次约30分钟。',
        }
        for _ in range(6):
            if result.get('status') != 'ASK':
                break
            target = service.sessions[case].state.action_history[-1]['target']
            if target not in replies:
                break
            result = request(case, replies[target])
        request('case2', '什么是刺激控制？为什么 CBT-I 要减少不必要的卧床时间？')

        # Explicitly synthetic seven-day data, never real patient data.
        diary = {'bedtime': '23:00', 'wake_time': '07:00', 'sleep_onset_latency': 60,
                 'total_sleep_time': 360, 'nighttime_awakenings': 1,
                 'recent_sleep_pattern': [
                     {'date': f'2026-09-{day:02d}', 'total_sleep_time': 360,
                      'bedtime': '23:00', 'wake_time': '07:00', 'sleep_onset_latency': 60,
                      'nighttime_awakenings': 1} for day in range(11, 18)]}
        for case, fixture, advertised in [('case3-available', diary, True),
                                          ('case3-unavailable', None, False),
                                          ('case3-discovered', diary, False)]:
            service.loop.diary_tool = SessionDiaryTool(fixture)
            observe_method(service.loop.diary_tool, 'read', 'diary')
            service.sessions[case] = AdaptiveSession()
            service.sessions[case].state.available_diary = advertised
            request(case, '帮我分析最近7天的睡眠日记。')
    finally:
        if server:
            server.shutdown()
            thread.join(timeout=5)


if __name__ == '__main__':
    main()
