from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

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
    "GOVERNANCE_TRACEABILITY.md",
    "MARKET_TRACKER.md",
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

MONITORING_PATHS = {
    "/api/v1/monitoring/overview",
    "/api/v1/monitoring/decisions",
    "/api/v1/monitoring/decisions/{proposal_id}",
    "/api/v1/monitoring/portfolio",
    "/api/v1/monitoring/alternatives",
    "/api/v1/monitoring/alternatives/{session_id}",
    "/api/v1/monitoring/news",
    "/api/v1/monitoring/agents",
    "/api/v1/monitoring/agents/{agent_id}",
    "/api/v1/monitoring/governance",
    "/api/v1/monitoring/weekly-summary",
}
SPECIALIST_NAMES = (
    "News Agent",
    "Quantitative Agent",
    "Industry Agent",
    "Fundamental Agent",
    "Macroeconomic Agent",
    "Market Reaction/Mispricing Agent",
    "Trading Decision Agent",
)
CONCEPT_REVISION = "2026-08-29 / ecosystem-consolidation-v1"


def _docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as package:
        root = ElementTree.fromstring(package.read("word/document.xml"))
    return " ".join(node.text or "" for node in root.iter() if node.tag.endswith("}t"))


def _check_governance(failures: list[str]) -> None:
    registry_path = ROOT / "backend" / "app" / "rules" / "authorized_baseline.v1.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    expected = {
        "take_profit_default_pct": "75.00",
        "stop_loss_pct": "50.00",
        "data_freshness_seconds": 30,
        "balanced_opportunity_score": "78",
        "max_hold_default_days": 14,
        "hackathon_max_hold_trading_days": 4,
    }
    for key, value in expected.items():
        if registry["parameters"].get(key) != value:
            failures.append(f"Authorized registry mismatch for {key}: expected {value}")
    if (
        registry.get("version") != "1.0.0"
        or registry.get("default_profile") != "balanced"
    ):
        failures.append("Authorized registry identity/default profile drifted")
    window = registry.get("parameters", {}).get("hackathon_window", {})
    expected_window = {
        "trading_start_at": "2026-08-31T13:30:00Z",
        "new_entry_cutoff_at": "2026-09-02T20:00:00Z",
        "official_scoring_at": "2026-09-03T20:00:00Z",
        "force_flatten_by": "2026-09-03T20:00:00Z",
        "window_outer_boundary_at": "2026-09-04T13:30:00Z",
        "scoring_basis": "total_account_equity",
    }
    for key, value in expected_window.items():
        if window.get(key) != value:
            failures.append(
                f"Authorized hackathon window mismatch for {key}: expected {value}"
            )

    first_party_markdown = [ROOT / "README.md", ROOT / "AGENTS.md"]
    first_party_markdown.extend((ROOT / "docs").rglob("*.md"))
    first_party_markdown.extend((ROOT / ".agents" / "rules").glob("*.md"))
    first_party_markdown.append(
        ROOT / ".agents" / "skills" / "prism-design" / "SKILL.md"
    )
    prohibited_patterns = {
        "LaTeX command": re.compile(
            r"\\(?:text|le|ge|ne|approx|times|Delta|Gamma|Theta|rightarrow|to)\b"
        ),
        "LaTeX display delimiter": re.compile(r"\$\$"),
        "Unicode arrow": re.compile(r"[→←]"),
        "stale BA status": re.compile(
            r"BA pending|THRESHOLD TBD|RULE TBD|product-name TBD", re.IGNORECASE
        ),
        "stale authorization vocabulary": re.compile(
            r"APPROVE\s*/\s*MODIFY\s*/\s*REJECT|accepted authorization",
            re.IGNORECASE,
        ),
    }
    for path in first_party_markdown:
        content = path.read_text(encoding="utf-8")
        for label, pattern in prohibited_patterns.items():
            if pattern.search(content):
                failures.append(f"{label} found in {path.relative_to(ROOT)}")

    concept_paths = (
        ROOT / "docs" / "conceptual" / "PROJECT_CONCEPT.md",
        ROOT / "docs" / "conceptual" / "Project_Concept.docx",
    )
    concept_texts = (
        concept_paths[0].read_text(encoding="utf-8"),
        _docx_text(concept_paths[1]),
    )
    critical_terms = (
        CONCEPT_REVISION,
        *SPECIALIST_NAMES,
        "75.00%",
        "50.00%",
        "14 days",
        "4 trading days",
        "illustrative_fixture",
        "MODIFIED_PENDING_ACCEPTANCE",
        "total account equity",
        "Sep 3",
        "new-entry cutoff",
        "force-flatten",
    )
    for path, content in zip(concept_paths, concept_texts, strict=True):
        missing = [term for term in critical_terms if term not in content]
        if missing:
            failures.append(
                f"Concept synchronization drift in {path.relative_to(ROOT)}: {missing}"
            )

    openapi = json.loads(
        (ROOT / "backend" / "build" / "contracts.openapi.json").read_text(
            encoding="utf-8"
        )
    )
    missing_paths = MONITORING_PATHS - set(openapi.get("paths", {}))
    if missing_paths:
        failures.append(f"OpenAPI is missing monitoring paths: {sorted(missing_paths)}")
    api_catalog = (ROOT / "docs" / "DATA_API_CONTRACTS.md").read_text(encoding="utf-8")
    uncatalogued = [path for path in MONITORING_PATHS if f"`{path}`" not in api_catalog]
    if uncatalogued:
        failures.append(
            f"API catalog is missing monitoring paths: {sorted(uncatalogued)}"
        )
    docs_index = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    if "[Market Tracker](MARKET_TRACKER.md)" not in docs_index:
        failures.append("Docs index is missing Market Tracker")

    frontend_root = ROOT / "frontend" / "src"
    frontend_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in frontend_root.rglob("*")
        if path.suffix in {".ts", ".tsx"}
    )
    for stale in ("story-data", "demo-credentials", "Active paper"):
        if stale in frontend_text:
            failures.append(f"Stale frontend fixture/auth phrase remains: {stale}")


def main() -> None:
    failures: list[str] = []
    _check_governance(failures)
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
    if len(set(identifiers)) != 49:
        failures.append(
            f"Expected 49 unique requirement IDs; found {len(set(identifiers))}"
        )
    pr_skill = ROOT / ".agents" / "skills" / "github-pr" / "SKILL.md"
    if not pr_skill.is_file() or "description:" not in pr_skill.read_text(
        encoding="utf-8"
    ):
        failures.append("Missing or malformed repository GitHub PR skill")
    branch_cases = {
        ("feature/status-ui", "staging"): True,
        ("fix/order-gate", "staging"): True,
        ("copilot/fix-ci-verify-job", "staging"): True,
        ("staging", "main"): True,
        ("main", "staging"): False,
        ("feature/status-ui", "main"): True,
        ("fix/order-gate", "main"): True,
        ("copilot/fix-ci-verify-job", "main"): True,
        ("docs/runbook", "main"): True,
        ("untyped-branch", "main"): False,
        ("copilot/untyped-branch", "main"): False,
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
