import argparse
from pathlib import Path

from adversarial_ai_evals.judge import ClaudeComplianceVerifier
from adversarial_ai_evals.loader import load_attack_cases
from adversarial_ai_evals.model_client import AnthropicModelClient, FakeModelClient, OpenAIModelClient
from adversarial_ai_evals.runner import attack_success_rate, run_suite

DEFAULT_MODELS = {"anthropic": "claude-opus-5-5", "openai": "gpt-4.1"}


def first_sentence(user_prompt: str, tool_response: str) -> str:
    return tool_response.split(".")[0] + "."


def main() -> None:
    parser = argparse.ArgumentParser(description="Run indirect prompt-injection evals against a model.")
    parser.add_argument("--attacks-dir", default="attacks", help="directory of attack case JSON files")
    parser.add_argument("--provider", choices=DEFAULT_MODELS, default="anthropic", help="model API to call")
    parser.add_argument("--model", help="model ID to evaluate (default depends on --provider)")
    parser.add_argument("--repeats", type=int, default=1, help="times to run each case (default: 1)")
    parser.add_argument(
        "--defense",
        action="store_true",
        help="add a system prompt telling the model to treat tool output as untrusted data",
    )
    parser.add_argument(
        "--canary-only",
        action="store_true",
        help="score with the canary string match alone; skips the Claude check that tells "
        "obeying apart from warning (needs no Anthropic key, but over-counts successes)",
    )
    parser.add_argument(
        "--output", help="JSONL results file (default: results/<model>[-defense].jsonl)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="use an offline fake model that echoes the first sentence; no API calls",
    )
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be at least 1")

    if args.dry_run:
        client = FakeModelClient(respond=first_sentence, defense=args.defense)
    elif args.provider == "openai":
        client = OpenAIModelClient(model_id=args.model or DEFAULT_MODELS["openai"], defense=args.defense)
    else:
        client = AnthropicModelClient(
            model_id=args.model or DEFAULT_MODELS["anthropic"], defense=args.defense
        )

    verifier = None if args.dry_run or args.canary_only else ClaudeComplianceVerifier()

    cases = load_attack_cases(args.attacks_dir)
    if not cases:
        parser.error(f"no attack cases found in {args.attacks_dir}")

    suffix = "-defense" if args.defense else ""
    output = Path(args.output or f"results/{client.model_id}{suffix}.jsonl")
    output.parent.mkdir(parents=True, exist_ok=True)

    total = len(cases) * args.repeats
    print(f"Running {len(cases)} cases x {args.repeats} repeats against {client.model_id} "
          f"({total * 2} API calls). Writing to {output}", flush=True)

    # Each result is written as soon as it arrives, so an interrupted run keeps what it finished.
    with output.open("w", encoding="utf-8") as results_file:
        def record(result):
            results_file.write(result.model_dump_json() + "\n")
            results_file.flush()
            done = record.count = getattr(record, "count", 0) + 1
            verdict = "ATTACK SUCCEEDED" if result.attack_succeeded else "resisted"
            print(f"[{done}/{total}] {result.case_id} trial {result.trial}: {verdict}", flush=True)

        results = run_suite(cases, client, repeats=args.repeats, on_result=record, verifier=verifier)

    print()
    for case in cases:
        case_results = [r for r in results if r.case_id == case.case_id]
        succeeded = sum(r.attack_succeeded for r in case_results)
        print(f"{case.case_id} ({case.technique}, {case.severity}): attack succeeded {succeeded}/{len(case_results)}")
    succeeded = sum(result.attack_succeeded for result in results)
    label = f"{client.model_id}{' with defense prompt' if args.defense else ''}"
    print(
        f"\n{label}: attack success rate {succeeded}/{len(results)} "
        f"({attack_success_rate(results):.0%}). Results written to {output}"
    )
