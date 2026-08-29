from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel
from pydantic.json_schema import models_json_schema

from app import contracts
from app.main import app


def main() -> None:
    document = app.openapi()
    domain_models = [
        model
        for name in contracts.__all__
        if isinstance((model := getattr(contracts, name)), type) and issubclass(model, BaseModel)
    ]
    _, definitions = models_json_schema(
        [(model, "validation") for model in domain_models],
        ref_template="#/components/schemas/{model}",
    )
    document.setdefault("components", {}).setdefault("schemas", {}).update(
        definitions.get("$defs", {})
    )
    target = Path(__file__).resolve().parents[1] / "build" / "contracts.openapi.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
