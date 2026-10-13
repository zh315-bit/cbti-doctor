import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'output'
IDENTITY = 'Codex AI reviewer (model: gpt-6 sol, version: unknown)'

def line(path, n):
    return json.loads((ROOT / path).read_text().splitlines()[n - 1])

def show(n):
    t = line('review_template.jsonl', n)
    cid = t['immutable_execution_facts']['case_id']
    s = (ROOT / 'cases/benchmark_v4_cases.yaml').read_text()
    blocks = re.split(r'(?=^  - case_id: )', s, flags=re.M)
    block = next(x for x in blocks if x.startswith('  - case_id: ' + cid + '\n'))
    r = line('v3_run/raw_traces.jsonl', n)
    c = line('v3_run/case_results.jsonl', n)
    assert r['case_id'] == c['case_id'] == cid
    print('CASE', n, cid, 'FACTS', {k:v for k,v in t['immutable_execution_facts'].items() if k in ('ASK_count','READ_DIARY_count','RETRIEVE_count','action_path','final_status','lineage_ready')})
    print('ORACLE\n', block)
    print('RESULT ANSWER\n', c.get('answer'))
    for ti, turn in enumerate(r['turns'], 1):
        print('TURN', ti, 'USER', turn['user_turn'])
        if turn['response'].get('assistant') != c.get('answer'):
            print('RESPONSE', turn['response'].get('assistant'))
        for hi, h in enumerate(turn['state_history']):
            if h.get('event') in ('INPUT_UNDERSTANDING', 'ASK', 'RETRIEVE', 'READ_DIARY'):
                print('EVENT', hi, h.get('event'), 'FACTS', h.get('facts'), 'RESOURCE', h.get('resource_status'), 'DIARY', h.get('diary_projection'))
                ev = h.get('evidence')
                if ev: print(' EVIDENCE', json.dumps(ev, ensure_ascii=False)[:4000])
        st = turn['state']
        print('FINAL STATE FACTS', st.get('facts'), 'STATUS', st.get('resource_status'), 'MISSING', st.get('critical_missing'), st.get('required_missing'))
        print('ACTION HISTORY', json.dumps(st.get('action_history'), ensure_ascii=False)[:2500])
    print('SUMMARY', {k:c.get(k) for k in ('action_path','ASK_count','RETRIEVE_count','READ_DIARY_count','final_status')})

def commit(n):
    t = line('review_template.jsonl', n)
    x = json.loads(sys.stdin.read())
    cid = t['immutable_execution_facts']['case_id']
    dim = dict(zip(('goal_alignment','facts_state_integrity','action_resource_selection','evidence_answer_scope','interaction_efficiency'), x['scores']))
    counts = {k: x.get('ask', []).count(k) for k in ('necessary','useful_but_optional','redundant','irrelevant')}
    target = {'V4-CA-01':'recent_sleep_pattern','V4-PD-01':'shift_transition_pattern','V4-PD-03':'bedtime','V4-PD-09':'nap_duration'}.get(cid)
    targets = [{'target_id':target,'required_by_oracle':True,'acquired':x.get('acquired',False)}] if target else []
    judgments = {
        'dimension_scores': dim, 'total_score': sum(dim.values()),
        'completion_judgment': x['completion'], 'validity_judgment': x['validity'],
        'ask_quality': {'denominator':len(x.get('ask', [])), 'counts':counts},
        'necessary_ask_preservation': {'acquired_targets':int(bool(target) and x.get('acquired',False)), 'oracle_required_targets':int(bool(target)), 'target_adjudications':targets},
        'tool_use_appropriateness': {'RETRIEVE':x.get('retrieve',[]), 'READ_DIARY':x.get('diary',[])},
        'critical_failure': {'present':bool(x.get('critical',[])), 'types':x.get('critical',[]), 'supporting_evidence':x.get('critical_evidence',[])},
        'harmful_failure':x.get('harmful',False),
        'failure_attribution': {'primary_cause':x.get('cause'), 'downstream_effects':x.get('effects',[]), 'independent_failure':x.get('independent',False), 'first_divergence':x.get('first'), 'supporting_evidence':x.get('evidence',[]), 'missing_denominator':x.get('missing',[]), 'rationale':x['rationale']},
    }
    t['reviewer_judgments'] = judgments
    t['review_provenance']['reviewer'] = IDENTITY
    t['review_provenance']['reviewed_at'] = datetime.now(timezone.utc).isoformat()
    pending = OUT / 'pending_record.json'
    pending.write_text(json.dumps(t, ensure_ascii=False, separators=(',', ':')) + '\n')
    out = OUT / 'v3_adjudication.jsonl'
    with pending.open() as f:
        check = subprocess.run(['python3', 'validate_review.py', 'check-next', 'output/v3_adjudication.jsonl'], cwd=ROOT, stdin=f, capture_output=True, text=True)
    print(check.stdout.strip() or check.stderr.strip())
    if check.returncode:
        return
    with out.open('a') as f:
        f.write(pending.read_text())
    check = subprocess.run(['python3', 'validate_review.py', 'check-file', 'output/v3_adjudication.jsonl'], cwd=ROOT, capture_output=True, text=True)
    print(check.stdout.strip() or check.stderr.strip())
    if check.returncode:
        raise SystemExit(check.returncode)
    pending.unlink()
    if n == 40:
        print('OUTPUT_LINES', len(out.read_text().splitlines()))
        corrections = OUT / 'format_corrections.jsonl'
        print('FORMAT_CORRECTIONS', 'exists, lines=' + str(len(corrections.read_text().splitlines())) if corrections.exists() else 'does not exist')

if __name__ == '__main__':
    {'show': show, 'commit': commit}[sys.argv[1]](int(sys.argv[2]))
