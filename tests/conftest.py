"""Pytest configuration and fixtures"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def temp_cert_dir():
    """Create a temporary directory for certificate files"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def mock_cert_files(temp_cert_dir):
    """Create mock certificate files in temporary directory"""
    cert_dir = Path(temp_cert_dir)

    # Create mock certificate files
    (cert_dir / "caseta-bridge.crt").write_text("mock ca certificate")
    (cert_dir / "caseta.crt").write_text("mock client certificate")
    (cert_dir / "caseta.key").write_text("mock private key")

    return temp_cert_dir


@pytest.fixture
def mock_bridge_env():
    """Mock environment variables for bridge configuration"""
    with patch.dict(
        os.environ, {"LUTRON_BRIDGE_IP": "192.168.1.100", "LUTRON_CERT_DIR": "/tmp/test_certs"}
    ):
        yield


@pytest.fixture
def clean_env():
    """Clean environment variables"""
    env_vars_to_clear = ["LUTRON_BRIDGE_IP", "LUTRON_CERT_DIR"]

    # Store original values
    original_values = {}
    for var in env_vars_to_clear:
        original_values[var] = os.environ.get(var)
        if var in os.environ:
            del os.environ[var]

    yield

    # Restore original values
    for var, value in original_values.items():
        if value is not None:
            os.environ[var] = value
        elif var in os.environ:
            del os.environ[var]


@pytest.fixture
def mock_devices():
    """Mock device data for testing"""
    return [
        {"device_id": "1", "name": "Living Room Light", "type": "light", "zone": "living_room"},
        {"device_id": "2", "name": "Kitchen Light", "type": "light", "zone": "kitchen"},
        {"device_id": "3", "name": "Bedroom Dimmer", "type": "dimmer", "zone": "bedroom"},
    ]
