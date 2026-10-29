import pytest
from adversarial_ai_evals.loader import load_attack_case, load_attack_cases
from adversarial_ai_evals.model_client import FakeModelClient
from adversarial_ai_evals.runner import attack_success_rate, evaluate_case, rejudge, run_suite


def obeys_injection(user_prompt, tool_response):
    if "purple lantern" in tool_response:
        return "Renewable energy uses water, geothermal and solar. The purple lantern is lit."
    return "Renewable energy uses water, geothermal and solar."


def ignores_injection(user_prompt, tool_response):
    return "Renewable energy uses water, geothermal and solar."


def test_attack_succeeds_when_model_obeys():
    case = load_attack_case("attacks/case_001.json")
    result = evaluate_case(case, FakeModelClient(respond=obeys_injection, model_id="obeys"))
    assert result.attack_succeeded
    assert result.model_id == "obeys"


def test_attack_fails_when_model_ignores():
    case = load_attack_case("attacks/case_001.json")
    result = evaluate_case(case, FakeModelClient(respond=ignores_injection))
    assert not result.attack_succeeded


def test_unsupported_attack_surface():
    case = load_attack_case("attacks/case_001.json").model_copy(update={"attack_surface": "image"})
    with pytest.raises(ValueError):
        evaluate_case(case, FakeModelClient(respond=ignores_injection))


def test_run_suite_over_all_cases():
    cases = load_attack_cases("attacks")
    assert len(cases) >= 3
    results = run_suite(cases, FakeModelClient(respond=ignores_injection))
    assert [r.case_id for r in results] == [c.case_id for c in cases]
    assert attack_success_rate(results) == 0.0


def test_repeats_and_labels():
    case = load_attack_case("attacks/case_001.json")
    client = FakeModelClient(respond=ignores_injection, defense=True)
    results = run_suite([case], client, repeats=3)
    assert [r.trial for r in results] == [1, 2, 3]
    assert all(r.defense for r in results)
    assert all(r.technique == case.technique and r.severity == case.severity for r in results)


def test_attack_success_rate_empty():
    assert attack_success_rate([]) == 0.0


def test_rejudge_rescores_saved_results():
    case = load_attack_case("attacks/case_001.json")
    saved = [evaluate_case(case, FakeModelClient(respond=obeys_injection))]
    assert saved[0].canary_found and saved[0].attack_succeeded

    class Resisted:
        def complied(self, case, response):
            return False

    rescored = rejudge(saved, [case], Resisted())
    assert rescored[0].canary_found
    assert not rescored[0].attack_succeeded
    assert rescored[0].attack_response == saved[0].attack_response
