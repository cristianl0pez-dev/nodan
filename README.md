# Nodan - Internet-wide Device Search Engine

[Nodan](https://github.com/nodan/nodan) is a network scanning and search system inspired by [Shodan](https://www.shodan.io/). It scans IP ranges, detects open ports and services, stores the results, and provides a REST API and CLI for searching through the collected data.

## Features

- **High-speed port scanning** using Masscan
- **Service detection** using Nmap
- **Geolocation enrichment** with MaxMind GeoIP
- **REST API** with Shodan-like query syntax
- **CLI client** for easy interaction
- **Elasticsearch** backend for fast searching

## Architecture

```
nodan/
├── scanner/       # Port scanning (Masscan, Nmap)
├── processor/    # Data processing & enrichment
├── database/     # Elasticsearch storage
├── api/          # FastAPI REST API
├── cli/          # Command-line interface
└── config/       # Configuration
```

## Quick Start

### Using Docker (Recommended)

```bash
# Start services
docker-compose up -d

# Wait for Elasticsearch to be ready
docker-compose logs -f elasticsearch

# Run a scan
docker exec nodan-api nodan scan --range 192.168.1.0/24 --ports 22,80,443

# Search via CLI
docker exec nodan-api nodan search "port:22 country:US"

# Or use the API
curl "http://localhost:8000/search?q=port:22"
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Install system tools
sudo apt-get install masscan nmap

# Download MaxMind GeoIP database
mkdir -p data && cd data
wget https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-City&license_key=YOUR_LICENSE_KEY -O GeoLite2-City.tar.gz
wget https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-ASN&license_key=YOUR_LICENSE_KEY -O GeoLite2-ASN.tar.gz
tar -xzf GeoLite2-City.tar.gz
tar -xzf GeoLite2-ASN.tar.gz

# Update config/config.yaml with your paths

# Start Elasticsearch
docker run -d -p 9200:9200 -e discovery.type=single-node elasticsearch:8.11.0

# Run the API
python -m nodan.api.main

# In another terminal, run the CLI
nodan search "port:22"
```

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/nodan/nodan.git
cd nodan

# Create virtual environment (optional)
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install nodan CLI
pip install -e .
```

## Configuration

Edit `config/config.yaml`:

```yaml
scanner:
  masscan:
    rate: 10000
    wait: 10
    retries: 3
  nmap:
    timing: T4
    scripts: default,banner
    timeout: 30s

database:
  elasticsearch:
    hosts:
      - http://localhost:9200
    index: nodan
    username: ""
    password: ""

geolocation:
  city_db: data/GeoLite2-City/GeoLite2-City.mmdb
  asn_db: data/GeoLite2-ASN/GeoLite2-ASN.mmdb

api:
  host: 0.0.0.0
  port: 8000
  title: "Nodan API"
  version: "1.0.0"

cli:
  api_url: http://localhost:8000
  default_limit: 100
  max_limit: 1000
```

## CLI Usage

### Search

```bash
# Search for SSH servers
nodan search "port:22"

# Search for HTTP servers in the US
nodan search "port:80 country:US"

# Search for Nginx servers
nodan search "service:nginx"

# Search with filters
nodan search "port:443 service:https org:Google"

# JSON output
nodan search "port:22" --json
```

### Host Information

```bash
# Get host details
nodan host 8.8.8.8

# Include scan history
nodan host 8.8.8.8 --history

# JSON output
nodan host 8.8.8.8 --json
```

### Statistics

```bash
# View statistics
nodan stats

# Custom top limit
nodan stats --limit 20

# JSON output
nodan stats --json
```

### Running Scans

```bash
# Basic scan
nodan scan --range 192.168.1.0/24 --ports 22,80,443

# High-speed scan
nodan scan --range 10.0.0.0/8 --ports 22,80,443,8080 --rate 50000

# Masscan only (no Nmap)
nodan scan --range 192.168.1.0/24 --ports 22,80,443 --no-nmap

# Scan without storing results
nodan scan --range 192.168.1.0/24 --ports 22,80,443 --no-store
```

## API Endpoints

### GET /search

Search for devices by query.

```bash
# Basic search
curl "http://localhost:8000/search?q=port:22"

# With pagination
curl "http://localhost:8000/search?q=port:22&limit=10&offset=0"

# Country filter
curl "http://localhost:8000/search?q=country:US"

# Service filter
curl "http://localhost:8000/search?q=service:nginx"
```

Query syntax:
- `port:22` - specific port
- `country:US` - country code
- `service:ssh` - service name
- `ip:1.2.3.4` - specific IP
- `asn:AS15169` - ASN
- `org:"Google LLC"` - organization

### GET /host/{ip}

Get all information about a specific host.

```bash
curl "http://localhost:8000/host/8.8.8.8"

# With history
curl "http://localhost:8000/host/8.8.8.8?history=true"
```

### GET /stats

Get search statistics.

```bash
curl "http://localhost:8000/stats"

# Custom limit
curl "http://localhost:8000/stats?limit=20"
```

### GET /health

Check API health.

```bash
curl "http://localhost:8000/health"
```

## API Documentation

Interactive API docs available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Development

```bash
# Install development dependencies
pip install -r requirements.txt

# Run tests
pytest tests/

# Run with custom config
NODAN_CONFIG=/path/to/config.yaml python -m nodan.api.main
```

## Docker Development

```bash
# Build image
docker build -t nodan .

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Run tests in container
docker exec nodan-api pytest tests/

# Stop services
docker-compose down
```

## Output Format

Scan results are stored in Elasticsearch with the following structure:

```json
{
  "ip": "1.2.3.4",
  "port": 22,
  "protocol": "tcp",
  "service": "ssh",
  "banner": "OpenSSH 8.2",
  "country": "US",
  "asn": "AS15169",
  "org": "Google LLC",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## System Requirements

- Python 3.11+
- Masscan
- Nmap
- Elasticsearch 8.x (or Docker)

## License

MIT License

## Disclaimer

This tool is for educational and research purposes only. Always obtain proper authorization before scanning IP ranges that you don't own or have permission to scan.
