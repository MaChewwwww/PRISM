from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

from alembic import command

BACKEND_ROOT = Path(__file__).resolve().parents[1]


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
