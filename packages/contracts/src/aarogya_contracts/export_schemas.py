"""Export and verify JSON Schema Draft 2020-12 files for all core Aarogya Mesh contracts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from aarogya_contracts.models import CONTRACT_SCHEMA_VERSION, CORE_CONTRACT_MODELS

JSON_SCHEMA_DRAFT_2020_12 = "https://json-schema.org/draft/2020-12/schema"
DEFAULT_SCHEMAS_DIR = Path(__file__).resolve().parents[2] / "schemas"


def build_contract_schema(name: str) -> dict[str, Any]:
    """Generate a JSON Schema Draft 2020-12 document for a named core model."""
    model_cls = CORE_CONTRACT_MODELS[name]
    raw_schema = model_cls.model_json_schema(mode="validation")
    ordered: dict[str, Any] = {
        "$schema": JSON_SCHEMA_DRAFT_2020_12,
        "$id": f"https://aarogya-mesh.local/schemas/{CONTRACT_SCHEMA_VERSION}/{name}.schema.json",
    }
    ordered.update(raw_schema)
    return ordered


def render_json(payload: dict[str, Any]) -> str:
    """Serialize JSON deterministically with trailing newline."""
    return json.dumps(payload, indent=2, sort_keys=False) + "\n"


def export_all_schemas(output_dir: Path = DEFAULT_SCHEMAS_DIR) -> list[Path]:
    """Write all core contract JSON Schema Draft 2020-12 files to output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name in sorted(CORE_CONTRACT_MODELS.keys()):
        target = output_dir / f"{name}.schema.json"
        target.write_text(render_json(build_contract_schema(name)), encoding="utf-8")
        written.append(target)
    return written


def check_exported_schemas(output_dir: Path = DEFAULT_SCHEMAS_DIR) -> list[str]:
    """Return a list of drift/missing errors comparing disk schemas to Pydantic models."""
    errors: list[str] = []
    expected_files: dict[str, str] = {
        f"{name}.schema.json": render_json(build_contract_schema(name))
        for name in sorted(CORE_CONTRACT_MODELS.keys())
    }

    for filename, expected_text in expected_files.items():
        path = output_dir / filename
        if not path.exists():
            errors.append(f"Missing schema file: {path}")
            continue
        actual_text = path.read_text(encoding="utf-8")
        if actual_text != expected_text:
            errors.append(f"Schema drift detected in: {path}")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export or verify Aarogya Mesh JSON Schemas.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_SCHEMAS_DIR,
        help="Target directory for .schema.json files",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify exported schemas match Pydantic models without modifying disk",
    )
    args = parser.parse_args(argv)

    if args.check:
        errors = check_exported_schemas(args.output_dir)
        if errors:
            for err in errors:
                print(f"ERROR: {err}", file=sys.stderr)
            return 1
        print(f"OK: {len(CORE_CONTRACT_MODELS)} contract schemas verified in {args.output_dir}")
        return 0

    written = export_all_schemas(args.output_dir)
    print(f"Exported {len(written)} files to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
