![](https://raw.githubusercontent.com/sancovp/starship-mcp/refs/heads/main/starship_small.png)
[![Part of STARSYSTEM](https://img.shields.io/badge/Part%20of-STARSYSTEM-blue)](https://github.com/sancovp/starsystem-metarepo)

# STARSHIP MCP

## Installation

```
pip install pydantic-stack-core payload-discovery starlog-mcp starship-mcp
```

## MCP
#### Claude Code
```
"starlog": {
      "type": "stdio",
      "command": "python",
      "args": [
        "-m",
        "starlog_mcp.starlog_mcp"
      ],
      "env": {
        "HEAVEN_DATA_DIR": "/tmp/heaven_data"
      }
    },
    "starship": {
      "type": "stdio",
      "command": "python",
      "args": [
        "-m",
        "starship_mcp.starship_mcp"
      ],
      "env": {
        "HEAVEN_DATA_DIR": "/tmp/heaven_data"
      }
    },
    "waypoint": {
      "type": "stdio",
      "command": "python",
      "args": [
        "-m",
        "payload_discovery.mcp_server_v2"
      ],
      "env": {
        "HEAVEN_DATA_DIR": "/tmp/heaven_data"
      }
    },
```
