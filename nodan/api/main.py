"""Main FastAPI application for Nodan."""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from nodan.database import ElasticsearchClient
from nodan.scanner import Scanner
from nodan.processor import GeoEnricher, BannerNormalizer


class Config:
    """Application configuration."""

    def __init__(self, config_path: Optional[str] = None):
        """Load configuration from YAML file."""
        self.config_path = config_path or os.environ.get("NODAN_CONFIG", "config/config.yaml")

        default_config = {
            "scanner": {
                "masscan": {"rate": 10000, "wait": 10, "retries": 3},
                "nmap": {"timing": "T4", "scripts": "default,banner", "timeout": "30s"}
            },
            "database": {
                "elasticsearch": {
                    "hosts": ["http://localhost:9200"],
                    "index": "nodan",
                    "username": "",
                    "password": ""
                }
            },
            "geolocation": {
                "city_db": "data/GeoLite2-City/GeoLite2-City.mmdb",
                "asn_db": "data/GeoLite2-ASN/GeoLite2-ASN.mmdb"
            },
            "api": {
                "host": "0.0.0.0",
                "port": 8000,
                "title": "Nodan API",
                "version": "1.0.0"
            },
            "cli": {
                "api_url": "http://localhost:8000",
                "default_limit": 100,
                "max_limit": 1000
            }
        }

        if Path(self.config_path).exists():
            with open(self.config_path) as f:
                loaded = yaml.safe_load(f)
                self._config = self._merge(default_config, loaded)
        else:
            self._config = default_config

    def _merge(self, default: dict, loaded: dict) -> dict:
        """Merge loaded config with defaults."""
        result = default.copy()
        for key, value in loaded.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge(result[key], value)
            else:
                result[key] = value
        return result

    @property
    def database(self) -> dict:
        return self._config.get("database", {})

    @property
    def scanner(self) -> dict:
        return self._config.get("scanner", {})

    @property
    def geolocation(self) -> dict:
        return self._config.get("geolocation", {})

    @property
    def api(self) -> dict:
        return self._config.get("api", {})

    @property
    def cli(self) -> dict:
        return self._config.get("cli", {})


config = Config()


class ScanResult(BaseModel):
    """Scan result model."""
    ip: str
    port: int
    protocol: str = "tcp"
    service: str
    banner: Optional[str] = None
    country: Optional[str] = None
    asn: Optional[str] = None
    org: Optional[str] = None
    timestamp: str


db_client: Optional[ElasticsearchClient] = None
geo_enricher: Optional[GeoEnricher] = None
scanner: Optional[Scanner] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global db_client, geo_enricher, scanner

    es_config = config.database.get("elasticsearch", {})
    db_client = ElasticsearchClient(
        hosts=es_config.get("hosts", ["http://localhost:9200"]),
        index=es_config.get("index", "nodan"),
        username=es_config.get("username") or None,
        password=es_config.get("password") or None
    )

    try:
        db_client.create_index()
    except Exception as e:
        print(f"Warning: Could not create index: {e}")

    geo_config = config.geolocation
    try:
        geo_enricher = GeoEnricher(
            city_db_path=geo_config.get("city_db"),
            asn_db_path=geo_config.get("asn_db")
        )
    except Exception as e:
        print(f"Warning: Could not load GeoIP databases: {e}")
        geo_enricher = None

    scanner = Scanner(
        masscan_config=config.scanner.get("masscan"),
        nmap_config=config.scanner.get("nmap")
    )

    yield

    if db_client:
        db_client.close()
    if geo_enricher:
        geo_enricher.close()


app = FastAPI(
    title=config.api.get("title", "Nodan API"),
    version=config.api.get("version", "1.0.0"),
    description="Internet-wide device search engine API",
    lifespan=lifespan
)


def get_db() -> ElasticsearchClient:
    """Get database client."""
    if db_client is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    return db_client


def get_geo_enricher() -> Optional[GeoEnricher]:
    """Get geolocation enricher."""
    return geo_enricher


def get_scanner() -> Scanner:
    """Get scanner instance."""
    if scanner is None:
        raise HTTPException(status_code=503, detail="Scanner not initialized")
    return scanner


from nodan.api.routes import search, host, stats

app.include_router(search.router, prefix="/search", tags=["search"])
app.include_router(host.router, prefix="/host", tags=["host"])
app.include_router(stats.router, prefix="/stats", tags=["stats"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Nodan API",
        "version": config.api.get("version", "1.0.0"),
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    db = get_db()
    return {
        "status": "healthy" if db.health_check() else "unhealthy",
        "database": "connected" if db.health_check() else "disconnected",
        "geolocation": "available" if geo_enricher and geo_enricher.is_available else "unavailable"
    }
