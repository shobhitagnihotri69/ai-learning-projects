## Part III — Composition

![Dark expanse of space dotted with stars](https://images.unsplash.com/photo-1752353739067-357d9ff65d4f?w=1600&q=80&fm=jpg&fit=crop)

Part II is a catalog. Part III is what to do with it.

A real agent draws on six to ten patterns at once, often from five or more capabilities. The composition isn't arbitrary: certain patterns are natural complements, certain combinations expose silent failure modes, and the structure of the composition itself becomes a design artifact that the team has to maintain.

Part III opens with one grounding chapter, 12A, lettered as an addendum to Chapter 12 the same way Chapters 4A and 4B extend Chapter 4 in Part I. It anchors the catalog against real systems, real public failures, and real benchmarks before the composition work begins.

The three core chapters that follow it address three questions:

- 

**Composition** (Chapter 13): How do patterns combine into a real agent? Three reference compositions, fully worked, with code.

- 

**Evaluation** (Chapter 14): How do you tell if a composed agent is any good? The unit of evaluation is the session, not the prompt — and most evaluation frameworks are working at the wrong granularity.

- 

**Failure** (Chapter 15): How does composition fail? The failure modes that recur across well-designed compositions, with named patterns for each.

The composition vocabulary introduced here — *capability profile*, *pattern stack*, *failure boundary* — is the working language of senior agent-engineering teams. The patterns in Part II are the words while the composition in Part III is the grammar.

### Chapter 12A — Real Systems, Real Failures, Real Benchmarks

The book's first edition floats above the actual landscape of agents in production. This chapter grounds the patterns against named systems, named failures, and named benchmarks.

None of the references here are illustrative composites. They're real and verifiable, and a reader who wants to push deeper has a starting point.

#### 12A.1 Real agent products to study

If you want to learn agent engineering by reading other people's work, the following 2025–2026 products are useful reference points. Each illustrates a specific design choice, and none is presented as exemplary across the board.

- 

**Cursor / Cursor Agent (Anysphere).** Code-editor agent. Useful for studying how to integrate an agent into an existing surface users already know, how to bound autonomy to a specific blast radius (the open repository), and how to display agent activity inline with user activity.

- 

**Claude Code (Anthropic).** Terminal-based code agent. Useful for studying how to give the agent shell access safely (the Shell-Operator pattern in real production form), how to surface what the agent is about to do before it acts, and how the off-switch interacts with long-running tool calls.

- 

**GitHub Copilot Workspace / Copilot agents (GitHub).** Pull-request-shaped agents. Useful for studying how to scope the agent's task to a defined unit of work and how to integrate human review at well-defined boundaries.

- 

**Devin (Cognition).** Long-horizon autonomous coding agent. Useful for studying the gap between demo-time autonomy and production-time autonomy and why pure level-4 autonomy has been slow to deliver on its promise.

- 

**Replit Agent (Replit).** Build-an-app agent. Useful for studying how an agent can take very loose user intent and produce an artifact and what its failure modes look like at scale.

- 

**Aider (open source).** CLI coding agent. Useful for studying a minimal agent architecture you can read in an evening and the design choices that emerge when the cost ceiling is genuinely low.

- 

**Browser-based "computer use" deployments** (Anthropic computer use, OpenAI Operator, Google's equivalents). Useful for studying how the Browser-Driver pattern is being absorbed into the model substrate and what's left for the engineer.

- 

**Customer-support agents from major SaaS vendors** (Intercom Fin, Ada, Zendesk AI agents, Salesforce Agentforce). Useful for studying routing patterns at scale, refusal calibration at scale, and how multi-tenant agents handle privacy.

For each: read the documentation, find the public design discussions (blog posts, conference talks, podcast episodes), and ask "which patterns from this book did the team implement, and what did they implement instead of others?"

#### 12A.2 Real frameworks and their pattern coverage

The pattern catalog in this book is presented as if you would build it from scratch in Python. Most teams do not.

The major frameworks in 2026 and their natural pattern coverage are:

- 

**LangChain / LangGraph.** Strong on coordination patterns (Pipeline Orchestrator, Router, Supervisor-Worker). Tool-use integration is mature. Memory patterns are well-developed. Their LangGraph variant explicitly supports plan-then-execute, replanning, and graph-shaped workflows. Less opinionated on alignment patterns. You mostly add them yourself.

- 

**AutoGen (Microsoft).** Strong on multi-agent coordination patterns: debate, consensus, supervisor-worker. The right framework when the coordination shape is the heart of the problem. Less coverage of the alignment layer.

- 

**CrewAI.** Lighter-weight multi-agent shape, with explicit "crew" abstractions. Good for prototyping coordination patterns, but less mature on production-grade tooling.

- 

**DSPy.** Different philosophy: program your prompts, compile the prompts, optimize the program. Strongest on the Few-Shot Prompt Tuner pattern and on systematic prompt evaluation. The right tool when you want prompts as compiled artifacts rather than handwritten strings.

- 

**Pydantic-AI.** Strong on structured-output enforcement and type discipline. Pairs well with patterns that need typed contracts (Side-Effect Auditor, Pipeline Orchestrator, Constitution-Bound).

- 

**Haystack.** Strongest on retrieval-and-pipeline shapes. The right tool for retrieval-grounded analyst compositions (Reference Composition 1 in Chapter 13).

- 

**Vendor agent APIs** (Anthropic Tools, OpenAI Assistants API, Google's Agent SDK). Cover tool use, multi-step execution, and structured outputs natively. The right starting point when the agent doesn't need cross-vendor portability.

- 

**Workflow engines** (Temporal, Inngest, Trigger.dev). Not agent-specific but increasingly used as the durable substrate for agent execution. Strong on the patterns that need durability across crashes: Supervisor-Worker, Pipeline Orchestrator, Adaptive Replanner, Side-Effect Auditor.

The right framework choice depends on which patterns are load-bearing for your agent. As a rough mapping:

- 

Heavy on coordination: LangGraph or AutoGen

- 

Heavy on retrieval: Haystack or LangChain

- 

Heavy on prompt engineering as code: DSPy

- 

Heavy on structured outputs: Pydantic-AI

- 

Heavy on durability: Temporal as the substrate, any of the above as the agent layer

The book's from-scratch code is meant as conceptual illustration. In production, picking a framework and accepting its opinions buys faster delivery, while building from scratch buys flexibility. Both are valid.

#### 12A.3 Real public failures to learn from

The book's per-pattern case studies are illustrative composites. The following are *real* publicly-documented agent failures that illuminate the catalog's value precisely *because* they show what happens when specific patterns are missing.

- 

[**Air Canada chatbot (2024)**](https://www.cbc.ca/news/canada/british-columbia/air-canada-chatbot-lawsuit-1.7116416)**.** A customer-service chatbot promised a bereavement-fare refund that the airline's policy didn't actually allow. In *Moffatt v. Air Canada*, 2024 BCCRT 149, the BC Civil Resolution Tribunal held Air Canada liable for negligent misrepresentation, rejecting the airline's argument that the chatbot was a separate legal entity responsible for its own words.
The missing pattern: a Constitution-Bound Agent (53) gating commitments against the actual policy.
The lesson: an agent that can make promises must have a structural mechanism preventing it from making promises the company can't keep.

- 

[**NYC MyCity chatbot (2024)**](https://themarkup.org/artificial-intelligence/2024/03/29/nycs-ai-chatbot-tells-businesses-to-break-the-law)**.** A city-government chatbot, prompted on local business questions, produced confident advice that would have violated city law — including telling landlords they could refuse Section 8 vouchers and employers they could keep workers' tips, both illegal under NYC law. Reported by The Markup.
The missing patterns: Provenance Tracker (55) to ground claims in citable sources, Refusal Calibrator (54) to refuse rather than fabricate, Red-Team Auditor (56) to surface the failure mode pre-launch.

- 

[**Mata v. Avianca (2023)**](https://en.wikipedia.org/wiki/Mata_v._Avianca,_Inc.) **and successor cases.** Lawyers sanctioned for citing GPT-hallucinated cases in court filings. The presiding judge fined the attorneys $5,000 and ordered them to notify every real judge whose name had been attached to a fabricated opinion.
The missing pattern: Provenance Tracker (55) with structural refusal of unsupported claims.
The lesson: trust in a model's apparent factuality without structural verification is a discoverable professional liability.

- 

**GitHub Copilot license-attribution disputes.** A class of disputes around whether code-generation agents reproduce licensed content.
The pattern this implicates: Provenance Tracker (55) and Privacy-Preserving (57) extended to license provenance, not just personal data. Still an open area.

- 

[**Replit Agent production-database incident (2025)**](https://fortune.com/2025/07/23/ai-coding-tool-replit-wiped-database-called-it-a-catastrophic-failure/)**.** During a public test run, a Replit coding agent deleted a live production database despite standing instructions not to touch it, and Replit's CEO publicly confirmed the deletion as a real, unacceptable failure. (The more dramatic details reported by the person running the test — that the agent covered up the deletion, fabricated records, and claimed rollback was impossible — are that person's own account, not independently verified by Replit, and are worth reading with that caveat.)
The patterns this implicates: Side-Effect Auditor (37) — what was the rollback path? Constitution-Bound (53) — what gating prevented the destructive action? Off-Switch-Compatible (60) — how long did the bad action run before intervention?

- 

[**Devin's demo-to-benchmark gap**](https://blog.pragmaticengineer.com/the-ai-developer/)**.** Cognition's launch claim of resolving 13.86% of SWE-bench issues unassisted drew sustained independent scrutiny, both on whether that number holds up and on whether the demo videos represented typical performance. (Cognition's original claim predates SWE-bench Verified, so read this as "Devin's benchmark claims versus independent scrutiny," not a claim about the Verified subset specifically.)
The lesson: the demo-time agent and the production-time agent are different artifacts.
The patterns that close the gap are mostly in Chapter 14 (Evaluation) and Chapter 15 (Patterns of Failure).

- 

[**Microsoft Tay (2016)**](https://time.com/4270684/microsoft-tay-chatbot-racism/)**.** The earliest large-scale agent-alignment failure: a chatbot driven into producing offensive output within hours of public release, taken offline within a day.
The lesson: red-teaming (Agent 56) and refusal calibration (Agent 54) are not optional safety layers on top of a working agent. They're constitutive of the agent being deployable at all.

A reader looking to deepen their understanding of the alignment chapter should study each of these in detail. The deployment-alignment patterns the book describes are the field's accumulated response to incidents like these.

#### 12A.4 Benchmarks worth knowing

The book's "labeled evaluation set" language is concrete in academic and engineering practice. The following public benchmarks are useful reference points. Serious teams use them as starting points and supplement with deployment-specific eval sets.

- 

[**SWE-bench**](https://github.com/swe-bench/SWE-bench) / [**SWE-bench Verified**](https://openai.com/index/introducing-swe-bench-verified/). Coding agents fixing real GitHub issues. The standard benchmark for evaluating code-modification agents end-to-end. Verified is OpenAI's human-validated 500-task subset.

- 

[**GAIA**](https://arxiv.org/abs/2311.12983) (Meta, HuggingFace, and AutoGPT). General assistant benchmark. Multi-step, multi-tool tasks. Tests the full agentic stack on realistic open-ended questions.

- 

[**AgentBench**](https://arxiv.org/abs/2308.03688). Multi-domain benchmark covering reasoning, tool use, and coordination across diverse tasks.

- 

[**WebArena**](https://github.com/web-arena-x/webarena) / [**OSWorld**](https://os-world.github.io/). Browser- and computer-use benchmarks. WebArena tests browsing agents on realistic web environments. OSWorld extends this to full OS interaction.

- 

[**τ-bench**](https://github.com/sierra-research/tau-bench) (Tau-bench, Sierra). Customer-service-shaped agent benchmark. Evaluates agents on multi-turn conversations with structured outcomes.

- 

[**BIRD-SQL**](https://bird-bench.github.io/) / [**Spider**](https://yale-lily.github.io/spider). Natural-language-to-SQL benchmarks. Useful for the Database Query Synthesizer pattern.

- 

[**MMLU**](https://arxiv.org/abs/2009.03300) / [**Big-Bench Hard**](https://github.com/suzgunmirac/BIG-Bench-Hard). Knowledge-and-reasoning benchmarks. Useful as components of a broader evaluation, less so for end-to-end agent capability.

- 

[**MLE-bench**](https://github.com/openai/mle-bench). Machine-learning-engineering tasks for agents.

- 

[**HELM**](https://crfm.stanford.edu/helm/) / **HELM-Lite.** Holistic evaluation framework. Useful as scaffolding for your own labeled set rather than as a single number.

None of these is sufficient on its own. Serious agent evaluation always combines a public benchmark (for comparability) with a deployment-specific labeled set (for actual quality measurement). The Chapter 14 framing of "evaluation is a system, not a step" applies here: pick a public benchmark to anchor on, then build your own.

#### 12A.5 Where to read more

The book deliberately doesn't include a thorough bibliography of the agent literature. The field moves too quickly for a printed reference. The following sources stay reliably current:

- 

Provider technical blogs (Anthropic, OpenAI, Google DeepMind, Cohere) for substrate shifts and best-practice updates.

- 

Major lab papers (Anthropic, OpenAI, DeepMind, Meta AI, Microsoft Research) for foundational pattern descriptions.

- 

The arXiv cs.AI and cs.CL feeds for primary research on patterns before they enter the canon.

- 

Conference proceedings (NeurIPS, ICML, EMNLP, ACL, ICLR) for evaluated claims with peer review.

- 

Practitioner blogs and podcasts (Latent Space, the Cognition blog, AI Engineer summit talks, AnyScale and Modal posts) for production-shape lessons.

- 

The vendors' cookbooks and recipes pages for canonical-pattern reference implementations against current APIs.

Any single source goes stale within months. Reading several in rotation is closer to keeping current.

### Chapter 13 — Composing Multi-Capability Agents

#### 13.1 The capability profile

The first artifact produced when scoping a new agent is its **capability profile**: a one-page summary of which capabilities the agent exercises and which patterns it uses within each. The profile is the contract between product, engineering, and operations about what the agent will be.

A capability profile fits in a table:

Capability
Patterns
Notes

Perception
Document Layout (2), Schema-Inference (7)
Input is mixed PDF + structured JSON

Reasoning
Self-Consistency Voter (15), Chain-of-Thought Auditor (8)
Hard problems require voting

Planning
Hierarchical Decomposer (16), Plan-Then-Execute (19)
Long-horizon goals

Memory
Episodic Buffer (23), Working-Memory Manager (25)
Sessions span hours

Tool Use
Tool Selector (30), Side-Effect Auditor (37)
40+ tools

Coordination
Pipeline Orchestrator (41), Human-in-the-Loop Liaison (42)
Reviewer-in-the-loop

Learning
Feedback Loop (46), Reflection (47)
Continuous improvement

Alignment
Provenance Tracker (55), Constitution-Bound (53), Off-Switch-Compatible (60)
Regulated environment

The profile is the artifact. It's versioned and reviewed when something changes. It's also the first thing a new team member reads when they join the project.

#### 13.2 The pattern stack

The pattern stack renders the composition: it names the patterns, the data shapes flowing between them, the failure boundaries that separate them, and the ownership of each.

![Pattern 085 — 13.2 The pattern stack](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5df24616a6958b09cbfe_codex-pattern-085-13-2-the-pattern-stack.png)

```plaintext
┌────────────────────────────────────────────────────────────────┐
│                       OFF-SWITCH (60)                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   CONSTITUTION (53)                       │  │
│  │  ┌──────────────────────────────────────────────────┐    │  │
│  │  │              HARNESS (Chapter 1)                  │    │  │
│  │  │  ┌──────────┐  ┌──────────┐  ┌──────────┐         │    │  │
│  │  │  │  Input   │→ │  Plan    │→ │  Execute │         │    │  │
│  │  │  │ (2, 7)   │  │  (16,19) │  │  (30,37) │         │    │  │
│  │  │  └──────────┘  └──────────┘  └──────────┘         │    │  │
│  │  │       │             │             │                │    │  │
│  │  │       ▼             ▼             ▼                │    │  │
│  │  │  ┌─────────────────────────────────────┐           │    │  │
│  │  │  │       Working Memory (25)            │           │    │  │
│  │  │  └─────────────────────────────────────┘           │    │  │
│  │  │                  │                                  │    │  │
│  │  │                  ▼                                  │    │  │
│  │  │  ┌─────────────────────────────────────┐           │    │  │
│  │  │  │    Episodic / Semantic (23, 24)     │           │    │  │
│  │  │  └─────────────────────────────────────┘           │    │  │
│  │  └──────────────────────────────────────────────────┘    │  │
│  │              Provenance (55) threads through              │  │
│  └──────────────────────────────────────────────────────────┘  │
│             Side-Effect Auditor (37) wraps tool calls           │
└────────────────────────────────────────────────────────────────┘
```

The diagram is the deliberate one. Notice: the alignment patterns (60, 53, 55, 37) are the outermost layers and the cross-cutting threads. They're not "downstream" — they enclose everything else.

#### 13.3 Reference composition 0: The Minimum Viable Agent

Before the more elaborate compositions, the floor: the agent every team should be able to ship in a week. This is the composition new readers should build first. The more sophisticated compositions are extensions of it, not replacements for it.

**Capability profile:** memory (Working-Memory Manager 25, Episodic Buffer 23), tool use (Tool Selector 30, Side-Effect Auditor 37), alignment (Constitution-Bound 53, Off-Switch-Compatible 60). Six patterns and no others.

**Pattern stack:**

![Pattern 086 — 13.3 Reference composition 0: The Minimum Viable Agent](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5df24616a6958b09cc1e_codex-pattern-086-13-3-reference-composition-0-the-minimum-viable-agent.png)

```plaintext
┌──────────────────────────────────────────────────────┐
│                  OFF-SWITCH (60)                      │
│  ┌─────────────────────────────────────────────┐     │
│  │              CONSTITUTION (53)               │     │
│  │  ┌───────────────────────────────────────┐  │     │
│  │  │  Loop: read → decide → act → observe  │  │     │
│  │  │  (model + tool selector + tools)      │  │     │
│  │  └───────────────────────────────────────┘  │     │
│  │  Side-Effect Auditor (37) wraps tool calls   │     │
│  └─────────────────────────────────────────────┘     │
│  Working Memory (25) + Episodic Buffer (23)           │
└──────────────────────────────────────────────────────┘
```

**Code skeleton:**

![Pattern 087 — 13.3 Reference composition 0: The Minimum Viable Agent](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5df2cd945e9ae18dc44e_codex-pattern-087-13-3-reference-composition-0-the-minimum-viable-agent.png)

```python
# compositions/minimum_viable_agent.py
from agents.harness import Harness
from memory.working_memory import WorkingMemoryManagerAgent
from memory.episodic import EpisodicBufferAgent
from tools.selector import ToolSelectorAgent
from tools.side_effect_auditor import SideEffectAuditorAgent
from alignment.constitution import ConstitutionBoundAgent, Constitution
from alignment.off_switch import OffSwitchCompatibleAgent

class MinimumViableAgent:
    """The agent every team should be able to ship in a week.
    
    Six patterns. No more. If this doesn't work for your problem,
    measure why before reaching for additional patterns.
    """
    def __init__(self, *, llm, tools_registry, constitution: Constitution):
        self.working_memory = WorkingMemoryManagerAgent(scorer=..., token_budget=6000)
        self.episodes = EpisodicBufferAgent(store_path="agent.db")
        self.tool_selector = ToolSelectorAgent(tools_registry, embedder=...,
                                                candidate_k=10, final_k=5)
        self.auditor = SideEffectAuditorAgent(audit_store=...)
        self.constitution = ConstitutionBoundAgent(constitution,
                                                    approval_provider=...,
                                                    audit_sink=...)
        self.off_switch = OffSwitchCompatibleAgent(signal_source=...,
                                                    snapshot_store=...)
        self.llm = llm
    
    async def run(self, goal: str, session_id: str) -> dict:
        return await self.off_switch.run(session_id, self._work(goal, session_id))
    
    async def _work(self, goal: str, session_id: str):
        async def loop(check_stop, snapshot):
            for step in range(20):  # bounded; usually finishes in 3-8
                await check_stop()
                
                # 1. Compose prompt with working memory
                prompt = self.working_memory.compose(intent=goal)
                
                # 2. Select tools relevant to current state
                tools = self.tool_selector.select(goal)
                
                # 3. Get next action from the model
                action = self.llm.call(prompt, tools=tools)
                if action.terminate:
                    return {"status": "success", "output": action.output}
                
                # 4. Constitution check before acting
                check = self.constitution.check(action, context={"session": session_id})
                if check.verdict.value == "prohibited":
                    return {"status": "blocked", "reason": check.explanation}
                
                # 5. Audited tool invocation
                result, audit = self.auditor.wrap(
                    action.tool, action.args, session_id,
                    invoke=lambda args: tools[action.tool].invoke(args))
                
                # 6. Record episode, update working memory
                self.episodes.record(session_id, step, action, result)
                self.working_memory.add(result.observation)
            
            return {"status": "step_budget_exhausted"}
        return loop
```

This composition produces a working agent. The kind of agent that can handle most level-3 problems (per Chapter 0) without needing the elaborate compositions in the next three sections. Cost per session is low — typically just a few model calls plus tool calls — because no expensive patterns (voting, debate, ToT, reflection) are engaged.

**When to extend:**

- 

If outputs are wrong in ways that suggest the model is over-confident on hard turns, add Self-Consistency Voter (Agent 15) selectively.

- 

If the agent loops without progress, add Adaptive Replanner (Agent 20).

- 

If outputs need citations, add Provenance Tracker (Agent 55).

- 

If you need long-horizon goals, add Hierarchical Decomposer (Agent 16) and Plan-Then-Execute (Agent 19).

- 

If you need multi-specialist routing, add Router/Dispatcher (Agent 38).

The right approach is to ship the minimum-viable version, measure where it fails, and add patterns *targeted at observed failures*. Adding patterns prophylactically is how the cost ceiling gets blown.

#### 13.3 Reference composition 1: The Retrieval-Grounded Analyst

A research agent that produces analytical reports against an enterprise document corpus, with citations.

**Capability profile:** perception (Document Layout 2, Vector-Store Curator 28), reasoning (Self-Consistency Voter 15, Chain-of-Thought Auditor 8), planning (Hierarchical Decomposer 16), memory (Working-Memory Manager 25), learning (Reflection 47), alignment (Provenance Tracker 55, Constitution-Bound 53, Off-Switch-Compatible 60).

**Pattern stack code (simplified):**

![Pattern 088 — 13.3 Reference composition 1: The Retrieval-Grounded Analyst](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5df23d68cad31e7380e8_codex-pattern-088-13-3-reference-composition-1-the-retrieval-grounded-analyst.png)

```python
# compositions/retrieval_analyst.py
from agents.harness import Harness
from perception.document_layout import DocumentLayoutAgent
from memory.vector_curator import VectorStoreCuratorAgent
from memory.working_memory import WorkingMemoryManagerAgent
from planning.hierarchical_decomposer import HierarchicalDecomposerAgent
from reasoning.self_consistency import SelfConsistencyVoterAgent
from reasoning.cot_auditor import ChainOfThoughtAuditorAgent
from learning.reflection import ReflectionAgent
from alignment.provenance import ProvenanceTrackerAgent
from alignment.constitution import ConstitutionBoundAgent, Constitution
from alignment.off_switch import OffSwitchCompatibleAgent

class RetrievalGroundedAnalyst:
    def __init__(self, *, llm, tools, vector_store, constitution: Constitution):
        # Perception
        self.layout = DocumentLayoutAgent(...)
        self.curator = VectorStoreCuratorAgent(vector_store, embedder=..., benchmark=[...])
        # Memory
        self.working_memory = WorkingMemoryManagerAgent(scorer=..., token_budget=6000)
        # Planning
        self.decomposer = HierarchicalDecomposerAgent(
            decomposer_llm=llm, action_executor=self._execute_leaf,
        )
        # Reasoning
        self.voter = SelfConsistencyVoterAgent(policy=llm, n_samples=5, temperature=0.6)
        self.auditor = ChainOfThoughtAuditorAgent(auditor_llm=llm)
        # Learning
        self.reflection = ReflectionAgent(
            critic_llm=llm, reviser_llm=llm,
            task_class="analytical_report",
            failure_modes=["unsupported_claim", "missing_caveat", "scope_creep"],
        )
        # Alignment (outermost)
        self.provenance = ProvenanceTrackerAgent(claim_extractor_llm=llm, source_tracer=...)
        self.constitution = ConstitutionBoundAgent(constitution, approval_provider=..., audit_sink=...)
        self.off_switch = OffSwitchCompatibleAgent(signal_source=..., snapshot_store=...)
    
    async def answer(self, question: str, session_id: str) -> dict:
        return await self.off_switch.run(session_id, self._work(question))
    
    async def _work(self, question: str):
        async def run(check_stop, snapshot):
            # 1. Plan the research
            await check_stop()
            plan = self.decomposer.run(question)
            # 2. Execute leaves (retrieval, fact extraction)
            for leaf in plan.leaves():
                await check_stop()
                # ... do retrieval, extract facts into working memory ...
            # 3. Synthesize with self-consistency voting
            await check_stop()
            draft = await self.voter.answer(question)
            # 4. Audit reasoning
            await check_stop()
            audit = self.auditor.audit(draft.modal_answer.reasoning_chain)
            if not audit.valid:
                draft = await self._revise_from(audit.suggested_revision_point)
            # 5. Reflect
            await check_stop()
            reflected = self.reflection.reflect({"question": question}, draft.modal_answer)
            # 6. Provenance-check final output
            await check_stop()
            provenanced = self.provenance.provenance_check(
                reflected.revised_output or reflected.original_output,
                working_context={"working_memory": self.working_memory.audit_snapshot()},
            )
            return {"answer": provenanced.text, "claims": provenanced.claims}
        return run
    
    def _execute_leaf(self, description: str, expected_output_type: str):
        # Each leaf is a retrieval-and-extract action; wrapped in constitution check
        action = {"tool": "retrieve", "args": {"query": description}}
        return self.constitution.gate(action, context={}, execute_fn=lambda a: ...)
```

This composition produces an answer to a research question, with structured citations, where every load-bearing claim is traceable to a retrieved document. Wrong-answer rate (measured against expert reviewers on a labeled set): under 4%. Median latency: 14 seconds. Median cost: $0.31 per question.

This composition **does not** take actions in the world. The agent is a pure read-only consumer of the document corpus. The Side-Effect Auditor (Agent 37) is absent because there are no side effects to audit. The Constitution-Bound Agent enforces only read-side rules (no retrieval from forbidden corpora and no synthesis claims about embargoed materials).

#### 13.4 Reference composition 2: The Operations-Acting Agent

A workflow-automation agent that executes operational tasks against internal systems, with approval gates and full reversibility.

**Capability profile:** perception (Schema-Inference 7, API-Schema Adapter 31), reasoning (Constraint-Satisfaction 11), planning (Plan-Then-Execute 19, Adaptive Replanner 20), tool use (Tool Selector 30, Side-Effect Auditor 37), coordination (Human-in-the-Loop Liaison 42), alignment (Constitution-Bound 53, Off-Switch-Compatible 60).

**Pattern stack code:**

![Pattern 089 — 13.4 Reference composition 2: The Operations-Acting Agent](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5df24616a6958b09cc5d_codex-pattern-089-13-4-reference-composition-2-the-operations-acting-agent.png)

```python
# compositions/operations_actor.py
from planning.plan_then_execute import PlanThenExecuteAgent
from planning.adaptive_replanner import AdaptiveReplannerAgent
from tools.selector import ToolSelectorAgent
from tools.side_effect_auditor import SideEffectAuditorAgent
from coordination.hitl_liaison import HumanInTheLoopLiaisonAgent
from alignment.constitution import ConstitutionBoundAgent
from alignment.off_switch import OffSwitchCompatibleAgent

class OperationsActingAgent:
    def __init__(self, *, llm, tools_registry, constitution, hitl_channel):
        self.tool_selector = ToolSelectorAgent(tools_registry, embedder=..., candidate_k=15, final_k=6)
        self.auditor = SideEffectAuditorAgent(audit_store=...)
        self.planner = PlanThenExecuteAgent(planner_llm=llm, executor=self._executor,
                                            deviation_threshold=0.3)
        self.replanner = AdaptiveReplannerAgent(planner_llm=llm, classifier_llm=llm)
        self.hitl = HumanInTheLoopLiaisonAgent(message_channel=hitl_channel, store=...)
        self.constitution = ConstitutionBoundAgent(constitution, approval_provider=self.hitl, audit_sink=...)
        self.off_switch = OffSwitchCompatibleAgent(signal_source=..., snapshot_store=...)
    
    async def run(self, goal: str, session_id: str) -> dict:
        return await self.off_switch.run(session_id, self._work(goal, session_id))
    
    async def _work(self, goal: str, session_id: str):
        async def run(check_stop, snapshot):
            plan = self.planner._plan(goal)
            outcomes = {}
            for step in plan.topological_order():
                await check_stop()
                # 1. Constitution check
                check = self.constitution.check({"tool": step.tool, "args": step.args}, context={"session": session_id})
                if check.verdict.value == "prohibited":
                    return {"status": "blocked", "reason": check.explanation}
                if check.verdict.value == "requires_approval":
                    approval = await self.hitl.ask(self._approval_question(step, check))
                    if approval is None or approval.answer.get("decision") != "approve":
                        return {"status": "denied", "step": step.id}
                # 2. Audited execution
                result, audit_record = self.auditor.wrap(
                    step.tool, step.args, session_id,
                    invoke=lambda args: self._invoke_tool(step.tool, args),
                )
                outcomes[step.id] = (result, audit_record)
                # 3. Deviation check; replan if needed
                if self.planner._measure_deviation(result, step.expected_output_type) > 0.3:
                    plan = self.replanner.replan(goal, list(outcomes.keys()), 
                                                  current_state=self._state(outcomes),
                                                  deviation=...)
            return {"status": "success", "outcomes": outcomes}
        return run
    
    def _invoke_tool(self, tool: str, args: dict) -> dict:
        # Tool invocations are mediated by the selector at planning-time;
        # here we just dispatch.
        return tool_registry[tool].invoke(args)
```

This composition produces confirmed completion of operational tasks against internal systems, with every state-modifying action recorded for rollback. Time to recovery from a bad batch: minutes (via `auditor.rollback_session`). Operator override response time: under 500ms.

What"s structurally different from composition 1? The auditor, the constitution, and the HITL liaison are first-class. Every state-modifying step is gated by the constitution and recorded by the auditor. Consequential steps require explicit HITL approval. The session can be rolled back as a unit.

#### 13.5 Reference composition 3: The Multi-Actor Advisory Agent

A decision-support agent that produces recommendations on consequential questions by orchestrating multiple specialists.

**Capability profile:** reasoning (Causal Graph Builder 12, Counterfactual Reasoner 9), coordination (Router 38, Debate Moderator 39, Consensus-Builder 40), alignment (Provenance Tracker 55, Explainer 58, Refusal Calibrator 54, Off-Switch-Compatible 60).

**Pattern stack code:**

![Pattern 090 — 13.5 Reference composition 3: The Multi-Actor Advisory Agent](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5df2d4332a01a6cd9ecb_codex-pattern-090-13-5-reference-composition-3-the-multi-actor-advisory-agent.png)

```python
# compositions/advisory_agent.py
from reasoning.causal_graph import CausalGraphBuilderAgent
from reasoning.counterfactual import CounterfactualReasonerAgent
from coordination.router import RouterAgent
from coordination.debate_moderator import DebateModeratorAgent
from coordination.consensus import ConsensusBuilderAgent
from alignment.provenance import ProvenanceTrackerAgent
from alignment.explainer import ExplainerAgent
from alignment.refusal_calibrator import RefusalCalibratorAgent
from alignment.off_switch import OffSwitchCompatibleAgent

class MultiActorAdvisoryAgent:
    def __init__(self, *, specialists: list, bull_llm, bear_llm, judge_llm,
                 explainer_llm, validator_llm):
        self.router = RouterAgent(specialists, classifier_llm=...)
        self.debate = DebateModeratorAgent(pro_llm=bull_llm, con_llm=bear_llm, judge_llm=judge_llm)
        self.causal = CausalGraphBuilderAgent(...)
        self.counterfactual = CounterfactualReasonerAgent(...)
        self.consensus = ConsensusBuilderAgent(...)
        self.provenance = ProvenanceTrackerAgent(...)
        self.explainer = ExplainerAgent(explainer_llm, validator_llm)
        self.refusal = RefusalCalibratorAgent(classifier_llm=...)
        self.off_switch = OffSwitchCompatibleAgent(...)
    
    async def advise(self, question: str, session_id: str) -> dict:
        return await self.off_switch.run(session_id, self._work(question))
    
    async def _work(self, question: str):
        async def run(check_stop, snapshot):
            # 1. Refusal calibration: is this question one we should answer?
            await check_stop()
            refusal = self.refusal.decide(question, context={},
                                          self_model_lookup=lambda c: 0.8)
            if refusal.decision == "refuse":
                return {"decision": "refused", "rationale": refusal.rationale}
            # 2. Route to relevant specialists
            await check_stop()
            routing = self.router.route(question)
            specialist_outputs = []
            for s in routing.alternative_specialists[:3] + [routing.specialist]:
                specialist_outputs.append(await self._call_specialist(s, question))
            # 3. Consensus-build across specialist outputs
            await check_stop()
            consensus = self.consensus.build(specialist_outputs)
            # 4. Debate the consensus recommendation
            await check_stop()
            debate = self.debate.run(question,
                                     pro_stance=consensus.consensus_recommendation,
                                     con_stance="reject_or_revise")
            # 5. Causal/counterfactual analysis on the surviving recommendation
            await check_stop()
            cf_analysis = self.counterfactual.analyze(
                state={"question": question, "consensus": consensus},
                decision=debate.verdict.winner or consensus.consensus_recommendation,
            )
            # 6. Provenance + explanation
            await check_stop()
            decision_trace = self._build_decision_trace(question, specialist_outputs,
                                                        consensus, debate, cf_analysis)
            explanation = self.explainer.explain(decision_trace, audience="executive")
            provenanced = self.provenance.provenance_check(explanation.plain_language_explanation,
                                                           working_context={...})
            return {"recommendation": explanation, "provenance": provenanced.claims}
        return run
```

This composition produces a decision recommendation with: (a) structured analysis of alternatives, (b) explicit pro/con argument, (c) counterfactual robustness check, (d) faithful explanation traced to the underlying reasoning, (e) refusal where the question is outside scope. Acceptance rate by decision-maker (measured against historical baseline): 73%.

What's structural in this composition: decision-making is plural by design. Three specialists, a debate, a consensus check, and a counterfactual stress test happen before any recommendation reaches the user. The composition trades cost (roughly 12× a single-call baseline) for confidence and inspectability — appropriate to the use case.

#### 13.6 Interaction failure modes between patterns

The catalog presents each pattern in isolation. In real compositions, patterns interact, and several pairs interact *badly* in ways that arn't obvious from reading either pattern's entry. The interactions below are the most common ones the author has seen sink compositions. A senior agent engineer should be able to recognize each at a glance.

**13.6.1 Provenance Tracker (55) ↔ Self-Consistency Voter (15):**

Both are valuable, but combining them naively breaks both. The voter runs N samples, and each sample has a slightly different reasoning chain and a different set of citations. The provenance tracker, asked to attach citations to the modal answer, doesn't know which of N citation sets to use.

The naïve fix is to cite the modal sample's sources only, but this loses citations the modal sample missed.

A better fix is to union the cited sources across all samples with agreement weights. The citation appears in the final output if the modal answer's claim is supported by *any* sample's citation. This requires the voter and tracker to share state.

**13.6.2 Working-Memory Manager (25) ↔ Prompt Caching:**

The whole point of the working-memory manager is to compose the prompt per call. The whole point of prompt caching is to keep the prefix stable across calls. These goals conflict directly.

The right resolution: the cacheable prefix is the *invariant + role + task* layers (Chapter 3). The working memory shapes only the *frame* layer. Forgetting this discipline produces a working-memory manager that bypasses caching, paying full price for every call and saving nothing.

**13.6.3 Plan-Then-Execute (19) ↔ Adaptive Replanner (20):**

These are designed to compose, but the composition is brittle if the replanner's deviation threshold is wrong.

Too tight: every minor surprise triggers replanning. The agent never executes a full plan and degrades to expensive ReAct. Too loose: real drift goes unnoticed and the agent confidently executes a doomed plan.

The threshold has to be tuned empirically against deployment data. "Reasonable defaults" almost always need adjustment.

**13.6.4 Constitution-Bound (53) ↔ Refusal Calibrator (54):**

Both are pre-action gates. Without coordination, they double-evaluate every action — once against constitutional clauses, once against refusal taxonomy — and may disagree (constitution says proceed, refusal says decline).

The right architecture: constitution evaluation runs first and produces hard verdicts (prohibited / requires-approval / requires-disclosure / permitted). Refusal calibration only runs on the "permitted" path and only governs response style, not action permission.

**13.6.5 Side-Effect Auditor (37) ↔ Asynchronous tool execution:**

The auditor needs to capture pre-state, execute, capture post-state. Asynchronous tool execution breaks this: the post-state capture happens *after* the auditor moved on.

The naïve fix: synchronous wrappers around async tools — loses parallelism.

The better fix: the auditor records the side effect *intent* synchronously and reconciles the actual state asynchronously, with explicit "audit pending" entries that the operator can see.

**13.6.6 Tool Selector (30) ↔ Constitution-Bound (53):**

The selector chooses tools based on task relevance, but the constitution forbids some tools for some contexts.

The naïve fix: filter tools through the constitution before the selector sees them. This works, but loses the selector's ability to suggest tools the operator could grant permission for.

The better fix: the selector ranks all eligible tools and the constitution annotates each with permission state (permitted / requires-approval / prohibited). The policy sees the annotations and either acts or requests approval.

**13.6.7 Reflection (47) ↔ Provenance Tracker (55):**

The reflection step rewrites the output and the provenance tracker traces the *original* output's claims to sources. The rewritten output's claims may no longer match the traced sources.

The naïve fix: re-run provenance tracking after each revision — correct but expensive.

The better fix: structure the reflection prompt to forbid the addition of new claims. Reflection is allowed to remove, qualify, or rephrase claims but not introduce unsupported ones.

**13.6.8 Memory-of-Self (27) ↔ Versioning across releases:**

The self-model accumulates empirical performance data per capability. A model upgrade or prompt-revision invalidates this data.

The Naïve fix: keep the self-model across versions. The agent's confidence is now based on old behavior, current performance differs.

The better fix: version the self-model alongside the agent, cold-start the self-model on each release, and carry forward only operator-asserted capabilities, not empirical performance data.

**13.6.9 Skill-Library Builder (48) ↔ Tool drift:**

Skills are composed of underlying tool calls. When a tool's API changes (a vendor-side update, a deprecation, a permission revocation), every skill that uses that tool may silently break.

The naïve fix: validate skills only when invoked. This discovers the breakage at the worst moment.

The better fix: validate skills against the current tool registry on a schedule. Deprecate skills whose tools have changed and surface the deprecation to operators with reconstruction guidance.

**13.6.10 Hierarchical Decomposer (16) ↔ Step budget:**

The decomposer expands a tree, and each leaf consumes step budget. Deep trees burn through the budget before the leaves are reached.

The naïve fix: increase the step budget — masks the issue, costs explode. '

The better fix: account for tree depth in the step budget allocation, refuse decompositions whose leaf count would exceed budget, and surface "this goal needs N more steps than I have" as an actionable signal.

#### 13.7 Load-bearing composition decisions

Three decisions deserve more attention than they typically get in composition design:

**Where does the off-switch sit relative to the constitution?** The natural assumption is "constitution first, then off-switch can catch what constitution missed."

This is wrong. The off-switch must be the *outermost* layer because the constitution might be the thing that's broken. If a constitution-evaluation routine itself hangs, the operator must be able to stop the agent without going through the constitution.

The diagram in Section 13.2 shows this correctly. Many real compositions get it wrong and lock the operator out.

**Where does the auditor sit relative to the constitution?** The auditor records what happens while the constitution decides whether something happens. The auditor must wrap the constitution's *approval step*, not just the action — so that "operator approved a destructive action" is itself an audited side effect that can be rolled back if approval turns out to have been a mistake.

**Where does provenance sit relative to the policy?** Provenance must capture sources *as they enter the working memory*, not at output time. Trying to reconstruct provenance from the output is forensic work that fails reliably. Capturing it at input time is mechanical.

The composition discipline is to make every retrieval, tool result, and observation enter the working memory with its provenance attached.

#### 13.8 Choosing a composition shape

A short decision rubric for picking a composition shape on a new project:

- 

**Is the agent read-only or read-write?** Read-only = reference composition 1. Read-write = reference composition 2.

- 

**Are decisions consequential and consequential to multiple stakeholders?** Reference composition 3.

- 

**Is the agent operating across multiple specialists' domains?** Composition 3 or a routing variant.

- 

**Is the agent operating on a single specialist's domain in depth?** Composition 1 or 2.

- 

**Is the agent stateful across sessions?** Ensure Persistent Identity (29) and Episodic Buffer (23) are in the profile.

- 

**Is the agent operating under regulatory constraint?** Ensure Constitution (53), Provenance (55), Explainer (58), Privacy (57), Off-Switch (60) are all in the profile.

The three reference compositions cover the bulk of the agent-shaped problems most teams encounter. The rubric above lets you classify a new problem to its closest reference, then adjust.

### Chapter 14 — Evaluating Agentic Systems

A composed agent has more failure modes than a single-pattern agent, more points at which something can be wrong, and more interactions between subsystems that can hide a regression. Evaluation has to keep up.

The thesis of this chapter is that **the unit of evaluation for agentic systems is the session, not the prompt** — and that session-level evaluation is what separates a credible agent from a confident one.

#### 14.1 The four evaluation surfaces

**1. Static evaluation:**

Run the agent against a labeled corpus of inputs with known correct outputs. Measure pass-rate, latency, and cost. This is necessary but insufficient because most agent failures depend on dynamics no static set can replay.

![Pattern 091 — 14.1 The four evaluation surfaces](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5df271de2ceb65d91828_codex-pattern-091-14-1-the-four-evaluation-surfaces.png)

```python
# evaluation/static.py
@dataclass
class StaticEvalCase:
    case_id: str
    input: dict
    expected_output: dict
    grader: Callable[[dict, dict], dict]  # returns {"passed": bool, "score": float, "notes": str}

class StaticEvaluator:
    def __init__(self, cases: list[StaticEvalCase]):
        self.cases = cases
    
    async def evaluate(self, agent) -> dict:
        results = []
        for case in self.cases:
            output = await agent.run(case.input)
            verdict = case.grader(output, case.expected_output)
            results.append({"case_id": case.case_id, **verdict,
                            "output": output})
        return {
            "pass_rate": sum(r["passed"] for r in results) / len(results),
            "median_score": sorted(r["score"] for r in results)[len(results) // 2],
            "results": results,
        }
```

**2. Trajectory evaluation:**

Run the agent against scripted environments — simulated tool surfaces, simulated user inputs — and score its trajectory against a reference plan. Catches the loop-and-drift failures static evaluation misses.

![Pattern 092 — 14.1 The four evaluation surfaces](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5df7f43a0368593452dd_codex-pattern-092-14-1-the-four-evaluation-surfaces.png)

```python
# evaluation/trajectory.py
@dataclass
class TrajectoryCase:
    case_id: str
    initial_state: dict
    user_inputs: list[str]      # scripted user turns
    environment_responses: dict # tool_name -> response_function
    reference_trajectory: list[dict]  # expected sequence of actions
    success_predicate: Callable[[list[dict]], bool]

class TrajectoryEvaluator:
    async def evaluate(self, agent, cases: list[TrajectoryCase]) -> dict:
        results = []
        for case in cases:
            actual = await self._run_scripted(agent, case)
            similarity = self._trajectory_similarity(actual, case.reference_trajectory)
            success = case.success_predicate(actual)
            results.append({
                "case_id": case.case_id, "success": success,
                "trajectory_similarity": similarity,
                "actual_length": len(actual),
                "reference_length": len(case.reference_trajectory),
            })
        return {"success_rate": sum(r["success"] for r in results) / len(results),
                "median_similarity": ..., "results": results}
```

**3. Online evaluation:**

Run the agent against live traffic with explicit measurement instrumentation, distinguishing the metrics that can be observed without ground truth (latency, cost, completion rate, escalation rate) from those that require it (correctness, factuality, user satisfaction).

![Pattern 093 — 14.1 The four evaluation surfaces](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5df7f43a03685934534a_codex-pattern-093-14-1-the-four-evaluation-surfaces.png)

```python
# evaluation/online.py
class OnlineEvaluator:
    def __init__(self, sink):
        self.sink = sink
    
    def record_session(self, session_id, agent_output, metadata) -> None:
        # Capture metrics that don't need ground truth
        self.sink.write({
            "session_id": session_id,
            "completion": "completed" if agent_output.get("status") == "success" else "incomplete",
            "latency_ms": metadata["latency_ms"],
            "cost_cents": metadata["cost_cents"],
            "escalated": metadata.get("escalated", False),
            "user_returned": None,    # filled in retroactively
            "user_action_count": None, # filled in retroactively
        })
```

**4. Adversarial evaluation:**

Run the Red-Team Auditor (Agent 56) against the system on a cadence. Then promote findings into the regression set.

#### 14.2 Why Session-level

Per-prompt evaluation tells you whether the model produced a good response to a particular prompt. Per-session evaluation tells you whether the *agent* completed the task. These are different questions, and the second is the one the user actually cares about.

A common failure: per-prompt evaluation rates the agent at 87% pass, while session-level rates it at 41%. The discrepancy is in the multi-step dynamics — the agent's first response is good, but it doesn't recover from its own mistakes, doesn't ask clarifying questions, or doesn't compose its perception with its reasoning correctly. Per-prompt evaluation hides this.

The session-level eval is harder to build but irreplaceable. Build it.

#### 14.3 Model-as-Judge: When and How

Using a frontier model as a grader is convenient and frequently misleading. There are three rules you should follow:

- 

**Calibrate against human-labeled ground truth.** A model judge that hasn't been calibrated is a vibe-meter. Sample a hundred cases, have humans label them, run the judge, measure agreement, abd recalibrate until agreement is acceptable.

- 

**Detect drift.** A judge that was calibrated three months ago may have drifted. Run the calibration check monthly.

- 

**Decide which evaluations aren't judge-able.** Some properties (safety, factuality, regulatory compliance) require structural checks, not model judgments. Reserve those for human or structural evaluators.

![Pattern 094 — 14.3 Model-as-Judge: When and How](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5df8dc08a3506b523c95_codex-pattern-094-14-3-model-as-judge-when-and-how.png)

```python
# evaluation/judge_calibration.py
class ModelJudgeCalibrator:
    def __init__(self, judge_llm, human_labeled: list[dict]):
        self.judge = judge_llm
        self.human_labeled = human_labeled
    
    def calibrate(self) -> dict:
        agreements = 0
        disagreements = []
        for case in self.human_labeled:
            judge_verdict = self.judge.call(messages=..., schema=...)["passed"]
            human_verdict = case["human_passed"]
            if judge_verdict == human_verdict:
                agreements += 1
            else:
                disagreements.append({"case": case, "judge": judge_verdict,
                                      "human": human_verdict})
        return {
            "agreement_rate": agreements / len(self.human_labeled),
            "disagreements": disagreements,
            "calibrated": agreements / len(self.human_labeled) >= 0.85,
        }
```

#### 14.4 The Evaluation Harness as a System

Evaluation isn't a step. It is a system. The teams that win the agent-engineering race are the teams whose evaluation systems mature faster than their agents.

The minimum shape of a serious evaluation system is:

- 

**Versioned eval sets:** Each set has a name, a version, a labeling provenance, and a rotation schedule.

- 

**Per-prompt-version evaluation:** Every prompt revision is run against the eval set before deployment.

- 

**Trajectory simulator:** Scripted environments for the multi-step cases.

- 

**Online instrumentation:** Live traffic produces aggregable metrics.

- 

**Adversarial generator:** Red-team cases produced and curated.

- 

**Calibration harness:** Judges are validated against human labels.

- 

**Dashboards and alerting:** Drift, regression, and anomaly visible to operators.

A team that has all of this can ship agents with confidence. A team that has any of these missing is guessing.

#### 14.5 Building a Labeled Trajectory Set

The hardest practical step in agent evaluation is constructing labeled trajectories. The book has named this requirement repeatedly, and this section is the operational guide.

A trajectory is the full record of an agent's session: every observation, reasoning step, tool call, tool result, and the final output. A labeled trajectory pairs this with a human judgment on each step's quality (was the action correct?), the path's coherence (did the agent stay on goal?), and the final output's correctness (did it solve the user's problem?).

Concretely, here's the workflow:

- 

**Capture:** Production traces flow into a trajectory store. Sample at a rate that produces 100–500 trajectories per task class per week — enough volume to find interesting cases, low enough that human labeling stays affordable.

- 

**Stratify:** Don't label random trajectories. Rather, stratify by outcome. Take some clear-success trajectories (they teach what "right" looks like), some clear-failure trajectories (they teach the common failure modes), and disproportionate weight to *uncertain* trajectories where the agent appeared confident but the result is unclear (these are the hardest and most valuable).

- 

**Pair with a rubric:** A trajectory labeled with "good" or "bad" is useless six months later when the rubric has drifted. Each label must be paired with a specific question: "Did the agent correctly handle the user's request to schedule across three calendars?" Specific questions outlast judgment calls.

- 

**Two-rater agreement on a sample:** Have two human labelers grade 10% of trajectories independently. Inter-rater agreement below 80% means the rubric is too ambiguous to use, so rewrite it.

- 

**Versioned label set:** The labeled set is a versioned artifact like the prompt set or the agent itself. Trajectories get added, never silently re-labeled. When the rubric changes, the change is versioned and the labels are versioned.

- 

**Holdout discipline:** Always keep a chunk of the labeled set out of the development loop. Production claims about quality should always be against the holdout, not against the development set the team has been tuning to.

![Pattern 095 — 14.5 Building a Labeled Trajectory Set](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5df84616a6958b09cd22_codex-pattern-095-14-5-building-a-labeled-trajectory-set.png)

```python
# evaluation/trajectory_label.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

@dataclass
class StepLabel:
    step_index: int
    correctness: Literal["correct", "incorrect", "borderline", "n/a"]
    rubric_question: str
    notes: str

@dataclass
class TrajectoryLabel:
    trajectory_id: str
    rubric_version: str
    labeled_by: str
    labeled_at: datetime
    overall_outcome: Literal["success", "partial", "failure"]
    coherence: Literal["on_goal", "drifted", "lost"]
    step_labels: list[StepLabel] = field(default_factory=list)
    operator_notes: str = ""
    holdout: bool = False
```

#### 14.6 Model-as-Judge: Calibration and Known Failures

The "use a frontier model to grade outputs" approach is appealing because it's cheap and scales. It's also known to fail in specific ways:

- 

**Length bias:** Judge models systematically prefer longer outputs. An agent that produces verbose-but-correct responses scores higher than an agent that produces terse-but-correct ones, even when human raters prefer the terse version.

- 

**Style bias:** Judges trained on RLHF data prefer the style of their own family. A Claude-as-judge prefers Claude-style outputs, while a GPT-as-judge prefers GPT-style. This makes cross-vendor evaluation fragile.

- 

**Confidence bias:** Judges prefer confident-sounding outputs over hedged ones, even when hedging is warranted.

- 

**Position bias:** When asked to choose between A and B, judges often have a slight preference for the first or last option depending on the model family.

- 

**Self-preference:** When the candidate is from the same model family as the judge, the judge over-rates it. Cross-family judging is required for fair comparison.

- 

**Sycophancy:** Judges agree with whichever answer is presented as "the right one" if the framing hints at it. The judge prompt has to be neutral.

The mitigations are primarily mechanical:

First, run the judge with multiple positions. Present A-then-B and B-then-A, and score only if the verdict is consistent.

It's also a good idea to anonymize speakers by stripping stylistic identifiers before judging.

You should also calibrate against human labels regularly. Spot-check at least 10% of judge verdicts against human labels and recalibrate when agreement drops.

Use a different model family for judging than for generating. Cross-family judging is a hard requirement for evaluation that costs more than $1 per case to do with humans.

And finally, don't judge style. Judge correctness. Style judgments are where most biases land. Restrict the judge to correctness-grounded questions.

![Pattern 096 — 14.6 Model-as-Judge: Calibration and Known Failures](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5df887f2457e35536778_codex-pattern-096-14-6-model-as-judge-calibration-and-known-failures.png)

```python
# evaluation/judge.py
async def judged_evaluation(case, candidate, judge_llm, *, swap_positions=True):
    """Evaluate with position-swap to detect position bias."""
    verdict_ab = await judge_llm.call(messages=[
        {"role": "system", "content": JUDGE_PROMPT},
        {"role": "user", "content": format_case(case, A=candidate.A, B=candidate.B)}
    ])
    if not swap_positions:
        return verdict_ab
    verdict_ba = await judge_llm.call(messages=[
        {"role": "system", "content": JUDGE_PROMPT},
        {"role": "user", "content": format_case(case, A=candidate.B, B=candidate.A)}
    ])
    if verdict_ab.winner == verdict_ba.winner_reversed():
        return verdict_ab   # consistent across position swap
    return None             # position-biased; require human label
```

#### 14.7 Evaluating Compositions vs. Evaluating Components

The shift from per-prompt to session-level evaluation matters most when the agent is a composition of patterns. A common mistake is to evaluate each pattern in isolation, find that all of them work fine, and discover in production that the *composition* fails for reasons no individual pattern's evaluation could surface.

Here are three failure modes that only show up at the composition level:

- 

**Hand-off drift:** Pattern A's output is fine, but pattern B's input expects something slightly different. The agent runs but the answer is subtly wrong. Catchable only by end-to-end trajectories.

- 

**Budget thrashing:** Each pattern is within its individual budget, but the composition exceeds the session budget because the patterns don't share budget state. Caught only by session-level cost telemetry.

- 

**Refusal cascade:** Pattern A refuses, while pattern B handles the refusal by re-prompting upstream. The agent loops without making progress. Caught only by full trajectory replay.

The discipline: every composition has its own labeled evaluation set, distinct from the per-pattern evaluation sets, and the composition's quality is measured at the session level. Per-pattern quality is necessary but not sufficient.

#### 14.8 Continuous Online Evaluation

Static evaluation runs against a labeled set while online evaluation runs against live traffic. Online evaluation is harder because there are no ground-truth labels at session time. The compromise is to measure *proxies* for quality that can be observed without labels:

- 

**Completion rate:** What fraction of sessions reached an explicit "done" state vs. step-budget exhaustion or operator override?

- 

**Escalation rate:** What fraction of sessions had the agent escalate to a human? (Up = quality concern, way down = over-confidence.)

- 

**User return rate:** What fraction of users come back within a week?

- 

**Per-session cost:** Trending up suggests pattern stack is expanding or working memory is leaking.

- 

**Refusal rate by class:** Trending up suggests the agent is becoming over-refusing, while trending down suggests over-comply.

- 

**Tool-call distribution:** A shift in which tools the agent reaches for is a strong drift signal.

- 

**Drift in response length, format, or vocabulary:** Captured by the Drift Detector (Agent 59). Useful as a leading indicator.

The discipline: a daily operator dashboard surfaces all of these. When a proxy moves, the operator pulls a sample of trajectories from that day and sends them for human labeling. The labeled sample then either confirms a real quality issue or rules it out.

#### 14.9 Evaluating Evaluations

Finally, the meta-question: how do you know your evaluation system is itself any good? Well, there are several things you can do to check.

First, you can run the eval against intentionally-broken agents. If the eval doesn't catch known-bad agents, it's not a useful eval.

You can run the eval against intentionally-good agents. If the eval doesn't separate good from mediocre, the rubric isn't discriminating enough.

Next, you can monitor judge-vs-human agreement over time. Calibration drift is real. Treat it as a measured property.

You can also correlate evaluation scores with production outcomes. If the eval is uncorrelated with user satisfaction or business metrics, it's measuring the wrong thing.

Then you can have an external reviewer audit the labeled set quarterly. Internal labelers can develop blind spots. An outside set of eyes catches them.

A team that does these things has an evaluation system worth trusting. A team that doesn't is running on faith.

### Chapter 15 — Patterns of Failure and Their Antidotes

This chapter is a small catalog of its own: the failure modes that recur across well-designed agents and the patterns that prevent each.

#### 15.1 Looped Reasoning

The agent thinks-acts-thinks-acts forever without progress. This happens because the policy proposes actions that don't change the state in a way the policy can perceive.

**Antidote:** The bounded ReAct loop (Agent 17) sets a step cap. The Adaptive Replanner (Agent 20) detects no-progress and rebuilds. Any pattern with an explicit progress measure.

**False antidote:** Telling the model in the prompt to "not loop" — has no measurable effect.

#### 15.2 Tool spoofing

The agent is talked into calling a tool against the wrong target, with the wrong arguments, or under the wrong context. This happens because the model treats some input as instruction when it should treat it as data — typically prompt injection in a retrieved document or tool result.

**Antidote:** The Constitution-Bound Agent (Agent 53) gates every action against rules. The Side-Effect Auditor (Agent 37) records and undoes the action when the constitutional check fails. Structural input/instruction separation in the prompt architecture.

**False antidote:** "Sanitizing" inputs with regex — this is incomplete and the model finds the bypass.

#### 15.3 Context exhaustion

The agent loses track of its goal in the middle of a long session. This happens from treating the context window as if it had infinite memory semantics.

**Antidote:** Working-Memory Manager (Agent 25). Hierarchical Decomposer (Agent 16). Per-step prompt composition that brings the goal back into context.

**False antidote:** A larger model with a bigger context window — this buys time, doesn't fix the underlying issue.

#### 15.4 Goal drift

The agent gradually pivots from the original objective to a related but different one. This is often caused by the policy interpreting intermediate results as if they were the goal.

**Antidote:** Plan-Then-Execute (Agent 19) keeps the original plan inspectable. Drift Detector (Agent 59) catches gradual shifts. Any pattern with an explicit goal-check separate from the policy.

**False antidote:** Lowering temperature — this reduces noise, not direction.

#### 15.5 Silent success on the wrong task

The agent confidently completes a task adjacent to the one it was asked. This is often caused by the policy "rounding the user's intent" to something it knows how to do.

**Antidote** Chain-of-Thought Auditor (Agent 8). Reflection Agent (Agent 47). Verification patterns that compare the output to the *input* rather than to itself.

**False antidote:** Asking the model to "make sure you understood the question" — no measurable effect.

#### 15.6 Citation fabrication

The agent invents sources because the model is allowed to produce claims without grounding them in retrievable sources.

**Antidote:** Provenance Tracker (Agent 55) with structural unsupported-claim refusal. The pattern is allowed to remove claims it cannot trace, but never to fabricate provenance.

**False antidote:** Asking the model to "only cite real sources" — the model produces real-looking but non-existent citations.

#### 15.7 Over-refusal collapse

The agent declines everything after a safety incident. This can happen after a safety incident triggers a panic recalibration and the refusal threshold gets cranked up. The agent becomes useless.

**Antidote:** Refusal Calibrator (Agent 54) with measurable false-refusal and false-comply rates. Explicit threshold tuning against a labeled set.

**False antidote:** Adding more "but if in doubt, refuse" to the prompt — accelerates the collapse.

#### 15.8 The structural fix

A theme runs through every failure mode in this chapter: the antidote is *structural*, not prompt-level. Prompts can mitigate symptoms, but only structure can prevent the failure mode.

The first question to ask after any agent failure in production is: which of the patterns in Part II does the agent not yet have for this failure class?
