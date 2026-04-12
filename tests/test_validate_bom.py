"""Tests for BOM schema validation and completeness checking."""

import json
import tempfile
from pathlib import Path

import pytest
import yaml

# Add parent directory to path so we can import the module
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from validate_bom import (
    check_completeness_base,
    check_completeness_site,
    is_site_override,
    load_schema,
    validate_schema,
    validate_file,
    PLACEHOLDER_PART_NUMBERS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def schema():
    return load_schema()


@pytest.fixture
def valid_base_bom():
    """A minimal valid base BOM."""
    return {
        "project": "test-project",
        "revision": "1.0",
        "date": "2026-01-01",
        "target_build_date": "2026-06-01",
        "assemblies": [
            {
                "name": "assembly-one",
                "description": "Test assembly.",
                "items": [
                    {
                        "part": "Widget A",
                        "pn": "WA-100",
                        "vendor": "WidgetCo",
                        "qty": 2,
                        "unit_cost_usd": 50.0,
                        "lead_time_weeks": 2,
                        "stage": "300K",
                        "status": "planned",
                        "notes": "Test item.",
                    },
                    {
                        "part": "Widget B",
                        "pn": "WB-200",
                        "vendor": "WidgetCo",
                        "qty": 1,
                        "unit_cost_usd": 100.0,
                        "lead_time_weeks": 4,
                        "stage": "4K",
                        "status": "quoted",
                    },
                ],
            }
        ],
    }


@pytest.fixture
def valid_site_override():
    """A minimal valid site-override BOM."""
    return {
        "site": "TestSite",
        "base": "bom.yaml",
        "revision": "0.1",
        "date": "2026-01-01",
        "notes": "Test site override.",
        "overrides": [],
        "additions": [
            {
                "assembly": "assembly-one",
                "part": "Site-Specific Gadget",
                "pn": "SSG-300",
                "vendor": "GadgetCo",
                "qty": 1,
                "unit_cost_usd": 200.0,
                "lead_time_weeks": 1,
                "stage": "300K",
                "status": "planned",
            }
        ],
    }


def write_yaml(data: dict) -> Path:
    """Write data to a temp YAML file and return its path."""
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    yaml.dump(data, tmp, default_flow_style=False)
    tmp.close()
    return Path(tmp.name)


# ---------------------------------------------------------------------------
# Schema validation tests
# ---------------------------------------------------------------------------

class TestSchemaValidation:

    def test_valid_base_bom_passes(self, schema, valid_base_bom):
        errors = validate_schema(valid_base_bom, schema, "test.yaml")
        assert errors == []

    def test_valid_site_override_passes(self, schema, valid_site_override):
        errors = validate_schema(valid_site_override, schema, "test.yaml")
        assert errors == []

    def test_missing_required_field_project(self, schema, valid_base_bom):
        del valid_base_bom["project"]
        errors = validate_schema(valid_base_bom, schema, "test.yaml")
        assert len(errors) > 0

    def test_missing_required_field_assemblies(self, schema, valid_base_bom):
        del valid_base_bom["assemblies"]
        errors = validate_schema(valid_base_bom, schema, "test.yaml")
        assert len(errors) > 0

    def test_item_missing_required_part(self, schema, valid_base_bom):
        del valid_base_bom["assemblies"][0]["items"][0]["part"]
        errors = validate_schema(valid_base_bom, schema, "test.yaml")
        assert len(errors) > 0

    def test_item_missing_required_qty(self, schema, valid_base_bom):
        del valid_base_bom["assemblies"][0]["items"][0]["qty"]
        errors = validate_schema(valid_base_bom, schema, "test.yaml")
        assert len(errors) > 0

    def test_item_missing_required_status(self, schema, valid_base_bom):
        del valid_base_bom["assemblies"][0]["items"][0]["status"]
        errors = validate_schema(valid_base_bom, schema, "test.yaml")
        assert len(errors) > 0

    def test_invalid_status_value(self, schema, valid_base_bom):
        valid_base_bom["assemblies"][0]["items"][0]["status"] = "invalid_status"
        errors = validate_schema(valid_base_bom, schema, "test.yaml")
        assert len(errors) > 0

    def test_negative_qty(self, schema, valid_base_bom):
        valid_base_bom["assemblies"][0]["items"][0]["qty"] = -1
        errors = validate_schema(valid_base_bom, schema, "test.yaml")
        assert len(errors) > 0

    def test_negative_cost(self, schema, valid_base_bom):
        valid_base_bom["assemblies"][0]["items"][0]["unit_cost_usd"] = -10.0
        errors = validate_schema(valid_base_bom, schema, "test.yaml")
        assert len(errors) > 0

    def test_null_pn_is_valid(self, schema, valid_base_bom):
        """Null part number is schema-valid (just a completeness warning)."""
        valid_base_bom["assemblies"][0]["items"][0]["pn"] = None
        errors = validate_schema(valid_base_bom, schema, "test.yaml")
        assert errors == []

    def test_null_cost_is_valid(self, schema, valid_base_bom):
        """Null cost is schema-valid."""
        valid_base_bom["assemblies"][0]["items"][0]["unit_cost_usd"] = None
        errors = validate_schema(valid_base_bom, schema, "test.yaml")
        assert errors == []

    def test_null_lead_time_is_valid(self, schema, valid_base_bom):
        """Null lead time is schema-valid."""
        valid_base_bom["assemblies"][0]["items"][0]["lead_time_weeks"] = None
        errors = validate_schema(valid_base_bom, schema, "test.yaml")
        assert errors == []

    def test_additional_properties_rejected(self, schema, valid_base_bom):
        """Unknown fields on items are rejected."""
        valid_base_bom["assemblies"][0]["items"][0]["bogus_field"] = "oops"
        errors = validate_schema(valid_base_bom, schema, "test.yaml")
        assert len(errors) > 0

    def test_empty_assemblies_rejected(self, schema, valid_base_bom):
        """Assemblies array must have at least one entry."""
        valid_base_bom["assemblies"] = []
        errors = validate_schema(valid_base_bom, schema, "test.yaml")
        assert len(errors) > 0

    def test_site_override_null_overrides(self, schema, valid_site_override):
        """Null overrides list is valid (empty site)."""
        valid_site_override["overrides"] = None
        errors = validate_schema(valid_site_override, schema, "test.yaml")
        assert errors == []

    def test_site_override_null_additions(self, schema, valid_site_override):
        """Null additions list is valid."""
        valid_site_override["additions"] = None
        errors = validate_schema(valid_site_override, schema, "test.yaml")
        assert errors == []


# ---------------------------------------------------------------------------
# Completeness check tests
# ---------------------------------------------------------------------------

class TestCompletenessBase:

    def test_all_complete(self, valid_base_bom):
        result = check_completeness_base(valid_base_bom, "test.yaml")
        assert result["total_items"] == 2
        assert result["complete_items"] == 2
        assert result["incomplete_items"] == 0
        assert result["missing"]["part_number"] == []
        assert result["missing"]["lead_time"] == []
        assert result["missing"]["unit_price"] == []

    def test_missing_part_number_null(self, valid_base_bom):
        valid_base_bom["assemblies"][0]["items"][0]["pn"] = None
        result = check_completeness_base(valid_base_bom, "test.yaml")
        assert len(result["missing"]["part_number"]) == 1
        assert "Widget A" in result["missing"]["part_number"][0]

    def test_missing_part_number_custom(self, valid_base_bom):
        valid_base_bom["assemblies"][0]["items"][0]["pn"] = "CUSTOM"
        result = check_completeness_base(valid_base_bom, "test.yaml")
        assert len(result["missing"]["part_number"]) == 1

    def test_missing_part_number_diy(self, valid_base_bom):
        valid_base_bom["assemblies"][0]["items"][0]["pn"] = "DIY"
        result = check_completeness_base(valid_base_bom, "test.yaml")
        assert len(result["missing"]["part_number"]) == 1

    def test_missing_part_number_various(self, valid_base_bom):
        valid_base_bom["assemblies"][0]["items"][0]["pn"] = "various"
        result = check_completeness_base(valid_base_bom, "test.yaml")
        assert len(result["missing"]["part_number"]) == 1

    def test_placeholder_case_insensitive(self, valid_base_bom):
        valid_base_bom["assemblies"][0]["items"][0]["pn"] = "Custom"
        result = check_completeness_base(valid_base_bom, "test.yaml")
        assert len(result["missing"]["part_number"]) == 1

    def test_missing_lead_time(self, valid_base_bom):
        valid_base_bom["assemblies"][0]["items"][0]["lead_time_weeks"] = None
        result = check_completeness_base(valid_base_bom, "test.yaml")
        assert len(result["missing"]["lead_time"]) == 1
        assert "Widget A" in result["missing"]["lead_time"][0]

    def test_missing_unit_price(self, valid_base_bom):
        valid_base_bom["assemblies"][0]["items"][0]["unit_cost_usd"] = None
        result = check_completeness_base(valid_base_bom, "test.yaml")
        assert len(result["missing"]["unit_price"]) == 1

    def test_multiple_missing_fields(self, valid_base_bom):
        """Item missing multiple fields is still counted once in incomplete."""
        valid_base_bom["assemblies"][0]["items"][0]["pn"] = None
        valid_base_bom["assemblies"][0]["items"][0]["lead_time_weeks"] = None
        valid_base_bom["assemblies"][0]["items"][0]["unit_cost_usd"] = None
        result = check_completeness_base(valid_base_bom, "test.yaml")
        assert result["incomplete_items"] == 1  # one item, multiple gaps
        assert len(result["missing"]["part_number"]) == 1
        assert len(result["missing"]["lead_time"]) == 1
        assert len(result["missing"]["unit_price"]) == 1

    def test_all_items_missing_pn(self, valid_base_bom):
        for item in valid_base_bom["assemblies"][0]["items"]:
            item["pn"] = None
        result = check_completeness_base(valid_base_bom, "test.yaml")
        assert len(result["missing"]["part_number"]) == 2
        assert result["incomplete_items"] == 2

    def test_no_pn_field_at_all(self, valid_base_bom):
        """Item without pn field entirely is treated as missing."""
        del valid_base_bom["assemblies"][0]["items"][0]["pn"]
        result = check_completeness_base(valid_base_bom, "test.yaml")
        assert len(result["missing"]["part_number"]) == 1


class TestCompletenessSite:

    def test_site_additions_complete(self, valid_site_override):
        result = check_completeness_site(valid_site_override, "test.yaml")
        assert result["total_items"] == 1
        assert result["complete_items"] == 1
        assert result["incomplete_items"] == 0

    def test_site_additions_missing_pn(self, valid_site_override):
        valid_site_override["additions"][0]["pn"] = None
        result = check_completeness_site(valid_site_override, "test.yaml")
        assert len(result["missing"]["part_number"]) == 1

    def test_site_empty_additions(self, valid_site_override):
        valid_site_override["additions"] = []
        result = check_completeness_site(valid_site_override, "test.yaml")
        assert result["total_items"] == 0
        assert result["complete_items"] == 0

    def test_site_null_additions(self, valid_site_override):
        valid_site_override["additions"] = None
        result = check_completeness_site(valid_site_override, "test.yaml")
        assert result["total_items"] == 0


# ---------------------------------------------------------------------------
# Detection tests
# ---------------------------------------------------------------------------

class TestDetection:

    def test_base_bom_detection(self, valid_base_bom):
        assert not is_site_override(valid_base_bom)

    def test_site_override_detection(self, valid_site_override):
        assert is_site_override(valid_site_override)


# ---------------------------------------------------------------------------
# Integration: validate_file end-to-end
# ---------------------------------------------------------------------------

class TestValidateFile:

    def test_valid_base_file(self, schema, valid_base_bom):
        path = write_yaml(valid_base_bom)
        try:
            result = validate_file(path, schema)
            assert result["schema_errors"] == []
            assert result["type"] == "base"
            assert result["completeness"]["total_items"] == 2
            assert result["completeness"]["complete_items"] == 2
        finally:
            path.unlink()

    def test_valid_site_override_file(self, schema, valid_site_override):
        path = write_yaml(valid_site_override)
        try:
            result = validate_file(path, schema)
            assert result["schema_errors"] == []
            assert "site-override" in result["type"]
        finally:
            path.unlink()

    def test_schema_errors_detected(self, schema, valid_base_bom):
        valid_base_bom["assemblies"][0]["items"][0]["status"] = "bogus"
        path = write_yaml(valid_base_bom)
        try:
            result = validate_file(path, schema)
            assert len(result["schema_errors"]) > 0
        finally:
            path.unlink()

    def test_malformed_item_extra_field(self, schema, valid_base_bom):
        valid_base_bom["assemblies"][0]["items"][0]["unexpected"] = True
        path = write_yaml(valid_base_bom)
        try:
            result = validate_file(path, schema)
            assert len(result["schema_errors"]) > 0
        finally:
            path.unlink()


# ---------------------------------------------------------------------------
# Actual BOM files (integration with real data)
# ---------------------------------------------------------------------------

class TestRealBoms:
    """Validate the actual BOM files in the repo."""

    @pytest.fixture
    def repo_root(self):
        return Path(__file__).resolve().parent.parent

    def test_base_bom_schema_valid(self, schema, repo_root):
        path = repo_root / "bom" / "bom.yaml"
        if not path.exists():
            pytest.skip("bom.yaml not found")
        result = validate_file(path, schema)
        assert result["schema_errors"] == [], (
            f"Schema errors: {result['schema_errors']}"
        )

    def test_base_bom_has_39_items(self, schema, repo_root):
        path = repo_root / "bom" / "bom.yaml"
        if not path.exists():
            pytest.skip("bom.yaml not found")
        result = validate_file(path, schema)
        assert result["completeness"]["total_items"] == 39

    def test_base_bom_missing_lead_times(self, schema, repo_root):
        path = repo_root / "bom" / "bom.yaml"
        if not path.exists():
            pytest.skip("bom.yaml not found")
        result = validate_file(path, schema)
        assert len(result["completeness"]["missing"]["lead_time"]) == 2

    def test_cba_override_schema_valid(self, schema, repo_root):
        path = repo_root / "bom" / "bom-cba.yaml"
        if not path.exists():
            pytest.skip("bom-cba.yaml not found")
        result = validate_file(path, schema)
        assert result["schema_errors"] == []

    def test_vertiv_override_schema_valid(self, schema, repo_root):
        path = repo_root / "bom" / "bom-vertiv.yaml"
        if not path.exists():
            pytest.skip("bom-vertiv.yaml not found")
        result = validate_file(path, schema)
        assert result["schema_errors"] == []

    def test_vertiv_additions_all_complete(self, schema, repo_root):
        path = repo_root / "bom" / "bom-vertiv.yaml"
        if not path.exists():
            pytest.skip("bom-vertiv.yaml not found")
        result = validate_file(path, schema)
        assert result["completeness"]["incomplete_items"] == 0
