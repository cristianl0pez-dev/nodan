"""CLI main entry point for Nodan."""

import os
import json
import sys

import click
import httpx

from nodan.scanner import Scanner
from nodan.processor import GeoEnricher
from nodan.database import ElasticsearchClient


API_URL = os.environ.get("NODAN_API_URL", "http://localhost:8000")


def get_api_client() -> httpx.Client:
    """Get HTTP client for API."""
    return httpx.Client(base_url=API_URL, timeout=30.0)


def load_config():
    """Load configuration."""
    config_path = os.environ.get("NODAN_CONFIG", "config/config.yaml")

    if not os.path.exists(config_path):
        return {}

    import yaml
    with open(config_path) as f:
        return yaml.safe_load(f) or {}


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Nodan - Internet-wide Device Search Engine."""
    pass


@cli.command()
@click.argument("query")
@click.option("--limit", "-l", default=100, help="Max results")
@click.option("--offset", "-o", default=0, help="Result offset")
@click.option("--json/--no-json", default=False, help="Output as JSON")
def search(query: str, limit: int, offset: int, json_output: bool):
    """Search for devices.

    QUERY is a Shodan-style query string.

    Examples:
        nodan search "port:22"
        nodan search "port:80 country:US"
        nodan search "service:nginx"
    """
    client = get_api_client()

    try:
        response = client.get("/search", params={
            "q": query,
            "limit": limit,
            "offset": offset
        })
        response.raise_for_status()
        data = response.json()

        if json_output:
            click.echo(json.dumps(data, indent=2))
        else:
            click.echo(f"Found {data['total']} results\n")

            for result in data["results"]:
                ip = result.get("ip", "unknown")
                port = result.get("port", 0)
                service = result.get("service", "unknown")
                banner = result.get("banner", "")
                country = result.get("country", "")

                if country:
                    click.echo(f"[{country}] {ip}:{port} ({service})")
                else:
                    click.echo(f"{ip}:{port} ({service})")

                if banner:
                    click.echo(f"    {banner}")

    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("ip")
@click.option("--history/--no-history", default=False, help="Include scan history")
@click.option("--json/--no-json", default=False, help="Output as JSON")
def host(ip: str, history: bool, json_output: bool):
    """Get information about a specific host.

    IP is the target IP address.
    """
    client = get_api_client()

    try:
        response = client.get(f"/host/{ip}", params={"history": history})
        response.raise_for_status()
        data = response.json()

        if json_output:
            click.echo(json.dumps(data, indent=2))
        else:
            click.echo(f"Host: {ip}")
            click.echo(f"Total ports: {data.get('total_ports', 0)}")

            if data.get("country"):
                click.echo(f"Country: {data.get('country')}")
            if data.get("org"):
                click.echo(f"Organization: {data.get('org')}")
            if data.get("asn"):
                click.echo(f"ASN: {data.get('asn')}")

            click.echo("\nOpen ports:")
            for port_info in data.get("ports", []):
                port = port_info.get("port")
                service = port_info.get("service", "unknown")
                banner = port_info.get("banner", "")
                protocol = port_info.get("protocol", "tcp")

                click.echo(f"  {port}/{protocol} - {service}")
                if banner:
                    click.echo(f"      {banner}")

    except httpx.HTTPError as e:
        if response.status_code == 404:
            click.echo(f"Error: Host {ip} not found", err=True)
        else:
            click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--json/--no-json", default=False, help="Output as JSON")
@click.option("--limit", "-l", default=10, help="Top N results")
def stats(json_output: bool, limit: int):
    """Get search statistics."""
    client = get_api_client()

    try:
        response = client.get("/stats", params={"limit": limit})
        response.raise_for_status()
        data = response.json()

        if json_output:
            click.echo(json.dumps(data, indent=2))
        else:
            click.echo(f"Total hosts: {data.get('total_hosts', 0)}")
            click.echo(f"Total records: {data.get('total_records', 0)}")

            click.echo("\nTop services:")
            for item in data.get("top_services", []):
                click.echo(f"  {item['service']}: {item['count']}")

            click.echo("\nTop countries:")
            for item in data.get("top_countries", []):
                click.echo(f"  {item['country']}: {item['count']}")

            click.echo("\nTop ports:")
            for item in data.get("top_ports", []):
                click.echo(f"  {item['port']}: {item['count']}")

    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--range", "-r", required=True, help="IP range (CIDR notation)")
@click.option("--ports", "-p", default="22,80,443", help="Ports to scan")
@click.option("--rate", default=10000, help="Masscan rate")
@click.option("--nmap/--no-nmap", default=True, help="Use Nmap for service detection")
@click.option("--nmap-max", default=100, help="Max hosts for Nmap")
@click.option("--store/--no-store", default=True, help="Store results in database")
def scan(range: str, ports: str, rate: int, nmap: bool, nmap_max: int, store: bool):
    """Run a scan on an IP range.

    Examples:
        nodan scan --range 192.168.1.0/24 --ports 22,80,443
        nodan scan --range 10.0.0.0/8 --ports 22,80,443,8080 --rate 50000
    """
    config = load_config()

    click.echo(f"[*] Starting scan of {range}:{ports}")

    scanner_config = config.get("scanner", {})
    scanner = Scanner(
        masscan_config=scanner_config.get("masscan"),
        nmap_config=scanner_config.get("nmap")
    )

    deps = scanner.check_dependencies()
    if not deps.get("masscan"):
        click.echo("[!] Error: Masscan not found. Please install it.", err=True)
        sys.exit(1)

    if nmap and not deps.get("nmap"):
        click.echo("[!] Warning: Nmap not found. Falling back to Masscan only.", err=True)
        nmap = False

    try:
        results = scanner.scan(targets=range, ports=ports, use_nmap=nmap, nmap_max_hosts=nmap_max)

        if not results:
            click.echo("[*] No open ports found")
            return

        click.echo(f"[*] Found {len(results)} open ports")

        geo_config = config.get("geolocation", {})
        try:
            enricher = GeoEnricher(
                city_db_path=geo_config.get("city_db"),
                asn_db_path=geo_config.get("asn_db")
            )

            for result in results:
                result_dict = result.to_dict() if hasattr(result, 'to_dict') else result
                result_dict = enricher.enrich_result(result_dict)

                if store:
                    result_dict["ip"] = result.get("ip")
                    result_dict["port"] = result.get("port")

            enricher.close()
        except Exception as e:
            click.echo(f"[!] Warning: Could not enrich with geolocation: {e}")

        if store:
            es_config = config.get("database", {}).get("elasticsearch", {})
            try:
                db = ElasticsearchClient(
                    hosts=es_config.get("hosts", ["http://localhost:9200"]),
                    index=es_config.get("index", "nodan"),
                    username=es_config.get("username") or None,
                    password=es_config.get("password") or None
                )

                results_to_store = []
                for result in results:
                    result_dict = result.to_dict() if hasattr(result, 'to_dict') else result
                    results_to_store.append(result_dict)

                success, errors = db.bulk_index(results_to_store)
                click.echo(f"[*] Indexed {success} results in database")
                if errors:
                    click.echo(f"[!] {errors} errors during indexing")

                db.close()
            except Exception as e:
                click.echo(f"[!] Warning: Could not store in database: {e}")

        click.echo("\nResults:")
        for result in results[:20]:
            result_dict = result.to_dict() if hasattr(result, 'to_dict') else result
            click.echo(f"  {result_dict['ip']}:{result_dict['port']} ({result_dict['service']})")

        if len(results) > 20:
            click.echo(f"  ... and {len(results) - 20} more")

    except Exception as e:
        click.echo(f"[!] Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
