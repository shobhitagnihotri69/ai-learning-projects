from typing import Dict, Any, List, Optional, Tuple

def mcp_tool_to_openai(server_name: str, tool: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert an MCP tool definition to OpenAI function call format.
    Prefixed with mcp__<server_name>__<tool_name> to prevent name collisions.
    """
    original_name = tool.get("name", "")
    namespaced_name = f"mcp__{server_name}__{original_name}"
    
    return {
        "type": "function",
        "function": {
            "name": namespaced_name,
            "description": f"[{server_name.upper()}] {tool.get('description', '')}",
            "parameters": tool.get("inputSchema", {
                "type": "object",
                "properties": {},
                "required": []
            })
        }
    }

def parse_tool_name(tool_name: str) -> Tuple[Optional[str], str]:
    """
    Parse a namespaced tool name into (server_name, original_tool_name).
    Example: 'mcp__github__create_issue' -> ('github', 'create_issue')
    """
    if tool_name.startswith("mcp__"):
        parts = tool_name.split("__", 2)
        if len(parts) == 3:
            return parts[1], parts[2]
    return None, tool_name

def format_mcp_result(result: Any) -> str:
    """Format the result of an MCP tool call for display / LLM context."""
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        if "content" in result and isinstance(result["content"], list):
            texts = [c.get("text", "") for c in result["content"] if isinstance(c, dict) and "text" in c]
            if texts:
                return "\n".join(texts)
    import json
    return json.dumps(result, indent=2)
