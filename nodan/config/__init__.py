"""Configuration utilities for Nodan."""

import os
from pathlib import Path

import yaml


def load_config(config_path: str = None) -> dict:
    """Load configuration from YAML file."""
    if config_path is None:
        config_path = os.environ.get("NODAN_CONFIG", "config/config.yaml")

    if not Path(config_path).exists():
        return get_default_config()

    with open(config_path) as f:
        return yaml.safe_load(f) or {}


def get_default_config() -> dict:
    """Get default configuration."""
    return {
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
        }
    }
