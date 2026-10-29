from adversarial_ai_evals.report import build_report, load_results
from adversarial_ai_evals.schemas import EvaluationResult


def result(case_id, severity, defense, succeeded, trial=1):
    return EvaluationResult(
        case_id=case_id,
        model_id="model-a",
        technique="plain_instruction",
        severity=severity,
        defense=defense,
        trial=trial,
        clean_response="clean",
        attack_response="attack",
        attack_succeeded=succeeded,
    )


def test_build_report_tables():
    results = [
        result("case_001", "benign", False, True, trial=1),
        result("case_001", "benign", False, False, trial=2),
        result("case_002", "harmful", False, False),
        result("case_001", "benign", True, False),
        result("case_002", "harmful", True, False),
    ]
    report = build_report(results)
    assert "| model-a | no | 1/3 (33%) | 1/2 (50%) | 0/1 (0%) |" in report
    assert "| model-a | yes | 0/2 (0%) | 0/1 (0%) | 0/1 (0%) |" in report
    assert "| case_001 | plain_instruction | benign | 1/2 (50%) | 0/1 (0%) |" in report


def test_load_results_round_trip(tmp_path):
    path = tmp_path / "results.jsonl"
    original = [result("case_001", "benign", False, True)]
    path.write_text("".join(r.model_dump_json() + "\n" for r in original), encoding="utf-8")
    assert load_results([path]) == original
