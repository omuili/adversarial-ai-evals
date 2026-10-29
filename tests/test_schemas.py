import pytest
from adversarial_ai_evals.schemas import AttackCase
from pydantic import ValidationError


def test_valid_attack_case():
    attack = AttackCase(
        case_id="1", 
        user_prompt="1",
        attack_surface="1",
        technique="1",
        severity="benign",
        clean_content="1",
        attack_content="1",
        attacker_objective="1",
        success_criterion="1",
        canary="1")
    assert attack.case_id == "1"

def test_missing_case_id():
    with pytest.raises(ValidationError):
        attack = AttackCase(
            user_prompt="1",
            attack_surface="1",
            clean_content="1",
            attack_content="1",
            attacker_objective="1",
            success_criterion="1"

            )
def test_empty_case_id():
    with pytest.raises(ValidationError):
        attack = AttackCase(
            case_id="", 
            user_prompt="1",
            attack_surface="1",
            clean_content="1",
            attack_content="1",
            attacker_objective="1",
            success_criterion="1"

        )

def test_whitespace_case_id():
    with pytest.raises(ValidationError):
        attack = AttackCase(
        case_id=" ", 
        user_prompt="1",
        attack_surface="1",
        clean_content="1",
        attack_content="1",
        attacker_objective="1",
        success_criterion="1"

        )
    
     

def test_invalid_severity():
    with pytest.raises(ValidationError):
        AttackCase(
            case_id="1",
            user_prompt="1",
            attack_surface="1",
            technique="1",
            severity="medium",
            clean_content="1",
            attack_content="1",
            attacker_objective="1",
            success_criterion="1",
            canary="1",
        )
