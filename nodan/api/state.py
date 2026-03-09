"""Application state - global variables."""

from typing import Optional

from nodan.database import ElasticsearchClient
from nodan.processor import GeoEnricher
from nodan.scanner import Scanner

db_client: Optional[ElasticsearchClient] = None
geo_enricher: Optional[GeoEnricher] = None
scanner: Optional[Scanner] = None
