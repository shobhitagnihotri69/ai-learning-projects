"""
Agent 31 — The API-Schema Adapter Agent
Implementation from The AI Agent Engineer's Guide
"""



# ======================================================================# tools/api_adapter.py
from dataclasses import dataclass, field
import jsonschema, requests

@dataclass
class AdaptedTool:
    name: str
    description: str
    parameters: dict       # JSON Schema
    method: str            # "GET" | "POST" | ...
    url_template: str
    auth: dict             # how to authenticate
    response_schema: dict
    side_effect_class: str

class APISchemaAdapterAgent:
    def __init__(self, openapi_doc: dict, base_url: str, auth_provider):
        self.spec = openapi_doc
        self.base_url = base_url
        self.auth = auth_provider
    
    def derive_tools(self) -> list[AdaptedTool]:
        tools = []
        for path, methods in self.spec.get("paths", {}).items():
            for method, op in methods.items():
                if method.upper() not in ("GET", "POST", "PUT", "PATCH", "DELETE"):
                    continue
                tool = self._operation_to_tool(path, method, op)
                tools.append(tool)
        return tools
    
    def _operation_to_tool(self, path: str, method: str, op: dict) -> AdaptedTool:
        name = op.get("operationId") or f"{method}_{path.replace('/', '_').strip('_')}"
        # Synthesize a natural-language description from the spec
        description = op.get("summary") or op.get("description") or name
        # Build a JSON Schema for the call's arguments
        parameters = self._collect_parameters(op)
        # Classify side effect from method + tags
        side_effect = self._classify(method, op.get("tags", []))
        return AdaptedTool(
            name=name,
            description=description,
            parameters=parameters,
            method=method.upper(),
            url_template=self.base_url + path,
            auth=self.auth.descriptor(),
            response_schema=self._collect_response_schema(op),
            side_effect_class=side_effect,
        )
    
    def invoke(self, tool: AdaptedTool, args: dict) -> dict:
        # 1. Validate args against schema BEFORE making the call
        jsonschema.validate(args, tool.parameters)
        # 2. Bind URL params and query/body
        url = tool.url_template
        path_params = {p["name"]: args.pop(p["name"]) for p in tool.parameters.get("path_params", [])}
        for k, v in path_params.items():
            url = url.replace("{" + k + "}", str(v))
        # 3. Authenticate
        headers = self.auth.headers()
        # 4. Make the call
        resp = requests.request(tool.method, url, headers=headers, json=args)
        # 5. Map errors to actionable feedback
        if resp.status_code >= 400:
            return {"error": self._classify_error(resp), "status": resp.status_code,
                    "body": resp.text[:1000]}
        return {"result": resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text}
    
    def _collect_parameters(self, op: dict) -> dict:
        schema = {"type": "object", "properties": {}, "required": [], "path_params": []}
        for p in op.get("parameters", []):
            schema["properties"][p["name"]] = p.get("schema", {"type": "string"})
            if p.get("required"):
                schema["required"].append(p["name"])
            if p["in"] == "path":
                schema["path_params"].append({"name": p["name"]})
        if "requestBody" in op:
            body_schema = op["requestBody"].get("content", {}).get(
                "application/json", {}).get("schema", {})
            schema["properties"].update(body_schema.get("properties", {}))
            schema["required"].extend(body_schema.get("required", []))
        return schema
    
    def _classify(self, method: str, tags: list[str]) -> str:
        if method.upper() in ("GET", "HEAD"):
            return "read"
        if method.upper() == "DELETE":
            return "destructive"
        return "write"
    
    def _classify_error(self, resp) -> str:
        if resp.status_code == 401:
            return "auth_failed"
        if resp.status_code == 403:
            return "forbidden"
        if resp.status_code == 404:
            return "not_found"
        if resp.status_code == 429:
            return "rate_limited"
        if 500 <= resp.status_code < 600:
            return "server_error"
        return "client_error"




