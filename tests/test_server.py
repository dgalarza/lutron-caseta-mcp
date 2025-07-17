"""Tests for MCP server functionality"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lutron_caseta_mcp.server import LutronCasetaManager


class TestLutronCasetaManager:
    """Test LutronCasetaManager class"""

    def test_init(self):
        """Test LutronCasetaManager initialization"""
        manager = LutronCasetaManager(
            bridge_ip="192.168.1.100",
            key_path="/path/to/key",
            cert_path="/path/to/cert",
            ca_path="/path/to/ca",
        )

        assert manager.bridge_ip == "192.168.1.100"
        assert manager.key_path == "/path/to/key"
        assert manager.cert_path == "/path/to/cert"
        assert manager.ca_path == "/path/to/ca"
        assert manager.bridge is None
        assert manager.connected is False

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful bridge connection"""
        manager = LutronCasetaManager(
            bridge_ip="192.168.1.100",
            key_path="/path/to/key",
            cert_path="/path/to/cert",
            ca_path="/path/to/ca",
        )

        mock_bridge = AsyncMock()

        with patch("lutron_caseta_mcp.server.Smartbridge") as mock_smartbridge:
            mock_smartbridge.create_tls.return_value = mock_bridge

            result = await manager.connect()

            assert result is True
            assert manager.connected is True
            assert manager.bridge == mock_bridge
            mock_bridge.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Test failed bridge connection"""
        manager = LutronCasetaManager(
            bridge_ip="192.168.1.100",
            key_path="/path/to/key",
            cert_path="/path/to/cert",
            ca_path="/path/to/ca",
        )

        mock_bridge = AsyncMock()
        mock_bridge.connect.side_effect = Exception("Connection failed")

        with patch("lutron_caseta_mcp.server.Smartbridge") as mock_smartbridge:
            mock_smartbridge.create_tls.return_value = mock_bridge

            result = await manager.connect()

            assert result is False
            assert manager.connected is False

    @pytest.mark.asyncio
    async def test_disconnect(self):
        """Test bridge disconnection"""
        manager = LutronCasetaManager(
            bridge_ip="192.168.1.100",
            key_path="/path/to/key",
            cert_path="/path/to/cert",
            ca_path="/path/to/ca",
        )

        mock_bridge = AsyncMock()
        manager.bridge = mock_bridge
        manager.connected = True

        await manager.disconnect()

        assert manager.connected is False
        mock_bridge.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_devices_by_domain(self):
        """Test getting devices by domain"""
        manager = LutronCasetaManager(
            bridge_ip="192.168.1.100",
            key_path="/path/to/key",
            cert_path="/path/to/cert",
            ca_path="/path/to/ca",
        )

        mock_bridge = MagicMock()
        mock_devices = [{"device_id": "1", "name": "Living Room Light"}]
        mock_bridge.get_devices_by_domain.return_value = mock_devices

        manager.bridge = mock_bridge
        manager.connected = True

        result = await manager.get_devices_by_domain("light")

        assert result == mock_devices
        mock_bridge.get_devices_by_domain.assert_called_once_with("light")

    @pytest.mark.asyncio
    async def test_get_devices_not_connected(self):
        """Test getting devices when not connected"""
        manager = LutronCasetaManager(
            bridge_ip="192.168.1.100",
            key_path="/path/to/key",
            cert_path="/path/to/cert",
            ca_path="/path/to/ca",
        )

        with pytest.raises(RuntimeError, match="Not connected to Lutron Caseta bridge"):
            await manager.get_devices_by_domain("light")

    @pytest.mark.asyncio
    async def test_turn_on_success(self):
        """Test successful device turn on"""
        manager = LutronCasetaManager(
            bridge_ip="192.168.1.100",
            key_path="/path/to/key",
            cert_path="/path/to/cert",
            ca_path="/path/to/ca",
        )

        mock_bridge = AsyncMock()
        manager.bridge = mock_bridge
        manager.connected = True

        result = await manager.turn_on("1")

        assert result is True
        mock_bridge.turn_on.assert_called_once_with("1")

    @pytest.mark.asyncio
    async def test_turn_on_failure(self):
        """Test failed device turn on"""
        manager = LutronCasetaManager(
            bridge_ip="192.168.1.100",
            key_path="/path/to/key",
            cert_path="/path/to/cert",
            ca_path="/path/to/ca",
        )

        mock_bridge = AsyncMock()
        mock_bridge.turn_on.side_effect = Exception("Turn on failed")
        manager.bridge = mock_bridge
        manager.connected = True

        result = await manager.turn_on("1")

        assert result is False

    @pytest.mark.asyncio
    async def test_turn_off_success(self):
        """Test successful device turn off"""
        manager = LutronCasetaManager(
            bridge_ip="192.168.1.100",
            key_path="/path/to/key",
            cert_path="/path/to/cert",
            ca_path="/path/to/ca",
        )

        mock_bridge = AsyncMock()
        manager.bridge = mock_bridge
        manager.connected = True

        result = await manager.turn_off("1")

        assert result is True
        mock_bridge.turn_off.assert_called_once_with("1")

    @pytest.mark.asyncio
    async def test_set_level_success(self):
        """Test successful device level setting"""
        manager = LutronCasetaManager(
            bridge_ip="192.168.1.100",
            key_path="/path/to/key",
            cert_path="/path/to/cert",
            ca_path="/path/to/ca",
        )

        mock_bridge = AsyncMock()
        manager.bridge = mock_bridge
        manager.connected = True

        result = await manager.set_level("1", 50)

        assert result is True
        mock_bridge.set_value.assert_called_once_with("1", value=50)

    @pytest.mark.asyncio
    async def test_set_level_invalid_range(self):
        """Test setting device level with invalid range"""
        manager = LutronCasetaManager(
            bridge_ip="192.168.1.100",
            key_path="/path/to/key",
            cert_path="/path/to/cert",
            ca_path="/path/to/ca",
        )

        manager.connected = True
        manager.bridge = MagicMock()

        with pytest.raises(ValueError, match="Level must be between 0 and 100"):
            await manager.set_level("1", 150)

    @pytest.mark.asyncio
    async def test_set_level_not_connected(self):
        """Test setting device level when not connected"""
        manager = LutronCasetaManager(
            bridge_ip="192.168.1.100",
            key_path="/path/to/key",
            cert_path="/path/to/cert",
            ca_path="/path/to/ca",
        )

        with pytest.raises(RuntimeError, match="Not connected to Lutron Caseta bridge"):
            await manager.set_level("1", 50)
