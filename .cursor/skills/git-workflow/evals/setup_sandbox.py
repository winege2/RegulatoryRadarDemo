"""Create an isolated git clone for git-workflow skill evals."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], cwd: Path) -> str:
    result = subprocess.run(
        cmd,
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True, help="Path to RegulatoryRadarDemo root")
    parser.add_argument("--dest", type=Path, required=True, help="Sandbox directory (will contain repo/)")
    parser.add_argument("--eval-id", type=int, required=True, choices=[1, 2, 3])
    args = parser.parse_args()

    source = args.source.resolve()
    dest = args.dest.resolve()
    repo_dir = dest / "repo"

    if repo_dir.exists():
        shutil.rmtree(repo_dir)
    dest.mkdir(parents=True, exist_ok=True)

    run(["git", "clone", "--local", str(source), str(repo_dir)], cwd=dest)

    baseline = run(["git", "rev-parse", "HEAD"], cwd=repo_dir)
    (dest / "INITIAL_HEAD").write_text(baseline + "\n", encoding="utf-8")

    if args.eval_id == 2:
        readme = repo_dir / "README.md"
        text = readme.read_text(encoding="utf-8")
        if "sevrer" not in text:
            text = re.sub(
                r"(edit a file\. Stop it with `Ctrl\+C`\.)",
                r"Stop the sevrer with `Ctrl+C`.",
                text,
                count=1,
            )
            readme.write_text(text, encoding="utf-8")
            run(["git", "add", "README.md"], cwd=repo_dir)
            run(
                ["git", "commit", "-m", "chore: seed README typo for eval"],
                cwd=repo_dir,
            )
            baseline = run(["git", "rev-parse", "HEAD"], cwd=repo_dir)
            (dest / "INITIAL_HEAD").write_text(baseline + "\n", encoding="utf-8")

    if args.eval_id == 3:
        env_path = repo_dir / ".env"
        if not env_path.exists():
            shutil.copy(repo_dir / ".env.example", env_path)

    (dest / "outputs").mkdir(parents=True, exist_ok=True)
    print(f"Sandbox ready at {repo_dir}")
    print(f"INITIAL_HEAD={baseline}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
