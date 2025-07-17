#!/usr/bin/env python3
"""Lutron Caseta MCP Server"""

import logging
import os
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from mcp.server.fastmcp import FastMCP
from pylutron_caseta.smartbridge import Smartbridge

from .pairing import certificates_exist, check_certificates, get_cert_dir, pair_bridge
from .validation import ValidationError, validate_device_level, validate_domain, validate_host_ip

# Configure logging to use stderr
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger(__name__)


@dataclass
class LutronConfig:
    """Configuration for Lutron Caseta MCP server"""

    bridge_ip: str
    cert_dir: str
    key_path: str
    cert_path: str
    ca_path: str

    @classmethod
    def from_env(cls) -> "LutronConfig":
        """Create configuration from environment variables"""
        cert_dir = get_cert_dir()
        return cls(
            bridge_ip=os.getenv("LUTRON_BRIDGE_IP", ""),
            cert_dir=cert_dir,
            key_path=os.path.join(cert_dir, "caseta.key"),
            cert_path=os.path.join(cert_dir, "caseta.crt"),
            ca_path=os.path.join(cert_dir, "caseta-bridge.crt"),
        )

    @property
    def is_complete(self) -> bool:
        """Check if all required configuration is present"""
        return bool(self.bridge_ip and self.cert_dir)

    @property
    def certificates_exist(self) -> bool:
        """Check if all certificate files exist"""
        return certificates_exist(self.cert_dir)


class MCPServerState:
    """Manages the state of the MCP server"""

    def __init__(self) -> None:
        self.config: LutronConfig | None = None
        self.caseta_manager: LutronCasetaManager | None = None
        self.connected: bool = False

    async def initialize(self) -> bool:
        """Initialize the server state"""
        self.config = LutronConfig.from_env()

        if not self.config.is_complete:
            logger.warning("LUTRON_BRIDGE_IP environment variable not set")
            logger.warning(
                "Bridge connection will not be established. Use pair_bridge tool to configure."
            )
            return False

        if not self.config.certificates_exist:
            logger.warning(f"Certificate files not found in {self.config.cert_dir}")
            logger.warning("Use the pair_bridge tool or run the standalone pairing utility first.")
            return False

        # Initialize and connect to Lutron Caseta bridge
        self.caseta_manager = LutronCasetaManager(
            self.config.bridge_ip, self.config.key_path, self.config.cert_path, self.config.ca_path
        )

        self.connected = await self.caseta_manager.connect()
        if self.connected:
            logger.info(f"Connected to Lutron Caseta bridge at {self.config.bridge_ip}")
        else:
            logger.error("Failed to connect to Lutron Caseta bridge")

        return self.connected

    async def cleanup(self) -> None:
        """Clean up resources"""
        if self.caseta_manager:
            await self.caseta_manager.disconnect()
            logger.info("Disconnected from Lutron Caseta bridge")
        self.connected = False

    def update_config(self, bridge_ip: str) -> bool:
        """Update configuration with new bridge IP"""
        if not self.config:
            self.config = LutronConfig.from_env()

        self.config.bridge_ip = bridge_ip
        return True


class LutronCasetaManager:
    """Manages Lutron Caseta bridge connection and device operations"""

    def __init__(self, bridge_ip: str, key_path: str, cert_path: str, ca_path: str):
        self.bridge_ip = bridge_ip
        self.key_path = key_path
        self.cert_path = cert_path
        self.ca_path = ca_path
        self.bridge: Smartbridge | None = None
        self.connected = False

    async def connect(self) -> bool:
        """Connect to the Lutron Caseta bridge"""
        try:
            self.bridge = Smartbridge.create_tls(
                self.bridge_ip, self.key_path, self.cert_path, self.ca_path
            )
            await self.bridge.connect()
            self.connected = True
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Lutron Caseta bridge: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from the bridge"""
        if self.bridge and self.connected:
            await self.bridge.close()
            self.connected = False

    async def get_devices_by_domain(self, domain: str = "light") -> list[dict[str, Any]]:
        """Get devices by domain (light, fan, etc.)"""
        if not self.connected or not self.bridge:
            raise RuntimeError("Not connected to Lutron Caseta bridge")

        devices = self.bridge.get_devices_by_domain(domain)
        return devices if devices is not None else []

    async def turn_on(self, device_id: str) -> bool:
        """Turn on a device"""
        if not self.connected or not self.bridge:
            raise RuntimeError("Not connected to Lutron Caseta bridge")

        try:
            await self.bridge.turn_on(device_id)
            return True
        except Exception as e:
            logger.error(f"Failed to turn on device {device_id}: {e}")
            return False

    async def turn_off(self, device_id: str) -> bool:
        """Turn off a device"""
        if not self.connected or not self.bridge:
            raise RuntimeError("Not connected to Lutron Caseta bridge")

        try:
            await self.bridge.turn_off(device_id)
            return True
        except Exception as e:
            logger.error(f"Failed to turn off device {device_id}: {e}")
            return False

    async def set_level(self, device_id: str, level: int) -> bool:
        """Set device level (0-100)"""
        if not self.connected or not self.bridge:
            raise RuntimeError("Not connected to Lutron Caseta bridge")

        if not 0 <= level <= 100:
            raise ValueError("Level must be between 0 and 100")

        try:
            # The set_value method expects device_id as string and value as int
            await self.bridge.set_value(device_id, value=level)
            return True
        except Exception as e:
            logger.error(f"Failed to set value for device {device_id}: {e}")
            return False


# Global server state instance
server_state: MCPServerState | None = None


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncGenerator[None, None]:
    """Manage application lifecycle"""
    global server_state

    # Initialize server state
    server_state = MCPServerState()

    # Create certificate directory if it doesn't exist
    config = LutronConfig.from_env()
    os.makedirs(config.cert_dir, exist_ok=True)
    logger.info(f"Using certificate directory: {config.cert_dir}")

    # Initialize connection if possible
    await server_state.initialize()

    try:
        yield
    finally:
        # Cleanup on shutdown
        if server_state:
            await server_state.cleanup()


# Create MCP server with lifespan manager
mcp = FastMCP(name="lutron-caseta-mcp", lifespan=app_lifespan)


@mcp.tool()
async def pair_bridge_tool(host: str) -> dict[str, Any]:
    """
    Pair with Lutron Caseta bridge and save certificates.

    CRITICAL: Before calling this tool, tell the user:
    "I'm about to start the pairing process. Please be ready to press the small black button
    on the back of your Lutron Caseta bridge within 30 seconds when I start the pairing."

    Args:
        host: IP address of the bridge

    Returns:
        Dict with pairing result and certificate file paths
    """
    global server_state

    try:
        host = validate_host_ip(host)
    except ValidationError as e:
        return {
            "success": False,
            "message": f"❌ INVALID INPUT: {e}",
            "status": "Please provide a valid IP address for your Lutron Caseta bridge.",
            "connected": False,
        }

    if not server_state:
        return {
            "success": False,
            "message": "❌ ERROR: Server state not initialized",
            "status": "Internal server error. Please restart the MCP server.",
            "connected": False,
        }

    cert_dir = get_cert_dir()

    def ready_callback() -> str:
        return "🔘 PRESS THE BUTTON NOW: Find the small black button on the back of your Lutron Caseta bridge and press it now! You have 30 seconds..."

    try:
        result = await pair_bridge(host, cert_dir, ready_callback)

        if result.success:
            server_state.update_config(host)

            key_path = os.path.join(cert_dir, "caseta.key")
            cert_path = os.path.join(cert_dir, "caseta.crt")
            ca_path = os.path.join(cert_dir, "caseta-bridge.crt")

            server_state.caseta_manager = LutronCasetaManager(host, key_path, cert_path, ca_path)
            connected = await server_state.caseta_manager.connect()
            server_state.connected = connected

            return {
                "success": True,
                "message": f"✅ SUCCESS: Bridge paired successfully! {result.message}",
                "status": "Your Lutron Caseta bridge is now connected and ready to control lights.",
                "connected": connected,
                "certificate_files": result.data,
            }
        else:
            return {
                "success": False,
                "message": f"❌ FAILED: {result.message}",
                "status": "Pairing failed. Please try again and make sure to press the small black button on the back of your bridge when the pairing starts.",
                "connected": False,
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"❌ ERROR: Pairing process failed with error: {str(e)}",
            "status": "An unexpected error occurred. Please check that your bridge IP is correct and try again.",
            "connected": False,
        }


@mcp.tool()
async def check_connection() -> dict[str, Any]:
    """Check connection status and certificate files"""
    global server_state

    current_bridge_ip = os.getenv("LUTRON_BRIDGE_IP", "")
    current_cert_dir = get_cert_dir()
    cert_status = check_certificates(current_cert_dir)

    return {
        "bridge_ip": current_bridge_ip,
        "cert_dir": current_cert_dir,
        "certificates": cert_status,
        "connected": server_state.connected if server_state else False,
    }


@mcp.tool()
async def list_devices(domain: str = "light") -> list[dict[str, Any]]:
    """
    List all devices in the specified domain.

    Args:
        domain: Device domain type. Valid values are: light, switch, cover, sensor, fan
    """
    if not server_state or not server_state.caseta_manager or not server_state.connected:
        raise RuntimeError("Not connected to Lutron Caseta bridge. Use pair_bridge tool first.")

    try:
        domain = validate_domain(domain)
    except ValidationError as e:
        raise ValueError(str(e)) from e

    devices = await server_state.caseta_manager.get_devices_by_domain(domain)
    return devices


@mcp.tool()
async def turn_on_device(device_id: str) -> dict[str, Any]:
    """Turn on a device by ID"""
    if not server_state or not server_state.caseta_manager or not server_state.connected:
        raise RuntimeError("Not connected to Lutron Caseta bridge. Use pair_bridge tool first.")

    success = await server_state.caseta_manager.turn_on(device_id)
    return {"device_id": device_id, "action": "turn_on", "success": success}


@mcp.tool()
async def turn_off_device(device_id: str) -> dict[str, Any]:
    """Turn off a device by ID"""
    if not server_state or not server_state.caseta_manager or not server_state.connected:
        raise RuntimeError("Not connected to Lutron Caseta bridge. Use pair_bridge tool first.")

    success = await server_state.caseta_manager.turn_off(device_id)
    return {"device_id": device_id, "action": "turn_off", "success": success}


@mcp.tool()
async def set_device_level(device_id: str, level: int) -> dict[str, Any]:
    """Set device level (0-100) for dimmers"""
    if not server_state or not server_state.caseta_manager or not server_state.connected:
        raise RuntimeError("Not connected to Lutron Caseta bridge. Use pair_bridge tool first.")

    try:
        level = validate_device_level(level)
    except ValidationError as e:
        raise ValueError(str(e)) from e

    success = await server_state.caseta_manager.set_level(device_id, level)
    return {"device_id": device_id, "action": "set_level", "level": level, "success": success}


def main() -> None:
    """Main entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Lutron Caseta MCP Server")
        print("========================")
        print("Environment variables:")
        print("  LUTRON_BRIDGE_IP     - IP address of Lutron Caseta bridge")
        print("  LUTRON_CERT_DIR      - Directory containing certificate files (default: .)")
        print()
        print("Certificate files needed:")
        print("  - caseta-bridge.crt  (CA certificate)")
        print("  - caseta.crt         (Client certificate)")
        print("  - caseta.key         (Private key)")
        print()
        print("To pair with bridge:")
        print("  1. Use standalone utility: lutron-caseta-pair <bridge_ip> [cert_dir]")
        print("  2. Use MCP tool: pair_bridge_tool")
        print()
        print("Available MCP tools:")
        print("  - pair_bridge_tool(host, output_dir)")
        print("  - check_connection()")
        print("  - list_devices(domain)")
        print("  - turn_on_device(device_id)")
        print("  - turn_off_device(device_id)")
        print("  - set_device_level(device_id, level)")
        return

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
