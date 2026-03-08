"""Nmap scanner wrapper for service detection and banner grabbing."""

import nmap
import json
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class NmapResult:
    """Represents an Nmap scan result."""
    ip: str
    port: int
    protocol: str
    state: str
    service: str
    product: Optional[str] = None
    version: Optional[str] = None
    banner: Optional[str] = None
    extrainfo: Optional[str] = None


class NmapScanner:
    """Wrapper for Nmap service detection."""

    def __init__(
        self,
        timing: str = "T4",
        scripts: str = "default,banner",
        timeout: int = 30,
        binary_path: str = "nmap"
    ):
        """
        Initialize Nmap scanner.

        Args:
            timing: Timing template (T0-T5)
            scripts: Nmap scripts to run
            timeout: Scan timeout in seconds
            binary_path: Path to nmap binary
        """
        self.timing = timing
        self.scripts = scripts
        self.timeout = timeout
        self.binary_path = binary_path
        self._nm = nmap.PortScanner()

    def scan(
        self,
        hosts: str,
        ports: str = "1-1000",
        arguments: Optional[str] = None
    ) -> list[NmapResult]:
        """
        Scan hosts for services and grab banners.

        Args:
            hosts: Host or IP range (e.g., "192.168.1.1" or "192.168.1.0/24")
            ports: Port range (e.g., "22,80,443" or "1-1000")
            arguments: Additional nmap arguments

        Returns:
            List of NmapResult objects
        """
        if arguments is None:
            arguments = f"-{self.timing} -sV --script {self.scripts}"

        scan_args = f"-p {ports} {arguments}"

        self._nm.scan(
            hosts=hosts,
            ports=ports,
            arguments=scan_args,
            timeout=self.timeout
        )

        return self._parse_results(hosts)

    def scan_from_masscan_results(
        self,
        masscan_results: list,
        max_hosts: int = 100
    ) -> list[NmapResult]:
        """
        Run Nmap scan on hosts found by Masscan.

        Args:
            masscan_results: List of MasscanResult objects
            max_hosts: Maximum hosts to scan with Nmap

        Returns:
            List of NmapResult objects
        """
        unique_ips = list(set(r.ip for r in masscan_results))[:max_hosts]

        if not unique_ips:
            return []

        hosts_str = ",".join(unique_ips)
        ports = ",".join(str(r.port) for r in masscan_results if r.ip in unique_ips)

        return self.scan(hosts_str, ports)

    def _parse_results(self, hosts_pattern: str) -> list[NmapResult]:
        """Parse Nmap scan results."""
        results = []

        for host in self._nm.all_hosts():
            if self._nm[host].state() != "up":
                continue

            for proto in self._nm[host].all_protocols():
                ports = self._nm[host][proto].keys()

                for port in ports:
                    port_info = self._nm[host][proto][port]
                    state = port_info.get("state", "")

                    if state != "open":
                        continue

                    service = port_info.get("name", "unknown")
                    product = port_info.get("product")
                    version = port_info.get("version")
                    extrainfo = port_info.get("extrainfo")

                    banner = self._build_banner(port_info)

                    results.append(NmapResult(
                        ip=host,
                        port=port,
                        protocol=proto,
                        state=state,
                        service=service,
                        product=product,
                        version=version,
                        banner=banner,
                        extrainfo=extrainfo
                    ))

        return results

    def _build_banner(self, port_info: dict) -> Optional[str]:
        """Build banner string from port info."""
        banner_parts = []

        if port_info.get("product"):
            banner_parts.append(port_info["product"])

        if port_info.get("version"):
            banner_parts.append(port_info["version"])

        if port_info.get("extrainfo"):
            banner_parts.append(f"({port_info['extrainfo']})")

        if banner_parts:
            return " ".join(banner_parts)

        if port_info.get("name"):
            return port_info["name"]

        return None

    def get_available(self) -> bool:
        """Check if nmap is available."""
        try:
            return self._nm.nmap_version().get("version") is not None
        except Exception:
            return False
