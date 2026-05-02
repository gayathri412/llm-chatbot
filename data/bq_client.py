# data/bq_client.py
"""BigQuery client for enterprise data access"""

try:
    from google.cloud import bigquery
    BQ_AVAILABLE = True
except ImportError:
    BQ_AVAILABLE = False
    bigquery = None

import os
import re
from typing import Any, List, Dict, Optional

import pandas as pd

class BigQueryClient:
    """BigQuery client wrapper for data operations"""
    
    def __init__(self, project_id: Optional[str] = None, access_policy: Any = None):
        if not BQ_AVAILABLE:
            raise ImportError("google-cloud-bigquery not installed. Run: pip install google-cloud-bigquery")
        self.client = bigquery.Client(project=project_id)
        self.project_id = project_id or self.client.project
        self.access_policy = access_policy

    def _require_unrestricted_access(self, operation: str) -> None:
        if self.access_policy and getattr(self.access_policy, "restricted", False):
            raise PermissionError(
                f"{operation} requires unrestricted data access. "
                "Your role/group is limited to approved context sources."
            )
    
    def execute_query(self, query: str, limit: int = 1000) -> pd.DataFrame:
        """Execute SQL query and return DataFrame"""
        self._require_unrestricted_access("Direct BigQuery SQL")
        query_job = self.client.query(query)
        results = query_job.result()
        return results.to_dataframe()
    
    def fetch_context(self, user_query: str, table: str = "chat_context_docs",
                     dataset: str = "analytics", limit: int = 5,
                     allowed_sources: set[str] | frozenset[str] | None = None) -> List[Dict]:
        """Fetch context from BigQuery for RAG"""
        if allowed_sources is not None and not allowed_sources:
            return []

        safe_pattern = re.escape(user_query.lower())
        source_filter = ""
        query_parameters = [
            bigquery.ScalarQueryParameter("pattern", "STRING", safe_pattern),
            bigquery.ScalarQueryParameter("limit", "INT64", limit),
        ]
        if allowed_sources is not None:
            source_filter = "AND LOWER(source) IN UNNEST(@allowed_sources)"
            query_parameters.append(
                bigquery.ArrayQueryParameter(
                    "allowed_sources",
                    "STRING",
                    sorted(str(source).lower() for source in allowed_sources),
                )
            )

        query = f"""
        SELECT
            doc_id,
            title,
            body,
            source,
            tags,
            allowed_roles,
            allowed_groups,
            sensitivity,
            metadata,
            updated_at,
            ingestion_date
        FROM `{self.project_id}.{dataset}.{table}`
        WHERE (
            REGEXP_CONTAINS(LOWER(body), @pattern)
            OR REGEXP_CONTAINS(LOWER(title), @pattern)
        )
        {source_filter}
        ORDER BY updated_at DESC
        LIMIT @limit
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=query_parameters
        )
        rows = self.client.query(query, job_config=job_config).result()
        return [dict(r) for r in rows]
    
    def list_tables(self, dataset: str = "analytics") -> List[str]:
        """List all tables in a dataset"""
        self._require_unrestricted_access("Listing BigQuery tables")
        dataset_ref = f"{self.project_id}.{dataset}"
        tables = self.client.list_tables(dataset_ref)
        return [table.table_id for table in tables]
    
    def get_table_schema(self, table: str, dataset: str = "analytics") -> List[Dict]:
        """Get table schema"""
        self._require_unrestricted_access("Reading BigQuery table schema")
        table_ref = f"{self.project_id}.{dataset}.{table}"
        table = self.client.get_table(table_ref)
        return [{"name": field.name, "type": field.field_type} for field in table.schema]
    
    def preview_table(self, table: str, dataset: str = "analytics", limit: int = 10) -> pd.DataFrame:
        """Preview table data"""
        self._require_unrestricted_access("Previewing BigQuery tables")
        query = f"SELECT * FROM `{self.project_id}.{dataset}.{table}` LIMIT {limit}"
        return self.execute_query(query)

def fetch_context_from_bq(user_query: str, project_id: Optional[str] = None, 
                          limit: int = 5,
                          allowed_sources: set[str] | frozenset[str] | None = None) -> List[Dict]:
    """Simple function to fetch context from BigQuery"""
    if not BQ_AVAILABLE:
        return []
    client = BigQueryClient(project_id)
    dataset = os.getenv("BIGQUERY_CONTEXT_DATASET", "analytics")
    table = os.getenv("BIGQUERY_CONTEXT_TABLE", "chat_context_docs")
    return client.fetch_context(
        user_query,
        dataset=dataset,
        table=table,
        limit=limit,
        allowed_sources=allowed_sources,
    )

# JSON ingestion utilities
def prepare_json_for_bq(json_data: Dict) -> Dict:
    """Prepare JSON data for BigQuery ingestion"""
    required_fields = ["doc_id", "body"]
    for field in required_fields:
        if field not in json_data:
            raise ValueError(f"Missing required field: {field}")
    
    # Ensure tags is an array
    if "tags" in json_data and not isinstance(json_data["tags"], list):
        json_data["tags"] = [json_data["tags"]]
    
    return json_data
