# Lutron Caseta MCP Server

A Model Context Protocol (MCP) server for controlling Lutron Caseta smart lights and devices. Powered by [pylutron-caseta](https://github.com/gurumitts/pylutron-caseta). This server allows AI assistants to interact with your Lutron Caseta bridge to control lights, check device status, and manage your smart home lighting.

## Features

- **Device Control**: Turn lights on/off and set dimmer levels
- **Device Discovery**: List all lights and devices connected to your bridge
- **Hybrid Pairing**: Support for both standalone pairing utility and MCP tool-based pairing
- **Type Safety**: Full type hints for better development experience
- **Error Handling**: Robust error handling with clear error messages

## Installation

### Prerequisites

- Python 3.10 or higher
- Lutron Caseta bridge connected to your network
- Network access to your Lutron Caseta bridge

### Install from Source

1. Clone the repository:
```bash
git clone <repository-url>
cd lutron-caseta-mcp
```

2. Install with uv (recommended):
```bash
uv sync
```

Or with pip:
```bash
pip install -e .
```

## Setup

### 1. Find Your Bridge IP Address

You need to find the IP address of your Lutron Caseta bridge on your network. You can:
- Check your router's device list
- Use a network scanner app
- Check the Lutron Caseta app settings

### 2. Pair with Your Bridge

You have two options for pairing:

#### Option A: Standalone Pairing Utility (Recommended)
```bash
# Run the pairing utility
uv run lutron-caseta-pair 192.168.1.100

# Or specify a custom directory for certificates
uv run lutron-caseta-pair 192.168.1.100 ./certificates
```

#### Option B: MCP Tool Pairing
Start the MCP server and use the `pair_bridge_tool` through your MCP client.

**For both options:**
1. When prompted, press the small black button on the back of your Lutron Caseta bridge
2. You have 30 seconds to press the button after the prompt appears
3. Three certificate files will be created:
   - `caseta-bridge.crt` (CA certificate)
   - `caseta.crt` (Client certificate)  
   - `caseta.key` (Private key)

### 3. Configure Environment Variables

Set the required environment variables:

```bash
export LUTRON_BRIDGE_IP=192.168.1.100
export LUTRON_CERT_DIR=./certificates  # Optional, defaults to current directory
```

## Usage

### Starting the MCP Server

```bash
uv run lutron-caseta-mcp
```

The server will:
1. Check for required certificate files
2. Connect to your Lutron Caseta bridge
3. Start the MCP server and wait for client connections

### Available MCP Tools

The server provides the following tools that can be called by MCP clients:

#### `pair_bridge_tool(host: str, output_dir: str = ".")`
Pair with a Lutron Caseta bridge and save certificates.

**Parameters:**
- `host`: IP address of the bridge
- `output_dir`: Directory to save certificate files (optional)

**Returns:**
- Success status, message, and certificate file paths

#### `check_connection()`
Check connection status and certificate files.

**Returns:**
- Bridge IP, certificate directory, certificate status, and connection status

#### `list_devices(domain: str = "light")`
List all devices in the specified domain.

**Parameters:**
- `domain`: Device domain to list (default: "light")

**Returns:**
- List of devices with their IDs, names, and capabilities

#### `turn_on_device(device_id: str)`
Turn on a device by ID.

**Parameters:**
- `device_id`: The device ID to turn on

**Returns:**
- Device ID, action performed, and success status

#### `turn_off_device(device_id: str)`
Turn off a device by ID.

**Parameters:**
- `device_id`: The device ID to turn off

**Returns:**
- Device ID, action performed, and success status

#### `set_device_level(device_id: str, level: int)`
Set device level (0-100) for dimmers.

**Parameters:**
- `device_id`: The device ID to control
- `level`: Brightness level (0-100)

**Returns:**
- Device ID, action performed, level set, and success status

## Example Usage with Claude Desktop

Add this to your Claude Desktop MCP configuration:

```json
{
  "mcpServers": {
    "lutron-caseta": {
      "command": "uv",
      "args": ["run", "lutron-caseta-mcp"],
      "cwd": "/path/to/lutron-caseta-mcp",
      "env": {
        "LUTRON_BRIDGE_IP": "192.168.1.100",
        "LUTRON_CERT_DIR": "/path/to/certificates"
      }
    }
  }
}
```

**Note:** If you get `spawn uv ENOENT` errors, you may need to use the full path to `uv`. Find it with `which uv` and use the full path:

```json
{
  "mcpServers": {
    "lutron-caseta": {
      "command": "/Users/yourname/.local/bin/uv",
      "args": ["run", "lutron-caseta-mcp"],
      "cwd": "/path/to/lutron-caseta-mcp",
      "env": {
        "LUTRON_BRIDGE_IP": "192.168.1.100",
        "LUTRON_CERT_DIR": "/path/to/certificates"
      }
    }
  }
}
```

Then you can ask Claude to:
- "Turn on the living room lights"
- "Set the bedroom lights to 50% brightness"
- "List all my lights"
- "Turn off all the lights in the kitchen"

## Troubleshooting

### Connection Issues

1. **Certificate files not found**: Run the pairing utility first
2. **Bridge connection failed**: Check that the bridge IP is correct and reachable
3. **Pairing timeout**: Make sure to press the bridge button within 30 seconds

### Common Error Messages

- `"Not connected to Lutron Caseta bridge"`: The server couldn't connect to your bridge. Check the IP address and certificate files.
- `"Certificate files not found"`: Run the pairing process first.
- `"Pairing failed"`: The bridge button wasn't pressed in time, or there was a network issue.

### Debug Mode

For more detailed logging, you can modify the server to enable debug mode or check the console output when running the server.

## Development

### Running Tests

```bash
uv run pytest
```

### Code Structure

- `src/lutron_caseta_mcp/server.py`: Main MCP server implementation
- `src/lutron_caseta_mcp/pairing.py`: Pairing utilities and standalone pairing tool
- `src/lutron_caseta_mcp/__init__.py`: Package initialization

## Requirements

- `mcp>=1.0.0`: Model Context Protocol implementation
- `pylutron-caseta>=0.10.0`: Lutron Caseta bridge communication

## License

MIT License

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Security Notes

- Certificate files contain sensitive authentication data
- Keep certificate files secure and don't commit them to version control
- The `.gitignore` file is configured to exclude certificate files
- Consider storing certificates in a secure location outside the project directory