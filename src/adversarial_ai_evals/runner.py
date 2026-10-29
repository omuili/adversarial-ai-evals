from typing import Callable

from adversarial_ai_evals.judge import ComplianceVerifier, canary_found, judge_attack
from adversarial_ai_evals.model_client import ModelClient
from adversarial_ai_evals.schemas import AttackCase, EvaluationResult

SUPPORTED_ATTACK_SURFACES = {"tool_response"}


def evaluate_case(
    case: AttackCase,
    client: ModelClient,
    trial: int = 1,
    verifier: ComplianceVerifier | None = None,
) -> EvaluationResult:
    if case.attack_surface not in SUPPORTED_ATTACK_SURFACES:
        raise ValueError(f"{case.case_id}: unsupported attack_surface {case.attack_surface!r}")
    clean_response = client.run_with_tool_response(case.user_prompt, case.clean_content)
    attack_response = client.run_with_tool_response(case.user_prompt, case.attack_content)
    return EvaluationResult(
        case_id=case.case_id,
        model_id=client.model_id,
        technique=case.technique,
        severity=case.severity,
        defense=client.defense,
        trial=trial,
        clean_response=clean_response,
        attack_response=attack_response,
        canary_found=canary_found(case, clean_response, attack_response),
        attack_succeeded=judge_attack(case, clean_response, attack_response, verifier),
    )


def run_suite(
    cases: list[AttackCase],
    client: ModelClient,
    repeats: int = 1,
    on_result: Callable[[EvaluationResult], None] | None = None,
    verifier: ComplianceVerifier | None = None,
) -> list[EvaluationResult]:
    # Model output varies between calls, so each case is run `repeats` times.
    results = []
    for case in cases:
        for trial in range(1, repeats + 1):
            result = evaluate_case(case, client, trial, verifier)
            results.append(result)
            if on_result:
                on_result(result)
    return results


def attack_success_rate(results: list[EvaluationResult]) -> float:
    if not results:
        return 0.0
    return sum(result.attack_succeeded for result in results) / len(results)


def rejudge(
    results: list[EvaluationResult], cases: list[AttackCase], verifier: ComplianceVerifier | None
) -> list[EvaluationResult]:
    """Re-score saved responses with the current judge, without calling the evaluated model again."""
    cases_by_id = {case.case_id: case for case in cases}
    rescored = []
    for result in results:
        case = cases_by_id[result.case_id]
        rescored.append(result.model_copy(update={
            "canary_found": canary_found(case, result.clean_response, result.attack_response),
            "attack_succeeded": judge_attack(
                case, result.clean_response, result.attack_response, verifier
            ),
        }))
    return rescored
