# Agent 35 — The Database Query Synthesizer Agent

### Agent 35 — The Database Query Synthesizer Agent

*Translates intent into SQL, Cypher, or similar query languages and validates before execution.*

#### The Problem

A natural-language-to-SQL agent that runs the generated query directly is a security incident waiting to happen. Beyond security, raw text-to-SQL has accuracy problems: ambiguous column names, wrong joins, accidental cross joins, and queries that return wrong-but-plausible numbers. The user trusts the answer, the answer is wrong, the dashboard shows the wrong number, and decisions get made.

The general problem is **safe and auditable natural-language-to-query translation**: producing a query that does what the user meant, never does anything else, and is explained to the user before execution on consequential queries.

#### Why Naïve Approaches Fail

- 

*"Run whatever the model produces."* Inevitable injection vulnerability, inevitable accuracy problems.

- 

*"Allow only* `SELECT` *queries."* Limits but doesn't prevent damage (a wrong `SELECT` can still produce wrong numbers for downstream decisions).

- 

*"Have the model paraphrase the query before running."* Adds a check but doesn't bound the query's safety properties structurally.

#### The Mechanism

Schema introspection at session start with a freshness policy. Query synthesis against a schema-aware grammar rather than free-form text-to-SQL. A static safety check covering read-only enforcement, parameterization, and join-cost bounds. A natural-language explanation produced before execution for user confirmation on consequential queries. A structured result interface that distinguishes data from metadata.

![Pattern 059 — Agent 35 — The Database Query Synthesizer Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5df5f32977bfedb072ed_codex-pattern-059-agent-35-the-database-query-synthesizer-agent-the-mechanism.png)

```python
# tools/db_synthesizer.py
from dataclasses import dataclass, field
import sqlparse

@dataclass
class TableSchema:
    name: str
    columns: list[dict]            # {name, type, nullable, description}
    primary_key: list[str]
    foreign_keys: list[dict]
    row_count_estimate: int

@dataclass
class SynthesizedQuery:
    sql: str
    parameters: dict
    estimated_rows: int
    explanation: str               # natural language
    consequential: bool            # writes, or large reads, or sensitive tables
    safety_violations: list[str]

class DatabaseQuerySynthesizerAgent:
    def __init__(self, schema: list[TableSchema], synthesizer_llm, executor,
                 *, query_timeout_s: float = 30, max_rows: int = 100000):
        self.schema = schema
        self.llm = synthesizer_llm
        self.executor = executor
        self.timeout = query_timeout_s
        self.max_rows = max_rows
    
    def synthesize(self, intent: str) -> SynthesizedQuery:
        response = self.llm.call(
            messages=[
                {"role": "system", "content": SYNTHESIS_PROMPT.format(
                    schema=self._render_schema())},
                {"role": "user", "content": intent}
            ],
            schema=SYNTHESIS_SCHEMA,
        )
        synthesized = SynthesizedQuery(
            sql=response["sql"], parameters=response.get("parameters", {}),
            estimated_rows=response.get("estimated_rows", 0),
            explanation=response.get("explanation", ""),
            consequential=False, safety_violations=[],
        )
        synthesized.safety_violations = self._safety_check(synthesized)
        synthesized.consequential = self._is_consequential(synthesized)
        return synthesized
    
    def execute(self, query: SynthesizedQuery, *,
                approved_by_user: bool = False) -> dict:
        if query.safety_violations:
            return {"error": "safety_violations", "violations": query.safety_violations}
        if query.consequential and not approved_by_user:
            return {"error": "requires_approval", "explanation": query.explanation}
        return self.executor.run(query.sql, query.parameters,
                                 timeout=self.timeout, max_rows=self.max_rows)
    
    def _safety_check(self, query: SynthesizedQuery) -> list[str]:
        violations = []
        parsed = sqlparse.parse(query.sql)
        if not parsed:
            violations.append("unparseable")
            return violations
        stmt = parsed[0]
        # Read-only enforcement
        if stmt.get_type() not in ("SELECT", "UNKNOWN"):
            violations.append(f"write_query:{stmt.get_type()}")
        # No multiple statements
        if ";" in query.sql.rstrip().rstrip(";"):
            violations.append("multiple_statements")
        # Parameterization check — all string-like values should be parameterized
        if self._has_string_literals(stmt) and not query.parameters:
            violations.append("unparameterized_literals")
        # Estimated rows over cap
        if query.estimated_rows > self.max_rows:
            violations.append(f"estimated_rows_over_cap:{query.estimated_rows}")
        return violations
    
    def _is_consequential(self, query: SynthesizedQuery) -> bool:
        if query.estimated_rows > 10000:
            return True
        # Heuristic: queries touching tables marked sensitive
        for table in self.schema:
            if table.name in query.sql and "sensitive" in (table.columns[0].get("tags") or []):
                return True
        return False
    
    def _render_schema(self) -> str:
        out = []
        for t in self.schema:
            cols = ", ".join(f"{c['name']} {c['type']}" for c in t.columns)
            out.append(f"TABLE {t.name} ({cols}); rows~{t.row_count_estimate}")
        return "\n".join(out)
```

#### Trade-offs and Alternatives

Schema-aware synthesis adds latency (schema introspection, safety checking) and operational complexity (the schema has to be kept in sync, queries against stale schemas fail).

For agents operating against a small, stable schema, the cost is low. For agents operating across many tenants' schemas, the freshness policy becomes a real concern.

For databases with constrained query interfaces (a parameterized stored-procedure surface or a Looker-style modeling layer), the synthesizer should target the constrained interface rather than raw SQL. The constraint surface already encodes most of the safety properties.

#### Production Failure Modes

- 

**Wrong join:** The synthesizer joins on the wrong keys, and the result is plausible but wrong. Mitigate by enforcing primary-key/foreign-key adherence in the safety check, refusing joins that don't follow declared relationships.

- 

**Schema drift:** Tables are added, columns are renamed. The cached schema is stale, and synthesis fails on real tables or succeeds on phantom ones. Mitigate by refreshing the schema on a short TTL and invalidating cached schemas on detected drift.

- 

**Synthesizer hallucination of columns:** The model invents a column name that doesn't exist. Mitigate by parsing the SQL post-synthesis and verifying every referenced column exists in the schema (reject and re-prompt if not).

#### Case Study

A self-service analytics product at a mid-sized enterprise replaces approximately 70% of ad-hoc analyst requests with synthesizer-driven queries. Every query is explained in natural language to the requesting user before execution on consequential queries.

The user-confirmed accuracy of the explanations (sampled and reviewed) is 91%, and the rate of synthesized queries returning wrong-but-plausible numbers (compared to expert hand-written queries on the same intent) is 3.4%, down from 14% before the safety-check and explanation pattern was added.

**Pairs with:** Schema-Inference (Agent 7), Provenance Tracker (Agent 55), Side-Effect Auditor (Agent 37).
