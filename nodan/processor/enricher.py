"""Geolocation enrichment using MaxMind GeoIP."""

from typing import Optional
from dataclasses import dataclass

try:
    import maxminddb
    MAXMIND_AVAILABLE = True
except ImportError:
    MAXMIND_AVAILABLE = False


@dataclass
class GeoInfo:
    """Geolocation information for an IP."""
    country: Optional[str] = None
    country_code: Optional[str] = None
    city: Optional[str] = None
    asn: Optional[str] = None
    org: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class GeoEnricher:
    """Enrich IP addresses with geolocation data."""

    def __init__(
        self,
        city_db_path: Optional[str] = None,
        asn_db_path: Optional[str] = None
    ):
        """
        Initialize the enricher.

        Args:
            city_db_path: Path to MaxMind City database
            asn_db_path: Path to MaxMind ASN database
        """
        self.city_db = None
        self.asn_db = None

        if MAXMIND_AVAILABLE:
            if city_db_path:
                try:
                    self.city_db = maxminddb.open_database(city_db_path)
                except Exception as e:
                    print(f"Warning: Could not open city DB: {e}")

            if asn_db_path:
                try:
                    self.asn_db = maxminddb.open_database(asn_db_path)
                except Exception as e:
                    print(f"Warning: Could not open ASN DB: {e}")

    def enrich(self, ip: str) -> GeoInfo:
        """
        Get geolocation data for an IP.

        Args:
            ip: IP address

        Returns:
            GeoInfo object with geolocation data
        """
        geo = GeoInfo()

        if self.asn_db:
            try:
                asn_data = self.asn_db.get(ip)
                if asn_data:
                    geo.asn = asn_data.get("autonomous_system_number")
                    geo.org = asn_data.get("autonomous_system_organization")
                    if geo.asn:
                        geo.asn = f"AS{geo.asn}"
            except Exception:
                pass

        if self.city_db:
            try:
                city_data = self.city_db.get(ip)
                if city_data:
                    if "country" in city_data:
                        geo.country = city_data["country"].get("names", {}).get("en")
                        geo.country_code = city_data["country"].get("iso_code")

                    if "city" in city_data:
                        geo.city = city_data["city"].get("names", {}).get("en")

                    if "location" in city_data:
                        geo.latitude = city_data["location"].get("latitude")
                        geo.longitude = city_data["location"].get("longitude")
            except Exception:
                pass

        return geo

    def enrich_result(self, result: dict) -> dict:
        """
        Enrich a scan result with geolocation data.

        Args:
            result: Scan result dictionary

        Returns:
            Enriched result dictionary
        """
        ip = result.get("ip")
        if not ip:
            return result

        geo = self.enrich(ip)

        result["country"] = geo.country_code or geo.country
        result["asn"] = geo.asn
        result["org"] = geo.org

        if geo.city:
            result["city"] = geo.city

        return result

    def close(self):
        """Close database connections."""
        if self.city_db:
            self.city_db.close()
        if self.asn_db:
            self.asn_db.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @property
    def is_available(self) -> bool:
        """Check if enricher has databases loaded."""
        return self.city_db is not None or self.asn_db is not None
