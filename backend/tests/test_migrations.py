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
NEWS_FIELDS_MIGRATION_PATH = (
    BACKEND_ROOT / "alembic" / "versions" / "20260831_0011_news_analysis_fields.py"
)
RESEARCH_FIELDS_MIGRATION_PATH = (
    BACKEND_ROOT / "alembic" / "versions" / "20260831_0012_research_model_fields.py"
)
NEWS_FIELDS_REPAIR_MIGRATION_PATH = (
    BACKEND_ROOT / "alembic" / "versions" / "20260831_0013_news_analysis_fields_repair.py"
)


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
    assert head.revision == "20260831_0013"
    assert head.down_revision == "20260831_0012"

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


def test_news_fields_migration_adds_only_missing_legacy_columns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = importlib.util.spec_from_file_location(
        "news_fields_migration", NEWS_FIELDS_MIGRATION_PATH
    )
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    added: list[str] = []

    class ExistingInspector:
        def has_table(self, table_name: str) -> bool:
            return table_name == "llm_event_analyses"

        def get_columns(self, table_name: str) -> list[dict[str, str]]:
            assert table_name == "llm_event_analyses"
            return [{"name": "source"}]

    monkeypatch.setattr(migration.op, "get_bind", lambda: object())
    monkeypatch.setattr(migration.context, "is_offline_mode", lambda: False)
    monkeypatch.setattr(migration.sa, "inspect", lambda _bind: ExistingInspector())
    monkeypatch.setattr(
        migration.op, "add_column", lambda _table, column: added.append(column.name)
    )

    migration.upgrade()

    assert "source" not in added
    assert set(added) == {
        "source_confidence",
        "event_age_seconds",
        "event_category",
        "catalyst_materiality",
        "guidance_change",
        "earnings_surprise_json",
        "has_contradictory_signals",
        "contradiction_notes",
    }


def test_research_fields_migration_reconciles_all_legacy_model_tables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = importlib.util.spec_from_file_location(
        "research_fields_migration", RESEARCH_FIELDS_MIGRATION_PATH
    )
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    added: list[tuple[str, str]] = []

    class ExistingInspector:
        def has_table(self, table_name: str) -> bool:
            return table_name in migration._TABLE_COLUMNS

        def get_columns(self, table_name: str) -> list[dict[str, str]]:
            assert table_name in migration._TABLE_COLUMNS
            return [{"name": "id"}]

    monkeypatch.setattr(migration.op, "get_bind", lambda: object())
    monkeypatch.setattr(migration.context, "is_offline_mode", lambda: False)
    monkeypatch.setattr(migration.sa, "inspect", lambda _bind: ExistingInspector())
    monkeypatch.setattr(
        migration.op,
        "add_column",
        lambda table, column: added.append((table, column.name)),
    )

    migration.upgrade()

    expected = {
        (table, column.name)
        for table, columns in migration._TABLE_COLUMNS.items()
        for column in columns
    }
    assert set(added) == expected


def test_news_fields_repair_migration_adds_fields_missing_from_applied_revision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = importlib.util.spec_from_file_location(
        "news_fields_repair_migration", NEWS_FIELDS_REPAIR_MIGRATION_PATH
    )
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    added: list[str] = []

    class ExistingInspector:
        def has_table(self, table_name: str) -> bool:
            return table_name == "llm_event_analyses"

        def get_columns(self, table_name: str) -> list[dict[str, str]]:
            assert table_name == "llm_event_analyses"
            return [{"name": "id"}, {"name": "event_category"}]

    monkeypatch.setattr(migration.op, "get_bind", lambda: object())
    monkeypatch.setattr(migration.context, "is_offline_mode", lambda: False)
    monkeypatch.setattr(migration.sa, "inspect", lambda _bind: ExistingInspector())
    monkeypatch.setattr(
        migration.op, "add_column", lambda _table, column: added.append(column.name)
    )

    migration.upgrade()

    assert added == ["event_age_seconds"]
