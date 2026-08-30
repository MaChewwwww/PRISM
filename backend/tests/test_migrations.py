from __future__ import annotations

import importlib.util
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

from alembic import command

BACKEND_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = BACKEND_ROOT / "alembic" / "versions" / "20260829_0001_news_analysis.py"
REPORT_MIGRATION_PATH = BACKEND_ROOT / "alembic" / "versions" / "20260829_0002_research_reports.py"


def _config(output: StringIO | None = None) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"), stdout=output)
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    return config


def test_initial_migration_is_an_empty_database_baseline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The offline plan proves the initial revision has no predecessor and emits all required DDL
    # without requiring a networked database in normal CI.
    monkeypatch.delenv("DATABASE_URL", raising=False)
    output = StringIO()
    config = _config(output)
    script = ScriptDirectory.from_config(config)
    initial = script.get_revision("20260829_0001")
    head = script.get_revision(script.get_current_head())

    assert initial is not None
    assert initial.down_revision is None
    assert head is not None
    assert head.revision == "20260831_0010"
    assert head.down_revision == "20260831_0009"

    with redirect_stdout(output):
        command.upgrade(config, "head", sql=True)
    sql = output.getvalue()
    assert "CREATE TABLE llm_event_analyses" in sql
    assert "CREATE TABLE research_reports" in sql
    assert "CREATE TABLE industry_analyses" in sql
    assert "CREATE TABLE macro_analyses" in sql
    assert "CREATE TABLE trade_decisions" in sql
    assert "CREATE TABLE autonomous_controls" in sql
    assert "CREATE TABLE autonomous_cycles" in sql
    assert "CREATE TABLE research_bundles" in sql
    assert "CREATE TABLE trade_proposals" in sql
    assert "CREATE TABLE risk_assessments" in sql
    assert "CREATE TABLE portfolio_snapshots" in sql
    assert "CREATE TABLE authorizations" in sql
    assert "CREATE TABLE execution_receipts" in sql
    assert "CREATE TABLE reconciliation_events" in sql
    assert "CREATE TABLE autonomous_audit_events" in sql
    assert "CREATE TABLE option_iv_observations" in sql
    assert "CREATE TABLE ai_profiles" in sql
    assert "CREATE TABLE profile_calibration_preferences" in sql
    assert "CREATE TABLE profile_governance_audit_events" in sql
    assert "CREATE TABLE llm_usage_events" in sql
    assert "CREATE TABLE alembic_version" in sql


def test_initial_migration_adopts_compatible_legacy_table(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = importlib.util.spec_from_file_location("news_migration", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    class LegacyInspector:
        def has_table(self, table_name: str) -> bool:
            return table_name == "llm_event_analyses"

        def get_columns(self, table_name: str) -> list[dict[str, str]]:
            assert table_name == "llm_event_analyses"
            return [{"name": name} for name in migration._REQUIRED_COLUMNS]

    monkeypatch.setattr(migration.op, "get_bind", lambda: object())
    monkeypatch.setattr(migration.context, "is_offline_mode", lambda: False)
    monkeypatch.setattr(migration.sa, "inspect", lambda _bind: LegacyInspector())
    monkeypatch.setattr(
        migration.op,
        "create_table",
        lambda *_args, **_kwargs: pytest.fail("compatible legacy table must be adopted"),
    )

    migration.upgrade()


def test_research_report_migration_adopts_compatible_table(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = importlib.util.spec_from_file_location(
        "research_reports_migration", REPORT_MIGRATION_PATH
    )
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    class ExistingInspector:
        def has_table(self, table_name: str) -> bool:
            return table_name == "research_reports"

        def get_columns(self, table_name: str) -> list[dict[str, str]]:
            assert table_name == "research_reports"
            return [{"name": name} for name in migration._REQUIRED_COLUMNS]

    monkeypatch.setattr(migration.op, "get_bind", lambda: object())
    monkeypatch.setattr(migration.context, "is_offline_mode", lambda: False)
    monkeypatch.setattr(migration.sa, "inspect", lambda _bind: ExistingInspector())
    monkeypatch.setattr(
        migration.op,
        "create_table",
        lambda *_args, **_kwargs: pytest.fail("compatible table must be adopted"),
    )

    migration.upgrade()
