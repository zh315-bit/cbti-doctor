"""Scan files for baseline / treatment-V1 / treatment-V2 references and prior adjudication text."""
import json, re, sys, hashlib
from pathlib import Path
R=Path("/Volumes/Elements/cbti-doctor-main")
IDENT={
 "baseline_eval":"heldout-v4-step9_28-20260925-01","baseline_attempt":"attempt-step9_29b-5370d36a64d84a3da4f2585e9b57055a",
 "baseline_auth":"auth-step9_29b-7c9d4ba6c7b649e69a64f9b9e68175db","baseline_agent":"4e2bffea0d7eaa9299074a960df84a1806b3ae9d4930662929abc58ca5b2ae79",
 "v1_eval":"heldout-v4-step9_34a-treatment-20260928-01","v1_attempt":"attempt-step9_35b-e469d82618d4c51d91d193bb439507e4",
 "v1_auth":"auth-step9_35b-19cb1db7c4b46f073df71237a8608fc2","v1_agent":"e5e4841b51ecc6bced0f342a261a356756d07b39764670d774b910b86b8625a7",
 "v2_eval":"heldout-v4-step9_43-treatment-v2-20260928-01","v2_attempt":"attempt-step9_44r1-cb362342ae31449aaffba8092c346864",
 "v2_auth":"auth-step9_44r1-ecce3f6d87e64ace822fc46c97c18f55","v2_agent":"b9e891e7cd077dd5b3c6fa72b71faad978a24226c2b5e89e0b06aabde93b51d6"}
PATTERNS={
 "prior_step_ids": r"step9_(?:2[89]|29b|30[abc]?|3[0-9]a?|4[0-9]a?|50)\b|Step 9\.(?:2[89]|3[0-9]|4[0-9]|50)\b",
 "baseline_word": r"(?i)\bbaseline\b|基线",
 "treatment_v1_v2": r"(?i)treatment[-_ ]?v[12]\b|\bv[12]_material|\b(?:V1|V2)\b",
 "reviewer_identity": r"(?i)\bcodex\b|frozen reviewer|human_adjudication|adjudication\.jsonl",
 "score_like_dims": r"\[\s*\d{1,2}\s*,\s*\d{1,2}\s*,\s*\d{1,2}\s*,\s*\d{1,2}\s*,\s*\d{1,2}\s*\]",
}
def prior_texts():
    out=set()
    for p in ["evaluation/v1_2_3/step9_30b_v4_human_adjudication.jsonl","evaluation/v1_2_3/step9_37_treatment_adjudication.jsonl","evaluation/v1_2_3/step9_46_v2_adjudication.jsonl"]:
        for line in open(R/p,encoding="utf-8"):
            def walk(o):
                if isinstance(o,dict): [walk(v) for k,v in o.items() if k not in ("immutable_execution_facts","execution_provenance","review_provenance")]
                elif isinstance(o,list): [walk(v) for v in o]
                elif isinstance(o,str) and len(o)>=30: out.add(o)
            walk(json.loads(line))
    # 30-char shingles from each prior judgment string
    sh=set()
    for t in out:
        for i in range(0,max(1,len(t)-30),15): sh.add(t[i:i+30])
    return out, sh
def scan(paths):
    texts,shingles=prior_texts()
    res={"prior_judgment_strings":len(texts),"prior_shingles":len(shingles),"files":{}}
    for p in paths:
        p=Path(p); t=p.read_text(encoding="utf-8",errors="replace")
        r={"bytes":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),
           "identity_hits":{k:t.count(v) for k,v in IDENT.items() if t.count(v)},
           "pattern_hits":{}, "prior_judgment_shingle_hits":0, "samples":{}}
        for k,pat in PATTERNS.items():
            ms=[m for m in re.finditer(pat,t)]
            if ms:
                r["pattern_hits"][k]=len(ms)
                r["samples"][k]=sorted({t[max(0,m.start()-60):m.end()+60].replace("\n"," ") for m in ms})[:6]
        hits=[s for s in shingles if s in t]
        r["prior_judgment_shingle_hits"]=len(hits); 
        if hits: r["samples"]["prior_judgment_shingles"]=hits[:6]
        res["files"][str(p)]=r
    return res
if __name__=="__main__":
    print(json.dumps(scan(sys.argv[1:]),ensure_ascii=False,indent=1))
