import ipaddress
import socket
from urllib.parse import urlparse
from app.core.config import settings
from app.core.logging_config import logger

# Blocklist of high-risk / spam / tracking domains
DOMAIN_BLOCKLIST = {
    "doubleclick.net",
    "google-analytics.com",
    "googletagmanager.com",
    "facebook.net",
    "adnxs.com",
    "scorecardresearch.com",
    "outbrain.com",
    "taboola.com",
}

# Blocked resource extensions during web research to optimize speed & safety
BLOCKED_RESOURCE_EXTENSIONS = (
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico",
    ".mp4", ".webm", ".avi", ".mov", ".mkv",
    ".mp3", ".wav", ".ogg",
    ".woff", ".woff2", ".ttf", ".eot",
    ".exe", ".zip", ".tar", ".gz", ".iso", ".dmg"
)


def is_private_ip(ip_str: str) -> bool:
    """Checks if an IP address belongs to private/loopback/link-local ranges."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_unspecified
        )
    except ValueError:
        return False


def is_safe_url(url: str) -> tuple[bool, str]:
    """
    Validates a URL against SSRF vulnerabilities, illegal schemes, and domain blocklists.
    Returns (is_safe: bool, reason: str).
    """
    if not url or not isinstance(url, str):
        return False, "Empty or invalid URL type"

    try:
        parsed = urlparse(url.strip())
    except Exception as e:
        return False, f"Malformed URL: {e}"

    # Only allow http and https schemes
    if parsed.scheme.lower() not in ("http", "https"):
        return False, f"Disallowed scheme: '{parsed.scheme}'. Only HTTP/HTTPS permitted."

    hostname = parsed.hostname
    if not hostname:
        return False, "URL does not contain a valid hostname."

    hostname_lower = hostname.lower()

    # Block localhost and local names
    if hostname_lower in ("localhost", "local", "127.0.0.1", "0.0.0.0", "::1"):
        return False, f"Restricted hostname '{hostname_lower}' (SSRF prevention)."

    # Domain blocklist check
    for blocked_domain in DOMAIN_BLOCKLIST:
        if hostname_lower == blocked_domain or hostname_lower.endswith(f".{blocked_domain}"):
            return False, f"Domain '{hostname_lower}' is in tracker/ad blocklist."

    # SSRF IP resolution check if enabled
    if settings.ENABLE_SSRF_PROTECTION:
        try:
            resolved_ips = socket.getaddrinfo(hostname, None)
            for item in resolved_ips:
                sockaddr = item[4]
                ip_str = sockaddr[0]
                if is_private_ip(ip_str):
                    logger.warning(f"[SafeBrowsing] Blocked private IP resolution: {hostname} -> {ip_str}")
                    return False, f"Host '{hostname}' resolves to private IP ({ip_str}) - blocked for SSRF safety."
        except socket.gaierror:
            # Domain could not be resolved
            return False, f"Host '{hostname}' could not be resolved."
        except Exception as e:
            logger.warning(f"[SafeBrowsing] Error checking IP safety for {hostname}: {e}")
            return False, f"Safety verification failed: {e}"

    return True, "OK"


def should_block_resource(url: str, resource_type: str) -> bool:
    """Determines whether a page sub-resource should be aborted to save bandwidth & latency."""
    if not settings.ENABLE_AD_BLOCKING:
        return False

    if resource_type in ("image", "media", "font", "stylesheet"):
        return True

    url_path = urlparse(url).path.lower()
    if url_path.endswith(BLOCKED_RESOURCE_EXTENSIONS):
        return True

    return False
