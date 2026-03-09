"""Elasticsearch client for Nodan."""

import uuid
import ipaddress
from typing import Optional, Any
from datetime import datetime, timezone

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from elasticsearch.dsl import Q


INDEX_MAPPING = {
    "mappings": {
        "properties": {
            "ip": {"type": "ip"},
            "port": {"type": "integer"},
            "protocol": {"type": "keyword"},
            "service": {"type": "keyword"},
            "banner": {"type": "text"},
            "country": {"type": "keyword"},
            "asn": {"type": "keyword"},
            "org": {"type": "keyword"},
            "city": {"type": "keyword"},
            "timestamp": {"type": "date"},
            "scan_id": {"type": "keyword"}
        }
    },
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "index.mapping.total_fields.limit": 2000
    }
}


class ElasticsearchClient:
    """Elasticsearch client for storing and searching scan results."""

    def __init__(
        self,
        hosts: list[str],
        index: str = "nodan",
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_ssl: bool = True,
        verify_certs: bool = False
    ):
        """
        Initialize Elasticsearch client.

        Args:
            hosts: List of Elasticsearch hosts
            index: Index name
            username: Optional username
            password: Optional password
            use_ssl: Use SSL/TLS
            verify_certs: Verify SSL certificates
        """
        self.index = index

        kwargs: dict[str, Any] = {
            "hosts": hosts,
        }

        if username and password:
            kwargs["basic_auth"] = (username, password)

        self.client = Elasticsearch(**kwargs)

    def create_index(self, force: bool = False) -> bool:
        """
        Create the index if it doesn't exist.

        Args:
            force: Force recreate if exists

        Returns:
            True if created
        """
        if self.client.indices.exists(index=self.index):
            if force:
                self.client.indices.delete(index=self.index)
            else:
                return False

        self.client.indices.create(index=self.index, mappings=INDEX_MAPPING["mappings"], settings=INDEX_MAPPING["settings"])
        return True

    def index_result(self, result: dict) -> str:
        """
        Index a single scan result.

        Args:
            result: Scan result dictionary

        Returns:
            Document ID
        """
        doc_id = result.get("id") or str(uuid.uuid4())
        result["timestamp"] = result.get("timestamp") or datetime.now(timezone.utc).isoformat()

        self.client.index(
            index=self.index,
            id=doc_id,
            document=result
        )

        return doc_id

    def bulk_index(self, results: list[dict]) -> tuple[int, int]:
        """
        Bulk index multiple results.

        Args:
            results: List of scan results

        Returns:
            Tuple of (success_count, error_count)
        """
        if not results:
            return 0, 0

        actions = []
        for result in results:
            action = {
                "_index": self.index,
                "_id": result.get("id") or str(uuid.uuid4()),
                "_source": result
            }
            action["_source"]["timestamp"] = action["_source"].get("timestamp") or \
                datetime.now(timezone.utc).isoformat()
            actions.append(action)

        success, errors = bulk(self.client, actions, raise_on_error=False)

        error_count = len(errors) if isinstance(errors, list) else 0

        return success, error_count

    def search(
        self,
        query: Optional[dict] = None,
        query_string: Optional[str] = None,
        filters: Optional[dict] = None,
        limit: int = 100,
        offset: int = 0,
        sort: Optional[list] = None
    ) -> dict:
        """
        Search for scan results.

        Args:
            query: Full ES query dict
            query_string: Simple query string
            filters: Field filters (port, service, country, etc.)
            limit: Max results
            offset: Offset for pagination
            sort: Sort specification

        Returns:
            Search results
        """
        q = None

        if query:
            q = query
        else:
            must_clauses = []

            if query_string:
                fields = ["banner", "service", "country", "org", "asn"]
                try:
                    ipaddress.ip_address(query_string)
                    fields.insert(0, "ip")
                except ValueError:
                    pass
                
                must_clauses.append({
                    "query_string": {
                        "query": query_string,
                        "fields": fields
                    }
                })

            if filters:
                for field, value in filters.items():
                    if value:
                        must_clauses.append({
                            "term": {field: value}
                        })

            if must_clauses:
                q = {"bool": {"must": must_clauses}}
            else:
                q = {"match_all": {}}

        if sort is None:
            sort = [{"timestamp": {"order": "desc"}}]

        result = self.client.search(
            index=self.index,
            query=q,
            from_=offset,
            size=limit,
            sort=sort
        )

        return {
            "total": result["hits"]["total"]["value"],
            "results": [hit["_source"] for hit in result["hits"]["hits"]],
            "took": result["took"]
        }

    def search_by_ip(self, ip: str) -> list[dict]:
        """
        Get all results for a specific IP.

        Args:
            ip: IP address

        Returns:
            List of scan results
        """
        result = self.client.search(
            index=self.index,
            query={"term": {"ip": ip}},
            sort=[{"timestamp": {"order": "desc"}}],
            size=1000
        )

        return [hit["_source"] for hit in result["hits"]["hits"]]

    def aggregate_stats(self) -> dict:
        """
        Get aggregation statistics.

        Returns:
            Statistics dictionary
        """
        result = self.client.search(
            index=self.index,
            size=0,
            aggs={
                "services": {"terms": {"field": "service", "size": 50}},
                "countries": {"terms": {"field": "country", "size": 50}},
                "ports": {"terms": {"field": "port", "size": 50}},
                "total_hosts": {"value_count": {"field": "ip"}},
                "total_records": {"value_count": {"field": "timestamp"}}
            }
        )

        aggs = result.get("aggregations", {})

        return {
            "total_hosts": aggs.get("total_hosts", {}).get("value", 0),
            "total_records": aggs.get("total_records", {}).get("value", 0),
            "top_services": [
                {"service": b["key"], "count": b["doc_count"]}
                for b in aggs.get("services", {}).get("buckets", [])
            ],
            "top_countries": [
                {"country": b["key"], "count": b["doc_count"]}
                for b in aggs.get("countries", {}).get("buckets", [])
            ],
            "top_ports": [
                {"port": b["key"], "count": b["doc_count"]}
                for b in aggs.get("ports", {}).get("buckets", [])
            ]
        }

    def delete_by_query(self, query: dict) -> int:
        """
        Delete documents matching a query.

        Args:
            query: ES query

        Returns:
            Number of deleted documents
        """
        result = self.client.delete_by_query(
            index=self.index,
            body={"query": query}
        )

        return result["deleted"]

    def health_check(self) -> bool:
        """
        Check if Elasticsearch is available.

        Returns:
            True if healthy
        """
        try:
            return self.client.ping()
        except Exception:
            return False

    def close(self):
        """Close the client connection."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
