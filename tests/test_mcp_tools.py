"""Tests for MCP tools functionality"""

import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lutron_caseta_mcp.server import (
    check_connection,
    list_devices,
    pair_bridge_tool,
    set_device_level,
    turn_off_device,
    turn_on_device,
)


class TestMCPTools:
    """Test MCP tool functions"""

    @pytest.mark.asyncio
    async def test_check_connection_with_env_vars(self):
        """Test check_connection with environment variables set"""
        with patch.dict(os.environ, {"LUTRON_BRIDGE_IP": "192.168.1.100"}):
            with patch("lutron_caseta_mcp.server.check_certificates") as mock_check:
                mock_check.return_value = {"ca": True, "cert": True, "key": True}

                # Mock global server_state
                with patch("lutron_caseta_mcp.server.server_state") as mock_state:
                    mock_state.connected = True

                    result = await check_connection()

                    assert result["bridge_ip"] == "192.168.1.100"
                    assert result["connected"] is True
                    assert result["certificates"] == {"ca": True, "cert": True, "key": True}

    @pytest.mark.asyncio
    async def test_check_connection_no_manager(self):
        """Test check_connection when no manager is available"""
        with patch.dict(os.environ, {"LUTRON_BRIDGE_IP": "192.168.1.100"}):
            with patch("lutron_caseta_mcp.server.check_certificates") as mock_check:
                mock_check.return_value = {"ca": False, "cert": False, "key": False}

                # Mock global server_state as None
                with patch("lutron_caseta_mcp.server.server_state", None):
                    result = await check_connection()

                    assert result["bridge_ip"] == "192.168.1.100"
                    assert result["connected"] is False
                    assert result["certificates"] == {"ca": False, "cert": False, "key": False}

    @pytest.mark.asyncio
    async def test_list_devices_success(self):
        """Test successful device listing"""
        mock_devices = [
            {"device_id": "1", "name": "Living Room Light"},
            {"device_id": "2", "name": "Kitchen Light"},
        ]

        mock_manager = AsyncMock()
        mock_manager.connected = True
        mock_manager.get_devices_by_domain.return_value = mock_devices

        mock_state = MagicMock()
        mock_state.caseta_manager = mock_manager
        mock_state.connected = True

        with patch("lutron_caseta_mcp.server.server_state", mock_state):
            result = await list_devices("light")

            assert result == mock_devices
            mock_manager.get_devices_by_domain.assert_called_once_with("light")

    @pytest.mark.asyncio
    async def test_list_devices_not_connected(self):
        """Test device listing when not connected"""
        mock_manager = AsyncMock()
        mock_manager.connected = False

        mock_state = MagicMock()
        mock_state.caseta_manager = mock_manager
        mock_state.connected = False

        with patch("lutron_caseta_mcp.server.server_state", mock_state):
            with pytest.raises(RuntimeError, match="Not connected to Lutron Caseta bridge"):
                await list_devices("light")

    @pytest.mark.asyncio
    async def test_list_devices_no_manager(self):
        """Test device listing when no manager is available"""
        with patch("lutron_caseta_mcp.server.server_state", None):
            with pytest.raises(RuntimeError, match="Not connected to Lutron Caseta bridge"):
                await list_devices("light")

    @pytest.mark.asyncio
    async def test_turn_on_device_success(self):
        """Test successful device turn on"""
        mock_manager = AsyncMock()
        mock_manager.connected = True
        mock_manager.turn_on.return_value = True

        mock_state = MagicMock()
        mock_state.caseta_manager = mock_manager
        mock_state.connected = True

        with patch("lutron_caseta_mcp.server.server_state", mock_state):
            result = await turn_on_device("1")

            assert result == {"device_id": "1", "action": "turn_on", "success": True}
            mock_manager.turn_on.assert_called_once_with("1")

    @pytest.mark.asyncio
    async def test_turn_on_device_failure(self):
        """Test failed device turn on"""
        mock_manager = AsyncMock()
        mock_manager.connected = True
        mock_manager.turn_on.return_value = False

        mock_state = MagicMock()
        mock_state.caseta_manager = mock_manager
        mock_state.connected = True

        with patch("lutron_caseta_mcp.server.server_state", mock_state):
            result = await turn_on_device("1")

            assert result == {"device_id": "1", "action": "turn_on", "success": False}

    @pytest.mark.asyncio
    async def test_turn_off_device_success(self):
        """Test successful device turn off"""
        mock_manager = AsyncMock()
        mock_manager.connected = True
        mock_manager.turn_off.return_value = True

        mock_state = MagicMock()
        mock_state.caseta_manager = mock_manager
        mock_state.connected = True

        with patch("lutron_caseta_mcp.server.server_state", mock_state):
            result = await turn_off_device("1")

            assert result == {"device_id": "1", "action": "turn_off", "success": True}
            mock_manager.turn_off.assert_called_once_with("1")

    @pytest.mark.asyncio
    async def test_set_device_level_success(self):
        """Test successful device level setting"""
        mock_manager = AsyncMock()
        mock_manager.connected = True
        mock_manager.set_level.return_value = True

        mock_state = MagicMock()
        mock_state.caseta_manager = mock_manager
        mock_state.connected = True

        with patch("lutron_caseta_mcp.server.server_state", mock_state):
            result = await set_device_level("1", 50)

            assert result == {"device_id": "1", "action": "set_level", "level": 50, "success": True}
            mock_manager.set_level.assert_called_once_with("1", 50)

    @pytest.mark.asyncio
    async def test_set_device_level_failure(self):
        """Test failed device level setting"""
        mock_manager = AsyncMock()
        mock_manager.connected = True
        mock_manager.set_level.return_value = False

        mock_state = MagicMock()
        mock_state.caseta_manager = mock_manager
        mock_state.connected = True

        with patch("lutron_caseta_mcp.server.server_state", mock_state):
            result = await set_device_level("1", 50)

            assert result == {
                "device_id": "1",
                "action": "set_level",
                "level": 50,
                "success": False,
            }

    @pytest.mark.asyncio
    async def test_pair_bridge_tool_success(self):
        """Test successful bridge pairing via MCP tool"""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.message = "Pairing successful"
            mock_result.data = {
                "version": "1.0.0",
                "ca_path": f"{temp_dir}/caseta-bridge.crt",
                "cert_path": f"{temp_dir}/caseta.crt",
                "key_path": f"{temp_dir}/caseta.key",
            }

            mock_manager = AsyncMock()
            mock_manager.connect.return_value = True

            mock_state = MagicMock()
            mock_state.update_config.return_value = True

            with patch("lutron_caseta_mcp.server.server_state", mock_state):
                with patch("lutron_caseta_mcp.server.get_cert_dir", return_value=temp_dir):
                    with patch("lutron_caseta_mcp.server.pair_bridge", return_value=mock_result):
                        with patch(
                            "lutron_caseta_mcp.server.LutronCasetaManager",
                            return_value=mock_manager,
                        ):
                            result = await pair_bridge_tool("192.168.1.100")

                            assert result["success"] is True
                            assert "SUCCESS" in result["message"]
                            assert result["connected"] is True

    @pytest.mark.asyncio
    async def test_pair_bridge_tool_failure(self):
        """Test failed bridge pairing via MCP tool"""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_result = MagicMock()
            mock_result.success = False
            mock_result.message = "Pairing failed"

            mock_state = MagicMock()

            with patch("lutron_caseta_mcp.server.server_state", mock_state):
                with patch("lutron_caseta_mcp.server.get_cert_dir", return_value=temp_dir):
                    with patch("lutron_caseta_mcp.server.pair_bridge", return_value=mock_result):
                        result = await pair_bridge_tool("192.168.1.100")

                        assert result["success"] is False
                        assert "FAILED" in result["message"]
                        assert result["connected"] is False

    @pytest.mark.asyncio
    async def test_pair_bridge_tool_invalid_ip(self):
        """Test pair_bridge_tool with invalid IP address"""
        result = await pair_bridge_tool("invalid.ip")

        assert result["success"] is False
        assert "INVALID INPUT" in result["message"]
        assert result["connected"] is False

    @pytest.mark.asyncio
    async def test_list_devices_invalid_domain(self):
        """Test list_devices with invalid domain"""
        mock_manager = AsyncMock()
        mock_manager.connected = True

        mock_state = MagicMock()
        mock_state.caseta_manager = mock_manager
        mock_state.connected = True

        with patch("lutron_caseta_mcp.server.server_state", mock_state):
            with pytest.raises(ValueError, match="Invalid domain"):
                await list_devices("invalid_domain")

    @pytest.mark.asyncio
    async def test_set_device_level_invalid_level(self):
        """Test set_device_level with invalid level"""
        mock_manager = AsyncMock()
        mock_manager.connected = True

        mock_state = MagicMock()
        mock_state.caseta_manager = mock_manager
        mock_state.connected = True

        with patch("lutron_caseta_mcp.server.server_state", mock_state):
            with pytest.raises(ValueError, match="Device level must be between 0 and 100"):
                await set_device_level("1", 150)

    @pytest.mark.asyncio
    async def test_set_device_level_invalid_type(self):
        """Test set_device_level with invalid type"""
        mock_manager = AsyncMock()
        mock_manager.connected = True

        mock_state = MagicMock()
        mock_state.caseta_manager = mock_manager
        mock_state.connected = True

        with patch("lutron_caseta_mcp.server.server_state", mock_state):
            with pytest.raises(ValueError, match="Device level must be an integer"):
                await set_device_level("1", "50")
