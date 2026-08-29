from __future__ import annotations

import re
from pathlib import Path

from check_branch_flow import validate_branch_flow

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_DOCS = {
    "ARCHITECTURE.md",
    "AI_AGENTS.md",
    "AI_PROFILES.md",
    "BUSINESS_RULES.md",
    "SHADOWFUND.md",
    "DATA_API_CONTRACTS.md",
    "ALPACA_INTEGRATION.md",
    "TECH_STACK.md",
    "VPS_DEPLOYMENT.md",
    "SECURITY.md",
    "DOCKER.md",
    "IMPLEMENTATION_PLAN.md",
    "FRS_NFRS.md",
    "CI_CD.md",
    "DESIGN.md",
}
REQUIRED_RULES = {
    f"{number}-{name}.md"
    for number, name in [
        ("00", "repository-onboarding"),
        ("10", "architecture"),
        ("20", "alpaca-documentation"),
        ("30", "trading-safety"),
        ("40", "frontend-design"),
        ("50", "testing-quality"),
        ("60", "documentation"),
        ("70", "commits-pull-requests"),
    ]
}


def main() -> None:
    failures: list[str] = []
    for pointer in ("CLAUDE.md", "GEMINI.md"):
        content = (ROOT / pointer).read_text(encoding="utf-8")
        if "AGENTS.md" not in content:
            failures.append(f"{pointer} does not point to AGENTS.md")
    for name in REQUIRED_DOCS:
        path = ROOT / "docs" / name
        if not path.is_file() or path.stat().st_size == 0:
            failures.append(f"Missing or empty document: docs/{name}")
    actual_rules = {path.name for path in (ROOT / ".agents" / "rules").glob("*.md")}
    if not REQUIRED_RULES.issubset(actual_rules):
        failures.append(f"Missing agent rules: {sorted(REQUIRED_RULES - actual_rules)}")
    requirements = (ROOT / "docs" / "FRS_NFRS.md").read_text(encoding="utf-8")
    identifiers = re.findall(r"\b(?:FRS|NFRS)-\d{3}\b", requirements)
    if len(set(identifiers)) != 47:
        failures.append(
            f"Expected 47 unique requirement IDs; found {len(set(identifiers))}"
        )
    pr_skill = ROOT / ".agents" / "skills" / "github-pr" / "SKILL.md"
    if not pr_skill.is_file() or "description:" not in pr_skill.read_text(
        encoding="utf-8"
    ):
        failures.append("Missing or malformed repository GitHub PR skill")
    branch_cases = {
        ("feature/status-ui", "staging"): True,
        ("fix/order-gate", "staging"): True,
        ("staging", "main"): True,
        ("main", "staging"): False,
        ("feature/status-ui", "main"): False,
        ("feature/UPPERCASE", "staging"): False,
    }
    for (head, base), allowed in branch_cases.items():
        if (validate_branch_flow(head, base) is None) != allowed:
            failures.append(f"Incorrect branch policy result: {head} -> {base}")
    for markdown in (ROOT / "docs").glob("*.md"):
        for target in re.findall(
            r"\[[^]]+\]\(([^)#]+)(?:#[^)]+)?\)", markdown.read_text(encoding="utf-8")
        ):
            if (
                "://" not in target
                and not (markdown.parent / target).resolve().is_file()
            ):
                failures.append(f"Broken local link in {markdown.name}: {target}")
    if failures:
        raise SystemExit("\n".join(failures))
    print("Repository governance checks passed")


if __name__ == "__main__":
    main()
