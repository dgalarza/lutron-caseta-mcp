#!/usr/bin/env python3
"""Lutron Caseta Bridge Pairing Utilities"""

import asyncio
import logging
import os
import sys
from collections.abc import Callable
from pathlib import Path

from pylutron_caseta.pairing import async_pair

from .validation import ValidationError, validate_cert_directory

# Configure logging to use stderr
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger(__name__)

# Default certificate directory - single source of truth
DEFAULT_CERT_DIR = os.path.expanduser("~/.config/lutron-caseta-mcp")


def get_cert_dir() -> str:
    """Get the certificate directory - single source of truth"""
    cert_dir = os.getenv("LUTRON_CERT_DIR", DEFAULT_CERT_DIR)

    try:
        return validate_cert_directory(cert_dir)
    except ValidationError as e:
        logger.warning(f"Certificate directory validation failed: {e}")
        logger.warning(f"Falling back to default directory: {DEFAULT_CERT_DIR}")
        return DEFAULT_CERT_DIR


class PairingResult:
    """Result of a pairing operation"""

    def __init__(self, success: bool, message: str, data: dict | None = None):
        self.success = success
        self.message = message
        self.data = data


async def pair_bridge(
    host: str, output_dir: str, ready_callback: Callable | None = None
) -> PairingResult:
    """
    Pair with Lutron Caseta bridge and save certificates

    Args:
        host: IP address of the bridge
        output_dir: Directory to save certificate files
        ready_callback: Callback function to notify when ready to press button

    Returns:
        PairingResult with success status and message
    """

    def _ready() -> None:
        if ready_callback:
            ready_callback()
        else:
            # For standalone pairing, we can use print since it's not running as MCP server
            print("Press the small black button on the back of the bridge.")
            print("You have 30 seconds...")

    try:
        data = await async_pair(host, _ready)

        # Create output directory if it doesn't exist
        output_path = Path(output_dir).expanduser()
        output_path.mkdir(parents=True, exist_ok=True)

        # Write certificate files
        ca_path = output_path / "caseta-bridge.crt"
        cert_path = output_path / "caseta.crt"
        key_path = output_path / "caseta.key"

        # Write CA certificate (public, can be readable by others)
        with open(ca_path, "w") as cacert:
            cacert.write(data["ca"])

        # Write client certificate (public, can be readable by others)
        with open(cert_path, "w") as cert:
            cert.write(data["cert"])

        # Write private key with restricted permissions (owner only)
        with open(key_path, "w") as key:
            key.write(data["key"])
        key_path.chmod(0o600)  # Owner read/write only

        message = f"Successfully paired with {data['version']}. Certificate files saved to: {output_path.absolute()}"

        return PairingResult(
            success=True,
            message=message,
            data={
                "version": data["version"],
                "ca_path": str(ca_path),
                "cert_path": str(cert_path),
                "key_path": str(key_path),
            },
        )

    except Exception as e:
        return PairingResult(success=False, message=f"Pairing failed: {e}")


def check_certificates(cert_dir: str = ".") -> dict[str, bool]:
    """
    Check if all required certificate files exist

    Args:
        cert_dir: Directory to check for certificates

    Returns:
        Dict with existence status of each certificate file
    """
    cert_path = Path(cert_dir).expanduser()

    return {
        "ca": (cert_path / "caseta-bridge.crt").exists(),
        "cert": (cert_path / "caseta.crt").exists(),
        "key": (cert_path / "caseta.key").exists(),
    }


def certificates_exist(cert_dir: str = ".") -> bool:
    """Check if all required certificate files exist"""
    certs = check_certificates(cert_dir)
    return all(certs.values())


def main() -> None:
    """Main entry point for standalone pairing utility"""
    if len(sys.argv) < 2:
        print("Lutron Caseta Bridge Pairing Utility")
        print("====================================")
        print("Usage: python -m lutron_caseta_mcp.pairing <bridge_ip> [output_dir]")
        print("Example: python -m lutron_caseta_mcp.pairing 192.168.1.100 ./certs")
        print("\nThis will create three files:")
        print("  - caseta-bridge.crt (CA certificate)")
        print("  - caseta.crt (Client certificate)")
        print("  - caseta.key (Private key)")
        sys.exit(1)

    bridge_ip = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else get_cert_dir()

    print("Lutron Caseta Bridge Pairing Utility")
    print("====================================")
    print(f"Bridge IP: {bridge_ip}")

    if len(sys.argv) <= 2:
        print("Output directory: ~/.config/lutron-caseta-mcp (default)")
    else:
        print(f"Output directory: {output_dir}")
    print()

    result = asyncio.run(pair_bridge(bridge_ip, output_dir))

    if result.success:
        print(result.message)
        print("\nFiles created:")
        print("  - caseta-bridge.crt (CA certificate)")
        print("  - caseta.crt (Client certificate)")
        print("  - caseta.key (Private key)")
        print("\nYou can now start the MCP server with these certificates.")
    else:
        print(f"Error: {result.message}")

    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()
