### Chapter 4B — The Cost Economics of Agent Patterns

Most agent failures in 2026 production aren't quality failures. They're *economic* failures. The agent works in demo, then ships, then runs at a per-session cost the business can't sustain at the user volume the product attracts.

This is the single most under-discussed failure mode in current agent engineering. This chapter treats cost as a first-class design constraint.

#### 4B.1 Cost multipliers, named

Most patterns multiply the cost of the baseline agent (one model call per turn) by a roughly-known factor. Here are some approximate multipliers, useful for back-of-envelope calculations:

Pattern
Cost multiplier vs. baseline
Notes

Single LLM call (baseline)
1×
Reference point

Self-Consistency Voter (15)
4–8×
At N=4–8 samples

Reflection (47)
2–3×
Single round of critique + revise

Debate Moderator (39)
5–10×
Pro + con + judge across rounds

Tree-of-Thought (18)
10–50×
Depends on branching × depth × evaluator cost

Plan-Then-Execute (19)
1.3–2×
Plan once, execute many

Hierarchical Decomposer (16)
2–5×
Recursive expansion

CoT Auditor (8)
1.5–2×
One audit pass per chain

Constitution-Bound (53)
1.1–1.5×
One check per state-modifying action

Provenance Tracker (55)
1.2–1.5×
Claim extraction + tracing

Working-Memory Manager (25)
0.5–0.9×
Often *reduces* cost when sessions are long

Tool Selector (30)
0.7–0.9×
*Reduces* cost by shrinking prompts

Distillation (51)
0.1–0.3× of the original
After distillation. The multiplier is *for the student*

These are approximations and vary heavily by deployment. The point is the *order of magnitude*: a fully-stacked agent (perceive, decompose, plan, vote, audit, reflect, constitution-check, audit-side-effects, provenance-track, explain) easily runs 50–100× the cost of a single model call. For many use cases this is fine, but for many others it can be fatal.

#### 4B.2 The cost ceiling and what it forces

Every agent product has a cost ceiling: the maximum per-session cost the business can sustain at scale. The ceiling is usually some fraction of the session's user-perceived value.

For a \(50/month SaaS product with one session per user per week, the per-session cost ceiling is around \)0.10. For a \(500/year consumer product with daily sessions, it's around \)0.04. For an enterprise contract worth $100/user/month, it can be a few dollars per session.

The ceiling forces design choices:

- 

At a $0.05 ceiling, **the patterns you can afford** are roughly: working-memory management (free), tool selection (free or saves money), one model call per turn, one alignment-check per state-modifying action, and a cheap audit log. Self-consistency voting is borderline, debate is unaffordable, and ToT is unaffordable.

- 

At a $0.50 ceiling, you can afford: the above, plus self-consistency on hard turns, plus reflection on consequential outputs, plus a stronger model for the planner role.

- 

At a $5 ceiling (enterprise), the full pattern stack is plausible. You're limited by latency more than cost.

The right design move is to **set the ceiling first**, then choose patterns from a budget. This book's catalog presents the patterns without budget context. So you should add your own ceiling and prune accordingly.

#### 4B.3 The cost-quality Pareto

For most patterns, the relationship between cost and quality is non-linear with a knee. The knee is the operationally interesting point — beyond it, you pay multiplicatively more for marginally better quality.

A few patterns whose knees are reasonably well-known:

- 

**Self-Consistency Voter:** knee typically at N=4–8 on hard problems. Going to N=16 produces marginal gains at 2–4× the cost.

- 

**Tree-of-Thought:** knee depends sharply on the value estimator's quality. With a well-calibrated estimator, B=3, depth=4 is usually enough. Without, ToT degenerates to expensive random sampling.

- 

**Reflection:** knee at 1–2 rounds. Three or more rounds often degrade.

- 

**Hierarchical Decomposer:** knee at depth 3–4 for most goals. Deeper trees are sometimes warranted but the cost grows multiplicatively.

- 

**Debate Moderator:** knee at 2–3 rounds. Longer debates rarely produce new positions.

Cost-aware design starts at the knee and adds budget if and only if quality is below the floor. Starting above the knee is the most common cost mistake.

#### 4B.4 The economics-driven pattern hierarchy

If forced to rank patterns by economic priority for a typical agent deployment, the order looks roughly like this:

**Tier 1 — Net cost savers or free.** Implement these regardless of budget. They make the agent cheaper *and* better.

- 

Working-Memory Manager (25)

- 

Tool Selector (30)

- 

Side-Effect Auditor (37): saves money on the first prevented bad batch

- 

Off-Switch-Compatible (60): saves money on the first prevented runaway

- 

Constitution-Bound (53): saves money on the first prevented policy violation

- 

Drift Detector (59): saves money on the first prevented silent regression

**Tier 2 — Modest cost multiplier with high value.** Implement if budget allows.

- 

Provenance Tracker (55), CoT Auditor (8), Refusal Calibrator (54)

- 

Plan-Then-Execute (19) for state-modifying agents

- 

Feedback Loop (46), Reflection (47)

**Tier 3 — Significant cost multiplier, reserve for hard turns.**

- 

Self-Consistency Voter (15), Debate Moderator (39)

- 

Hierarchical Decomposer (16) for genuinely long-horizon goals

**Tier 4 — Expensive, use selectively or research-only.**

- 

Tree-of-Thought (18), Causal Graph Builder (12), Symbolic-Neural Bridge (13)

- 

Counterfactual Reasoner (9), Distillation (51) (cheap *after* one-time training cost)

This book's catalog presents all sixty patterns at equal billing. The economics-driven hierarchy treats the catalog as a budget-constrained choice problem instead.

#### 4B.5 Per-pattern cost-quality knees (rough field estimates)

The table below estimates the *knee* of the cost-quality curve for each major pattern. These are the points where additional cost stops producing meaningful quality improvement.

These are field estimates from typical deployments, not benchmark-derived. The precise knee varies by task class and model. Use them as starting calibration, then tune against your own evaluation data.

Pattern
Knee parameter
Approximate knee value
What's beyond the knee

Self-Consistency Voter (15)
N (samples)
N=4–8
N=16 is rarely 2× better than N=8

Tree-of-Thought (18)
branching × depth
B=3, depth=4
wider/deeper trees rarely improve over a calibrated value estimator

Reflection (47)
rounds
1–2 rounds
round 3+ often degrades

Debate Moderator (39)
rounds per side
2–3 turns each
longer debates rarely produce new positions

Hierarchical Decomposer (16)
tree depth
3–4
deeper decomposition burns step budget without quality gains

Counterfactual Reasoner (9)
branches per decision
3
5+ branches rarely surface new failure modes

Probabilistic Belief Updater (14)
hypotheses tracked
5–10
tracking 20+ rarely produces sharper posterior

Active Learner (52)
daily labeling budget
30–50 cases
larger budgets see diminishing per-case marginal lift

Chain-of-Thought Auditor (8)
auditor sample count
1 (single pass)
self-consistency on the auditor rarely pays

Tool Selector (30)
top-K final
5–8 tools
larger K bloats prompts without quality lift

Working-Memory Manager (25)
token budget
4–8K
larger budgets often regress past model's attention window

Episodic Buffer (23)
retrieval k
10–20 events
larger k pollutes context with noise

Vector-Store Curator (28)
benchmark cadence
weekly
daily benchmarking rarely catches issues weekly didn't

Refusal Calibrator (54)
recalibration cadence
monthly
more frequent recalibration chases noise

Drift Detector (59)
feature count
10–15
more features produce alarm fatigue

Red-Team Auditor (56)
cases per cycle
100–300
larger cycles rarely surface new failure modes per case

Two general principles fall out of the table:

- 

**Most patterns have a knee at small N:** N=4–8, depth 3–4, top-K 5–10. Practitioners who default to "more is better" pay a lot for the long tail past the knee.

- 

**The knee is task-dependent:** On easy tasks the knee is even lower, while on adversarial tasks it can be higher. Re-tune against your own evaluation data. Don't ship with default parameters.

#### 4B.7 Cost as a first-class evaluation metric

Most evaluation work treats quality as the primary metric and cost as a secondary one. For agents in production, this is backwards: cost is the *first* constraint and quality is what you maximize subject to it. The Resource-Aware Scheduler (Agent 21) is the catalog's nod to this, but the chapter-level point is that cost belongs in the evaluation harness from day one, with explicit per-pattern attribution.

The minimum cost telemetry every agent should carry:

- 

Per-session total cost (cents)

- 

Per-step cost attribution (cents per LLM call, cents per tool call)

- 

Per-pattern cost (when more than one pattern contributes to a step)

- 

P50, P90, P99 of per-session cost across the user population

- 

Cost-per-successful-session, not just cost-per-session

A team that has this telemetry can make informed pattern-selection decisions. A team without it makes pattern-selection decisions on vibes and discovers the budget problem at scale.
