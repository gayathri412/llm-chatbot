import argparse
import json
import os
import tempfile
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False

try:
    from google.cloud import bigquery, storage
except ImportError:
    bigquery = None
    storage = None


load_dotenv()


DEFAULT_CONTEXT_SCHEMA = [
    {"name": "doc_id", "type": "STRING", "mode": "REQUIRED"},
    {"name": "title", "type": "STRING", "mode": "NULLABLE"},
    {"name": "body", "type": "STRING", "mode": "REQUIRED"},
    {"name": "source", "type": "STRING", "mode": "NULLABLE"},
    {"name": "tags", "type": "STRING", "mode": "REPEATED"},
    {"name": "updated_at", "type": "TIMESTAMP", "mode": "NULLABLE"},
    {"name": "ingestion_date", "type": "DATE", "mode": "REQUIRED"},
]

EMBEDDINGS_SCHEMA = [
    {"name": "doc_id", "type": "STRING", "mode": "REQUIRED"},
    {"name": "chunk_id", "type": "STRING", "mode": "REQUIRED"},
    {"name": "chunk_text", "type": "STRING", "mode": "REQUIRED"},
    {"name": "embedding", "type": "FLOAT", "mode": "REPEATED"},
    {"name": "source", "type": "STRING", "mode": "NULLABLE"},
    {"name": "updated_at", "type": "TIMESTAMP", "mode": "NULLABLE"},
    {"name": "ingestion_date", "type": "DATE", "mode": "REQUIRED"},
]


def _parse_timestamp(value: Any, fallback: str) -> str:
    if not value:
        return fallback

    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()

    value_text = str(value).strip()
    if not value_text:
        return fallback

    return value_text


def _normalize_tags(value: Any) -> list[str]:
    if value is None:
        return []

    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]

    if isinstance(value, str):
        return [tag.strip() for tag in value.split(",") if tag.strip()]

    return [str(value)]


def normalize_json_documents(json_path: str | Path, source: str | None = None) -> list[dict[str, Any]]:
    path = Path(json_path)
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, dict):
        data = data.get("documents", data.get("items", []))

    if not isinstance(data, list):
        raise ValueError("Input JSON must be a list, or an object with documents/items.")

    now_dt = datetime.now(timezone.utc)
    now = now_dt.isoformat()
    ingestion_date = now_dt.date().isoformat()
    rows_by_key = {}

    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            continue

        doc_id = item.get("doc_id") or item.get("id")
        if not doc_id or not str(doc_id).strip():
            raise ValueError(f"Document at index {index} is missing required field: doc_id or id")

        body = item.get("body") or item.get("content") or item.get("text")
        if not body or not str(body).strip():
            raise ValueError(f"Document {doc_id} is missing required field: body/content/text")

        updated_at = _parse_timestamp(item.get("updated_at"), fallback=now)
        dedupe_key = (str(doc_id), updated_at)
        if dedupe_key in rows_by_key:
            continue

        rows_by_key[dedupe_key] = {
            "doc_id": str(doc_id),
            "title": str(item.get("title") or "Untitled"),
            "body": str(body),
            "source": str(item.get("source") or source or path.name),
            "tags": _normalize_tags(item.get("tags")),
            "updated_at": updated_at,
            "ingestion_date": str(item.get("ingestion_date") or ingestion_date),
        }

    return list(rows_by_key.values())


class CloudDataLayer:
    def __init__(
        self,
        project_id: str | None = None,
        bucket_name: str | None = None,
        location: str | None = None,
        raw_dataset: str | None = None,
        curated_dataset: str | None = None,
    ) -> None:
        if storage is None or bigquery is None:
            raise ImportError(
                "Install google-cloud-storage and google-cloud-bigquery to use the cloud data layer."
            )

        self.project_id = project_id or os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.bucket_name = bucket_name or os.getenv("GCS_STAGING_BUCKET")
        self.location = location or os.getenv("GCP_LOCATION", "US")
        self.raw_dataset = raw_dataset or os.getenv("BIGQUERY_RAW_DATASET", "raw")
        self.curated_dataset = curated_dataset or os.getenv("BIGQUERY_CONTEXT_DATASET", "analytics")

        if not self.project_id:
            raise ValueError("GCP_PROJECT_ID is required.")
        if not self.bucket_name:
            raise ValueError("GCS_STAGING_BUCKET is required.")

        self.storage_client = storage.Client(project=self.project_id)
        self.bq_client = bigquery.Client(project=self.project_id)

    def ensure_bucket(self) -> None:
        try:
            self.storage_client.get_bucket(self.bucket_name)
        except Exception:
            bucket = storage.Bucket(self.storage_client, self.bucket_name)
            bucket.location = self.location
            self.storage_client.create_bucket(bucket, project=self.project_id)

    def ensure_dataset(self, dataset_id: str) -> None:
        dataset_ref = f"{self.project_id}.{dataset_id}"
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = self.location
        self.bq_client.create_dataset(dataset, exists_ok=True)

    def ensure_context_table(self, dataset_id: str | None = None, table_id: str = "chat_context_docs") -> None:
        dataset_id = dataset_id or self.curated_dataset
        self.ensure_dataset(dataset_id)

        table_ref = f"{self.project_id}.{dataset_id}.{table_id}"
        schema = [
            bigquery.SchemaField(field["name"], field["type"], mode=field["mode"])
            for field in DEFAULT_CONTEXT_SCHEMA
        ]
        table = bigquery.Table(table_ref, schema=schema)
        table.time_partitioning = bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY,
            field="ingestion_date",
        )
        table.clustering_fields = ["source", "title"]
        self.bq_client.create_table(table, exists_ok=True)

    def ensure_embeddings_table(self, dataset_id: str | None = None, table_id: str = "chat_context_embeddings") -> None:
        dataset_id = dataset_id or self.curated_dataset
        self.ensure_dataset(dataset_id)

        table_ref = f"{self.project_id}.{dataset_id}.{table_id}"
        schema = [
            bigquery.SchemaField(field["name"], field["type"], mode=field["mode"])
            for field in EMBEDDINGS_SCHEMA
        ]
        table = bigquery.Table(table_ref, schema=schema)
        table.time_partitioning = bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY,
            field="ingestion_date",
        )
        table.clustering_fields = ["doc_id", "source"]
        self.bq_client.create_table(table, exists_ok=True)

    def normalize_json_documents(self, json_path: str | Path, source: str | None = None) -> list[dict[str, Any]]:
        return normalize_json_documents(json_path, source=source)

    def stage_json_to_gcs(self, json_path: str | Path, prefix: str = "raw/context_docs") -> str:
        rows = self.normalize_json_documents(json_path)
        if not rows:
            raise ValueError("No valid documents found to stage.")

        object_name = (
            f"{prefix}/{datetime.now(timezone.utc).strftime('%Y/%m/%d')}/"
            f"{Path(json_path).stem}-{uuid.uuid4().hex}.jsonl"
        )
        payload = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows)

        bucket = self.storage_client.bucket(self.bucket_name)
        blob = bucket.blob(object_name)
        blob.upload_from_string(payload, content_type="application/json")
        return f"gs://{self.bucket_name}/{object_name}"

    def load_gcs_json_to_bigquery(
        self,
        gcs_uri: str,
        dataset_id: str | None = None,
        table_id: str = "chat_context_docs",
        write_disposition: str = "WRITE_APPEND",
    ) -> str:
        dataset_id = dataset_id or self.curated_dataset
        self.ensure_context_table(dataset_id=dataset_id, table_id=table_id)

        destination = f"{self.project_id}.{dataset_id}.{table_id}"
        schema = [
            bigquery.SchemaField(field["name"], field["type"], mode=field["mode"])
            for field in DEFAULT_CONTEXT_SCHEMA
        ]
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            schema=schema,
            write_disposition=write_disposition,
        )

        load_job = self.bq_client.load_table_from_uri(gcs_uri, destination, job_config=job_config)
        load_job.result()
        return destination

    def ingest_json_file(
        self,
        json_path: str | Path,
        table_id: str = "chat_context_docs",
        write_disposition: str = "WRITE_APPEND",
        ensure_embeddings: bool = False,
    ) -> dict[str, str]:
        self.ensure_bucket()
        if ensure_embeddings:
            self.ensure_embeddings_table()
        gcs_uri = self.stage_json_to_gcs(json_path)
        table_ref = self.load_gcs_json_to_bigquery(
            gcs_uri,
            table_id=table_id,
            write_disposition=write_disposition,
        )
        return {"gcs_uri": gcs_uri, "table": table_ref}

    def write_local_jsonl(self, json_path: str | Path) -> str:
        rows = self.normalize_json_documents(json_path)
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jsonl", mode="w", encoding="utf-8")
        with temp_file:
            for row in rows:
                temp_file.write(json.dumps(row, ensure_ascii=False) + "\n")
        return temp_file.name


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage local JSON in GCS and load it to BigQuery.")
    parser.add_argument("json_path", help="Path to local JSON knowledge file.")
    parser.add_argument("--table", default="chat_context_docs", help="Curated BigQuery table name.")
    parser.add_argument("--write-disposition", default="WRITE_APPEND", choices=["WRITE_APPEND", "WRITE_TRUNCATE"])
    parser.add_argument("--ensure-embeddings-table", action="store_true", help="Create the optional embeddings table.")
    args = parser.parse_args()

    layer = CloudDataLayer()
    result = layer.ingest_json_file(
        args.json_path,
        table_id=args.table,
        write_disposition=args.write_disposition,
        ensure_embeddings=args.ensure_embeddings_table,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
