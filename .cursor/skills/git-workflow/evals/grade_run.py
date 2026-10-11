"""Grade a git-workflow eval run from sandbox + agent outputs."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SECRET_PATHS = {".env", "credentials.json", ".pem", ".p8"}
BRANCH_PREFIXES = ("feat/", "fix/", "docs/")


def run(cmd: list[str], cwd: Path) -> str:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode, cmd, result.stdout, result.stderr
        )
    return result.stdout.strip()


def grade_assertion(
    assertion_id: str,
    repo: Path,
    baseline: str,
    outputs: Path,
    eval_id: int,
) -> tuple[bool, str]:
    branch = run(["git", "branch", "--show-current"], cwd=repo)
    changed_files = run(
        ["git", "diff", "--name-only", f"{baseline}..HEAD"], cwd=repo
    ).splitlines()
    changed_files = [f for f in changed_files if f]

    summary_path = outputs / "agent_summary.md"
    summary_text = summary_path.read_text(encoding="utf-8") if summary_path.exists() else ""
    pr_plan_path = outputs / "pr_plan.md"
    pr_plan_text = pr_plan_path.read_text(encoding="utf-8") if pr_plan_path.exists() else ""

    if assertion_id in ("branch_prefix", "branch_feat_prefix"):
        if assertion_id == "branch_feat_prefix":
            ok = branch.startswith("feat/")
        else:
            ok = branch != "main" and branch.startswith(BRANCH_PREFIXES)
        return ok, f"branch={branch}"

    if assertion_id == "branch_docs_prefix":
        ok = branch.startswith("docs/")
        return ok, f"branch={branch}"

    if assertion_id == "main_updated_before_branch":
        reflog = run(
            ["git", "reflog", "--grep-reflog=checkout", "-n", "40", "--format=%gs"],
            cwd=repo,
        )
        lines = [line.strip().lower() for line in reflog.splitlines() if line.strip()]
        branch_idx = None
        main_idx = None
        for i, line in enumerate(lines):
            if branch_idx is None and re.search(r"to (feat|fix|docs)/", line):
                branch_idx = i
            if main_idx is None and re.search(r"to main$", line):
                main_idx = i
        if branch_idx is not None and main_idx is not None:
            ok = main_idx > branch_idx
            return ok, f"reflog main_idx={main_idx} branch_idx={branch_idx} (main before feature)"
        lowered = summary_text.lower()
        ok = ("pull" in lowered or "fetch" in lowered) and "checkout main" in lowered.replace("_", " ")
        return ok, "fallback: agent_summary.md (reflog inconclusive)"

    if assertion_id == "ready_route_implemented":
        main_py = (repo / "app" / "main.py").read_text(encoding="utf-8")
        ok = '"/ready"' in main_py or "'/ready'" in main_py
        ok = ok and "ready" in main_py
        return ok, "scanned app/main.py for /ready route"

    if assertion_id == "ready_test_added":
        tests_dir = repo / "tests"
        text = "\n".join(p.read_text(encoding="utf-8") for p in tests_dir.glob("*.py"))
        ok = "/ready" in text
        return ok, "scanned tests for /ready"

    if assertion_id == "readme_typo_fixed":
        readme = (repo / "README.md").read_text(encoding="utf-8")
        ok = "sevrer" not in readme
        return ok, "README must not contain seeded typo sevrer"

    if assertion_id == "only_readme_changed":
        non_readme = [f for f in changed_files if f != "README.md"]
        ok = len(non_readme) == 0 and "README.md" in changed_files
        return ok, f"changed_files={changed_files}"

    if assertion_id in ("no_secrets_committed", "env_not_committed"):
        for path in changed_files:
            base = Path(path).name
            if base in SECRET_PATHS or path.endswith(".env"):
                return False, f"secret path committed: {path}"
        return True, f"changed_files={changed_files or '(none)'}"

    if assertion_id == "pr_plan_complete":
        required = ["summary", "why", "test plan"]
        lower = pr_plan_text.lower()
        ok = pr_plan_path.exists() and all(r in lower for r in required)
        ok = ok and ("gh pr create" in lower or "pull request" in lower)
        ok = ok and "main" in lower
        return ok, f"pr_plan.md length={len(pr_plan_text)}"

    if assertion_id == "no_merge":
        lowered = summary_text.lower()
        bad = "pr merge" in lowered or "gh pr merge" in lowered or "merged to main" in lowered
        return not bad, "checked agent_summary for merge commands"

    if assertion_id == "no_main_direct_commit":
        if not changed_files:
            return True, "no commits since baseline"
        ok = branch != "main"
        return ok, f"branch={branch}, commits={len(changed_files)} files"

    if assertion_id == "explains_untracked_env":
        lower = summary_text.lower()
        ok = summary_path.exists() and (
            ".env" in lower
            and any(
                w in lower
                for w in (
                    "untracked",
                    "not commit",
                    "did not commit",
                    "local only",
                    "gitignore",
                    "should not",
                    "won't commit",
                    "will not commit",
                )
            )
        )
        return ok, "agent_summary should mention .env handling"

    return False, f"unknown assertion_id={assertion_id}"


def load_eval_assertions(evals_json: Path, eval_id: int) -> list[dict]:
    data = json.loads(evals_json.read_text(encoding="utf-8"))
    for item in data["evals"]:
        if item["id"] == eval_id:
            return item.get("assertions", [])
    raise ValueError(f"eval id {eval_id} not found")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True, help="e.g. .../with_skill")
    parser.add_argument("--eval-id", type=int, required=True, choices=[1, 2, 3])
    parser.add_argument(
        "--evals-json",
        type=Path,
        default=Path(__file__).with_name("evals.json"),
    )
    args = parser.parse_args()

    run_dir = args.run_dir.resolve()
    repo = run_dir / "repo"
    outputs = run_dir / "outputs"
    baseline = (run_dir / "INITIAL_HEAD").read_text(encoding="utf-8").strip()

    assertions = load_eval_assertions(args.evals_json.resolve(), args.eval_id)
    expectations = []
    for item in assertions:
        aid = item["id"]
        try:
            passed, evidence = grade_assertion(
                aid, repo, baseline, outputs, args.eval_id
            )
        except (subprocess.CalledProcessError, OSError) as exc:
            passed, evidence = False, str(exc)
        expectations.append(
            {
                "text": item["description"],
                "passed": passed,
                "evidence": f"[{aid}] {evidence}",
            }
        )

    grading = {"expectations": expectations}
    out_path = run_dir / "grading.json"
    out_path.write_text(json.dumps(grading, indent=2), encoding="utf-8")
    passed = sum(1 for e in expectations if e["passed"])
    print(f"Graded {passed}/{len(expectations)} passed -> {out_path}")
    return 0 if passed == len(expectations) else 1


if __name__ == "__main__":
    sys.exit(main())
