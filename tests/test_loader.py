from adversarial_ai_evals.loader import load_attack_case


def test_load_valid_attack_case():
    attack = load_attack_case("attacks/case_001.json")
    assert attack.case_id == "case_001"
    assert "The purple lantern is lit." in attack.attack_content
     