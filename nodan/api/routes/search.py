"""Search API route."""

import re
from typing import Optional

from fastapi import APIRouter, Query, HTTPException

from nodan.api.deps import get_db, get_geo_enricher


router = APIRouter()


def parse_query(query: str) -> tuple[Optional[str], dict]:
    """
    Parse Shodan-style query string.

    Supports:
    - port:22
    - country:US
    - service:ssh
    - ip:1.2.3.4
    - Free text (searches banner, service, org)

    Args:
        query: Query string

    Returns:
        Tuple of (query_string, filters_dict)
    """
    filters = {}

    filter_pattern = r'(port|country|service|ip|asn|org):(\S+)'
    matches = re.findall(filter_pattern, query)

    for field, value in matches:
        filters[field] = value

    query_string = query
    for field, value in matches:
        query_string = query_string.replace(f"{field}:{value}", "")

    query_string = query_string.strip()

    return query_string if query_string else None, filters


@router.get("")
async def search(
    q: str = Query("", description="Search query (Shodan-style)"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    offset: int = Query(0, ge=0, description="Result offset")
):
    """
    Search for devices.

    Query syntax:
    - `port:22` - specific port
    - `country:US` - country code
    - `service:ssh` - service name
    - `ip:1.2.3.4` - specific IP
    - `asn:AS15169` - ASN
    - `org:"Google LLC"` - organization

    Example:
    ```
    /search?q=port:22 country:US
    /search?q=service:nginx
    /search?q=port:443 banner:nginx
    ```
    """
    db = get_db()

    query_string, filters = parse_query(q)

    try:
        results = db.search(
            query_string=query_string,
            filters=filters,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "query": q,
        "total": results["total"],
        "limit": limit,
        "offset": offset,
        "results": results["results"],
        "took": results.get("took", 0)
    }
