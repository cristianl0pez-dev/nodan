"""Masscan scanner wrapper for high-speed port scanning."""

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class MasscanResult:
    """Represents a Masscan scan result."""
    ip: str
    port: int
    protocol: str
    timestamp: str


class MasscanScanner:
    """Wrapper for Masscan port scanner."""

    def __init__(
        self,
        rate: int = 10000,
        wait: int = 10,
        retries: int = 3,
        binary_path: str = "masscan"
    ):
        """
        Initialize Masscan scanner.

        Args:
            rate: Packets per second rate
            wait: Seconds to wait after scan
            retries: Number of retries
            binary_path: Path to masscan binary
        """
        self.rate = rate
        self.wait = wait
        self.retries = retries
        self.binary_path = binary_path

    def scan(
        self,
        targets: str,
        ports: str,
        output_format: str = "json"
    ) -> list[MasscanResult]:
        """
        Scan IP ranges for open ports.

        Args:
            targets: IP range (e.g., "192.168.1.0/24")
            ports: Port range (e.g., "22,80,443" or "1-1000")
            output_format: Output format (json, xml, etc.)

        Returns:
            List of MasscanResult objects
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_file = f.name

        try:
            cmd = [
                self.binary_path,
                "-p", ports,
                "--rate", str(self.rate),
                "-oJ", output_file,
                "-w", str(self.wait),
                "--retries", str(self.retries),
                targets
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.wait + 60
            )

            if result.returncode not in (0, 1):
                raise RuntimeError(f"Masscan error: {result.stderr}")

            return self._parse_output(output_file)

        except FileNotFoundError:
            raise RuntimeError(
                f"Masscan not found at {self.binary_path}. "
                "Please install masscan: sudo apt-get install masscan"
            )
        finally:
            try:
                Path(output_file).unlink(missing_ok=True)
            except Exception:
                pass

    def _parse_output(self, output_file: str) -> list[MasscanResult]:
        """Parse Masscan JSON output."""
        results = []

        try:
            with open(output_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        if data.get("ip") and data.get("ports"):
                            for port_info in data.get("ports", []):
                                results.append(MasscanResult(
                                    ip=data["ip"],
                                    port=port_info.get("port", 0),
                                    protocol=port_info.get("proto", "tcp"),
                                    timestamp=data.get("timestamp", "")
                                ))
                    except json.JSONDecodeError:
                        continue
        except FileNotFoundError:
            pass

        return results

    def get_available(self) -> bool:
        """Check if masscan is available."""
        try:
            result = subprocess.run(
                [self.binary_path, "--version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
