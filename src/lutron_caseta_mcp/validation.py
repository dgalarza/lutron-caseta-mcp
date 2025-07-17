#!/usr/bin/env python3
"""Input validation utilities for Lutron Caseta MCP Server"""

import ipaddress
import os
import tempfile
from pathlib import Path


class ValidationError(ValueError):
    """Custom validation error for input validation failures"""

    pass


def validate_host_ip(host: str) -> str:
    """
    Validate host IP address format.

    Args:
        host: Host IP address to validate

    Returns:
        Validated IP address string

    Raises:
        ValidationError: If host IP is invalid
    """
    if not host or not host.strip():
        raise ValidationError("Host IP cannot be empty")

    host = host.strip()

    try:
        ipaddress.ip_address(host)
    except ValueError as e:
        raise ValidationError(f"Invalid IP address format: {host}") from e

    return host


def validate_device_level(level: int) -> int:
    """
    Validate device level value (0-100).

    Args:
        level: Device level to validate

    Returns:
        Validated level as integer

    Raises:
        ValidationError: If level is invalid
    """
    if not isinstance(level, int):
        raise ValidationError(f"Device level must be an integer, got {type(level).__name__}")

    if not 0 <= level <= 100:
        raise ValidationError(f"Device level must be between 0 and 100, got {level}")

    return level


def validate_domain(domain: str) -> str:
    """
    Validate device domain for Lutron Caseta devices.

    Args:
        domain: Device domain to validate

    Returns:
        Validated domain string

    Raises:
        ValidationError: If domain is invalid
    """
    if not domain or not domain.strip():
        raise ValidationError("Domain cannot be empty")

    domain = domain.strip().lower()

    # Valid domains for Lutron Caseta devices
    valid_domains = {"light", "switch", "cover", "sensor", "fan"}

    if domain not in valid_domains:
        raise ValidationError(
            f"Invalid domain '{domain}'. Valid domains are: {', '.join(sorted(valid_domains))}"
        )

    return domain


def validate_cert_directory(cert_dir: str) -> str:
    """
    Validate certificate directory path for security.

    Args:
        cert_dir: Certificate directory path to validate

    Returns:
        Validated and normalized directory path

    Raises:
        ValidationError: If directory path is invalid or unsafe
    """
    if not cert_dir or not cert_dir.strip():
        raise ValidationError("Certificate directory cannot be empty")

    try:
        # Expand user path and resolve to absolute path
        cert_dir_path = Path(cert_dir).expanduser().resolve()

        # Security check: ensure it's within safe locations
        home_dir = Path.home().resolve()
        tmp_dir = Path(tempfile.gettempdir()).resolve()

        if not (cert_dir_path.is_relative_to(home_dir) or cert_dir_path.is_relative_to(tmp_dir)):
            raise ValidationError(
                f"Certificate directory must be within home directory or temp directory: {cert_dir_path}"
            )

        return str(cert_dir_path)

    except (OSError, ValueError) as e:
        raise ValidationError(f"Invalid certificate directory path: {cert_dir}") from e


def validate_environment_variable(var_name: str, required: bool = False) -> str | None:
    """
    Validate environment variable value.

    Args:
        var_name: Environment variable name
        required: Whether the variable is required

    Returns:
        Environment variable value or None if not set and not required

    Raises:
        ValidationError: If required variable is missing or invalid
    """
    if not var_name or not var_name.strip():
        raise ValidationError("Environment variable name cannot be empty")

    value = os.getenv(var_name)

    if value is None:
        if required:
            raise ValidationError(f"Required environment variable not set: {var_name}")
        return None

    value = value.strip()

    if not value and required:
        raise ValidationError(f"Required environment variable cannot be empty: {var_name}")

    return value if value else None
