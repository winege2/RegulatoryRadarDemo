"""Aggregate grading.json files into a simple benchmark summary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_grading(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def pass_rate(grading: dict) -> float:
    ex = grading.get("expectations", [])
    if not ex:
        return 0.0
    return sum(1 for e in ex if e.get("passed")) / len(ex)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("iteration_dir", type=Path)
    parser.add_argument("--skill-name", default="git-workflow")
    args = parser.parse_args()

    iteration = args.iteration_dir.resolve()
    runs: list[dict] = []
    for grading_path in sorted(iteration.rglob("grading.json")):
        run_dir = grading_path.parent
        mode = run_dir.name
        eval_name = run_dir.parent.name
        grading = load_grading(grading_path)
        runs.append(
            {
                "eval_name": eval_name,
                "mode": mode,
                "pass_rate": pass_rate(grading),
                "expectations": grading.get("expectations", []),
            }
        )

    with_skill = [r for r in runs if r["mode"] == "with_skill"]
    without_skill = [r for r in runs if r["mode"] == "without_skill"]

    def mean_rate(items: list[dict]) -> float:
        return sum(r["pass_rate"] for r in items) / len(items) if items else 0.0

    benchmark = {
        "skill_name": args.skill_name,
        "iteration": str(iteration),
        "with_skill_mean_pass_rate": mean_rate(with_skill),
        "without_skill_mean_pass_rate": mean_rate(without_skill),
        "runs": runs,
    }

    out_json = iteration / "benchmark.json"
    out_json.write_text(json.dumps(benchmark, indent=2), encoding="utf-8")

    lines = [
        f"# Benchmark: {args.skill_name}",
        "",
        f"| Configuration | Mean pass rate |",
        f"|---------------|----------------|",
        f"| with_skill | {benchmark['with_skill_mean_pass_rate']:.0%} |",
        f"| without_skill | {benchmark['without_skill_mean_pass_rate']:.0%} |",
        "",
        "## Per eval",
        "",
    ]
    for eval_name in sorted({r["eval_name"] for r in runs}):
        lines.append(f"### {eval_name}")
        for mode in ("with_skill", "without_skill"):
            match = next(
                (r for r in runs if r["eval_name"] == eval_name and r["mode"] == mode),
                None,
            )
            if not match:
                continue
            lines.append(f"- **{mode}**: {match['pass_rate']:.0%}")
            failed = [e for e in match["expectations"] if not e.get("passed")]
            if failed:
                for f in failed:
                    lines.append(f"  - FAIL: {f['text']} — {f.get('evidence', '')}")
        lines.append("")

    out_md = iteration / "benchmark.md"
    out_md.write_text("\n".join(lines), encoding="utf-8")
    print(out_md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
