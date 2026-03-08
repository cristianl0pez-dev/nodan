"""Parser for scan results."""

import json
from typing import Optional
from dataclasses import asdict
from datetime import datetime, timezone


class ResultParser:
    """Parser for various scan output formats."""

    @staticmethod
    def parse_masscan_output(output: str) -> list[dict]:
        """
        Parse Masscan JSON output.

        Args:
            output: Raw Masscan JSON output

        Returns:
            List of parsed results
        """
        results = []

        for line in output.strip().split('\n'):
            if not line:
                continue
            try:
                data = json.loads(line)
                if "ip" in data and "ports" in data:
                    for port in data.get("ports", []):
                        results.append({
                            "ip": data["ip"],
                            "port": port.get("port"),
                            "protocol": port.get("proto", "tcp"),
                            "timestamp": data.get("timestamp", "")
                        })
            except json.JSONDecodeError:
                continue

        return results

    @staticmethod
    def parse_nmap_output(output: str) -> list[dict]:
        """
        Parse Nmap XML output.

        Args:
            output: Raw Nmap XML output

        Returns:
            List of parsed results
        """
        results = []

        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(output)

            for host in root.findall(".//host"):
                ip = host.find("address")
                if ip is None:
                    continue
                ip_addr = ip.get("addr")

                for port in host.findall(".//port"):
                    port_id = port.get("portid")
                    protocol = port.get("protocol")

                    state = port.find("state")
                    if state is None or state.get("state") != "open":
                        continue

                    service = port.find("service")
                    if service is not None:
                        results.append({
                            "ip": ip_addr,
                            "port": int(port_id),
                            "protocol": protocol,
                            "service": service.get("name"),
                            "product": service.get("product"),
                            "version": service.get("version"),
                            "banner": service.get("extrainfo")
                        })
                    else:
                        results.append({
                            "ip": ip_addr,
                            "port": int(port_id),
                            "protocol": protocol,
                            "service": "unknown"
                        })

        except Exception:
            pass

        return results

    @staticmethod
    def normalize_timestamp(timestamp: str) -> str:
        """
        Normalize timestamp to ISO 8601 format.

        Args:
            timestamp: Input timestamp

        Returns:
            ISO 8601 formatted timestamp
        """
        if not timestamp:
            return datetime.now(timezone.utc).isoformat()

        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return dt.isoformat()
        except Exception:
            return datetime.now(timezone.utc).isoformat()
