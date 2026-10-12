"""Isolated Google Cloud Platform (GCP) adapters for GCS and BigQuery.

Decoupled from core engine — core operations run 100% locally without cloud requirements.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import polars as pl

from datareliant.common.exceptions import ConfigurationError, DataReliantError


class GCPIntegrationError(DataReliantError):
    """Raised when GCP credentials or SDK interaction fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            error_code="GCP_INTEGRATION_ERROR",
            status_code=502,
            details=details,
        )


class GCSStorageAdapter:
    """Google Cloud Storage adapter for raw datasets, profiling artifacts, and model weights."""

    def __init__(self, bucket_name: str, project: str | None = None) -> None:
        self.bucket_name = bucket_name
        self.project = project
        self._client: Any = None
        self._bucket: Any = None

    def _get_bucket(self) -> Any:
        """Lazy-init GCS client and bucket reference."""
        if self._bucket is not None:
            return self._bucket

        try:
            from google.cloud import storage  # type: ignore[import-untyped]

            self._client = storage.Client(project=self.project)
            self._bucket = self._client.bucket(self.bucket_name)
            return self._bucket
        except ImportError as exc:
            raise GCPIntegrationError(
                "google-cloud-storage is not installed. Install with `pip install google-cloud-storage`"
            ) from exc
        except Exception as exc:
            raise GCPIntegrationError(f"Failed to authenticate with GCS bucket '{self.bucket_name}': {exc}") from exc

    def upload_file(self, local_path: str | Path, remote_key: str) -> str:
        """Upload a local file to GCS blob."""
        bucket = self._get_bucket()
        blob = bucket.blob(remote_key)
        blob.upload_from_filename(str(local_path))
        return f"gs://{self.bucket_name}/{remote_key}"

    def upload_bytes(self, data: bytes, remote_key: str, content_type: str = "application/octet-stream") -> str:
        """Upload in-memory bytes to GCS."""
        bucket = self._get_bucket()
        blob = bucket.blob(remote_key)
        blob.upload_from_string(data, content_type=content_type)
        return f"gs://{self.bucket_name}/{remote_key}"

    def download_file(self, remote_key: str, destination_path: str | Path) -> Path:
        """Download GCS blob to a local destination file."""
        bucket = self._get_bucket()
        blob = bucket.blob(remote_key)
        dest = Path(destination_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(str(dest))
        return dest

    def download_bytes(self, remote_key: str) -> bytes:
        """Read GCS blob directly into memory."""
        bucket = self._get_bucket()
        blob = bucket.blob(remote_key)
        return blob.download_as_bytes()

    def exists(self, remote_key: str) -> bool:
        """Check if remote key exists in bucket."""
        bucket = self._get_bucket()
        blob = bucket.blob(remote_key)
        return bool(blob.exists())

    def list_keys(self, prefix: str = "") -> list[str]:
        """List blob keys matching prefix."""
        bucket = self._get_bucket()
        blobs = bucket.list_blobs(prefix=prefix)
        return [b.name for b in blobs]


class BigQuerySource:
    """BigQuery dataset source adapter reading tables and queries directly into Polars DataFrames."""

    def __init__(self, project_id: str, dataset_id: str | None = None) -> None:
        self.project_id = project_id
        self.dataset_id = dataset_id
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client

        try:
            from google.cloud import bigquery  # type: ignore[import-untyped]

            self._client = bigquery.Client(project=self.project_id)
            return self._client
        except ImportError as exc:
            raise GCPIntegrationError(
                "google-cloud-bigquery is not installed. Install with `pip install google-cloud-bigquery`"
            ) from exc
        except Exception as exc:
            raise GCPIntegrationError(f"Failed to connect to BigQuery project '{self.project_id}': {exc}") from exc

    def query(self, sql_query: str) -> pl.DataFrame:
        """Execute BigQuery SQL and return Polars DataFrame via PyArrow."""
        client = self._get_client()
        try:
            job = client.query(sql_query)
            arrow_table = job.to_arrow()
            return pl.from_arrow(arrow_table)  # type: ignore[return-value]
        except Exception as exc:
            raise GCPIntegrationError(f"BigQuery query execution failed: {exc}") from exc

    def fetch_table(self, table_id: str, limit: int | None = None) -> pl.DataFrame:
        """Fetch entire table or partition into Polars DataFrame."""
        full_table = f"`{self.project_id}.{self.dataset_id}.{table_id}`" if self.dataset_id else f"`{self.project_id}.{table_id}`"
        sql = f"SELECT * FROM {full_table}"
        if limit:
            sql += f" LIMIT {int(limit)}"
        return self.query(sql)


class BigQuerySink:
    """BigQuery sink adapter for loading Polars DataFrames into tables."""

    def __init__(self, project_id: str, dataset_id: str) -> None:
        self.project_id = project_id
        self.dataset_id = dataset_id
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client

        try:
            from google.cloud import bigquery  # type: ignore[import-untyped]

            self._client = bigquery.Client(project=self.project_id)
            return self._client
        except ImportError as exc:
            raise GCPIntegrationError(
                "google-cloud-bigquery is not installed. Install with `pip install google-cloud-bigquery`"
            ) from exc
        except Exception as exc:
            raise GCPIntegrationError(f"Failed to connect to BigQuery project '{self.project_id}': {exc}") from exc

    def write_table(
        self,
        df: pl.DataFrame,
        table_id: str,
        write_disposition: str = "WRITE_APPEND",  # WRITE_TRUNCATE, WRITE_APPEND
    ) -> int:
        """Write Polars DataFrame to BigQuery table via PyArrow streaming."""
        client = self._get_client()
        from google.cloud import bigquery  # type: ignore[import-untyped]

        table_ref = f"{self.project_id}.{self.dataset_id}.{table_id}"
        arrow_table = df.to_arrow()

        job_config = bigquery.LoadJobConfig(
            write_disposition=write_disposition,
        )

        try:
            job = client.load_table_from_dataframe(
                arrow_table.to_pandas(),
                table_ref,
                job_config=job_config,
            )
            job.result()  # Wait for completion
            return df.height
        except Exception as exc:
            raise GCPIntegrationError(f"Failed to write DataFrame to BigQuery table '{table_ref}': {exc}") from exc
