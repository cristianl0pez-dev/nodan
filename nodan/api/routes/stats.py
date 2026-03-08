"""Stats API route."""

from fastapi import APIRouter, HTTPException, Query

from nodan.api.main import get_db


router = APIRouter()


@router.get("")
async def get_stats(
    limit: int = Query(10, ge=1, le=100, description="Top N results")
):
    """
    Get search statistics.

    Returns aggregated statistics about the scanned data including:
    - Total unique hosts
    - Total scan records
    - Top services
    - Top countries
    - Top ports
    """
    db = get_db()

    try:
        stats = db.aggregate_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "total_hosts": stats.get("total_hosts", 0),
        "total_records": stats.get("total_records", 0),
        "top_services": stats.get("top_services", [])[:limit],
        "top_countries": stats.get("top_countries", [])[:limit],
        "top_ports": stats.get("top_ports", [])[:limit]
    }
