"""Data validators for input validation."""

import re
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse


def validate_url(url: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a URL.
    
    Args:
        url: URL string to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not url:
        return False, "URL is required"
    
    if not url.strip():
        return False, "URL cannot be empty"
    
    try:
        result = urlparse(url)
        
        # Check scheme
        if result.scheme not in ("http", "https"):
            return False, "URL must start with http:// or https://"
        
        # Check netloc (domain)
        if not result.netloc:
            return False, "URL must have a valid domain"
        
        return True, None
        
    except Exception as e:
        return False, f"Invalid URL: {e}"


def validate_port(port: int) -> Tuple[bool, Optional[str]]:
    """
    Validate a port number.
    
    Args:
        port: Port number to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(port, int):
        return False, "Port must be a number"
    
    if port < 1 or port > 65535:
        return False, "Port must be between 1 and 65535"
    
    return True, None


def validate_file_path(
    path: str,
    must_exist: bool = False,
    allowed_extensions: Optional[list[str]] = None
) -> Tuple[bool, Optional[str]]:
    """
    Validate a file path.
    
    Args:
        path: File path to validate
        must_exist: Whether the file must exist
        allowed_extensions: List of allowed extensions (e.g., [".json", ".yaml"])
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not path:
        return False, "Path is required"
    
    try:
        p = Path(path)
        
        # Check existence if required
        if must_exist and not p.exists():
            return False, f"File does not exist: {path}"
        
        # Check extension if specified
        if allowed_extensions:
            ext = p.suffix.lower()
            if ext not in [e.lower() for e in allowed_extensions]:
                return False, f"Invalid file extension. Allowed: {', '.join(allowed_extensions)}"
        
        # Check if parent directory exists or can be created
        if not must_exist and not p.parent.exists():
            try:
                p.parent.mkdir(parents=True, exist_ok=True)
            except Exception:
                return False, f"Cannot create directory: {p.parent}"
        
        return True, None
        
    except Exception as e:
        return False, f"Invalid path: {e}"


def validate_proxy_host(host: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a proxy host.
    
    Args:
        host: Host string (IP or domain)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not host:
        return False, "Host is required"
    
    # Check for valid IP address
    ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if re.match(ip_pattern, host):
        # Validate IP octets
        octets = host.split('.')
        for octet in octets:
            if int(octet) > 255:
                return False, "Invalid IP address"
        return True, None
    
    # Check for valid hostname
    hostname_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*$'
    if re.match(hostname_pattern, host):
        return True, None
    
    return False, "Invalid host format"


def validate_positive_int(
    value: int,
    name: str = "Value",
    min_value: int = 1,
    max_value: Optional[int] = None
) -> Tuple[bool, Optional[str]]:
    """
    Validate a positive integer.
    
    Args:
        value: Integer to validate
        name: Name for error messages
        min_value: Minimum allowed value
        max_value: Maximum allowed value (optional)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(value, int):
        return False, f"{name} must be an integer"
    
    if value < min_value:
        return False, f"{name} must be at least {min_value}"
    
    if max_value is not None and value > max_value:
        return False, f"{name} must be at most {max_value}"
    
    return True, None


def validate_selector(selector: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a CSS selector (basic check).
    
    Args:
        selector: CSS selector string
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not selector:
        return False, "Selector is required"
    
    if not selector.strip():
        return False, "Selector cannot be empty"
    
    # Basic check for common invalid patterns
    invalid_patterns = [
        (r'^\s', "Selector cannot start with whitespace"),
        (r'\s$', "Selector cannot end with whitespace"),
    ]
    
    for pattern, message in invalid_patterns:
        if re.search(pattern, selector):
            return False, message
    
    return True, None


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing invalid characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove invalid characters
    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, '_', filename)
    
    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip(' .')
    
    # Limit length
    max_length = 200
    if len(sanitized) > max_length:
        name, ext = sanitized.rsplit('.', 1) if '.' in sanitized else (sanitized, '')
        name = name[:max_length - len(ext) - 1]
        sanitized = f"{name}.{ext}" if ext else name
    
    return sanitized or "unnamed"
