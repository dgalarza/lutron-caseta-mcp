"""Tests for pairing functionality"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from lutron_caseta_mcp.pairing import (
    DEFAULT_CERT_DIR,
    certificates_exist,
    check_certificates,
    get_cert_dir,
    pair_bridge,
)


class TestGetCertDir:
    """Test get_cert_dir function"""

    def test_get_cert_dir_default(self):
        """Test default certificate directory"""
        with patch.dict(os.environ, {}, clear=True):
            result = get_cert_dir()
            assert result == DEFAULT_CERT_DIR

    def test_get_cert_dir_env_override(self):
        """Test certificate directory from environment variable"""
        custom_dir = "~/custom/cert/dir"
        expected_dir = os.path.expanduser(custom_dir)
        with patch.dict(os.environ, {"LUTRON_CERT_DIR": custom_dir}):
            result = get_cert_dir()
            assert result == str(Path(expected_dir).resolve())


class TestCertificateChecking:
    """Test certificate file checking functions"""

    def test_check_certificates_all_exist(self):
        """Test checking certificates when all files exist"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create certificate files
            (Path(temp_dir) / "caseta-bridge.crt").write_text("ca cert")
            (Path(temp_dir) / "caseta.crt").write_text("client cert")
            (Path(temp_dir) / "caseta.key").write_text("private key")

            result = check_certificates(temp_dir)
            assert result == {"ca": True, "cert": True, "key": True}

    def test_check_certificates_missing_files(self):
        """Test checking certificates when some files are missing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Only create CA certificate
            (Path(temp_dir) / "caseta-bridge.crt").write_text("ca cert")

            result = check_certificates(temp_dir)
            assert result == {"ca": True, "cert": False, "key": False}

    def test_certificates_exist_all_present(self):
        """Test certificates_exist when all files are present"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create all certificate files
            (Path(temp_dir) / "caseta-bridge.crt").write_text("ca cert")
            (Path(temp_dir) / "caseta.crt").write_text("client cert")
            (Path(temp_dir) / "caseta.key").write_text("private key")

            result = certificates_exist(temp_dir)
            assert result is True

    def test_certificates_exist_missing_files(self):
        """Test certificates_exist when some files are missing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Only create CA certificate
            (Path(temp_dir) / "caseta-bridge.crt").write_text("ca cert")

            result = certificates_exist(temp_dir)
            assert result is False


class TestPairBridge:
    """Test bridge pairing functionality"""

    @pytest.mark.asyncio
    async def test_pair_bridge_success(self):
        """Test successful bridge pairing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_data = {
                "ca": "mock ca certificate",
                "cert": "mock client certificate",
                "key": "mock private key",
                "version": "1.0.0",
            }

            ready_callback = MagicMock()
            ready_callback.return_value = "Ready to pair"

            with patch("lutron_caseta_mcp.pairing.async_pair") as mock_async_pair:
                mock_async_pair.return_value = mock_data

                result = await pair_bridge("192.168.1.100", temp_dir, ready_callback)

                assert result.success is True
                assert "Successfully paired with 1.0.0" in result.message
                assert result.data["version"] == "1.0.0"

                # Check that certificate files were created
                assert (Path(temp_dir) / "caseta-bridge.crt").exists()
                assert (Path(temp_dir) / "caseta.crt").exists()
                assert (Path(temp_dir) / "caseta.key").exists()

                # Check file contents
                assert (Path(temp_dir) / "caseta-bridge.crt").read_text() == "mock ca certificate"
                assert (Path(temp_dir) / "caseta.crt").read_text() == "mock client certificate"
                assert (Path(temp_dir) / "caseta.key").read_text() == "mock private key"

    @pytest.mark.asyncio
    async def test_pair_bridge_failure(self):
        """Test failed bridge pairing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            ready_callback = MagicMock()

            with patch("lutron_caseta_mcp.pairing.async_pair") as mock_async_pair:
                mock_async_pair.side_effect = Exception("Pairing timeout")

                result = await pair_bridge("192.168.1.100", temp_dir, ready_callback)

                assert result.success is False
                assert "Pairing failed: Pairing timeout" in result.message

    @pytest.mark.asyncio
    async def test_pair_bridge_creates_directory(self):
        """Test that pairing creates the output directory if it doesn't exist"""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "new_cert_dir"
            assert not output_dir.exists()

            mock_data = {
                "ca": "mock ca certificate",
                "cert": "mock client certificate",
                "key": "mock private key",
                "version": "1.0.0",
            }

            with patch("lutron_caseta_mcp.pairing.async_pair") as mock_async_pair:
                mock_async_pair.return_value = mock_data

                result = await pair_bridge("192.168.1.100", str(output_dir))

                assert result.success is True
                assert output_dir.exists()
                assert (output_dir / "caseta-bridge.crt").exists()
