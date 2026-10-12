"""Unit tests for the Schema Drift Engine."""

from __future__ import annotations

from datareliant.common.types import SchemaChangeType
from datareliant.profiling.schema_drift import SchemaDriftEngine


class TestSchemaDriftEngine:
    """Test schema drift detection and breaking change classifications."""

    def test_identical_schemas_no_drift(self):
        engine = SchemaDriftEngine()
        schema1 = {"id": "Int64", "name": "String", "active": "Boolean"}
        schema2 = {"id": "Int64", "name": "String", "active": "Boolean"}

        diff = engine.compare_schemas(schema1, schema2)
        assert diff.has_changes is False
        assert diff.overall_classification == SchemaChangeType.NON_BREAKING
        assert len(diff.added_columns) == 0
        assert len(diff.removed_columns) == 0
        assert len(diff.changes) == 0

    def test_added_column_is_non_breaking(self):
        engine = SchemaDriftEngine()
        base = {"id": "Int64", "name": "String"}
        target = {"id": "Int64", "name": "String", "email": "String"}

        diff = engine.compare_schemas(base, target)
        assert diff.has_changes is True
        assert "email" in diff.added_columns
        assert diff.overall_classification == SchemaChangeType.NON_BREAKING
        assert len(diff.removed_columns) == 0

    def test_removed_column_is_breaking(self):
        engine = SchemaDriftEngine()
        base = {"id": "Int64", "name": "String", "deprecated_field": "String"}
        target = {"id": "Int64", "name": "String"}

        diff = engine.compare_schemas(base, target)
        assert diff.has_changes is True
        assert "deprecated_field" in diff.removed_columns
        assert diff.overall_classification == SchemaChangeType.BREAKING

    def test_renamed_column_inference(self):
        engine = SchemaDriftEngine()
        # "user_id" renamed to "cust_id" with identical Int64 type
        base = {"user_id": "Int64", "amount": "Float64"}
        target = {"cust_id": "Int64", "amount": "Float64"}

        diff = engine.compare_schemas(base, target)
        assert diff.has_changes is True
        assert len(diff.renamed_columns) == 1
        assert diff.renamed_columns[0]["old"] == "user_id"
        assert diff.renamed_columns[0]["new"] == "cust_id"
        assert diff.overall_classification == SchemaChangeType.BREAKING

    def test_type_widening_is_warning(self):
        engine = SchemaDriftEngine()
        base = {"id": "Int32", "val": "Float32"}
        target = {"id": "Int64", "val": "Float64"}

        diff = engine.compare_schemas(base, target)
        assert diff.has_changes is True
        assert diff.overall_classification == SchemaChangeType.WARNING
        assert len(diff.type_changes) == 2

    def test_narrowing_or_incompatible_type_is_breaking(self):
        engine = SchemaDriftEngine()
        base = {"code": "String", "score": "Float64"}
        target = {"code": "Int64", "score": "Int32"}

        diff = engine.compare_schemas(base, target)
        assert diff.has_changes is True
        assert diff.overall_classification == SchemaChangeType.BREAKING

    def test_machine_readable_output(self):
        engine = SchemaDriftEngine()
        base = {"a": "Int64", "b": "String"}
        target = {"a": "Int64", "c": "Float64"}

        diff = engine.compare_schemas(
            base, target, dataset_name="orders", base_version=1, target_version=2
        )
        d = diff.to_dict()
        assert d["dataset_name"] == "orders"
        assert d["base_version"] == 1
        assert d["target_version"] == 2
        assert d["has_changes"] is True
        assert "overall_classification" in d
        assert isinstance(d["changes"], list)
