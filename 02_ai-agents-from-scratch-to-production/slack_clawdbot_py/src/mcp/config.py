import os
import json
from pathlib import Path
from typing import List, Dict, Optional
from pydantic import BaseModel
from ..utils.logger import create_module_logger

logger = create_module_logger("mcp-config")

class MCPServerConfig(BaseModel):
    name: str
    command: str
    args: List[str] = []
    env: Dict[str, str] = {}

class MCPConfig(BaseModel):
    servers: List[MCPServerConfig] = []

def load_mcp_config() -> MCPConfig:
    """Load MCP server configs from mcp-config.json or environment."""
    config_file = Path.cwd() / "mcp-config.json"
    
    # Try loading from local file
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                config = MCPConfig(**data)
                logger.info(f"Loaded {len(config.servers)} MCP servers from {config_file}")
                return config
        except Exception as e:
            logger.error(f"Failed to parse {config_file}: {e}")

    # Fallback to environment variables
    servers = []
    gh_token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN") or os.getenv("MCP_GITHUB_TOKEN")
    if gh_token:
        servers.append(MCPServerConfig(
            name="github",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env={"GITHUB_PERSONAL_ACCESS_TOKEN": gh_token}
        ))

    notion_token = os.getenv("NOTION_API_TOKEN") or os.getenv("MCP_NOTION_TOKEN")
    if notion_token:
        servers.append(MCPServerConfig(
            name="notion",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-notion"],
            env={"NOTION_API_TOKEN": notion_token}
        ))

    return MCPConfig(servers=servers)
