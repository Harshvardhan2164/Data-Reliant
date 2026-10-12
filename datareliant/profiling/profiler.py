"""Statistical profiling engine using high-performance Polars operations."""

from __future__ import annotations

from datetime import UTC, datetime

import polars as pl

from datareliant.profiling.models import (
    ColumnStats,
    DataProfile,
    DatasetStats,
    TemporalStats,
)


class DataProfiler:
    """Computes comprehensive dataset, column, and temporal profiles."""

    def __init__(self, top_n_categories: int = 10) -> None:
        self.top_n_categories = top_n_categories

    def profile(
        self,
        df: pl.DataFrame,
        dataset_name: str = "dataset",
        version: int = 1,
        dataset_hash: str | None = None,
    ) -> DataProfile:
        """Execute full profiling on a Polars DataFrame.

        Args:
            df: The Polars DataFrame to profile.
            dataset_name: Name of the dataset.
            version: Version number.
            dataset_hash: Optional cryptographic checksum.

        Returns:
            DataProfile containing dataset, column, and temporal metrics.
        """
        row_count = df.height
        column_count = df.width
        mem_estimate = df.estimated_size()

        # Duplicate row calculation
        if row_count > 0 and column_count > 0:
            unique_rows = df.unique().height
            duplicate_count = max(0, row_count - unique_rows)
            duplicate_pct = (duplicate_count / row_count) * 100.0
        else:
            duplicate_count = 0
            duplicate_pct = 0.0

        column_stats: dict[str, ColumnStats] = {}
        temporal_stats: dict[str, TemporalStats] = {}

        temporal_coverages: list[str] = []

        for col in df.columns:
            series = df[col]
            dtype = series.dtype

            # Basic stats
            null_count = series.null_count()
            null_pct = (null_count / max(row_count, 1)) * 100.0
            n_unique = series.n_unique()
            unique_pct = (n_unique / max(row_count, 1)) * 100.0

            col_stat = ColumnStats(
                name=col,
                datatype=str(dtype),
                null_count=null_count,
                null_percentage=round(null_pct, 4),
                unique_count=n_unique,
                uniqueness_percentage=round(unique_pct, 4),
                approximate_cardinality=n_unique,
            )

            # Numeric metrics
            if dtype.is_numeric() and row_count > null_count:
                non_nulls = series.drop_nulls()
                if non_nulls.len() > 0:
                    col_stat.min_value = (
                        float(non_nulls.min()) if non_nulls.min() is not None else None
                    )
                    col_stat.max_value = (
                        float(non_nulls.max()) if non_nulls.max() is not None else None
                    )
                    col_stat.mean = (
                        float(non_nulls.mean()) if non_nulls.mean() is not None else None
                    )
                    col_stat.median = (
                        float(non_nulls.median()) if non_nulls.median() is not None else None
                    )
                    col_stat.std_dev = (
                        float(non_nulls.std())
                        if non_nulls.len() > 1 and non_nulls.std() is not None
                        else 0.0
                    )
                    # Quantiles
                    col_stat.quantiles = {
                        "p25": float(non_nulls.quantile(0.25))
                        if non_nulls.quantile(0.25) is not None
                        else 0.0,
                        "p50": float(non_nulls.quantile(0.50))
                        if non_nulls.quantile(0.50) is not None
                        else 0.0,
                        "p75": float(non_nulls.quantile(0.75))
                        if non_nulls.quantile(0.75) is not None
                        else 0.0,
                        "p90": float(non_nulls.quantile(0.90))
                        if non_nulls.quantile(0.90) is not None
                        else 0.0,
                        "p99": float(non_nulls.quantile(0.99))
                        if non_nulls.quantile(0.99) is not None
                        else 0.0,
                    }

            # Categorical / string metrics
            if (
                dtype == pl.String or dtype == pl.Categorical or dtype == pl.Boolean
            ) and row_count > 0:
                val_counts = series.drop_nulls().value_counts(sort=True).head(self.top_n_categories)
                freq_list = []
                for row in val_counts.iter_rows():
                    freq_list.append(
                        {
                            "value": str(row[0]),
                            "count": row[1],
                            "percentage": round((row[1] / row_count) * 100.0, 2),
                        }
                    )
                col_stat.categorical_frequencies = freq_list

            # Temporal analysis
            if dtype.is_temporal():
                t_stat = self._analyze_temporal(series, col)
                if t_stat:
                    temporal_stats[col] = t_stat
                    if t_stat.min_timestamp and t_stat.max_timestamp:
                        temporal_coverages.append(
                            f"{col}: [{t_stat.min_timestamp} to {t_stat.max_timestamp}]"
                        )
            elif dtype == pl.String and row_count > 0:
                # Try inferring if column is temporal string
                sample = series.drop_nulls().head(20)
                if sample.len() > 0:
                    try:
                        parsed = sample.str.to_datetime()
                        if parsed.null_count() < sample.len() * 0.5:
                            # It is a timestamp column
                            parsed_full = series.str.to_datetime(strict=False)
                            t_stat = self._analyze_temporal(parsed_full, col)
                            if t_stat:
                                temporal_stats[col] = t_stat
                                if t_stat.min_timestamp and t_stat.max_timestamp:
                                    temporal_coverages.append(
                                        f"{col}: [{t_stat.min_timestamp} to {t_stat.max_timestamp}]"
                                    )
                    except Exception:
                        pass

            column_stats[col] = col_stat

        coverage_summary = "; ".join(temporal_coverages) if temporal_coverages else None

        dataset_stats = DatasetStats(
            row_count=row_count,
            column_count=column_count,
            memory_estimate_bytes=mem_estimate,
            duplicate_row_count=duplicate_count,
            duplicate_row_percentage=round(duplicate_pct, 4),
            dataset_hash=dataset_hash,
            temporal_coverage=coverage_summary,
        )

        return DataProfile(
            dataset_name=dataset_name,
            version=version,
            dataset_stats=dataset_stats,
            column_stats=column_stats,
            temporal_stats=temporal_stats,
        )

    def _analyze_temporal(self, series: pl.Series, col_name: str) -> TemporalStats | None:
        """Compute minimum, maximum, inferred frequency, gaps, and freshness for a temporal series."""
        clean = series.drop_nulls().sort()
        if clean.len() == 0:
            return None

        min_val = clean.min()
        max_val = clean.max()

        min_ts = str(min_val) if min_val is not None else None
        max_ts = str(max_val) if max_val is not None else None

        # Freshness: time delta from max_val to current UTC in seconds
        freshness_sec: float | None = None
        if max_val is not None:
            try:
                # If date/datetime
                if isinstance(max_val, datetime):
                    aware_max = max_val.replace(tzinfo=UTC) if max_val.tzinfo is None else max_val
                    freshness_sec = max(0.0, (datetime.now(UTC) - aware_max).total_seconds())
            except Exception:
                pass

        # Inferred frequency and gaps
        inferred_freq: str | None = None
        gaps_count = 0

        if clean.len() >= 3:
            try:
                diffs = clean.diff().drop_nulls()
                if diffs.len() > 0:
                    median_diff = diffs.median()
                    if median_diff is not None:
                        # Estimate frequency label
                        total_secs = 0.0
                        if hasattr(median_diff, "total_seconds"):
                            total_secs = median_diff.total_seconds()
                        elif isinstance(median_diff, (int, float)):
                            total_secs = float(median_diff) / 1000.0  # ms if raw

                        if 55 <= total_secs <= 65:
                            inferred_freq = "1m"
                        elif 3500 <= total_secs <= 3700:
                            inferred_freq = "1h"
                        elif 86000 <= total_secs <= 87000:
                            inferred_freq = "1d"
                        elif total_secs > 0:
                            inferred_freq = f"{int(total_secs)}s"

                        # Gap detection: intervals > 2.0x median interval
                        if total_secs > 0:
                            sec_diffs = diffs.dt.total_seconds() if hasattr(diffs, "dt") else diffs
                            gaps = sec_diffs.filter(sec_diffs > (total_secs * 2.0))
                            gaps_count = gaps.len()
            except Exception:
                pass

        tz_meta = None
        if hasattr(series.dtype, "time_zone") and series.dtype.time_zone:
            tz_meta = str(series.dtype.time_zone)

        return TemporalStats(
            column_name=col_name,
            min_timestamp=min_ts,
            max_timestamp=max_ts,
            inferred_frequency=inferred_freq,
            gaps_count=gaps_count,
            freshness_seconds=freshness_sec,
            timezone_metadata=tz_meta,
        )
