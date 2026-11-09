"""Export the contracts' JSON Schema (consumed by web/scripts/gen-types.mjs).

python -m finn.models.export_schema > ../web/lib/schema.json
"""

from __future__ import annotations

import json
import sys

from pydantic.json_schema import models_json_schema

from finn.models import EXPORTED


def build() -> dict:
    _, schema = models_json_schema([(m, "serialization") for m in EXPORTED], title="FinnContracts")
    return schema


if __name__ == "__main__":
    json.dump(build(), sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
