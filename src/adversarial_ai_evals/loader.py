from pathlib import Path
import json
from adversarial_ai_evals.schemas import AttackCase

def load_attack_case(path) -> AttackCase:
    with Path(path).open('r', encoding="utf-8") as f:
        attack_case = json.load(f)
    validated_attack_case = AttackCase.model_validate(attack_case)
    return validated_attack_case


def load_attack_cases(directory) -> list[AttackCase]:
    return [load_attack_case(path) for path in sorted(Path(directory).glob("*.json"))]
