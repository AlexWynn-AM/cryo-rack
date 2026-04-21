#!/usr/bin/env python3
"""
BOM Schema Validation and Completeness Checker

Validates cryo-rack BOM YAML files against the JSON Schema and checks
procurement completeness (part numbers, lead times, unit prices).

Usage:
    python scripts/validate_bom.py                    # validate all BOMs in bom/
    python scripts/validate_bom.py bom/bom.yaml       # validate specific file(s)
    python scripts/validate_bom.py --json              # JSON output

Exit codes:
    0 - Schema valid (completeness warnings are OK)
    1 - Schema validation errors found
    2 - File loading errors
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

try:
    import jsonschema
    from jsonschema import Draft202012Validator
except ImportError:
    print("ERROR: jsonschema required. Install with: pip install jsonschema")
    sys.exit(2)


# ---------------------------------------------------------------------------
# Part-number placeholders that indicate incomplete procurement data.
# These are valid schema values but signal the item doesn't have a real
# orderable part number yet.
# ---------------------------------------------------------------------------
PLACEHOLDER_PART_NUMBERS = {"CUSTOM", "DIY", "various", "TBD", "N/A", "none"}


def load_schema() -> dict:
    """Load the BOM JSON Schema from the schemas/ directory."""
    schema_path = Path(__file__).resolve().parent.parent / "schemas" / "bom-schema.json"
    if not schema_path.exists():
        print(f"ERROR: Schema not found at {schema_path}")
        sys.exit(2)
    with open(schema_path) as f:
        return json.load(f)


def load_yaml(path: Path) -> dict:
    """Load and return a YAML file."""
    with open(path) as f:
        return yaml.safe_load(f)


def is_site_override(data: dict) -> bool:
    """Detect whether a BOM file is a site-override (has 'site' key) or base."""
    return "site" in data


def validate_schema(data: dict, schema: dict, filepath: str) -> list[dict]:
    """Validate data against JSON Schema. Returns list of error dicts."""
    validator = Draft202012Validator(schema)
    errors = []
    for error in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        errors.append({
            "file": filepath,
            "path": ".".join(str(p) for p in error.absolute_path) or "(root)",
            "message": error.message,
        })
    return errors


def check_completeness_base(data: dict, filepath: str) -> dict:
    """
    Check procurement completeness for a base BOM.

    Returns a dict with:
      - total_items: int
      - complete_items: int
      - incomplete_items: int
      - missing: dict mapping field name -> list of item descriptions
    """
    missing: dict[str, list[str]] = {
        "part_number": [],
        "lead_time": [],
        "unit_price": [],
    }
    total = 0

    for asm in data.get("assemblies", []):
        asm_name = asm.get("name", "unknown")
        for item in asm.get("items", []):
            total += 1
            part = item.get("part", "???")
            label = f"{asm_name} / {part}"

            # Part number: null or placeholder counts as missing
            pn = item.get("pn")
            if pn is None or (isinstance(pn, str) and pn.strip().lower() in {s.lower() for s in PLACEHOLDER_PART_NUMBERS}):
                missing["part_number"].append(label)

            # Lead time
            if item.get("lead_time_weeks") is None:
                missing["lead_time"].append(label)

            # Unit price
            if item.get("unit_cost_usd") is None:
                missing["unit_price"].append(label)

    all_missing = set()
    for items in missing.values():
        all_missing.update(items)
    complete = total - len(all_missing)

    return {
        "total_items": total,
        "complete_items": complete,
        "incomplete_items": len(all_missing),
        "missing": missing,
    }


def check_completeness_site(data: dict, filepath: str) -> dict:
    """
    Check procurement completeness for site-override additions.

    Overrides are partial by design (they inherit from base), so we only
    check additions for completeness.
    """
    missing: dict[str, list[str]] = {
        "part_number": [],
        "lead_time": [],
        "unit_price": [],
    }
    additions = data.get("additions") or []
    total = len(additions)

    for item in additions:
        asm_name = item.get("assembly", "unknown")
        part = item.get("part", "???")
        label = f"{asm_name} / {part}"

        pn = item.get("pn")
        if pn is None or (isinstance(pn, str) and pn.strip().lower() in {s.lower() for s in PLACEHOLDER_PART_NUMBERS}):
            missing["part_number"].append(label)

        if item.get("lead_time_weeks") is None:
            missing["lead_time"].append(label)

        if item.get("unit_cost_usd") is None:
            missing["unit_price"].append(label)

    all_missing = set()
    for items in missing.values():
        all_missing.update(items)
    complete = total - len(all_missing)

    return {
        "total_items": total,
        "complete_items": complete,
        "incomplete_items": len(all_missing),
        "missing": missing,
    }


def format_report(results: list[dict], output_json: bool = False) -> str:
    """Format validation results as text or JSON."""
    if output_json:
        return json.dumps(results, indent=2)

    lines = []
    for r in results:
        lines.append(f"{'='*70}")
        lines.append(f"File: {r['file']}")
        lines.append(f"Type: {r['type']}")
        lines.append(f"{'='*70}")

        # Schema errors
        schema_errors = r.get("schema_errors", [])
        if schema_errors:
            lines.append(f"\n  SCHEMA ERRORS ({len(schema_errors)}):")
            for err in schema_errors:
                lines.append(f"    [{err['path']}] {err['message']}")
        else:
            lines.append("\n  Schema: VALID")

        # Completeness
        comp = r.get("completeness", {})
        total = comp.get("total_items", 0)
        complete = comp.get("complete_items", 0)
        incomplete = comp.get("incomplete_items", 0)
        missing = comp.get("missing", {})

        lines.append(f"\n  Completeness: {complete}/{total} items fully specified"
                      f" ({incomplete} incomplete)")

        for field, items in missing.items():
            if items:
                lines.append(f"\n  Missing {field} ({len(items)} items):")
                for item in items:
                    lines.append(f"    - {item}")

        lines.append("")

    # Summary across all files
    total_schema_errors = sum(len(r.get("schema_errors", [])) for r in results)
    total_items = sum(r.get("completeness", {}).get("total_items", 0) for r in results)
    total_complete = sum(r.get("completeness", {}).get("complete_items", 0) for r in results)
    total_missing_pn = sum(len(r.get("completeness", {}).get("missing", {}).get("part_number", [])) for r in results)
    total_missing_lt = sum(len(r.get("completeness", {}).get("missing", {}).get("lead_time", [])) for r in results)
    total_missing_price = sum(len(r.get("completeness", {}).get("missing", {}).get("unit_price", [])) for r in results)

    lines.append(f"{'='*70}")
    lines.append("SUMMARY")
    lines.append(f"{'='*70}")
    lines.append(f"  Files validated:        {len(results)}")
    lines.append(f"  Schema errors:          {total_schema_errors}")
    lines.append(f"  Total items:            {total_items}")
    lines.append(f"  Complete items:          {total_complete}")
    lines.append(f"  Missing part_number:    {total_missing_pn}")
    lines.append(f"  Missing lead_time:      {total_missing_lt}")
    lines.append(f"  Missing unit_price:     {total_missing_price}")

    if total_schema_errors > 0:
        lines.append(f"\n  RESULT: FAIL ({total_schema_errors} schema errors)")
    else:
        lines.append(f"\n  RESULT: PASS (schema valid, {total_missing_pn + total_missing_lt + total_missing_price} completeness warnings)")

    return "\n".join(lines)


def validate_file(filepath: Path, schema: dict) -> dict:
    """Validate a single BOM YAML file. Returns result dict."""
    data = load_yaml(filepath)
    schema_errors = validate_schema(data, schema, str(filepath))

    if is_site_override(data):
        bom_type = f"site-override ({data.get('site', '?')})"
        completeness = check_completeness_site(data, str(filepath))
    else:
        bom_type = "base"
        completeness = check_completeness_base(data, str(filepath))

    return {
        "file": str(filepath),
        "type": bom_type,
        "schema_errors": schema_errors,
        "completeness": completeness,
    }


def find_bom_files(bom_dir: Path) -> list[Path]:
    """Find all BOM YAML files in the bom/ directory."""
    files = []
    for pattern in ["*.yaml", "*.yml"]:
        files.extend(sorted(bom_dir.glob(pattern)))
    return files


def main():
    parser = argparse.ArgumentParser(
        description="Validate BOM YAML files against schema and check completeness"
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="BOM YAML files to validate (default: all in bom/)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--schema",
        type=str,
        default=None,
        help="Path to JSON Schema (default: schemas/bom-schema.json)",
    )
    args = parser.parse_args()

    # Load schema
    if args.schema:
        with open(args.schema) as f:
            schema = json.load(f)
    else:
        schema = load_schema()

    # Find files
    if args.files:
        files = [Path(f) for f in args.files]
    else:
        repo_root = Path(__file__).resolve().parent.parent
        bom_dir = repo_root / "bom"
        files = find_bom_files(bom_dir)

    if not files:
        print("No BOM files found.")
        sys.exit(2)

    # Validate each file
    results = []
    load_errors = False
    for filepath in files:
        if not filepath.exists():
            print(f"ERROR: File not found: {filepath}")
            load_errors = True
            continue
        try:
            result = validate_file(filepath, schema)
            results.append(result)
        except yaml.YAMLError as e:
            print(f"ERROR: Failed to parse YAML: {filepath}\n  {e}")
            load_errors = True
        except Exception as e:
            print(f"ERROR: Failed to validate: {filepath}\n  {e}")
            load_errors = True

    if load_errors and not results:
        sys.exit(2)

    # Output report
    report = format_report(results, output_json=args.json)
    print(report)

    # Exit code: 0 if schema-valid, 1 if schema errors, 2 if load errors
    total_schema_errors = sum(len(r.get("schema_errors", [])) for r in results)
    if total_schema_errors > 0:
        sys.exit(1)
    if load_errors:
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
