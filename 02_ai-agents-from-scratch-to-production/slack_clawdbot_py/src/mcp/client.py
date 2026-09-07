import subprocess
import json
import os
import threading
from typing import Dict, Any, List, Optional
from .config import load_mcp_config, MCPServerConfig
from .tool_converter import mcp_tool_to_openai, parse_tool_name, format_mcp_result
from ..utils.logger import create_module_logger

logger = create_module_logger("mcp-client")

class MCPServerProcess:
    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.process: Optional[subprocess.Popen] = None
        self.request_id = 0
        self.lock = threading.Lock()
        self.tools: List[Dict[str, Any]] = []

    def start(self) -> bool:
        try:
            env = os.environ.copy()
            env.update(self.config.env)
            
            cmd = [self.config.command] + self.config.args
            logger.info(f"Starting MCP server '{self.config.name}': {' '.join(cmd)}")
            
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                bufsize=1
            )
            
            # 1. Initialize
            init_res = self._send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "slack_clawdbot_py", "version": "2.0.0"}
            })
            
            # Send initialized notification
            self._send_notification("notifications/initialized", {})
            
            # 2. List tools
            tools_res = self._send_request("tools/list", {})
            if tools_res and "result" in tools_res and "tools" in tools_res["result"]:
                self.tools = tools_res["result"]["tools"]
                logger.info(f"✅ Server '{self.config.name}' initialized with {len(self.tools)} tools")
                return True
            else:
                logger.warning(f"Server '{self.config.name}' returned no tools")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start MCP server '{self.config.name}': {e}")
            self.stop()
            return False

    def _send_request(self, method: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with self.lock:
            if not self.process or self.process.poll() is not None:
                return None
                
            self.request_id += 1
            req_id = self.request_id
            payload = {
                "jsonrpc": "2.0",
                "id": req_id,
                "method": method,
                "params": params
            }
            
            try:
                line = json.dumps(payload) + "\n"
                self.process.stdin.write(line)
                self.process.stdin.flush()
                
                # Read response line
                while True:
                    resp_line = self.process.stdout.readline()
                    if not resp_line:
                        return None
                    try:
                        data = json.loads(resp_line.strip())
                        if data.get("id") == req_id:
                            return data
                    except json.JSONDecodeError:
                        continue
            except Exception as e:
                logger.error(f"Error communicating with MCP server '{self.config.name}': {e}")
                return None

    def _send_notification(self, method: str, params: Dict[str, Any]) -> None:
        with self.lock:
            if not self.process or self.process.poll() is not None:
                return
            payload = {"jsonrpc": "2.0", "method": method, "params": params}
            try:
                line = json.dumps(payload) + "\n"
                self.process.stdin.write(line)
                self.process.stdin.flush()
            except Exception as e:
                logger.error(f"Error sending notification to '{self.config.name}': {e}")

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        res = self._send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments
        })
        if res and "result" in res:
            return res["result"]
        elif res and "error" in res:
            return f"MCP Error: {res['error'].get('message', 'Unknown error')}"
        return "No response from MCP tool"

    def stop(self) -> None:
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            finally:
                self.process = None

# Global manager
_servers: Dict[str, MCPServerProcess] = {}

def initialize_mcp() -> bool:
    """Initialize configured MCP servers."""
    global _servers
    config = load_mcp_config()
    
    if not config.servers:
        logger.info("No MCP servers configured")
        return False
        
    success_count = 0
    for server_cfg in config.servers:
        proc = MCPServerProcess(server_cfg)
        if proc.start():
            _servers[server_cfg.name] = proc
            success_count += 1
            
    return success_count > 0

def shutdown_mcp() -> None:
    global _servers
    for name, proc in _servers.items():
        logger.info(f"Stopping MCP server '{name}'...")
        proc.stop()
    _servers.clear()

def is_mcp_enabled() -> bool:
    return len(_servers) > 0

def get_connected_servers() -> List[str]:
    return list(_servers.keys())

def get_all_mcp_tools() -> List[Dict[str, Any]]:
    """Return all discovered MCP tools formatted for OpenAI function calling."""
    all_tools = []
    for s_name, proc in _servers.items():
        for tool in proc.tools:
            all_tools.append(mcp_tool_to_openai(s_name, tool))
    return all_tools

def execute_mcp_tool(namespaced_tool: str, arguments: Dict[str, Any]) -> str:
    server_name, orig_tool = parse_tool_name(namespaced_tool)
    if not server_name or server_name not in _servers:
        return f"❌ MCP server '{server_name}' not found or not running."
        
    proc = _servers[server_name]
    result = proc.call_tool(orig_tool, arguments)
    return format_mcp_result(result)
