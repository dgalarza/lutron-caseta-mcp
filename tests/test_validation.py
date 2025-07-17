"""Tests for input validation utilities"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from lutron_caseta_mcp.validation import (
    ValidationError,
    validate_cert_directory,
    validate_device_level,
    validate_domain,
    validate_environment_variable,
    validate_host_ip,
)


class TestValidateHostIP:
    """Test host IP validation"""

    def test_validate_host_ip_valid_ipv4(self):
        """Test valid IPv4 addresses"""
        valid_ips = ["192.168.1.1", "10.0.0.1", "127.0.0.1", "172.16.1.1"]
        for ip in valid_ips:
            result = validate_host_ip(ip)
            assert result == ip

    def test_validate_host_ip_valid_ipv6(self):
        """Test valid IPv6 addresses"""
        valid_ips = ["::1", "2001:db8::1", "fe80::1"]
        for ip in valid_ips:
            result = validate_host_ip(ip)
            assert result == ip

    def test_validate_host_ip_empty(self):
        """Test empty host IP"""
        with pytest.raises(ValidationError, match="Host IP cannot be empty"):
            validate_host_ip("")

    def test_validate_host_ip_whitespace(self):
        """Test whitespace-only host IP"""
        with pytest.raises(ValidationError, match="Host IP cannot be empty"):
            validate_host_ip("   ")

    def test_validate_host_ip_invalid_format(self):
        """Test invalid IP format"""
        invalid_ips = ["invalid", "192.168.1", "256.256.256.256", "not.an.ip"]
        for ip in invalid_ips:
            with pytest.raises(ValidationError, match="Invalid IP address format"):
                validate_host_ip(ip)

    def test_validate_host_ip_strips_whitespace(self):
        """Test that whitespace is stripped"""
        result = validate_host_ip("  192.168.1.1  ")
        assert result == "192.168.1.1"


class TestValidateDeviceLevel:
    """Test device level validation"""

    def test_validate_device_level_valid(self):
        """Test valid device levels"""
        valid_levels = [0, 1, 50, 99, 100]
        for level in valid_levels:
            result = validate_device_level(level)
            assert result == level

    def test_validate_device_level_invalid_type(self):
        """Test invalid type for device level"""
        invalid_types = ["50", 50.5, None, [50], {"level": 50}]
        for level in invalid_types:
            with pytest.raises(ValidationError, match="Device level must be an integer"):
                validate_device_level(level)

    def test_validate_device_level_out_of_range(self):
        """Test device level out of range"""
        invalid_levels = [-1, 101, 150, -50]
        for level in invalid_levels:
            with pytest.raises(ValidationError, match="Device level must be between 0 and 100"):
                validate_device_level(level)


class TestValidateDomain:
    """Test domain validation"""

    def test_validate_domain_valid(self):
        """Test valid domains"""
        valid_domains = ["light", "switch", "cover", "sensor", "fan"]
        for domain in valid_domains:
            result = validate_domain(domain)
            assert result == domain

    def test_validate_domain_case_insensitive(self):
        """Test domain validation is case insensitive"""
        test_cases = [
            ("Light", "light"),
            ("SWITCH", "switch"),
            ("Cover", "cover"),
            ("SENSOR", "sensor"),
            ("Fan", "fan"),
        ]
        for input_domain, expected in test_cases:
            result = validate_domain(input_domain)
            assert result == expected

    def test_validate_domain_strips_whitespace(self):
        """Test domain validation strips whitespace"""
        result = validate_domain("  light  ")
        assert result == "light"

    def test_validate_domain_empty(self):
        """Test empty domain"""
        with pytest.raises(ValidationError, match="Domain cannot be empty"):
            validate_domain("")

    def test_validate_domain_whitespace(self):
        """Test whitespace-only domain"""
        with pytest.raises(ValidationError, match="Domain cannot be empty"):
            validate_domain("   ")

    def test_validate_domain_invalid(self):
        """Test invalid domains"""
        invalid_domains = ["invalid", "lights", "switches", "unknown"]
        for domain in invalid_domains:
            with pytest.raises(ValidationError, match="Invalid domain"):
                validate_domain(domain)


class TestValidateCertDirectory:
    """Test certificate directory validation"""

    def test_validate_cert_directory_home_path(self):
        """Test valid path in home directory"""
        home_path = "~/test/certs"
        result = validate_cert_directory(home_path)
        expected = str(Path(home_path).expanduser().resolve())
        assert result == expected

    def test_validate_cert_directory_tmp_path(self):
        """Test valid path in temp directory"""
        tmp_path = os.path.join(tempfile.gettempdir(), "test/certs")
        result = validate_cert_directory(tmp_path)
        expected = str(Path(tmp_path).resolve())
        assert result == expected

    def test_validate_cert_directory_absolute_home(self):
        """Test absolute path in home directory"""
        home_dir = Path.home()
        test_path = home_dir / "test" / "certs"
        result = validate_cert_directory(str(test_path))
        assert result == str(test_path.resolve())

    def test_validate_cert_directory_empty(self):
        """Test empty directory path"""
        with pytest.raises(ValidationError, match="Certificate directory cannot be empty"):
            validate_cert_directory("")

    def test_validate_cert_directory_whitespace(self):
        """Test whitespace-only directory path"""
        with pytest.raises(ValidationError, match="Certificate directory cannot be empty"):
            validate_cert_directory("   ")

    def test_validate_cert_directory_invalid_path(self):
        """Test path outside allowed locations"""
        invalid_paths = ["/etc/ssl", "/var/lib/certs", "/root/certs"]
        for path in invalid_paths:
            with pytest.raises(ValidationError, match="Invalid certificate directory path"):
                validate_cert_directory(path)


class TestValidateEnvironmentVariable:
    """Test environment variable validation"""

    def test_validate_environment_variable_exists(self):
        """Test existing environment variable"""
        with patch.dict(os.environ, {"TEST_VAR": "test_value"}):
            result = validate_environment_variable("TEST_VAR")
            assert result == "test_value"

    def test_validate_environment_variable_not_exists_optional(self):
        """Test non-existing optional environment variable"""
        with patch.dict(os.environ, {}, clear=True):
            result = validate_environment_variable("NONEXISTENT_VAR")
            assert result is None

    def test_validate_environment_variable_not_exists_required(self):
        """Test non-existing required environment variable"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValidationError, match="Required environment variable not set"):
                validate_environment_variable("NONEXISTENT_VAR", required=True)

    def test_validate_environment_variable_empty_optional(self):
        """Test empty optional environment variable"""
        with patch.dict(os.environ, {"TEST_VAR": ""}):
            result = validate_environment_variable("TEST_VAR")
            assert result is None

    def test_validate_environment_variable_empty_required(self):
        """Test empty required environment variable"""
        with patch.dict(os.environ, {"TEST_VAR": ""}):
            with pytest.raises(
                ValidationError, match="Required environment variable cannot be empty"
            ):
                validate_environment_variable("TEST_VAR", required=True)

    def test_validate_environment_variable_whitespace(self):
        """Test whitespace-only environment variable"""
        with patch.dict(os.environ, {"TEST_VAR": "   "}):
            result = validate_environment_variable("TEST_VAR")
            assert result is None

    def test_validate_environment_variable_invalid_name(self):
        """Test invalid environment variable name"""
        with pytest.raises(ValidationError, match="Environment variable name cannot be empty"):
            validate_environment_variable("")

    def test_validate_environment_variable_strips_whitespace(self):
        """Test environment variable value whitespace stripping"""
        with patch.dict(os.environ, {"TEST_VAR": "  test_value  "}):
            result = validate_environment_variable("TEST_VAR")
            assert result == "test_value"
