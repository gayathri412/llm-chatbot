# data/bq_client.py
"""BigQuery client for enterprise data access"""

try:
    from google.cloud import bigquery
    BQ_AVAILABLE = True
except ImportError:
    BQ_AVAILABLE = False
    bigquery = None

import pandas as pd
import json
from typing import List, Dict, Optional

class BigQueryClient:
    """BigQuery client wrapper for data operations"""
    
    def __init__(self, project_id: Optional[str] = None):
        if not BQ_AVAILABLE:
            raise ImportError("google-cloud-bigquery not installed. Run: pip install google-cloud-bigquery")
        self.client = bigquery.Client(project=project_id)
        self.project_id = project_id or self.client.project
    
    def execute_query(self, query: str, limit: int = 1000) -> pd.DataFrame:
        """Execute SQL query and return DataFrame"""
        query_job = self.client.query(query)
        results = query_job.result()
        return results.to_dataframe()
    
    def fetch_context(self, user_query: str, table: str = "chat_context_docs", 
                     dataset: str = "analytics", limit: int = 5) -> List[Dict]:
        """Fetch context from BigQuery for RAG"""
        query = f"""
        SELECT doc_id, title, body, source, updated_at
        FROM `{self.project_id}.{dataset}.{table}` 
        WHERE REGEXP_CONTAINS(LOWER(body), r'{user_query.lower()}')
        OR REGEXP_CONTAINS(LOWER(title), r'{user_query.lower()}')
        ORDER BY updated_at DESC
        LIMIT {limit}
        """
        rows = self.client.query(query).result()
        return [dict(r) for r in rows]
    
    def list_tables(self, dataset: str = "analytics") -> List[str]:
        """List all tables in a dataset"""
        dataset_ref = f"{self.project_id}.{dataset}"
        tables = self.client.list_tables(dataset_ref)
        return [table.table_id for table in tables]
    
    def get_table_schema(self, table: str, dataset: str = "analytics") -> List[Dict]:
        """Get table schema"""
        table_ref = f"{self.project_id}.{dataset}.{table}"
        table = self.client.get_table(table_ref)
        return [{"name": field.name, "type": field.field_type} for field in table.schema]
    
    def preview_table(self, table: str, dataset: str = "analytics", limit: int = 10) -> pd.DataFrame:
        """Preview table data"""
        query = f"SELECT * FROM `{self.project_id}.{dataset}.{table}` LIMIT {limit}"
        return self.execute_query(query)

def fetch_context_from_bq(user_query: str, project_id: Optional[str] = None, 
                          limit: int = 5) -> List[Dict]:
    """Simple function to fetch context from BigQuery"""
    if not BQ_AVAILABLE:
        return []
    client = BigQueryClient(project_id)
    return client.fetch_context(user_query, limit=limit)

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
