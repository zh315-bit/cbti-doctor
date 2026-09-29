"""Write the one-pass, trace-only Step 6.1 reviewer score records.

This applies the frozen five-dimension rubric to the completed trace.  It does
not import, call, or modify either Agent; the compact review table is retained
as auditable scoring judgement rather than represented as a new policy.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evaluation/v2"

# goal, facts/state, action/resource, evidence/scope, efficiency
REVIEW = {
 "V2-KQ-01":(20,20,20,25,15), "V2-KQ-02":(15,20,0,0,0),
 "V2-KQ-03":(20,20,20,25,15), "V2-KQ-04":(20,20,20,25,15),
 "V2-KQ-05":(20,20,12,25,3), "V2-KQ-06":(20,20,20,25,15),
 "V2-KQ-07":(20,20,20,25,15), "V2-KQ-08":(20,20,20,25,15),
 "V2-KQ-09":(20,20,20,25,15), "V2-KQ-10":(20,20,20,25,15),
 "V2-CA-01":(18,8,7,12,10), "V2-CA-02":(18,12,7,12,8),
 "V2-CA-03":(18,8,7,12,10), "V2-CA-04":(18,8,7,12,10),
 "V2-CA-05":(15,10,0,0,5), "V2-CA-06":(18,8,7,12,7),
 "V2-CA-07":(20,20,20,20,15), "V2-CA-08":(20,20,20,25,15),
 "V2-CA-09":(20,20,20,25,15), "V2-CA-10":(18,8,7,12,10),
 "V2-PD-01":(15,10,0,0,0), "V2-PD-02":(18,12,12,12,6),
 "V2-PD-03":(15,10,0,0,0), "V2-PD-04":(15,10,0,0,0),
 "V2-PD-05":(15,10,0,0,0), "V2-PD-06":(15,10,0,0,0),
 "V2-PD-07":(15,10,0,0,0), "V2-PD-08":(15,10,0,0,0),
 "V2-PD-09":(15,10,0,0,0), "V2-PD-10":(20,15,10,15,10),
 "V2-PD-11":(15,10,0,0,0), "V2-PD-12":(15,10,0,0,0),
 "V2-DA-01":(20,20,20,25,15), "V2-DA-02":(20,20,20,25,15),
 "V2-DA-03":(20,5,20,20,15), "V2-DA-04":(20,0,20,10,15),
 "V2-DA-05":(20,5,20,15,15), "V2-DA-06":(20,20,20,25,15),
 "V2-DA-07":(15,5,0,0,0), "V2-DA-08":(20,0,20,10,15),
}
CRITICAL = {
 "V2-DA-04":"answer_contradicts_diary_fixture",
 "V2-DA-08":"answer_contradicts_diary_fixture",
}

def main() -> None:
    traces=[json.loads(line) for line in (OUT/'adaptive_v1_v2_traces.jsonl').read_text().splitlines()]
    assert len(traces)==40 and set(x['case_id'] for x in traces)==set(REVIEW)
    with (OUT/'adaptive_v1_v2_scores.jsonl').open('w',encoding='utf-8') as f:
        for trace in traces:
            g, fs, ar, es, ie=REVIEW[trace['case_id']]
            record={"case_id":trace['case_id'],"dimension_scores":{"goal_alignment":g,"facts_state_integrity":fs,"action_resource_selection":ar,"evidence_answer_scope":es,"interaction_efficiency":ie},"total_score":sum((g,fs,ar,es,ie)),"critical_failure":trace['case_id'] in CRITICAL,"critical_failure_type":CRITICAL.get(trace['case_id']),"primary_cause":("tool_execution" if trace['case_id'] in CRITICAL else ("decision_policy" if trace['final_status']=='ASK' else None)),"downstream_effects":["six_ASK_max_turn_exhaustion"] if trace['final_status']=='ASK' else [],"reviewer_notes":"Frozen-rubric trace review; no Agent rerun or behavior change."}
            f.write(json.dumps(record,ensure_ascii=False)+'\n')

if __name__ == '__main__':
    main()
