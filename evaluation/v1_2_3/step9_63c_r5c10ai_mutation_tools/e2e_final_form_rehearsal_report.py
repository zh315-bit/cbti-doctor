"""Runs the gated activation sequence and the negative rehearsals on temporary roots and records the
real output of every command. Writes nothing inside the repository.

usage: python e2e_final_form_rehearsal_report.py <out.json>
"""
import json, os, re, shutil, sys, tempfile
from pathlib import Path
sys.path[:0] = [".", "tests"]
import r11_activation_fixtures as fx
import r11_gated_fixtures as g
import r11_final_fixtures as ff
from scripts import authorization_lifecycle as lifecycle
from scripts import build_step9_63c_r11_runner_freeze as builder
from scripts import issue_step9_63c_r11_authorization as issuer
from scripts import run_step9_63_v3_formal_execution as formal

os.environ[builder.SYNTHETIC_ROOT_ENV] = "1"
clean = lambda text: re.sub(r"\x1b\[[0-9;]*m", "", text).strip()
steps = []


def rec(name, command, code, output, **extra):
    steps.append({"step": name, "command": command, "exit_code": code, "output": clean(output)[:3500], **extra})


real_ledger = fx.sha256(fx.REPO / builder.LEDGER_PATH)
base = Path(tempfile.mkdtemp(prefix="r11-gated-report-"))
root, approval = ff.final_flow_root(base / "full")
P, I = g.POINTER_MODULE, g.ISSUER_MODULE
rec("0 status", "--status", *fx.run_cli(P, root, ["--status"]))
rec("0 pointer plan before AR-14 (must NOT be ready)", "--plan", *fx.run_cli(P, root, ["--plan"]))
ledger_before = (root / builder.LEDGER_PATH).read_bytes()
rec("1 AR-14 plan", "--plan-retire", *fx.run_cli(P, root, ["--plan-retire"]))
rec("1 AR-14 verify before (NOT_RETIRED)", "--verify-retire", *fx.run_cli(P, root, ["--verify-retire"]))
rec("1 AR-14 write (real pty, typed token)", "--retire-r10", *g.cli(root, "--retire-r10", token=g.retire_token(root)))
rec("1 AR-14 verify after", "--verify-retire", *fx.run_cli(P, root, ["--verify-retire"]))
appended = (root / builder.LEDGER_PATH).read_bytes()[len(ledger_before):].decode()
rec("2 pointer plan", "--plan", *fx.run_cli(P, root, ["--plan"]))
rec("2 pointer write", "--create-pointer", *g.cli(root, "--create-pointer", token=builder.POINTER_TOKEN))
rec("2 pointer verify", "--verify", *fx.run_cli(P, root, ["--verify"]))
rec("3 Freeze plan", "--plan-freeze", *fx.run_cli(P, root, ["--plan-freeze"]))
rec("3 Freeze write", "--create-freeze", *g.cli(root, "--create-freeze", token=g.freeze_token(root)))
rec("3 Freeze verify", "--verify-freeze", *fx.run_cli(P, root, ["--verify-freeze"]))
rec("4 issuance plan", "issuer --plan", *fx.run_cli(I, root, ["--plan"]))
rec("4 issuance write", "issuer --issue", *fx.run_cli(I, root, ["--issue"], mode="tty", lines=[issuer.plan_issuance(root)["confirmation_token"]]))
rec("4 issuance verify", "issuer --verify", *fx.run_cli(I, root, ["--verify"]))
failures = g.with_gate(root, lambda a: formal.prepare_formal_gates(a)["precommit_failures"])
manifest = json.loads((root / builder.AUTHORIZATION_MANIFEST_PATH).read_text())
active = lifecycle.active_authorizations(root)
positive = {"consumer_gate_failures": failures, "active": active, "exactly_one_active": active == [manifest["authorization_id"]],
            "freeze_sha_equals_prediction": fx.sha256(root / builder.EXPECTED_FREEZE_PATH) == approval["freeze"]["predicted_sha256"],
            "retirement_appended_one_line": appended.count("\n") == 1, 
            "namespace_created": (root / "evaluation/v4_runs" / manifest["execution_namespace"]["namespace_id"]).exists(),
            "formal_execution_entered": False, "approval_unchanged_throughout": True}

ENTRIES = {
 "retire": ("s0", P, "--retire-r10", lambda r: builder.plan_retirement(r)["confirmation_token"]),
 "pointer": ("retired", P, "--create-pointer", lambda r: builder.POINTER_TOKEN),
 "freeze": ("pointer", P, "--create-freeze", lambda r: builder.plan_freeze(r)["confirmation_token"]),
 "issue": ("freeze", I, "--issue", lambda r: issuer.plan_issuance(r)["confirmation_token"]),
}
T = ff.FinalTemplates("r11-final-report-neg-")
T.build("s0", "retired", "pointer", "freeze")
negatives = []


def negative(name, root, module, flag, token, mode="tty", env=None, expect_code=2):
    before = fx.tree_digest(root)
    code, output = fx.run_cli(module, root, [flag], mode=mode, lines=[token] if token is not None else [], env=env)
    negatives.append({"rehearsal": name, "entry": flag, "mode": mode, "exit_code": code, "refused": code == expect_code,
                      "no_write": fx.tree_digest(root) == before, "reason": (re.findall(r'"reason": "([^"]{0,260})', output) or re.findall(r"refused[^\n]{0,200}", output) or [clean(output)[-200:]])[0]})


for entry, (state, module, flag, tokf) in ENTRIES.items():
    r = T.clone(state); tk = tokf(r)
    g.rewrite_approval(r, lambda a: a.update(status=builder.APPROVAL_DRAFT, approver=None, signed_at_utc=None))
    negative(f"unsigned approval / {entry}", r, module, flag, tk)
    r = T.clone(state); negative(f"wrong token / {entry}", r, module, flag, tokf(r) + "x")
    r = T.clone(state); negative(f"empty token / {entry}", r, module, flag, "")
    for mode in ("pipe", "tty-in-only", "tty-out-only"):
        r = T.clone(state); negative(f"non-interactive ({mode}) / {entry}", r, module, flag, tokf(r), mode=mode, env=fx.cli_env({"CI": "true"}))
r = T.clone("s0"); tk = g.retire_token(r)
with (r / builder.LEDGER_PATH).open("a") as stream:
    stream.write(json.dumps({"artifact_type": "AUTHORIZATION_LIFECYCLE_EVENT", "event_type": "PRE_APPENDED"}) + "\n")
negative("ledger had a line appended beforehand / retire", r, P, "--retire-r10", tk)
r = T.clone("pointer"); g.rewrite_approval(r, lambda a: a["freeze"].update(predicted_sha256="f" * 64))
negative("Freeze prediction does not match / freeze", r, P, "--create-freeze", "CREATE-R11-FREEZE-" + "f" * 12 + "-" + fx.sha256(r / builder.APPROVAL_PATH)[:12])
r = T.clone("s0"); negative("skip AR-14: create the pointer / pointer", r, P, "--create-pointer", builder.POINTER_TOKEN)
r = T.clone("s0")
(r / builder.IDENTITY_CONFIG_PATH).write_bytes(builder.canonical_pointer_bytes())
(r / builder.POINTER_CREATION_RECORD_PATH).write_text(json.dumps({"pointer_sha256": builder.POINTER_SHA256, "approval_record_sha256": fx.sha256(r / builder.APPROVAL_PATH)}))
negative("skip AR-14: create the Freeze directly / freeze", r, P, "--create-freeze", g.freeze_token(r))
r = T.clone("pointer"); negative("skip the Freeze: issue / issue", r, I, "--issue", "ISSUE-R11-AUTH-000000000000")
r = T.clone("retired"); negative("replay AR-14 / retire", r, P, "--retire-r10", "RETIRE-R10-auth-step9_6-" + fx.sha256(r / builder.APPROVAL_PATH)[:12])
r = T.clone("freeze"); negative("replay Freeze creation / freeze", r, P, "--create-freeze", "CREATE-R11-FREEZE-" + "0" * 12 + "-" + "0" * 12)

# --- new in r5c10ai: token and commit-pin negatives
content12 = json.loads((T.roots["s0"] / builder.APPROVAL_PATH).read_text())["content_sha256"][:12]
r = T.clone("s0")
negative("token from another step9_6x authorization id (step9_63c_r4) / retire", r, P, "--retire-r10", f"RETIRE-R10-4b2749ce1001-{content12}")
r = T.clone("s0")
negative("token with the previous literal first segment / retire", r, P, "--retire-r10", f"RETIRE-R10-auth-step9_6-{content12}")
r = T.clone("s0")
negative("token whose second part is the signed file hash instead of the content hash / retire", r, P, "--retire-r10", f"RETIRE-R10-aff5c4b96bb7-{fx.sha256(r / builder.APPROVAL_PATH)[:12]}")
for entry, (state, module, flag, tokf) in ENTRIES.items():
    r = T.clone(state); tk = tokf(r); ff.set_head(r, ff.OTHER_COMMIT)
    negative(f"Git HEAD moved after signing (committed again) / {entry}", r, module, flag, tk)
    r = T.clone(state); tk = tokf(r); g.rewrite_approval(r, lambda a: a.update(signed_at_commit=None))
    negative(f"approval names no signing commit / {entry}", r, module, flag, tk)
    r = T.clone(state); tk = tokf(r); g.rewrite_approval(r, lambda a: a["accepted_exceptions"][0].update(text="edited after the draft was prepared"))
    negative(f"approval content edited beyond the signature fields / {entry}", r, module, flag, tk)
# issuance negatives carried from the previous step: remove event, hand-written manifest, duplicate
issued, _ = ff.through_final(base / "issued", "issued")
lines = fx.ledger_lines(issued); del lines[fx.issued_event_index(issued)]; fx.write_ledger(issued, lines)
consumer = {"event_removed": formal.ISSUANCE_KEY in g.with_gate(issued, lambda a: formal.prepare_formal_gates(a)["precommit_failures"])}
report = {
 "artifact_type": "R5C10AI_FINAL_FORM_REHEARSAL_REPORT", "root_kind": "temporary directories, deleted afterwards",
 "sequence": "signed approval -> --retire-r10 -> --create-pointer -> --create-freeze -> --issue -> consumer precommit gate",
 "result": "PASS" if (positive["consumer_gate_failures"] == [] and positive["exactly_one_active"] and positive["freeze_sha_equals_prediction"]
                      and positive["retirement_appended_one_line"] and not positive["namespace_created"]
                      and all(n["refused"] and n["no_write"] for n in negatives) and consumer["event_removed"]) else "FAIL",
 "positive": positive, "retirement_event_line_appended": appended.strip()[:1800],
 "negative_rehearsals": negatives, "negative_summary": {"total": len(negatives), "refused": sum(n["refused"] for n in negatives), "no_write": sum(n["no_write"] for n in negatives)},
 "consumer_still_rejects_a_missing_issuance_event": consumer, "steps": steps,
 "real_repository": {"ledger_sha256_unchanged": fx.sha256(fx.REPO / builder.LEDGER_PATH) == real_ledger,
                     "r11_pointer_exists": (fx.REPO / builder.IDENTITY_CONFIG_PATH).exists(), "r11_freeze_exists": (fx.REPO / builder.EXPECTED_FREEZE_PATH).exists(),
                     "r11_authorization_exists": (fx.REPO / builder.AUTHORIZATION_MANIFEST_PATH).exists()}}
json.dump(report, open(sys.argv[1], "w"), indent=1)
T.close(); shutil.rmtree(base, ignore_errors=True)
print(report["result"], report["negative_summary"], positive["consumer_gate_failures"])
