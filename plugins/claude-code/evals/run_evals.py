#!/usr/bin/env python3
# ruff: noqa
"""
Trigger accuracy eval runner for mc-agent-toolkit skills.

Loads the skill description from SKILL.md and runs each case from trigger-evals.json
through the Claude API to check whether the skill would be triggered.

Usage:
    pip install anthropic
    export ANTHROPIC_API_KEY=sk-ant-...
    python run_evals.py --skill prevent
    python run_evals.py --skill push-ingestion [--model claude-sonnet-4-6] [--threshold 0.85]

Exit codes:
    0 — pass rate meets threshold
    1 — pass rate below threshold
"""

import argparse
import json
import re
import sys
from pathlib import Path

import anthropic

EVALS_DIR = Path(__file__).parent
PLUGIN_DIR = EVALS_DIR.parent
SKILLS_DIR = PLUGIN_DIR / "skills"

JUDGE_SYSTEM_PROMPT = """You are evaluating whether a Claude skill should be triggered for a given user message.

You will be given:
1. A skill name and its trigger description
2. A user message

Respond with exactly one word: TRIGGER if the skill should activate for this message, or NO_TRIGGER if it should not.

Rules:
- Trigger if the message clearly falls within the skill's stated scope
- Do NOT trigger for messages outside the skill's domain
- When in doubt, lean toward NO_TRIGGER
"""

JUDGE_USER_TEMPLATE = """Skill name: {skill_name}
Skill trigger description: {skill_description}

User message: {prompt}

Should this skill trigger? Answer TRIGGER or NO_TRIGGER."""


def load_skill_description(skill_dir: Path) -> tuple[str, str]:
    """Extract the name and description from SKILL.md frontmatter."""
    skill_md = skill_dir / "SKILL.md"
    content = skill_md.read_text()

    frontmatter = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not frontmatter:
        raise ValueError(f"No frontmatter found in {skill_md}")

    fm = frontmatter.group(1)
    name_match = re.search(r"^name:\s*(.+)$", fm, re.MULTILINE)
    # description may be multi-line (YAML block scalar with > or |)
    desc_match = re.search(r"^description:\s*[>|]\n((?:  .+\n?)+)", fm, re.MULTILINE)
    if not desc_match:
        desc_match = re.search(r"^description:\s*(.+)$", fm, re.MULTILINE)

    name = name_match.group(1).strip() if name_match else "unknown"
    description = re.sub(r"\s+", " ", desc_match.group(1).strip()) if desc_match else ""
    return name, description


def judge(client: anthropic.Anthropic, model: str, skill_name: str, skill_description: str, prompt: str) -> str:
    """Ask the judge model whether the skill should trigger. Returns 'trigger' or 'no-trigger'."""
    message = client.messages.create(
        model=model,
        max_tokens=10,
        system=JUDGE_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": JUDGE_USER_TEMPLATE.format(
                    skill_name=skill_name,
                    skill_description=skill_description,
                    prompt=prompt,
                ),
            }
        ],
    )
    raw = message.content[0].text.strip().upper()
    return "trigger" if "TRIGGER" in raw and "NO" not in raw else "no-trigger"


def main():
    parser = argparse.ArgumentParser(description="Run trigger accuracy evals for an mc-agent-toolkit skill")
    parser.add_argument("--skill", required=True, help="Skill directory name (e.g. 'prevent', 'push-ingestion')")
    parser.add_argument("--model", default="claude-sonnet-4-6", help="Claude model to use as judge")
    parser.add_argument("--threshold", type=float, default=0.85, help="Minimum pass rate to exit 0 (default: 0.85)")
    parser.add_argument("--evals", default=None, help="Path to eval cases JSON (default: <skill>/trigger-evals.json)")
    parser.add_argument("--dry-run", action="store_true", help="Load and validate cases without calling the API")
    args = parser.parse_args()

    skill_dir = SKILLS_DIR / args.skill
    if not skill_dir.exists():
        print(f"Error: Skill directory not found: {skill_dir}")
        sys.exit(1)

    evals_path = Path(args.evals) if args.evals else EVALS_DIR / args.skill / "trigger-evals.json"
    if not evals_path.exists():
        # An explicit --evals path was given but doesn't exist — that's a real error.
        if args.evals:
            print(f"Error: Eval cases not found: {evals_path}")
            sys.exit(1)
        # Default path missing — skill has no trigger-evals (live-evals-only). Skip gracefully.
        print(f"No trigger-evals for {args.skill} (live-evals-only skill). Skipping.")
        sys.exit(0)

    cases = json.loads(evals_path.read_text())["cases"]
    skill_name, skill_description = load_skill_description(skill_dir)

    print(f"Skill:     {skill_name}")
    print(f"Model:     {args.model}")
    print(f"Cases:     {len(cases)}")
    print(f"Threshold: {args.threshold:.0%}")

    if args.dry_run:
        print(f"\n[dry-run] Loaded {len(cases)} cases for {skill_name}")
        print(f"[dry-run] Skill description: {skill_description[:120]}...")
        for case in cases:
            print(f"  [{case['id']}] ({case['expected']}) {case['prompt'][:75]}{'…' if len(case['prompt']) > 75 else ''}")
        sys.exit(0)

    print()
    client = anthropic.Anthropic()

    results = []
    for case in cases:
        actual = judge(client, args.model, skill_name, skill_description, case["prompt"])
        passed = actual == case["expected"]
        results.append({"id": case["id"], "expected": case["expected"], "actual": actual, "passed": passed})

        status = "✓" if passed else "✗"
        print(f"  {status} [{case['id']}] {case['prompt'][:75]}{'…' if len(case['prompt']) > 75 else ''}")
        if not passed:
            print(f"      expected={case['expected']}  got={actual}")

    total = len(results)
    passed = sum(r["passed"] for r in results)
    pass_rate = passed / total

    print(f"\nResult: {passed}/{total} passed ({pass_rate:.0%})")

    if pass_rate >= args.threshold:
        print(f"✓ Pass rate meets threshold ({args.threshold:.0%})")
        sys.exit(0)
    else:
        print(f"✗ Pass rate below threshold ({args.threshold:.0%})")
        sys.exit(1)


if __name__ == "__main__":
    main()
