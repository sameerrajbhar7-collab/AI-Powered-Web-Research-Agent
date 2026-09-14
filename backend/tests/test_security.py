import pytest
from app.core.security import is_safe_url, is_private_ip, should_block_resource


def test_private_ip_detection():
    assert is_private_ip("127.0.0.1") is True
    assert is_private_ip("10.0.0.1") is True
    assert is_private_ip("192.168.1.1") is True
    assert is_private_ip("172.16.0.1") is True
    assert is_private_ip("169.254.169.254") is True
    assert is_private_ip("8.8.8.8") is False
    assert is_private_ip("1.1.1.1") is False


def test_safe_url_validation():
    # Dangerous schemes
    safe, msg = is_safe_url("file:///etc/passwd")
    assert safe is False
    assert "scheme" in msg.lower()

    safe, msg = is_safe_url("javascript:alert(1)")
    assert safe is False

    # SSRF hostnames
    safe, msg = is_safe_url("http://localhost/admin")
    assert safe is False
    assert "restricted hostname" in msg.lower()

    safe, msg = is_safe_url("http://127.0.0.1:8000/secret")
    assert safe is False

    # Blocklisted domains
    safe, msg = is_safe_url("https://doubleclick.net/ad")
    assert safe is False
    assert "tracker/ad blocklist" in msg.lower()

    # Valid public domain
    safe, msg = is_safe_url("https://en.wikipedia.org/wiki/Artificial_intelligence")
    assert safe is True


def test_should_block_resource():
    assert should_block_resource("https://example.com/banner.png", "image") is True
    assert should_block_resource("https://example.com/video.mp4", "media") is True
    assert should_block_resource("https://example.com/font.woff2", "font") is True
    assert should_block_resource("https://example.com/article", "document") is False
