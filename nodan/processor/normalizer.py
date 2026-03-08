"""Banner normalization for service detection."""

import re
from typing import Optional


class BannerNormalizer:
    """Normalize service banners and detect technology."""

    SERVICE_PATTERNS = {
        "ssh": [
            r"OpenSSH",
            r"SSH",
            r"dropbear",
        ],
        "http": [
            r"Apache",
            r"Nginx",
            r"Microsoft-IIS",
            r"lighttpd",
            r"Caddy",
        ],
        "https": [
            r"OpenSSL",
            r"nginx",
            r"Apache",
        ],
        "ftp": [
            r"ProFTPD",
            r"vsftpd",
            r"FileZilla",
            r"Microsoft FTP",
        ],
        "smtp": [
            r"Postfix",
            r"Exim",
            r"Microsoft ESMTP",
            r"Sendmail",
        ],
        "mysql": [
            r"MySQL",
            r"MariaDB",
        ],
        "postgresql": [
            r"PostgreSQL",
        ],
        "redis": [
            r"Redis",
        ],
        "mongodb": [
            r"MongoDB",
        ],
        "dns": [
            r"dnsmasq",
            r"BIND",
        ],
        "telnet": [
            r"Telnet",
        ],
        "rdp": [
            r"Windows terminal server",
        ],
    }

    VERSION_PATTERNS = [
        r"(\d+\.\d+[\.\d]*)",
        r"version (\d+[\.\d]*)",
    ]

    @classmethod
    def normalize_service(cls, banner: Optional[str]) -> str:
        """
        Detect service type from banner.

        Args:
            banner: Service banner string

        Returns:
            Normalized service name
        """
        if not banner:
            return "unknown"

        banner_lower = banner.lower()

        for service, patterns in cls.SERVICE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, banner, re.IGNORECASE):
                    return service

        return "unknown"

    @classmethod
    def normalize_banner(cls, banner: Optional[str]) -> str:
        """
        Clean and normalize banner string.

        Args:
            banner: Raw banner string

        Returns:
            Cleaned banner
        """
        if not banner:
            return ""

        banner = banner.strip()
        banner = re.sub(r'\s+', ' ', banner)

        return banner

    @classmethod
    def extract_version(cls, banner: Optional[str]) -> Optional[str]:
        """
        Extract version number from banner.

        Args:
            banner: Service banner

        Returns:
            Version string or None
        """
        if not banner:
            return None

        for pattern in cls.VERSION_PATTERNS:
            match = re.search(pattern, banner)
            if match:
                return match.group(1)

        return None

    @classmethod
    def detect_technology(cls, banner: Optional[str]) -> list[str]:
        """
        Detect technologies from banner.

        Args:
            banner: Service banner

        Returns:
            List of detected technologies
        """
        technologies = []

        if not banner:
            return technologies

        tech_map = {
            "OpenSSH": "OpenSSH",
            "OpenSSL": "OpenSSL",
            "Apache": "Apache",
            "Nginx": "Nginx",
            "Microsoft-IIS": "IIS",
            "lighttpd": "lighttpd",
            "Caddy": "Caddy",
            "ProFTPD": "ProFTPD",
            "vsftpd": "vsftpd",
            "Postfix": "Postfix",
            "Exim": "Exim",
            "MySQL": "MySQL",
            "MariaDB": "MariaDB",
            "PostgreSQL": "PostgreSQL",
            "Redis": "Redis",
            "MongoDB": "MongoDB",
            "dnsmasq": "dnsmasq",
            "BIND": "BIND",
        }

        for pattern, tech in tech_map.items():
            if pattern.lower() in banner.lower():
                technologies.append(tech)

        return list(set(technologies))
