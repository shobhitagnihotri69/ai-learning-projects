# Agent 31 — The API-Schema Adapter Agent

### Agent 31 — The API-Schema Adapter Agent

*Adapts to a new API at runtime by reading its OpenAPI specification.*

#### The Problem

When an agent is supposed to be able to use any API in a class — any CRM, any ticketing system, any cloud-storage vendor — hand-writing a tool wrapper per API doesn't scale. The integrations team becomes the bottleneck: each new customer integration takes days, and the agent's effective toolset is capped at whatever has been hand-wrapped.

The general problem is **dynamic tool surfaces**: turning a machine-readable API description into a typed agent-usable tool at runtime, without a human in the loop.

#### Why Naïve Approaches Fail

- 

*"Have the model construct HTTP requests directly."* The model gets URLs and body shapes wrong. The failure mode is silent (the API returns 4xx, the model interprets the response as the answer).

- 

*"Generate tool wrappers offline."* Works until the API changes, until a new customer wants a different API, or until the agent needs to handle a class of APIs rather than a specific one.

- 

*"Use a model with built-in API knowledge."* The knowledge is stale and inconsistent across APIs.

#### The Mechanism

A parser that produces typed tool descriptors from OpenAPI (or GraphQL, AsyncAPI, gRPC reflection). A synthesis step that produces natural-language tool descriptions from the parsed schema. An argument-construction guard that validates against the schema before any call is made. An error-recovery path that maps API error responses back to actionable feedback.

![Pattern 055 — Agent 31 — The API-Schema Adapter Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5df5bacc91e216d9279e_codex-pattern-055-agent-31-the-api-schema-adapter-agent-the-mechanism.png)

```python
# tools/api_adapter.py
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
```

#### Trade-offs and Alternatives

The adapter is only as good as the OpenAPI specs it consumes. Most public APIs have specs of varying quality, but many internal APIs don't have specs at all.

The pattern requires either spec-quality investment upstream or a tolerance for specs being wrong (graceful degradation when a derived tool doesn't actually work as documented).

For APIs where the spec is reliably good (Stripe, GitHub, the big SaaS vendors), the adapter is dramatically better than hand-wrapping. For APIs where the spec is unreliable, a thin hand-wrapped layer is more robust.

#### Production Failure Modes

- 

**Spec-API drift:** The spec is right at some point. But then the API changes, the spec isn't updated, and the derived tools are broken. Mitigate by validating derived tools against contract tests before exposing them to the policy.

- 

**Authentication leakage:** Credentials end up in tool descriptions exposed in prompts. Mitigate by routing all auth through the auth provider (the code shows this) so secrets are never in the descriptor itself.

- 

**Schema-validation false rejection.** The schema is over-restrictive, and valid calls are rejected. Mitigate by sampling rejections for operator review and loosening schemas where the spec is incorrect.

#### Case Study

An integration-platform agent at a B2B vendor lets a user say "connect Salesforce and run this query" and turns the request into a validated, schema-typed call against the user's tenant without a developer ever touching the integration. The platform supports approximately 480 distinct APIs via this pattern, with hand-wrapping reserved for the dozen most-used APIs that need richer behavior than the spec alone supports.

**Pairs with:** Schema-Inference (Agent 7), Database Query Synthesizer (Agent 35), Tool Selector (Agent 30).
