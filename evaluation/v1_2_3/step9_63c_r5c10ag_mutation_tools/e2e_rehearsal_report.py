"""Runs the activation rehearsal on a temporary root and records every command's real output.

usage: python e2e_rehearsal_report.py <out.json>     (writes nothing inside the repository)
"""
import json, os, re, shutil, sys, tempfile
from pathlib import Path
sys.path[:0] = [".", "tests"]
import r11_activation_fixtures as fx
from scripts import authorization_lifecycle as lifecycle
from scripts import build_step9_63c_r11_runner_freeze as builder
from scripts import issue_step9_63c_r11_authorization as issuer
from scripts import run_step9_63_v3_formal_execution as formal

os.environ[builder.SYNTHETIC_ROOT_ENV] = "1"
steps = []

def record(name, command, code, output, **extra):
    output = re.sub(r"\x1b\[[0-9;]*m", "", output)
    steps.append({"step": name, "command": command, "exit_code": code, "output_excerpt": output.strip()[:2500], **extra})

def run_json(module, root, args, **kw):
    code, output = fx.run_cli(module, root, args, **kw)
    return code, output

real_ledger = fx.sha256(fx.REPO / builder.LEDGER_PATH)
real_before = {p: (fx.REPO / p).exists() for p in (builder.IDENTITY_CONFIG_PATH, builder.EXPECTED_FREEZE_PATH, builder.REGISTRY_PATH, builder.AUTHORIZATION_MANIFEST_PATH, builder.APPROVAL_PATH)}
base = Path(tempfile.mkdtemp(prefix="r11-e2e-report-"))
root = fx.build_root(base / "full")
record("S0 status", "-m scripts.build_step9_63c_r11_runner_freeze --status", *run_json(fx.POINTER_MODULE, root, ["--status"]))
code, out = run_json(fx.POINTER_MODULE, root, ["--plan"])
record("pointer plan before AR-14 and approval (must NOT be ready)", "--plan", code, out)
ar14 = fx.retire_r10(root)
record("AR-14 rehearsal (frozen retire_unconsumed_authorization)", "lifecycle.retire_unconsumed_authorization(...)", 0, json.dumps({k: ar14[k] for k in list(ar14)[:6]}, default=str))
approval = fx.sign_approval(root)
code, out = run_json(fx.POINTER_MODULE, root, ["--plan"])
record("pointer plan after AR-14 and a signed approval (ready)", "--plan", code, out)
code, out = fx.create_pointer(root)
record("create pointer (real pty, typed token)", "--create-pointer", code, out)
record("verify pointer", "--verify", *run_json(fx.POINTER_MODULE, root, ["--verify"]))
digest = fx.persist_freeze(root, approval)
record("persist Freeze (library call; no gated CLI exists yet)", "builder.persist_candidate(assemble_candidate(...))", 0, digest,
       freeze_sha256=digest, equals_predicted=digest == approval["freeze"]["predicted_sha256"])
record("verify persisted Freeze", "--verify-freeze", *run_json(fx.POINTER_MODULE, root, ["--verify-freeze"]))
record("status S2", "--status", *run_json(fx.POINTER_MODULE, root, ["--status"]))
record("issuance plan", "issuer --plan", *run_json(fx.ISSUER_MODULE, root, ["--plan"]))
code, out = fx.issue(root)
record("issue (real pty, typed token)", "issuer --issue", code, out[-1500:])
record("issuance status", "issuer --status", *run_json(fx.ISSUER_MODULE, root, ["--status"]))
code, out = run_json(fx.ISSUER_MODULE, root, ["--verify"])
record("issuance verify", "issuer --verify", code, out)
failures, state = fx.gate_failures(root)
manifest = json.loads((root / issuer.MANIFEST_RELATIVE).read_text())
active = lifecycle.active_authorizations(root)
record("consumer precommit gate", "formal.prepare_formal_gates(...)", 0 if not failures else 1, json.dumps({"precommit_failures": failures, "issuance_detail": state.get("authorization_issuance_event_detail")}),
       exactly_one_active=active == [manifest["authorization_id"]], formal_execution_entered=False)
positive = {"gate_failures": failures, "active": active, "namespace_created": (root / "evaluation/v4_runs" / manifest["execution_namespace"]["namespace_id"]).exists()}

negatives = []
def negative(name, make):
    r, _ = fx.fully_issued(base / name)
    make(r)
    failures, state = fx.gate_failures(r)
    negatives.append({"rehearsal": name, "consumer_precommit_failures": failures, "rejected": formal.ISSUANCE_KEY in failures,
                      "issuance_state": issuer.issuance_status(r)["state"], "detail": state.get("authorization_issuance_event_detail")})
def remove_event(r):
    lines = fx.ledger_lines(r); del lines[fx.issued_event_index(r)]; fx.write_ledger(r, lines)
def duplicate_event(r):
    lines = fx.ledger_lines(r); lines.append(lines[fx.issued_event_index(r)]); fx.write_ledger(r, lines)
negative("remove_issuance_event", remove_event)
negative("duplicate_issuance_event", duplicate_event)
hand = fx.build_root(base / "hand_written")
fx.retire_r10(hand); a = fx.sign_approval(hand); assert fx.create_pointer(hand)[0] == 0; fx.persist_freeze(hand, a)
m = json.loads((hand / builder.R10_AUTHORIZATION_PATH).read_text())
m.update(a["issuance"]); m["runner_freeze_revision"] = "r11"; m["runner_freeze_path"] = builder.EXPECTED_FREEZE_PATH
m["runner_freeze_sha256"] = fx.sha256(hand / builder.EXPECTED_FREEZE_PATH); m["execution_namespace"]["namespace_id"] = a["issuance"]["namespace_id"]
(hand / issuer.MANIFEST_RELATIVE).write_text(json.dumps(m, indent=2, sort_keys=True) + "\n")
failures, state = fx.gate_failures(hand)
negatives.append({"rehearsal": "hand_written_manifest", "consumer_precommit_failures": failures, "rejected": formal.ISSUANCE_KEY in failures,
                  "issuance_state": issuer.issuance_status(hand)["state"], "detail": state.get("authorization_issuance_event_detail")})

real_after = {p: (fx.REPO / p).exists() for p in real_before}
report = {
    "artifact_type": "R5C10AG_END_TO_END_REHEARSAL_REPORT", "root_kind": "temporary directory, deleted afterwards",
    "sequence": "AR-14 -> signed approval -> pointer -> Freeze -> issuance -> consumer precommit gate",
    "result": "PASS" if positive["gate_failures"] == [] and positive["active"] == [manifest["authorization_id"]]
              and all(n["rejected"] for n in negatives) and not positive["namespace_created"] else "FAIL",
    "positive": positive, "negative_rehearsals": negatives, "steps": steps,
    "real_repository": {"ledger_sha256_unchanged": fx.sha256(fx.REPO / builder.LEDGER_PATH) == real_ledger,
                        "activation_artifacts_present_before": real_before, "activation_artifacts_present_after": real_after},
}
json.dump(report, open(sys.argv[1], "w"), indent=1)
shutil.rmtree(base, ignore_errors=True)
print(report["result"], "negatives rejected:", [n["rehearsal"] for n in negatives if n["rejected"]])
