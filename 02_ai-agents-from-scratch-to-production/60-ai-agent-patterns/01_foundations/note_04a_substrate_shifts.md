### Chapter 4A — Substrate Shifts (2025–2026)

The patterns in this book are framed as model-agnostic and roughly time-stable. Both framings are true at the level of the *pattern* (the shape of the architecture is the same regardless of the model behind it) and false at the level of *which patterns are worth deploying*.

The cost-benefit of nearly every pattern has shifted in the last eighteen months as the substrate has moved. This chapter names the shifts explicitly so you can update the catalog's recommendations against what your substrate actually looks like.

#### 4A.1 Long-context models

Frontier models now ship with context windows in the hundreds-of-thousands to millions of tokens. This rewrites the cost-benefit of every memory pattern:

- 

**Working-Memory Manager (Agent 25)** matters less in absolute terms when the model can absorb tens of thousands of tokens without degradation. It still matters at cost (longer contexts are more expensive) and at attention-saturation (the model's effective attention window is smaller than its nominal context window). But the case for aggressive per-step composition is weaker than it was at 8K context.

- 

**Vector-Store Curator (Agent 28)** is no longer the only practical way to retrieve over a corpus. For corpora that fit in context (typically a few hundred to a few thousand pages), feeding the whole corpus directly often beats retrieval. The curator's value is concentrated in corpora that genuinely exceed the context window or in deployments where context cost is a hard constraint.

- 

**Episodic Buffer (Agent 23)** retains most of its value because it's about *typed structure*, not raw token storage. The context window doesn't replace the ability to query the buffer by predicate.

The honest update: long context doesn't eliminate memory patterns. It just shifts the *threshold corpus size* at which retrieval is worth it upward by roughly an order of magnitude.

#### 4A.2 Reasoning-trained models

Models trained with reasoning RL (o1-style, Claude with extended thinking, comparable Gemini variants) internalize what older patterns externalized:

- 

**Self-Consistency Voter (Agent 15)** is less necessary on hard problems with these models. The voter pattern is still useful as an *escalation/verification* mechanism (run a single reasoning model, then sample a smaller model multiple times as a cross-check), but the "sample N from the same model and vote" framing buys less than it did.

- 

**Chain-of-Thought Auditor (Agent 8)** is more useful, not less. Reasoning-trained models produce more reasoning trace, which means more steps that could be invalid. The auditor's job — verify each step — applies just as much, arguably more.

- 

**Reflection (Agent 47)** overlaps with what reasoning models already do internally. Single-round reflection on a reasoning-model output often produces marginal improvement, while multi-round reflection sometimes degrades.

Honest update: reasoning models absorb some patterns and amplify the need for others. Verifying the trace becomes more important, and generating multiple traces becomes less.

#### 4A.3 Computer-use / browser-control models

Frontier-vendor "computer use" capabilities (Anthropic computer use, OpenAI Operator and comparable products, Google's equivalents) collapse much of the Browser-Driver pattern (Agent 34) into the model itself:

- 

The accessibility-tree-first architecture remains the right shape for many tasks, but the pixel-based vision fallback is now reliable enough to be the default for sites the accessibility tree fails on.

- 

The cost calculus has shifted: vendor-provided computer-use is expensive per session but eliminates the engineering cost of hand-driving Playwright.

- 

The pattern's case for in-house implementation is now strongest where (a) vendor cost is prohibitive at volume, (b) site coverage exceeds vendor support, or (c) sensitive credentials can't leave your network.

Honest update: many teams that would have built a Browser-Driver in 2024 should evaluate vendor computer-use first in 2026.

#### 4A.4 Prompt caching and pricing

Major providers now offer some form of prompt caching: a long static prefix can be cached at the provider and re-used at substantial discount for subsequent calls. This changes the economics of several patterns:

- 

The four-layer prompt architecture (invariant / role / task / frame) introduced in Chapter 3 now pays for itself directly. The invariant layer is exactly the cacheable prefix.

- 

**Few-Shot Prompt Tuner (Agent 50)** has a new tension: cached examples are cheap, while dynamically-selected examples per call bypass the cache and pay full price. The trade-off becomes "broader coverage at higher cost" vs. "narrower coverage at near-zero cost." Many teams now ship a hybrid: a cached "core" example set, augmented by selected examples only when the task type is unusual.

- 

**Working-Memory Manager (Agent 25)** trades against caching. Aggressive per-call recomposition optimizes prompt content but loses cache hits. The right shape is to compose the *variable* portion of the prompt while keeping the cacheable prefix stable.

Honest update: with caching enabled, the cost optimization problem changes shape. The goal is no longer "minimize prompt tokens" but "maximize cache hits at acceptable quality."

#### 4A.5 Tool-use APIs maturing

Tool-use is now a first-class capability in every major provider's API: typed function declarations, structured outputs, parallel tool calls, multi-turn tool loops. Implications for the catalog:

- 

The harness in Chapter 1 (and the toolkit in Chapter 2) is still useful as a *conceptual* spine, but the in-loop machinery (tool selection, parameter validation, multi-step execution) is increasingly handled at the API level.

- 

**Tool Selector (Agent 30)** is less necessary at small toolsets. Providers now ship native ways to expose hundreds of tools with automatic shortlisting.

- 

**Side-Effect Auditor (Agent 37)** remains essential because providers don't (and probably shouldn't) own the rollback story for your business logic.

Honest update: the harness is still yours, but an increasing fraction of the *coordination* of model-and-tools is the provider's.

#### 4A.6 Native multimodality

Frontier models now natively process image, audio, and video alongside text. Patterns in Chapter 5 (Perception) that previously required dedicated pipelines now have a one-model alternative:

- 

**Document Layout (Agent 2)** still beats native-multimodal extraction on structure-heavy documents, but the gap is closing. For most documents, native multimodal extraction is good enough for the first pass.

- 

**Multimodal Grounding (Agent 1)** still earns its keep for compound references and provenance, but single-turn vision-language Q&A no longer needs the pattern.

- 

**Visual Question Decomposition (Agent 5)** is less necessary when the model handles compound queries natively, but it's still essential when the user's question genuinely requires sequential sub-queries.

Honest update: many perception patterns have lower thresholds for "the model is good enough" than they did at the patterns' time of formulation.

#### 4A.7 What the shifts do NOT change

For honesty, the patterns whose case is essentially unchanged across substrate shifts:

- 

**All eight alignment patterns** (Chapter 12). Better models don't produce constitutions, refusal taxonomies, provenance, audit trails, privacy minimization, drift detection, explanations, or off-switches as side-effects of being better. These are structural commitments that have to be engineered no matter the substrate.

- 

**Side-Effect Auditor (37)**. Rollback semantics are your business logic. No model handles them.

- 

**Constitution-Bound (53), Off-Switch-Compatible (60), Provenance Tracker (55), Privacy-Preserving (57)**. Same reason. These are non-negotiable infrastructure that the model substrate does not provide.

- 

**Evaluation infrastructure (Chapter 14)**. Better models don't produce evaluation systems for you. They make evaluation harder, because they reach further into capability ranges where ground-truth labels are scarce.

The honest summary: the substrate has shifted the boundary of which patterns are worth in-house implementation. The patterns that *are* worth in-house implementation are increasingly concentrated in alignment, evaluation, and side-effect management. These are the parts of agent engineering the substrate genuinely can't do for you.
