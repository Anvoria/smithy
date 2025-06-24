import hashlib
import urllib.parse
from typing import Literal, Optional
import ipaddress
import logging

from fastapi import Request

logger = logging.getLogger(__name__)


class AvatarUtils:
    """Utilities for generating and managing user avatars."""

    GRAVATAR_BASE_URL = "https://www.gravatar.com/avatar/"

    @staticmethod
    def get_gravatar_url(
        email: str,
        size: int = 200,
        default: Literal[
            "mp", "identicon", "monsterid", "wavatar", "retro", "robohash", "blank"
        ] = "mp",
        rating: Literal["g", "pg", "r", "x"] = "g",
        force_default: bool = False,
    ) -> str:
        """
        Generate a Gravatar URL for the given email address.

        :param email: User's email address.
        :param size: Size of the avatar in pixels (1-2048).
        :param default: Default avatar type if no Gravatar is found
        - options are 'mp', 'identicon', 'monsterid', 'wavatar', 'retro', 'robohash', 'blank'.
        :param rating: Gravatar rating - 'g', 'pg', 'r', 'x'.
        :param force_default: If True, forces the default avatar even if a Gravatar exists.
        :return: Full Gravatar URL.
        """
        normalized_email = email.strip().lower()

        email_hash = hashlib.md5(normalized_email.encode("utf-8")).hexdigest()

        # Build query parameters
        params = {
            "s": str(max(1, min(size, 2048))),  # Ensure size is between 1 and 2048
            "d": default,
            "r": rating,
        }

        if force_default:
            params["f"] = "y"

        # Construct the full URL with query parameters
        query_string = urllib.parse.urlencode(params)
        return f"{AvatarUtils.GRAVATAR_BASE_URL}{email_hash}?{query_string}"

    @staticmethod
    def get_gravatar_profile_url(email: str) -> str:
        """
        Get Gravatar profile URL for given email.
        :param email: User's email address.
        :return: Gravatar profile URL.
        """
        email_normalized = email.lower().strip()
        email_hash = hashlib.md5(email_normalized.encode("utf-8")).hexdigest()
        return f"https://www.gravatar.com/{email_hash}"


class RequestUtils:
    """Utilities for extracting information from HTTP requests"""

    # Headers to check for real client IP (in order of priority)
    IP_HEADERS = [
        "cf-connecting-ip",  # Cloudflare
        "x-real-ip",  # Nginx proxy
        "x-forwarded-for",  # Standard proxy header
        "x-client-ip",  # Some proxies
        "x-cluster-client-ip",  # Kubernetes ingress
        "forwarded-for",  # Less common
        "forwarded",  # RFC 7239
        "x-forwarded",  # Variation
    ]

    # Private IP ranges that should be ignored when behind proxies
    PRIVATE_RANGES = [
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
        ipaddress.ip_network("127.0.0.0/8"),
        ipaddress.ip_network("169.254.0.0/16"),  # Link-local
        ipaddress.ip_network("::1/128"),  # IPv6 loopback
        ipaddress.ip_network("fc00::/7"),  # IPv6 private
        ipaddress.ip_network("fe80::/10"),  # IPv6 link-local
    ]

    @classmethod
    def get_client_ip(cls, request: Request, trust_proxy: bool = True) -> str:
        """
        Extract the real client IP address from the request.

        :param request: FastAPI Request object
        :param trust_proxy: Whether to trust proxy headers
        :return: Client IP address as string
        """
        if not trust_proxy:
            # direct connection
            return cls._get_direct_ip(request)

        # Check proxy headers in order of preference
        for header_name in cls.IP_HEADERS:
            header_value = request.headers.get(header_name)
            if header_value:
                ip = cls._extract_first_valid_ip(header_value)
                if ip:
                    logger.debug(f"Found client IP {ip} from header {header_name}")
                    return ip

        # Fallback to direct connection IP
        direct_ip = cls._get_direct_ip(request)
        logger.debug(f"Using direct connection IP: {direct_ip}")
        return direct_ip

    @classmethod
    def get_user_agent(cls, request: Request) -> str:
        """
        Extract User-Agent from request.

        :param request: FastAPI Request object
        :return: User-Agent string or "unknown"
        """
        return request.headers.get("user-agent", "unknown")

    @classmethod
    def get_request_fingerprint(cls, request: Request) -> dict:
        """
        Create a request fingerprint for security/audit purposes.

        :param request: FastAPI Request object
        :return: Dictionary with request information
        """
        return {
            "ip": cls.get_client_ip(request),
            "user_agent": cls.get_user_agent(request),
            "method": request.method,
            "path": str(request.url.path),
            "host": request.headers.get("host", "unknown"),
            "referer": request.headers.get("referer"),
            "origin": request.headers.get("origin"),
            "accept_language": request.headers.get("accept-language"),
            "x_forwarded_proto": request.headers.get("x-forwarded-proto"),
            "cf_ray": request.headers.get("cf-ray"),
        }

    @classmethod
    def is_local_request(cls, request: Request) -> bool:
        """
        Check if request is coming from localhost/local network.

        :param request: FastAPI Request object
        :return: True if request is local
        """
        client_ip = cls.get_client_ip(request)
        try:
            ip_obj = ipaddress.ip_address(client_ip)
            return any(ip_obj in network for network in cls.PRIVATE_RANGES)
        except ValueError:
            logger.warning(f"Invalid IP address: {client_ip}")
            return False

    @classmethod
    def get_cloudflare_info(cls, request: Request) -> dict:
        """
        Extract Cloudflare-specific information if available.

        :param request: FastAPI Request object
        :return: Dictionary with Cloudflare information
        """
        return {
            "cf_ray": request.headers.get("cf-ray"),
            "cf_connecting_ip": request.headers.get("cf-connecting-ip"),
            "cf_country": request.headers.get("cf-ipcountry"),
            "cf_visitor": request.headers.get("cf-visitor"),
            "cf_cache_status": request.headers.get("cf-cache-status"),
        }

    # Private helper methods

    @classmethod
    def _get_direct_ip(cls, request: Request) -> str:
        """Get IP from direct connection"""
        if request.client:
            return request.client.host
        return "unknown"

    @classmethod
    def _extract_first_valid_ip(cls, header_value: str) -> Optional[str]:
        """
        Extract the first valid public IP from a header value.
        Handles comma-separated lists and validates IP addresses.

        :param header_value: Header value that may contain IP addresses
        :return: First valid public IP or None
        """
        if not header_value:
            return None

        # Handle comma-separated IPs (common in X-Forwarded-For)
        ips = [ip.strip() for ip in header_value.split(",")]

        for ip_str in ips:
            # Handle port numbers
            if ":" in ip_str and not cls._is_ipv6(ip_str):
                ip_str = ip_str.split(":")[0]

            # Remove any surrounding quotes or brackets
            ip_str = ip_str.strip("\"'[]")

            if cls._is_valid_public_ip(ip_str):
                return ip_str

        return None

    @classmethod
    def _is_valid_public_ip(cls, ip_str: str) -> bool:
        """
        Check if string is a valid public IP address.

        :param ip_str: IP address string
        :return: True if valid public IP
        """
        try:
            ip_obj = ipaddress.ip_address(ip_str)

            for network in cls.PRIVATE_RANGES:
                if ip_obj in network:
                    return False

            if ip_obj.is_multicast or ip_obj.is_reserved:
                return False

            return True

        except ValueError:
            return False

    @classmethod
    def _is_ipv6(cls, ip_str: str) -> bool:
        """Check if string looks like IPv6 address"""
        return "::" in ip_str or ip_str.count(":") >= 2


__all__ = [
    "AvatarUtils",
    "RequestUtils",
]
