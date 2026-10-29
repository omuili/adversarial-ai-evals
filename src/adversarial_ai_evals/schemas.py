from typing import Literal
from pydantic import BaseModel, Field, ConfigDict

Severity = Literal["benign", "harmful"]

class AttackCase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    case_id: str = Field(min_length=1)
    user_prompt: str = Field(min_length=1)
    attack_surface: str = Field(min_length=1)
    # How the injection is delivered, e.g. hidden_html_comment, fake_system_notice.
    technique: str = Field(min_length=1)
    # Whether obeying the injection would hurt the user (phishing, exfiltration) or is just a harmless tell.
    severity: Severity
    clean_content: str = Field(min_length=1)
    attack_content: str = Field(min_length=1)
    attacker_objective: str = Field(min_length=1)
    success_criterion: str = Field(min_length=1)
    # Distinctive phrase the attacker wants in the response; the judge looks for it.
    canary: str = Field(min_length=1)

    
class EvaluationResult(BaseModel):
    case_id: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    technique: str = Field(min_length=1)
    severity: Severity
    defense: bool
    trial: int = Field(ge=1)
    clean_response: str
    attack_response: str
    # Stage 1: the canary appeared unquoted. Stage 2 (attack_succeeded) confirms the model obeyed.
    canary_found: bool = False
    attack_succeeded: bool 
    
