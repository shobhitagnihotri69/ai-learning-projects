# Agent 7 — The Schema-Inference Agent

### Agent 7 — The Schema-Inference Agent

*Discovers the structure of an unknown data source by sampling and probing.*

#### The Problem

The agent is pointed at a new database, a new file, a new API, or a new event stream, and is asked to figure out what's in it. The user doesn't have a schema – the schema is what the user wants. Without an inference step, the only way forward is for a human to write a config — which doesn't scale across thousands of customers, hundreds of data sources, or fast-changing schemas.

The general problem is **structure discovery at runtime**: producing a usable model of an unknown data source from samples, with explicit confidence and explicit unknowns, in a form downstream patterns can rely on.

#### Why Naïve Approaches Fail

- 

*"Type-infer the first row."* Wrong on most data. The first row is often atypical, has missing values, or has different types than the rest of the corpus.

- 

*"Ask an LLM to look at a sample and produce a schema."* Often hallucinates fields that aren't there, misses fields that are, and produces output with no calibrated confidence.

- 

*"Use a generic schema-inference library."* They're tuned for relational data and break on JSON with nested arrays, on CSVs with inconsistent delimiters, or on APIs whose responses vary by tenant.

#### The Mechanism

The schema-inference agent samples records strategically, hypothesizes a schema, validates the hypothesis against more records, refines, and emits a schema document with explicit uncertainty annotations.

![Pattern 031 — Agent 7 — The Schema-Inference Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5dcade598c27fe391738_codex-pattern-031-agent-7-the-schema-inference-agent-the-mechanism.png)

```python
# perception/schema_inference.py
from dataclasses import dataclass, field
from collections import Counter

@dataclass
class FieldSchema:
    name: str
    types: dict[str, int]              # observed type -> count
    nullable: bool
    examples: list                     # 3-5 representative values
    confidence: float                  # 0-1, based on consistency
    range: tuple | None = None          # for numeric / temporal fields
    enum_candidates: list | None = None # likely-categorical
    
    @property
    def dominant_type(self) -> str:
        return max(self.types.items(), key=lambda kv: kv[1])[0]

@dataclass
class InferredSchema:
    source_id: str
    sampled_records: int
    total_records_estimate: int | None
    fields: dict[str, FieldSchema] = field(default_factory=dict)
    relationships: list[dict] = field(default_factory=list)  # inferred FK candidates
    confidence: float = 0.0
    open_questions: list[str] = field(default_factory=list)

class SchemaInferenceAgent:
    def __init__(self, source_adapter, sample_target: int = 1000,
                 confidence_target: float = 0.9):
        self.source = source_adapter
        self.sample_target = sample_target
        self.target = confidence_target
    
    def infer(self) -> InferredSchema:
        schema = InferredSchema(
            source_id=self.source.id,
            sampled_records=0,
            total_records_estimate=self.source.estimate_size(),
        )
        # 1. Stratified sampling: head, tail, middle, plus random
        samples = self._stratified_sample()
        for record in samples:
            self._update_schema(schema, record)
        # 2. Confidence check; if too low, sample more strategically
        if schema.confidence < self.target:
            extra = self._sample_more(schema)
            for record in extra:
                self._update_schema(schema, record)
        # 3. Categorical detection
        for field_schema in schema.fields.values():
            if self._looks_categorical(field_schema):
                field_schema.enum_candidates = self._extract_enum(field_schema)
        # 4. Relationship inference
        schema.relationships = self._infer_relationships(schema, samples)
        return schema
    
    def _update_schema(self, schema: InferredSchema, record: dict) -> None:
        for k, v in record.items():
            fs = schema.fields.setdefault(k, FieldSchema(
                name=k, types=Counter(), nullable=False, examples=[], confidence=0))
            t = type(v).__name__ if v is not None else "null"
            fs.types[t] += 1
            if v is None:
                fs.nullable = True
            elif len(fs.examples) < 5:
                fs.examples.append(v)
        schema.sampled_records += 1
        self._update_confidence(schema)
    
    def _looks_categorical(self, fs: FieldSchema) -> bool:
        if fs.dominant_type != "str":
            return False
        unique_vals = len(set(fs.examples))
        return unique_vals < 20 and unique_vals < 0.1 * len(fs.examples)
```

#### Trade-offs and Alternatives

Schema inference is sampling-bound: precision improves with the number of samples but with diminishing returns.

For sources where a definitive schema exists elsewhere (a managed database with `INFORMATION_SCHEMA`, an OpenAPI document for an API, a Protobuf descriptor for a message stream), use the authoritative source and skip inference. Schema inference earns its keep when no authoritative source exists or when the authoritative source is stale/unreliable.

A common simplification: don't infer relationships at all. Field-level schemas are most of the value and relationship inference is brittle and easy to get wrong. Leave relationships to the downstream policy unless the use case explicitly requires them.

#### Production Failure Modes

- 

**Long-tail field surprise:** A field appears in 0.5% of records with a different type than the inferred dominant one, and the downstream policy crashes on it. Mitigate by sampling the long tail explicitly and capturing rare-type variants in the schema.

- 

**Confidence overshoot:** The inference reports high confidence on a field that varies across tenants. Mitigate by inferring per-tenant when the source supports it, and surface tenant-variance as an explicit field property otherwise.

- 

**Categorical false positive:** A field has only twelve distinct values in the sample but unbounded values in the source. Mitigate by sampling more aggressively when categorical detection is sensitive to it.

#### Case Study

A data-onboarding workflow at a B2B vendor lets new customers connect a SQL database and receive a starter analytics dashboard inside a single session. The Schema-Inference Agent runs against the customer's connected database, samples up to ten thousand rows across tables, infers field schemas and likely relationships, and produces a schema document the downstream dashboard-generation agent consumes.

Before the schema-inference step, onboarding required a customer-success engineer to write a config per customer (median three days). After, the median onboarding time dropped to under twenty minutes self-serve, with 71% of customers reaching a dashboard without any human assist.

**Pairs with:** Document Layout (Agent 2), Database Query Synthesizer (Agent 35), API-Schema Adapter (Agent 31).

### A Note on the References in the Deeper Dives

The "Theoretical roots" sub-section under each agent names papers, researchers, and intellectual traditions. **These references were compiled from working knowledge of the literature. They should be verified for specific information like publication year.**

If you want to cite any of them in your own work, you should should consult the bibliography at the end of the book, then verify the canonical citation against a reputable source (Google Scholar, the publishing venue, or the author's homepage).

The references are accurate as a *direction* — they point at real bodies of work — but a specific year or first author should be checked before reproduction.
