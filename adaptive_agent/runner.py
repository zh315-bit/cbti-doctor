"""The synchronous, one-action-at-a-time V1 adaptive-agent loop."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from copy import deepcopy
from typing import Any, Protocol

from .candidates import generate_candidates
from .answer_generation import authorize_final_answer, bounded_authorization_response
from .acquisition_gate import gate_acquisition_candidates
from .input_understanding import InputUnderstander, Understanding, apply_understanding
from .policy import HeuristicDecisionPolicy
from .requirements import RequirementSet, load_requirements, resolve_requirements, synchronize_requirements
from .dependency_resolver import DependencyResolver
from .state import ActionCandidate, AdaptiveAgentState, TaskType
from .state_update import apply_diary_result, apply_retrieval_result
from .sufficiency import SufficiencyEstimator
from .tools import DiaryTool, RetrievalTool


class AnswerGenerator(Protocol):
    def answer(self, state: AdaptiveAgentState, limitation: str | None = None) -> str:
        """Create a bounded answer from goal, explicit facts, and evidence only."""


class BoundedAnswerGenerator:
    """Safe placeholder until the response-generation module is added in Step 3."""

    def answer(self, state: AdaptiveAgentState, limitation: str | None = None) -> str:
        if limitation:
            return f"针对“{state.goal}”，目前无法补足所需信息：{limitation}。我不会据此作出确定的个性化结论。"
        return f"已收集到与“{state.goal}”相关的信息，可进入回答生成阶段。"


@dataclass(frozen=True)
class StateTransition:
    step: int
    action: str
    detail: str


@dataclass
class LoopResult:
    state: AdaptiveAgentState
    status: str
    response: str
    steps: int
    transitions: list[StateTransition] = field(default_factory=list)
    state_history: list[dict[str, Any]] = field(default_factory=list)


class AdaptiveAgentLoop:
    """Runs internal tool actions synchronously; ASK returns control to the caller."""

    def __init__(
        self,
        understander: InputUnderstander,
        retrieval_tool: RetrievalTool,
        diary_tool: DiaryTool,
        answer_generator: AnswerGenerator | None = None,
        requirements: dict[TaskType, RequirementSet] | None = None,
        estimator: SufficiencyEstimator | None = None,
        policy: HeuristicDecisionPolicy | None = None,
        max_steps: int = 4,
    ) -> None:
        self.understander = understander
        self.retrieval_tool = retrieval_tool
        self.diary_tool = diary_tool
        self.answer_generator = answer_generator or BoundedAnswerGenerator()
        self.requirements = requirements or load_requirements()
        self.estimator = estimator or SufficiencyEstimator()
        self.policy = policy or HeuristicDecisionPolicy()
        self.max_steps = max_steps

    def run_turn(self, user_input: str, state: AdaptiveAgentState | None = None) -> LoopResult:
        state = state or AdaptiveAgentState()
        state.turn_index += 1
        understanding = self.understander.understand(user_input, state)
        if state.goal and understanding.is_new_goal:
            state = AdaptiveAgentState()
        apply_understanding(state, understanding)
        state.goal_id = state.goal_id or f"goal_t{state.turn_index}"
        state.state_revision += 1
        state_history = [self._snapshot(state, "INPUT_UNDERSTANDING")]
        if state.task_type is None:
            return LoopResult(state, "ANSWER", self.answer_generator.answer(
                state, "无法可靠识别当前任务类型"), 0, state_history=state_history)

        requirements = resolve_requirements(self.requirements[state.task_type], state.goal)
        transitions: list[StateTransition] = []
        for step in range(1, self.max_steps + 1):
            requirements = self._refresh(state, requirements)
            candidate = self.policy.choose(state)
            decision = self._snapshot(state, "DECISION")
            decision.update(requirements=asdict(requirements), chosen_action=asdict(candidate), step=step)
            answer_authorization = None
            if candidate.action == "ANSWER":
                answer_authorization = authorize_final_answer(state, requirements)
                decision["answer_authorization"] = answer_authorization
                state.answer_context_audit["final_answer_authorization"] = answer_authorization
                if answer_authorization["status"] == "BLOCKED_NEEDS_INFORMATION":
                    needed = set(answer_authorization["material_missing"])
                    acquisition = next((item for item in state.candidate_actions
                                        if item.action == "READ_DIARY"), None)
                    if acquisition is None:
                        acquisition = next((item for item in state.candidate_actions
                                            if item.action == "ASK" and
                                            (not needed or item.target in needed)), None)
                    if acquisition is None:
                        answer_authorization = {
                            **answer_authorization,
                            "status": "BLOCKED_UNSAFE_OR_INVALID",
                            "reason": "no valid unexhausted acquisition candidate is available",
                        }
                        decision["answer_authorization"] = answer_authorization
                        state.answer_context_audit["final_answer_authorization"] = answer_authorization
                    else:
                        candidate = acquisition
                        decision["chosen_action"] = asdict(candidate)
            state_history.append(decision)
            action = state.record_action(candidate)

            if candidate.action == "ASK":
                transitions.append(StateTransition(step, "ASK", candidate.target or ""))
                state_history.append(self._snapshot(state, "ASK"))
                return LoopResult(state, "ASK", candidate.question or "", step, transitions, state_history)
            if candidate.action == "ANSWER":
                transitions.append(StateTransition(step, "ANSWER", candidate.rationale))
                limitation = candidate.rationale if candidate.expected_benefit == "MEDIUM" else None
                if answer_authorization and answer_authorization["status"] in {
                    "AUTHORIZED_BOUNDED", "BLOCKED_UNSAFE_OR_INVALID"
                }:
                    response = bounded_authorization_response(answer_authorization)
                else:
                    response = self.answer_generator.answer(state, limitation)
                state_history.append(self._snapshot(state, "ANSWER"))
                return LoopResult(state, "ANSWER", response, step, transitions, state_history)
            if candidate.action == "RETRIEVE":
                result = self.retrieval_tool.retrieve(candidate.query or state.goal)
                apply_retrieval_result(state, result)
                transitions.append(StateTransition(step, "RETRIEVE", result.detail))
                state.state_revision += 1
                requirements = self._refresh(state, requirements)
                snapshot = self._snapshot(state, "RETRIEVE")
                snapshot.update(tool_result=deepcopy(asdict(result)), step=step)
                state_history.append(snapshot)
                continue
            if candidate.action == "READ_DIARY":
                result = self.diary_tool.read(requirements)
                apply_diary_result(state, result)
                transitions.append(StateTransition(step, "READ_DIARY", result.detail))
                state.state_revision += 1
                requirements = self._refresh(state, requirements)
                snapshot = self._snapshot(state, "READ_DIARY")
                snapshot.update(tool_result=deepcopy(asdict(result)), step=step)
                state_history.append(snapshot)
                continue
            raise RuntimeError(f"Unsupported action: {candidate.action}")

        final_requirements = self._refresh(state, requirements)
        authorization = authorize_final_answer(state, final_requirements)
        state.answer_context_audit["final_answer_authorization"] = authorization
        max_steps_snapshot = self._snapshot(state, "MAX_STEPS")
        max_steps_snapshot["answer_authorization"] = authorization
        state_history.append(max_steps_snapshot)
        response = (bounded_authorization_response(authorization)
                    if authorization["status"] != "AUTHORIZED_FULL"
                    else self.answer_generator.answer(state, "已达到本轮行动上限"))
        return LoopResult(state, "MAX_STEPS", response, self.max_steps, transitions, state_history)

    def _refresh(self, state: AdaptiveAgentState, requirements: RequirementSet) -> RequirementSet:
        base = resolve_requirements(self.requirements[state.task_type], state.goal) if state.task_type else requirements
        self.estimator.update(state, base)
        for name in state.decision_missing:
            state.fact_status.setdefault(name, "UNKNOWN")
        dependencies = DependencyResolver().resolve(state, base)
        effective = synchronize_requirements(base, state, dependencies)
        state.base_requirements = asdict(base)
        state.effective_requirements = asdict(effective)
        self.estimator.update(state, effective)
        generated = generate_candidates(state, effective)
        state.candidate_actions = gate_acquisition_candidates(state, effective, generated)
        return effective

    @staticmethod
    def _snapshot(state: AdaptiveAgentState, event: str) -> dict[str, Any]:
        return {
            "event": event,
            "goal": state.goal,
            "goal_id": state.goal_id,
            "state_revision": state.state_revision,
            "task_type": state.task_type.value if state.task_type else None,
            "facts": deepcopy(state.facts),
            "fact_sources": deepcopy(state.fact_sources),
            "fact_status": deepcopy(state.fact_status),
            "target_status": deepcopy(state.target_status),
            "fact_conflicts": deepcopy(state.fact_conflicts),
            "claim_provenance": deepcopy(state.claim_provenance),
            "answer_context_audit": deepcopy(state.answer_context_audit),
            "information_estimates": deepcopy(state.information_estimates),
            "considered_information": deepcopy(state.considered_information),
            "rejected_information": deepcopy(state.rejected_information),
            "acquisition_decisions": deepcopy(state.acquisition_decisions),
            "stop_reason": state.stop_reason,
            "preconditions_considered": deepcopy(state.preconditions_considered),
            "dependencies_considered": deepcopy(state.dependencies_considered),
            "dependencies_required": deepcopy(state.dependencies_required),
            "dependencies_satisfied": deepcopy(state.dependencies_satisfied),
            "dependencies_unavailable": deepcopy(state.dependencies_unavailable),
            "semantic_provenance": deepcopy(state.semantic_provenance),
            "base_requirements": deepcopy(state.base_requirements),
            "effective_requirements": deepcopy(state.effective_requirements),
            "lineage_events": deepcopy(state.lineage_events),
            "diary_projection": deepcopy(state.diary_projection),
            "critical_missing": list(state.critical_missing),
            "required_missing": list(state.required_missing),
            "decision_relevant_missing": list(state.decision_relevant_missing),
            "validity_critical_missing": list(state.validity_critical_missing),
            "secondary_missing": list(state.secondary_missing),
            "evidence": list(state.evidence),
            "user_info_sufficiency": state.user_info_sufficiency,
            "evidence_sufficiency": state.evidence_sufficiency,
            "candidate_actions": [asdict(item) for item in state.candidate_actions],
            "available_diary": state.available_diary,
            "resource_status": dict(state.resource_status),
            "required_resources": list(state.required_resources),
            "decision_missing": list(state.decision_missing),
            "answer_scope": state.answer_scope,
            "turn_index": state.turn_index,
        }
