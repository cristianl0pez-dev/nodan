"""Host API route."""

import ipaddress
from typing import Optional
from collections import defaultdict

from fastapi import APIRouter, HTTPException, Path, Query

from nodan.api.main import get_db, get_geo_enricher


router = APIRouter()


@router.get("/{ip}")
async def get_host(
    ip: str = Path(..., description="IP address"),
    history: bool = Query(False, description="Include scan history")
):
    """
    Get all information about a specific host.

    Returns aggregated data about the host including all open ports,
    services, and geolocation information.
    """
    try:
        ipaddress.ip_address(ip)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid IP address")

    db = get_db()
    enricher = get_geo_enricher()

    try:
        results = db.search_by_ip(ip)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not results:
        raise HTTPException(status_code=404, detail="Host not found")

    ports_data = defaultdict(list)
    for result in results:
        port = result.get("port", 0)
        ports_data[port].append(result)

    ports = []
    for port, port_results in sorted(ports_data.items()):
        latest = port_results[0]
        ports.append({
            "port": port,
            "protocol": latest.get("protocol", "tcp"),
            "service": latest.get("service", "unknown"),
            "banner": latest.get("banner"),
            "timestamp": latest.get("timestamp")
        })

    host_info = {
        "ip": ip,
        "ports": ports,
        "total_ports": len(ports),
        "last_scan": results[0].get("timestamp") if results else None
    }

    if enricher and enricher.is_available:
        try:
            geo = enricher.enrich(ip)
            host_info["country"] = geo.country_code
            host_info["country_name"] = geo.country
            host_info["city"] = geo.city
            host_info["asn"] = geo.asn
            host_info["org"] = geo.org
            host_info["latitude"] = geo.latitude
            host_info["longitude"] = geo.longitude
        except Exception:
            pass

    if history:
        host_info["history"] = results

    return host_info
