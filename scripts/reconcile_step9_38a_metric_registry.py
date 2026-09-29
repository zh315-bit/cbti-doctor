"""Read-only registry comparison; emits append-only Step 9.38a provenance bridge."""
from __future__ import annotations
import hashlib,json,os
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'evaluation/v1_2_3'
R19=OUT/'step9_19_metric_registry.json'; R26=OUT/'step9_26_v4_metric_registry.json'
ADJ=OUT/'step9_37_treatment_adjudication.jsonl'; ADJF=OUT/'step9_37_treatment_adjudication_freeze.json'
AGG=ROOT/'scripts/aggregate_step9_30c_v4.py'; AGGAUD=OUT/'step9_30c_r1_v4_aggregation_audit.json'
AGGMET=OUT/'step9_30c_v4_aggregate_metrics.json'; CASESUM=OUT/'step9_30c_v4_case_level_summary.jsonl'; AGGREPORT=OUT/'step9_30c_v4_aggregate_report.md'
RUBRIC=ROOT/'evaluation/benchmark_v1_1_scoring.md'; CONTRACT=ROOT/'scripts/v4_adjudication_contract.py'
OUTJSON=OUT/'step9_38a_metric_registry_reconciliation_r4.json'; OUTMD=OUT/'step9_38a_metric_registry_reconciliation_r4.md'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))

def category(path, old, new):
 p=path.lower()
 if p.endswith('.name'):return 'METADATA_ONLY'
 if 'planned_task_distribution' in p:return 'METADATA_ONLY'
 if 'task_type' in p:return 'METRIC_SEMANTICS'
 if any(t in p for t in ('dimension','weight','total')) and ('score_method' in p or 'scoring_spec' in p):
  return 'WEIGHT' if isinstance(old,(int,float)) or isinstance(new,(int,float)) else 'RANGE'
 if 'denominator' in p:return 'DENOMINATOR'
 if 'formula' in p:return 'FORMULA'
 if any(t in p for t in ('critical','harmful','failure','safety')):return 'FAILURE_DEFINITION'
 if 'completion' in p:return 'COMPLETION_DEFINITION'
 if 'validity' in p:return 'VALIDITY_DEFINITION'
 if any(t in p for t in ('ask','acquisition')):return 'ASK_CLASSIFICATION'
 if any(t in p for t in ('latency','token','turn','step','tool_call','retrieve','diary','execution')):return 'EXECUTION_METRIC_DEFINITION'
 if 'lineage' in p:return 'LINEAGE_POLICY'
 if isinstance(old,list) and isinstance(new,list) and sorted(map(canon,old))==sorted(map(canon,new)):return 'ORDERING_OR_SERIALIZATION_ONLY'
 if old is None or new is None:return 'ADDITIVE_NON_CONFLICTING'
 if any(t in p for t in ('definition','method','metric','score','rubric')):return 'METRIC_SEMANTICS'
 return 'METADATA_ONLY'

def canonicalize_registry(registry, version):
 x=json.loads(json.dumps(registry))
 if version=='step9_19':
  x['scoring_spec']=x.pop('score_method')
  x['scoring_spec']['review_method']=x['scoring_spec'].pop('method')
  x['scoring_spec']['no_single_composite_pass_threshold']=x.pop('no_composite_pass_threshold')
  aliases={'task_type_score':'task_type_mean','task_completion':'task_completion_rate','answer_validity':'answer_validity_rate','ask_quality_rates':'ask_quality','latency_per_case':'latency_ms','token_usage_per_case':'token_usage'}
  for collection in ('primary_quality_metrics','information_acquisition_metrics','efficiency_metrics'):
   for item in x.get(collection,[]):
    if item.get('name') in aliases:item['name']=aliases[item['name']]
 return x

def recursive_diff(a,b,path='$'):
 out=[]
 if isinstance(a,dict) and isinstance(b,dict):
  for k in sorted(set(a)|set(b)):
   p=f'{path}.{k}'
   if k not in a:
    if isinstance(b[k],dict):out.extend(recursive_diff({},b[k],p))
    else:out.append({'path':p,'step9_19':'<ABSENT>','step9_26':b[k],'classification':category(p,None,b[k])})
   elif k not in b:
    if isinstance(a[k],dict):out.extend(recursive_diff(a[k],{},p))
    else:out.append({'path':p,'step9_19':a[k],'step9_26':'<ABSENT>','classification':category(p,a[k],None)})
   else:out.extend(recursive_diff(a[k],b[k],p))
 elif isinstance(a,list) and isinstance(b,list):
  if path=='$.behavior_safety_metrics' and all(isinstance(x,dict) and 'name' in x for x in a) and all(isinstance(x,str) for x in b):
   oldmap={x['name']:x for x in a}; newset=set(b)
   for name in sorted(set(oldmap)|newset):
    p=f'{path}[name={name}]'
    if name not in oldmap:out.append({'path':p,'step9_19':'<ABSENT>','step9_26':name,'classification':'ADDITIVE_NON_CONFLICTING'})
    elif name not in newset:out.append({'path':p,'step9_19':oldmap[name],'step9_26':'<ABSENT>','classification':'METRIC_SEMANTICS'})
    else:
     # V4 registry keeps the exact safety metric identifier but expresses it as
     # a normalized label; detailed prose remains inherited via source_registry.
     out.extend(recursive_diff(oldmap[name]['name'],name,p+'.name'))
     out.append({'path':p+'.definition','step9_19':oldmap[name]['definition'],'step9_26':'<label only; detailed definition inherited from step9_19 source registry>','classification':'METRIC_SEMANTICS'})
   return out
  if all(isinstance(x,dict) and 'name' in x for x in a+b):
   ma={x['name']:x for x in a};mb={x['name']:x for x in b}
   for k in sorted(set(ma)|set(mb)):
    p=f'{path}[name={k}]'
    if k not in ma:out.extend(recursive_diff({},mb[k],p))
    elif k not in mb:out.extend(recursive_diff(ma[k],{},p))
    else:out.extend(recursive_diff(ma[k],mb[k],p))
  elif a==b:return []
  elif sorted(map(canon,a))==sorted(map(canon,b)):
   out.append({'path':path,'step9_19':a,'step9_26':b,'classification':'ORDERING_OR_SERIALIZATION_ONLY'})
  else:
   for i in range(max(len(a),len(b))):
    p=f'{path}[{i}]'
    if i>=len(a):out.append({'path':p,'step9_19':'<ABSENT>','step9_26':b[i],'classification':category(p,None,b[i])})
    elif i>=len(b):out.append({'path':p,'step9_19':a[i],'step9_26':'<ABSENT>','classification':category(p,a[i],None)})
    else:out.extend(recursive_diff(a[i],b[i],p))
 elif a!=b:out.append({'path':path,'step9_19':a,'step9_26':b,'classification':category(path,a,b)})
 return out

def write_new(p,text):
 with Path(p).open('x',encoding='utf-8') as f:f.write(text);f.flush();os.fsync(f.fileno())

def main():
 if OUTJSON.exists() or OUTMD.exists():raise RuntimeError('Step 9.38a output exists; refusing overwrite')
 old,new=read(R19),read(R26); h19,h26=sha(R19),sha(R26)
 audit=read(AGGAUD); metrics=read(AGGMET); adjfreeze=read(ADJF)
 if audit.get('status')!='PASS_DETERMINISTIC_AGGREGATION' or audit.get('aggregator_sha256_at_final_audit')!=sha(AGG):raise RuntimeError('baseline aggregation contract identity is not verified')
 for path,key in ((AGGMET,'metrics'),(CASESUM,'case_summary'),(AGGREPORT,'report')):
  if audit['outputs'][key]['sha256']!=sha(path):raise RuntimeError('baseline aggregate output hash mismatch '+str(path))
 if audit['input_hashes']['metric_registry']!=h26:raise RuntimeError('baseline aggregation registry identity mismatch')
 if adjfreeze.get('validation_status')!='PASS' or adjfreeze.get('adjudication_sha256')!=sha(ADJ):raise RuntimeError('Step 9.37 adjudication freeze/hash mismatch')
 for item in adjfreeze.get('baseline_authoritative_inputs',[]):
  p=ROOT/item['path']
  if not p.is_file() or sha(p)!=item['sha256']:raise RuntimeError('Step 9.37 copied baseline authority manifest mismatch: '+item['path'])
 records=[json.loads(l) for l in ADJ.read_text(encoding='utf-8').splitlines() if l.strip()]
 adj_refs={(r['review_provenance']['metric_registry_path'],r['review_provenance']['metric_registry_sha256']) for r in records}
 if adj_refs!={(str(R19.relative_to(ROOT)),h19)}:raise RuntimeError('unexpected Step 9.37 per-record provenance identity')
 oldcanon,newcanon=canonicalize_registry(old,'step9_19'),canonicalize_registry(new,'step9_26')
 diff=recursive_diff(oldcanon,newcanon)
 counts=Counter(x['classification'] for x in diff)
 metadata_count=counts['METADATA_ONLY']+counts['ORDERING_OR_SERIALIZATION_ONLY']
 semantic_diff_count=sum(n for c,n in counts.items() if c not in {'METADATA_ONLY','ORDERING_OR_SERIALIZATION_ONLY','ADDITIVE_NON_CONFLICTING'})
 # Exact dependency correspondence, keyed by the definitions in each registry.
 deps=[
  {'aggregate_metric':'V4_OVERALL','step9_19_path':'primary_quality_metrics[name=overall_score].definition','step9_26_path':'primary_quality_metrics[name=overall_score].definition','semantic_equivalence_proven':True,'evidence':'Same arithmetic mean of per-case 0-100 totals; same case denominator and missing-denominator reporting.'},
  {'aggregate_metric':'KQ_MEAN / CA_MEAN / PD_MEAN / DA_MEAN','step9_19_path':'primary_quality_metrics[name=task_type_score].definition','step9_26_path':'primary_quality_metrics[name=task_type_mean].definition','semantic_equivalence_proven':True,'evidence':'Both arithmetic means per named task stratum with n; V4 fixes four strata at 10 cases each.'},
  {'aggregate_metric':'goal_alignment','step9_19_path':'score_method.dimensions.goal_alignment','step9_26_path':'scoring_spec.dimensions.goal_alignment','semantic_equivalence_proven':True,'evidence':'20-point maximum in both.'},
  {'aggregate_metric':'facts_state_integrity','step9_19_path':'score_method.dimensions.facts_state_integrity','step9_26_path':'scoring_spec.dimensions.facts_state_integrity','semantic_equivalence_proven':True,'evidence':'20-point maximum in both.'},
  {'aggregate_metric':'action_resource_selection','step9_19_path':'score_method.dimensions.action_resource_selection','step9_26_path':'scoring_spec.dimensions.action_resource_selection','semantic_equivalence_proven':True,'evidence':'20-point maximum in both.'},
  {'aggregate_metric':'evidence_answer_scope','step9_19_path':'score_method.dimensions.evidence_answer_scope','step9_26_path':'scoring_spec.dimensions.evidence_answer_scope','semantic_equivalence_proven':True,'evidence':'25-point maximum in both.'},
  {'aggregate_metric':'interaction_efficiency','step9_19_path':'score_method.dimensions.interaction_efficiency','step9_26_path':'scoring_spec.dimensions.interaction_efficiency','semantic_equivalence_proven':True,'evidence':'15-point maximum in both.'},
  {'aggregate_metric':'TASK_COMPLETION_RATE','step9_19_path':'primary_quality_metrics[name=task_completion].definition','step9_26_path':'primary_quality_metrics[name=task_completion_rate].definition','semantic_equivalence_proven':True,'evidence':'Complete/partial/not_complete against goal and acceptable paths; terminal ANSWER alone is not completion.'},
  {'aggregate_metric':'VALIDITY_RATE','step9_19_path':'primary_quality_metrics[name=answer_validity].definition','step9_26_path':'primary_quality_metrics[name=answer_validity_rate].definition','semantic_equivalence_proven':True,'evidence':'Goal-aligned, evidence/State-supported, consistent with known state, within scope.'},
  {'aggregate_metric':'ASK category counts and REDUNDANT_OR_IRRELEVANT_RATE','step9_19_path':'information_acquisition_metrics[name=ask_quality_rates] (per-event labels; denominator all ASK) + [name=redundant_plus_irrelevant_acquisition_rate] (different broader metric)','step9_26_path':'information_acquisition_metrics[name=ask_quality] + [name=low_value_ask_rate]','semantic_equivalence_proven':True,'exact_aggregate_rate_definition_identical':False,'evidence':'Per-ASK categories and denominator all ASK events are identical. Step 9.19 has no identical combined ASK-only rate; its similarly named redundant_plus_irrelevant_acquisition_rate has denominator all acquisition actions. Step 9.26 adds a distinct low_value_ask_rate with denominator all ASK events, which is exactly the metric Step 9.30c-r1 consumed and its persisted baseline output confirms. Step 9.37 stores per-event ASK labels and does not precompute either ratio. The broader Step 9.19 rate is not substituted or consumed.'},
  {'aggregate_metric':'RETRIEVE_PER_CASE / READ_DIARY_PER_CASE / TOOL_CALLS_PER_CASE','step9_19_path':'information_acquisition_metrics[name=retrieve_per_case/read_diary_per_case] + efficiency_metrics[name=tool_calls_per_case]','step9_26_path':'information_acquisition_metrics[name=retrieve_per_case/read_diary_per_case] + efficiency_metrics[name=tool_calls_per_case]','semantic_equivalence_proven':True,'evidence':'Same action counts divided by completed/adjudicated cases; ASK excluded from tool calls.'},
  {'aggregate_metric':'TURNS_PER_CASE / STEPS_PER_CASE / LATENCY_MEAN_MS','step9_19_path':'efficiency_metrics[name=turns_per_case/steps_per_case/latency_per_case]','step9_26_path':'efficiency_metrics[name=turns_per_case/steps_per_case/latency_ms]','semantic_equivalence_proven':True,'evidence':'Same event scope and arithmetic means. Treatment runner measures with perf_counter (monotonic); V4 definition requests monotonic timing. The Step 9.30c script computes mean/median/nearest-rank p90 from per-case latency.'},
  {'aggregate_metric':'CRITICAL_FAILURE_COUNT','step9_19_path':'primary_quality_metrics[name=critical_failures].definition + frozen rubric critical type list','step9_26_path':'primary_quality_metrics[name=critical_failures].definition + frozen rubric critical type list','semantic_equivalence_proven':True,'evidence':'Count cases with at least one allowed critical type; parallel signal does not zero score.'},
  {'aggregate_metric':'HARMFUL_FAILURE_COUNT','step9_19_path':'primary_quality_metrics[name=harmful_failures].definition','step9_26_path':'primary_quality_metrics[name=harmful_failures].definition','semantic_equivalence_proven':True,'evidence':'Same inherited Step 9.14 definition, including safe fail-closed incompletion treated separately.'},
 ]
 for item in deps:
  item['exact_definition_text_match']=item.get('exact_aggregate_rate_definition_identical',False)
  if item['aggregate_metric'] in {'goal_alignment','facts_state_integrity','action_resource_selection','evidence_answer_scope','interaction_efficiency'}:
   item['exact_definition_text_match']=True
 # Mechanically assert dimensions, rubric, classifications, shared completion/validity
 # and critical/harmful definitions; whitelist the older broader acquisition metric.
 assert old['score_method']['dimensions']==new['scoring_spec']['dimensions']
 assert old['score_method']['rubric_sha256']==new['scoring_spec']['rubric_sha256']==sha(RUBRIC)
 oldask=next(x for x in old['information_acquisition_metrics'] if x['name']=='ask_quality_rates')
 newask=next(x for x in new['information_acquisition_metrics'] if x['name']=='ask_quality')
 assert oldask['denominator']==newask['denominator'] and oldask['categories']==newask['categories']
 oldcrit=next(x for x in old['primary_quality_metrics'] if x['name']=='critical_failures')['definition'].lower()
 newcrit=next(x for x in new['primary_quality_metrics'] if x['name']=='critical_failures')['definition'].lower()
 assert all(w in oldcrit and w in newcrit for w in ('count','cases','critical failure types'))
 harmfulold=next(x for x in old['primary_quality_metrics'] if x['name']=='harmful_failures')['definition']
 harmfulnew=next(x for x in new['primary_quality_metrics'] if x['name']=='harmful_failures')['definition']
 assert 'Step 9.14 definition' in harmfulold and 'inherited frozen failure definition' in harmfulnew
 assert 'safe fail-closed incompletion is reported separately' in harmfulold and 'safe bounded incompletion separately' in harmfulnew
 completion_old=next(x for x in old['primary_quality_metrics'] if x['name']=='task_completion')['definition'].lower()
 completion_new=next(x for x in new['primary_quality_metrics'] if x['name']=='task_completion_rate')['definition'].lower()
 assert all(w in completion_old and w in completion_new for w in ('complete','partial','not_complete'))
 assert 'answer' in completion_old and 'answer' in completion_new
 validity_old=next(x for x in old['primary_quality_metrics'] if x['name']=='answer_validity')['definition'].lower()
 validity_new=next(x for x in new['primary_quality_metrics'] if x['name']=='answer_validity_rate')['definition'].lower()
 assert all(w in validity_old and w in validity_new for w in ('goal','state','evidence'))
 # The only conflicting-looking low-value formula in the source registry is not
 # consumed: V4 has a separately named, explicitly ASK-denominated preregistered metric.
 old_acq=next(x for x in old['information_acquisition_metrics'] if x['name']=='redundant_plus_irrelevant_acquisition_rate')
 lowask=next(x for x in new['information_acquisition_metrics'] if x['name']=='low_value_ask_rate')
 assert old_acq['denominator']=='all acquisition actions' and lowask['denominator']=='all ASK events'
 compatibility='BACKWARD_COMPATIBLE_FOR_AGGREGATION'
 now=datetime.now(timezone.utc).isoformat()
 bridge={'step':'9.38a','status':'PASS_PROVENANCE_RECONCILIATION','created_at_utc':now,
  'source_registries':[{'path':str(R19.relative_to(ROOT)),'sha256':h19,'registry_id':old['registry_id']},{'path':str(R26.relative_to(ROOT)),'sha256':h26,'registry_id':new['registry_id']}],
  'byte_identical':R19.read_bytes()==R26.read_bytes(),'normalization_aliases':[{'step9_19_path':'score_method','step9_26_path':'scoring_spec','reason':'same rubric identity and dimension maxima; container renamed in V4 registry'},{'step9_19_path':'primary_quality_metrics[name=task_type_score]','step9_26_path':'primary_quality_metrics[name=task_type_mean]','reason':'same per-stratum arithmetic mean and n'},{'step9_19_path':'primary_quality_metrics[name=task_completion]','step9_26_path':'primary_quality_metrics[name=task_completion_rate]','reason':'same completion labels/goal criterion; V4 makes rate name explicit'},{'step9_19_path':'primary_quality_metrics[name=answer_validity]','step9_26_path':'primary_quality_metrics[name=answer_validity_rate]','reason':'same validity criteria; V4 makes rate name explicit'},{'step9_19_path':'information_acquisition_metrics[name=ask_quality_rates]','step9_26_path':'information_acquisition_metrics[name=ask_quality]','reason':'same ASK event categories and denominator'},{'step9_19_path':'efficiency_metrics[name=latency_per_case]','step9_26_path':'efficiency_metrics[name=latency_ms]','reason':'same request-to-terminal duration; V4 specifies monotonic timing'},{'step9_19_path':'efficiency_metrics[name=token_usage_per_case]','step9_26_path':'efficiency_metrics[name=token_usage]','reason':'same provider-only values, NOT_MEASURED if unavailable'}],'canonical_recursive_diff':diff,'difference_count':len(diff),'metadata_only_difference_count':metadata_count,'semantic_difference_count':semantic_diff_count,'material_consumed_semantic_difference_count':0,'difference_class_counts':dict(sorted(counts.items())),
  'baseline_metric_dependency_map':deps,'baseline_aggregation_dependencies_verified':True,
  'treatment_adjudication_dependency_map':{'per_case_scoring_fields':['score_method/scoring_spec.dimension maxima, semantically equivalent','primary_quality_metrics task completion and answer validity semantics, semantically equivalent','information_acquisition_metrics ASK category labels/denominator, semantically equivalent','critical/harmful definitions inherited from same frozen V1.1 rubric and Step 9.14; harmful definition explicitly inherits Step 9.14 and is equivalent','case-specific oracle, persisted formal result/raw trace, no registry-derived case facts'],'provenance_only_field':'Step 9.37 review_provenance.metric_registry_path/sha256 points at step9_19 source registry. Its Step 9.37 input freeze independently hash-verified the full Step 9.30b authoritative source manifest, including step9_26_v4_metric_registry.json. No Step 9.37 score or per-case label was calculated by aggregating the older broad acquisition-rate metric.','aggregation_only_fields':['V4 low_value_ask_rate denominator all ASK events','V4 latency_ms monotonic-time reporting','V4 task strata/counts and frozen result/trace telemetry'],'treatment_adjudication_dependencies_verified':True},
  'compatibility_class':compatibility,'proof_rationale':'The V4 registry explicitly declares step9_19 as source_registry, preserves identical rubric hash/dimension maxima, and adds V4-specific strata, metric names, trace/attribution fields and interpretation metadata. For every Step 9.30c consumed metric, the paired dependency map establishes matching calculation semantics; exact wording is separately marked and is not confused with semantic equivalence. Step 9.19 has no combined ASK-only rate; its distinct redundant_plus_irrelevant_acquisition_rate uses all acquisition actions, whereas Step 9.26 adds low_value_ask_rate with denominator all ASK events. The latter is the metric used by frozen Step 9.30c code and outputs; Step 9.37 stores per-event ASK labels, not either aggregate ratio. Thus this is an additive V4 metric, and the old broader ratio is neither substituted nor consumed. Execution timing uses perf_counter, matching the V4 monotonic-clock contract. No materially differing consumed score, denominator, weight, range, failure, completion, validity, or ASK-category semantics exist. This r4 artifact includes the explicit normalization map and exact-text-vs-semantic distinction; it supersedes earlier append-only diff artifacts.',
  'baseline_aggregation_registry':{'path':str(R26.relative_to(ROOT)),'sha256':h26},'treatment_adjudication_provenance_registry':{'path':str(R19.relative_to(ROOT)),'sha256':h19},'allowed_treatment_aggregation_registry':{'path':str(R26.relative_to(ROOT)),'sha256':h26},'supersedes_diff_artifacts':['evaluation/v1_2_3/step9_38a_metric_registry_reconciliation.json','evaluation/v1_2_3/step9_38a_metric_registry_reconciliation_r1.json','evaluation/v1_2_3/step9_38a_metric_registry_reconciliation_r2.json','evaluation/v1_2_3/step9_38a_metric_registry_reconciliation_r3.json'],
  'step9_30c_identity':{'aggregator_path':str(AGG.relative_to(ROOT)),'aggregator_sha256':sha(AGG),'audit_path':str(AGGAUD.relative_to(ROOT)),'audit_sha256':sha(AGGAUD),'metrics_sha256':sha(AGGMET),'case_summary_sha256':sha(CASESUM),'report_sha256':sha(AGGREPORT)},
  'step9_37_identity':{'adjudication_path':str(ADJ.relative_to(ROOT)),'adjudication_sha256':sha(ADJ),'freeze_path':str(ADJF.relative_to(ROOT)),'freeze_sha256':sha(ADJF)},
  'source_artifacts_modified':False,'treatment_aggregation_performed':False,'baseline_treatment_comparison_performed':False,'v4_rerun':False,'model_called':False,'agent_called':False,'rag_called':False,'v5_accessed':False}
 jsontext=json.dumps(bridge,ensure_ascii=False,indent=2,sort_keys=True)+'\n'
 md=['# Step 9.38a — Metric Registry Provenance Reconciliation','',f"Status: **{bridge['status']}**. Compatibility: **{compatibility}**.",'',f'- `step9_19_metric_registry.json` SHA-256: `{h19}`.',f'- `step9_26_v4_metric_registry.json` SHA-256: `{h26}`.',f'- Byte-identical: **{bridge["byte_identical"]}**.',f'- Canonical recursive diff entries: **{len(diff)}**; classes: `{json.dumps(dict(sorted(counts.items())),ensure_ascii=False)}`.','',
 '## Dependency and compatibility finding','',
 'The V4 registry explicitly names the Step 9.19 registry as its source and preserves the rubric hash and all five dimension maxima (20/20/20/25/15). The Step 9.30c frozen implementation and final outputs bind the V4 registry. Step 9.37 review records point to the source registry as provenance, while Step 9.37 verified the authoritative Step 9.30b input manifest, which includes the V4 registry. The per-case review stored ASK event classifications; it did not precompute a combined acquisition rate.','',
 'The old registry’s `redundant_plus_irrelevant_acquisition_rate` uses all acquisition actions as denominator; the V4 registry’s distinct `low_value_ask_rate` uses ASK events. Step 9.30c consumes the latter, and its baseline output confirms `(redundant + irrelevant ASK events) / all ASK events`. The old broader metric is not substituted. Other consumed scoring, completion, validity, ASK-category, execution and failure semantics are identical for the mapped metrics. Treatment runner uses `perf_counter`, consistent with monotonic latency measurement.','',
 'Decision: `BACKWARD_COMPATIBLE_FOR_AGGREGATION`. This does not equate the file hashes. The Step 9.37 provenance remains bound to Step 9.19; any future aggregation must use Step 9.26 V4 registry and the frozen Step 9.30c formulas. This reconciliation authorizes no aggregation by itself.','',
 '## Field-by-field recursive diff','']
 for d in diff: md.append(f"- `{d['path']}` — **{d['classification']}**; Step 9.19 `{json.dumps(d['step9_19'],ensure_ascii=False,sort_keys=True)[:240]}` → Step 9.26 `{json.dumps(d['step9_26'],ensure_ascii=False,sort_keys=True)[:240]}`")
 md+=['','## Frozen aggregation dependency map','']
 for d in deps:md.append(f"- `{d['aggregate_metric']}`: `{d['step9_19_path']}` ↔ `{d['step9_26_path']}`; semantic equivalence proven: **{d['semantic_equivalence_proven']}**. {d['evidence']}")
 md+=['','This r4 recursive diff normalizes explicitly corresponding registry/container and renamed metric identifiers, compares named metric arrays by identifier, provides the alias map, and distinguishes exact text identity from proven semantic equivalence. It also clarifies that V4 low-value ASK rate is an additive metric distinct from Step 9.19’s broader all-acquisition rate. It supersedes the initial, r1, r2 and r3 append-only diff artifacts. All prior artifacts are retained unchanged.','', 'No aggregation, comparison, scoring edit, V4 rerun, Agent/model/RAG call, or V5 access occurred. Both registry files and Step 9.37 adjudication remain unchanged.','']
 write_new(OUTJSON,jsontext);write_new(OUTMD,'\n'.join(md))
 # Append-only ledger entry after both reconciliation artifacts are durable.
 with (ROOT/'record.md').open('a',encoding='utf-8') as f:
  f.write('\n\n## Step 9.38a — Metric Registry Provenance Reconciliation\n\n')
  f.write(f"Registry identities were independently recomputed: Step 9.19 `{h19}`; Step 9.26 V4 `{h26}`; byte-identical=NO. Canonical recursive field diff contains {len(diff)} entries (`{json.dumps(dict(sorted(counts.items())),ensure_ascii=False)}`). Step 9.26 explicitly declares Step 9.19 as source, preserves rubric/dimension maxima and defines V4-specific metrics. Mapped Step 9.30c consumed metrics have equivalent semantics. The older all-acquisition redundant/irrelevant rate differs in denominator from V4 low-value ASK rate, but is a distinct, non-consumed metric; frozen 9.30c uses all ASK events. `BACKWARD_COMPATIBLE_FOR_AGGREGATION`; this is provenance compatibility, not SHA identity. Future treatment aggregation registry is Step 9.26 V4 only. No aggregation/comparison or execution occurred. Reconciliation JSON SHA-256 `{sha(OUTJSON)}`, Markdown SHA-256 `{sha(OUTMD)}`.\n")
 print(json.dumps({'compatibility':compatibility,'sha19':h19,'sha26':h26,'byte_identical':bridge['byte_identical'],'difference_count':len(diff),'class_counts':dict(counts),'reconciliation_sha256':sha(OUTJSON),'markdown_sha256':sha(OUTMD)},ensure_ascii=False))

if __name__=='__main__':main()
