"""Unified scanner interface combining Masscan and Nmap."""

import json
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass, asdict

from nodan.scanner.masscan import MasscanScanner, MasscanResult
from nodan.scanner.nmap import NmapScanner, NmapResult


@dataclass
class ScanResult:
    """Combined scan result with all available information."""
    ip: str
    port: int
    protocol: str
    service: str
    banner: Optional[str] = None
    country: Optional[str] = None
    asn: Optional[str] = None
    org: Optional[str] = None
    timestamp: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


class Scanner:
    """
    Unified scanner that combines Masscan and Nmap.

    Masscan: Fast port scanning
    Nmap: Service detection and banner grabbing
    """

    def __init__(
        self,
        masscan_config: Optional[dict] = None,
        nmap_config: Optional[dict] = None
    ):
        """
        Initialize the scanner.

        Args:
            masscan_config: Configuration for Masscan
            nmap_config: Configuration for Nmap
        """
        mc_config = masscan_config or {}
        nm_config = nmap_config or {}

        self.masscan = MasscanScanner(
            rate=mc_config.get("rate", 10000),
            wait=mc_config.get("wait", 10),
            retries=mc_config.get("retries", 3),
            binary_path=mc_config.get("binary_path", "/usr/bin/masscan")
        )

        self.nmap = NmapScanner(
            timing=nm_config.get("timing", "T4"),
            scripts=nm_config.get("scripts", "default,banner"),
            timeout=int(nm_config.get("timeout", "30s").rstrip("s"))
        )

    def scan(
        self,
        targets: str,
        ports: str,
        use_nmap: bool = True,
        nmap_max_hosts: int = 100
    ) -> list[ScanResult]:
        """
        Perform a complete scan of the target range.

        Args:
            targets: IP range (e.g., "192.168.1.0/24")
            ports: Ports to scan (e.g., "22,80,443")
            use_nmap: Whether to run Nmap for service detection
            nmap_max_hosts: Maximum hosts for Nmap scanning

        Returns:
            List of ScanResult objects
        """
        print(f"[+] Running Masscan on {targets}:{ports}...")
        masscan_results = self.masscan.scan(targets, ports)

        if not masscan_results:
            print("[-] No open ports found")
            return []

        print(f"[+] Found {len(masscan_results)} open ports")

        if not use_nmap:
            return self._masscan_to_results(masscan_results)

        print(f"[+] Running Nmap on up to {nmap_max_hosts} hosts...")
        nmap_results = self.nmap.scan_from_masscan_results(
            masscan_results,
            max_hosts=nmap_max_hosts
        )

        print(f"[+] Nmap identified {len(nmap_results)} services")

        return self._merge_results(masscan_results, nmap_results)

    def quick_scan(self, targets: str, ports: str) -> list[ScanResult]:
        """
        Quick scan using only Masscan (no Nmap).

        Args:
            targets: IP range
            ports: Ports to scan

        Returns:
            List of ScanResult objects
        """
        return self.scan(targets, ports, use_nmap=False)

    def _masscan_to_results(self, masscan_results: list[MasscanResult]) -> list[ScanResult]:
        """Convert Masscan results to ScanResult."""
        timestamp = datetime.now(timezone.utc).isoformat()
        results = []

        service_map = {
            22: "ssh",
            80: "http",
            443: "https",
            21: "ftp",
            25: "smtp",
            53: "dns",
            3306: "mysql",
            5432: "postgresql",
            6379: "redis",
            27017: "mongodb",
        }

        for mr in masscan_results:
            results.append(ScanResult(
                ip=mr.ip,
                port=mr.port,
                protocol=mr.protocol,
                service=service_map.get(mr.port, "unknown"),
                timestamp=timestamp
            ))

        return results

    def _merge_results(
        self,
        masscan_results: list[MasscanResult],
        nmap_results: list[NmapResult]
    ) -> list[ScanResult]:
        """Merge Masscan and Nmap results."""
        timestamp = datetime.now(timezone.utc).isoformat()

        nmap_by_host_port = {
            (r.ip, r.port): r for r in nmap_results
        }

        results = []
        for mr in masscan_results:
            key = (mr.ip, mr.port)
            nmap_result = nmap_by_host_port.get(key)

            if nmap_result:
                results.append(ScanResult(
                    ip=mr.ip,
                    port=mr.port,
                    protocol=mr.protocol,
                    service=nmap_result.service,
                    banner=nmap_result.banner,
                    timestamp=timestamp
                ))
            else:
                results.append(ScanResult(
                    ip=mr.ip,
                    port=mr.port,
                    protocol=mr.protocol,
                    service="unknown",
                    timestamp=timestamp
                ))

        return results

    def check_dependencies(self) -> dict:
        """Check if required dependencies are available."""
        return {
            "masscan": self.masscan.get_available(),
            "nmap": self.nmap.get_available()
        }
