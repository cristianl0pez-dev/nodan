"""Dependency functions for API routes."""

from typing import Optional

from fastapi import HTTPException

from nodan.database import ElasticsearchClient
from nodan.processor import GeoEnricher
from nodan.scanner import Scanner

from nodan.api import state


def get_db() -> ElasticsearchClient:
    """Get database client."""
    if state.db_client is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    return state.db_client


def get_geo_enricher() -> Optional[GeoEnricher]:
    """Get geolocation enricher."""
    return state.geo_enricher


def get_scanner() -> Scanner:
    """Get scanner instance."""
    if state.scanner is None:
        raise HTTPException(status_code=503, detail="Scanner not initialized")
    return state.scanner
