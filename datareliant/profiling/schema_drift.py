"""Schema Drift Engine: Historical schema comparison, drift detection, and breaking change classification."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from datareliant.common.types import SchemaChangeType


class ColumnChange(BaseModel):
    """Detailed record of a single column-level schema change."""

    column_name: str
    change_type: str  # "ADDED", "REMOVED", "RENAMED", "TYPE_CHANGED", "NULLABILITY_CHANGED"
    classification: SchemaChangeType
    old_value: Any | None = None
    new_value: Any | None = None
    description: str


class SchemaDiff(BaseModel):
    """Machine-readable schema comparison output between two dataset versions."""

    dataset_name: str
    base_version: int
    target_version: int
    has_changes: bool
    overall_classification: SchemaChangeType
    added_columns: list[str] = Field(default_factory=list)
    removed_columns: list[str] = Field(default_factory=list)
    renamed_columns: list[dict[str, str]] = Field(
        default_factory=list
    )  # [{"old": ..., "new": ...}]
    type_changes: list[dict[str, Any]] = Field(default_factory=list)
    nullability_changes: list[dict[str, Any]] = Field(default_factory=list)
    changes: list[ColumnChange] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return self.model_dump(mode="json")


# Type widening map: changing from key to any value in target set is non-breaking / safe
_COMPATIBLE_TYPE_WIDENING: dict[str, set[str]] = {
    "int8": {"int16", "int32", "int64", "float32", "float64"},
    "int16": {"int32", "int64", "float32", "float64"},
    "int32": {"int64", "float64"},
    "uint8": {"uint16", "uint32", "uint64", "int16", "int32", "int64", "float64"},
    "uint16": {"uint32", "uint64", "int32", "int64", "float64"},
    "uint32": {"uint64", "int64", "float64"},
    "float32": {"float64"},
}


def _classify_type_change(old_type: str, new_type: str) -> SchemaChangeType:
    """Classify type changes based on widening compatibility."""
    old_clean = old_type.lower().strip()
    new_clean = new_type.lower().strip()

    if old_clean == new_clean:
        return SchemaChangeType.NON_BREAKING

    # Check safe widening
    allowed_widening = _COMPATIBLE_TYPE_WIDENING.get(old_clean, set())
    if new_clean in allowed_widening:
        return SchemaChangeType.WARNING

    # Any other change is considered potentially breaking (loss of precision or parse failure)
    return SchemaChangeType.BREAKING


def _levenshtein_distance(s1: str, s2: str) -> int:
    """Compute Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]


class SchemaDriftEngine:
    """Engine detecting structural differences and schema drift across dataset versions."""

    def compare_schemas(
        self,
        base_schema: dict[str, str],
        target_schema: dict[str, str],
        dataset_name: str = "dataset",
        base_version: int = 1,
        target_version: int = 2,
    ) -> SchemaDiff:
        """Compare two schemas and generate a classified SchemaDiff."""
        base_cols = set(base_schema.keys())
        target_cols = set(target_schema.keys())

        potentially_added = target_cols - base_cols
        potentially_removed = base_cols - target_cols
        common_cols = base_cols & target_cols

        changes: list[ColumnChange] = []
        renamed_pairs: list[dict[str, str]] = []
        actual_added: list[str] = []
        actual_removed: list[str] = []

        # 1. Infer renamed columns: match removed & added columns with identical type & high name similarity
        matched_added: set[str] = set()
        matched_removed: set[str] = set()

        for rem_col in sorted(potentially_removed):
            rem_type = base_schema[rem_col]
            best_match = None
            best_dist = 999
            for add_col in sorted(potentially_added):
                if add_col in matched_added:
                    continue
                add_type = target_schema[add_col]
                # Only match if same data type
                if rem_type == add_type:
                    dist = _levenshtein_distance(rem_col, add_col)
                    # Name edit distance threshold: <= 3 or <= 40% of length
                    max_len = max(len(rem_col), len(add_col))
                    if dist <= max(3, int(max_len * 0.4)) and dist < best_dist:
                        best_dist = dist
                        best_match = add_col

            if best_match:
                matched_removed.add(rem_col)
                matched_added.add(best_match)
                renamed_pairs.append({"old": rem_col, "new": best_match})
                changes.append(
                    ColumnChange(
                        column_name=best_match,
                        change_type="RENAMED",
                        classification=SchemaChangeType.BREAKING,
                        old_value=rem_col,
                        new_value=best_match,
                        description=f"Column '{rem_col}' was renamed to '{best_match}'",
                    )
                )

        # 2. Process added columns
        for col in sorted(potentially_added):
            if col not in matched_added:
                actual_added.append(col)
                changes.append(
                    ColumnChange(
                        column_name=col,
                        change_type="ADDED",
                        classification=SchemaChangeType.NON_BREAKING,
                        new_value=target_schema[col],
                        description=f"New column '{col}' of type '{target_schema[col]}' added",
                    )
                )

        # 3. Process removed columns
        for col in sorted(potentially_removed):
            if col not in matched_removed:
                actual_removed.append(col)
                changes.append(
                    ColumnChange(
                        column_name=col,
                        change_type="REMOVED",
                        classification=SchemaChangeType.BREAKING,
                        old_value=base_schema[col],
                        description=f"Column '{col}' of type '{base_schema[col]}' removed",
                    )
                )

        # 4. Process datatype changes in common columns
        type_changes_list: list[dict[str, Any]] = []
        for col in sorted(common_cols):
            old_t = base_schema[col]
            new_t = target_schema[col]
            if old_t != new_t:
                classification = _classify_type_change(old_t, new_t)
                type_changes_list.append(
                    {
                        "column": col,
                        "old_type": old_t,
                        "new_type": new_t,
                        "classification": classification.value,
                    }
                )
                changes.append(
                    ColumnChange(
                        column_name=col,
                        change_type="TYPE_CHANGED",
                        classification=classification,
                        old_value=old_t,
                        new_value=new_t,
                        description=f"Column '{col}' datatype changed from '{old_t}' to '{new_t}'",
                    )
                )

        # 5. Overall classification determination
        has_changes = len(changes) > 0
        if not has_changes:
            overall = SchemaChangeType.NON_BREAKING
        elif any(c.classification == SchemaChangeType.BREAKING for c in changes):
            overall = SchemaChangeType.BREAKING
        elif any(c.classification == SchemaChangeType.WARNING for c in changes):
            overall = SchemaChangeType.WARNING
        else:
            overall = SchemaChangeType.NON_BREAKING

        return SchemaDiff(
            dataset_name=dataset_name,
            base_version=base_version,
            target_version=target_version,
            has_changes=has_changes,
            overall_classification=overall,
            added_columns=actual_added,
            removed_columns=actual_removed,
            renamed_columns=renamed_pairs,
            type_changes=type_changes_list,
            changes=changes,
        )
