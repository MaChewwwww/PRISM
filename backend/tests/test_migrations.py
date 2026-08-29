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
    head = script.get_revision(script.get_current_head())

    assert head is not None
    assert head.down_revision is None

    with redirect_stdout(output):
        command.upgrade(config, "head", sql=True)
    sql = output.getvalue()
    assert "CREATE TABLE llm_event_analyses" in sql
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
