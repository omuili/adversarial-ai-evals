import argparse
from collections import defaultdict
from pathlib import Path

from adversarial_ai_evals.judge import ClaudeComplianceVerifier
from adversarial_ai_evals.loader import load_attack_cases
from adversarial_ai_evals.runner import attack_success_rate, rejudge
from adversarial_ai_evals.schemas import EvaluationResult


def load_results(paths) -> list[EvaluationResult]:
    results = []
    for path in paths:
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if line.strip():
                results.append(EvaluationResult.model_validate_json(line))
    return results


def run_label(model_id: str, defense: bool) -> str:
    return f"{model_id} + defense" if defense else model_id


def fraction(results: list[EvaluationResult]) -> str:
    if not results:
        return "–"
    succeeded = sum(result.attack_succeeded for result in results)
    return f"{succeeded}/{len(results)} ({attack_success_rate(results):.0%})"


def build_report(results: list[EvaluationResult]) -> str:
    """Markdown tables of attack success rate (lower is better for the model)."""
    by_run = defaultdict(list)
    for result in results:
        by_run[(result.model_id, result.defense)].append(result)
    runs = sorted(by_run)

    lines = [
        "### Attack success rate by model",
        "",
        "| Model | Defense prompt | All cases | Benign goals | Harmful goals |",
        "|---|---|---|---|---|",
    ]
    for model_id, defense in runs:
        run = by_run[(model_id, defense)]
        lines.append(
            f"| {model_id} | {'yes' if defense else 'no'} | {fraction(run)} "
            f"| {fraction([r for r in run if r.severity == 'benign'])} "
            f"| {fraction([r for r in run if r.severity == 'harmful'])} |"
        )

    cases = sorted({(r.case_id, r.technique, r.severity) for r in results})
    lines += [
        "",
        "### Attack success by case",
        "",
        "| Case | Technique | Goal | " + " | ".join(run_label(*run) for run in runs) + " |",
        "|---|---|---|" + "---|" * len(runs),
    ]
    for case_id, technique, severity in cases:
        cells = [
            fraction([r for r in by_run[run] if r.case_id == case_id]) for run in runs
        ]
        lines.append(f"| {case_id} | {technique} | {severity} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize eval results as Markdown tables.")
    parser.add_argument("paths", nargs="*", help="JSONL result files (default: results/*.jsonl)")
    args = parser.parse_args()
    # Dry-run output (results/fake*.jsonl) is skipped unless named explicitly.
    paths = args.paths or sorted(
        path for path in Path("results").glob("*.jsonl") if not path.name.startswith("fake")
    )
    if not paths:
        parser.error("no result files found")
    print(build_report(load_results(paths)), end="")


def rejudge_main() -> None:
    parser = argparse.ArgumentParser(
        description="Re-score saved results with the current judge (rewrites the files in place)."
    )
    parser.add_argument("paths", nargs="+", help="JSONL result files")
    parser.add_argument("--attacks-dir", default="attacks", help="directory of attack case JSON files")
    parser.add_argument("--canary-only", action="store_true", help="skip the Claude compliance check")
    args = parser.parse_args()

    cases = load_attack_cases(args.attacks_dir)
    verifier = None if args.canary_only else ClaudeComplianceVerifier()
    for path in args.paths:
        before = load_results([path])
        after = rejudge(before, cases, verifier)
        Path(path).write_text("".join(r.model_dump_json() + "\n" for r in after), encoding="utf-8")
        print(
            f"{path}: attack success {sum(r.attack_succeeded for r in before)}/{len(before)} -> "
            f"{sum(r.attack_succeeded for r in after)}/{len(after)} "
            f"(canary found in {sum(r.canary_found for r in after)})"
        )
