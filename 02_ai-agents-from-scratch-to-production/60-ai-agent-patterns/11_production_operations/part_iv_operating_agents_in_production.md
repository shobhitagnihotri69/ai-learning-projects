## Part IV — Operating Agents in Production

![Green binary code displayed in a matrix-style pattern](https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=1600&q=80&fm=jpg&fit=crop)

Part II is the catalog. Part III is composition. Part IV is what happens after the agent ships.

The book's first three parts treat the agent as an architectural artifact. The patterns are right, the composition is sound, the evaluation is rigorous.

And then the agent goes to production and meets the rest of the engineering organization: users who don't read the rubric, product managers with roadmap commitments, on-call engineers paged at 3 AM, version-control workflows, release schedules, customer-success teams escalating issues, legal teams asking about data retention, and security reviewers asking about prompt injection.

Most agents that fail in production fail at this seam, not at the architectural one.

The five chapters in this part address the operational reality:

- 

**Chapter 16 — Agent UX and Product Design:** What the agent looks like to the user, and how that shapes the architecture.

- 

**Chapter 17 — Teams, Roles, and Ownership:** Who owns which part of the agent stack, and what goes wrong when ownership is unclear.

- 

**Chapter 18 — Observability and Incident Response:** What to watch in production, what to do when something breaks, and what a runbook for agent incidents actually contains.

- 

**Chapter 19 — Versioning, Deployment, and Rollback:** How to roll changes to prompts, models, and constitutions without breaking production agents.

- 

**Chapter 20 — Long-Running Autonomy:** Agents that operate over hours, days, or indefinitely, and the patterns that emerge only at those time scales.

If you finish Part III and skip Part IV, you'll build an architecturally-sound agent that struggles in operation. The five chapters below aren't optional. They're the parts of agent engineering the catalog format hides.

### Chapter 16 — Agent UX and Product Design

Every pattern in this book is backend architecture. Every user-facing surface is product design. The two interact: backend choices constrain what UX is possible, and UX choices force backend decisions.

Most teams I've reviewed neglect the interaction and discover, after launch, that the agent that looks right in code looks wrong in the user's hands.

#### 16.1 Three UX surfaces every agent has

Regardless of the product wrapper, every agent has three UX surfaces the team must design deliberately:

- 

**The intake surface:** How the user expresses their goal. A typed-text box, a structured form, a voice channel, an API call, or an event from another system.

- 

**The progress surface:** How the user (or operator) observes what the agent is doing while it works. A spinner, a streaming text feed, a structured step list, a Gantt-style timeline, or a dashboard.

- 

**The output surface:** How the agent's result is presented. Prose, structured data, a clickable artifact, or an action that already happened.

There are various mistakes you can make in each of these surfaces.

First, the intake can be too free-form: "Tell the agent what you want." The user says something ambiguous and the agent does the wrong thing. The user's natural-language is wider than the agent's competence.

Structured intake (multi-step forms, suggested templates, refining questions) often produces better outcomes despite feeling less magical.

Second, progress can be invisible. If you have a spinner for 45 seconds, the user has no idea whether progress is being made. The trust dies in the silence. Streaming reasoning, visible step lists, or progress checkpoints reclaim it.

Third, the output can be opaque text. "Here's what I did": the user can't verify or revert. The user has to trust the agent fully. Structured output with citations, with side-effects listed, or with rollback affordances explicit, gives the user something to act on rather than just accept.

#### 16.2 Trust is built by exposure, not by hiding

The default product instinct is to hide the agent's mechanism: "magic just works." This is exactly wrong for agents that take consequential actions.

Trust scales with the user's ability to verify, override, and understand. The agent that *exposes* the most mechanism — what it's doing, why, what sources it used, what it's about to do, and what it just did — is the agent the user trusts further.

Concretely, show the plan before execution on any state-modifying agent. The Plan-Then-Execute pattern (Agent 19) was designed for this. The UX implication is that the plan must be human-readable, not just machine-readable.

Also, show citations inline on any factual output. The Provenance Tracker (Agent 55) produces them. The UX must render them as clickable references, not strip them out for "cleaner" presentation.

Show side effects in real time as they happen. The user should see "creating GitHub issue is done, assigning reviewer is done" as it happens, not get a summary after the fact.

And finally, show the off-switch. A prominent, always-available "stop" control. The user should never wonder how to interrupt the agent.

The teams the author has seen succeed are the ones that fight product-design instincts toward "magic" and instead build *legible* agents. The teams that lean into magic ship a demo that wows once and disappoints repeatedly.

#### 16.3 Surfacing confidence

Most agent outputs come with implicit confidence the user has no way to see. The agent says "the answer is X." The user can't tell whether the agent is 99% sure or 51% sure. Both are presented the same. This is the single biggest UX failure mode of factual agents.

The fix is structural: surface confidence as a first-class attribute of the output. Several shapes work:

- 

**Hedge language:** "The answer is X" vs. "The answer is likely X" vs. "Three possibilities — X, Y, Z — with X being most consistent with the sources."

- 

**Confidence visualization:** A bar, a percentage, or a stars rating. Works for numerical confidences, but loses nuance.

- 

**Source-strength indicators:** Show how many sources, and of what quality, support each claim. The reader makes their own confidence judgment.

- 

**Refusal as confidence floor:** When confidence is below an operator-set threshold, the agent refuses rather than answering. The Refusal Calibrator (Agent 54) handles this. The UX implication is that refusal must be presented as a *useful* output, not a failure.

The book's catalog has confidence-producing patterns (Self-Consistency Voter, Probabilistic Belief Updater). The UX layer is where the confidence becomes visible.

#### 16.4 The asymmetry of mistakes

The user evaluates the agent on its mistakes, not its successes. One spectacular failure shapes the user's mental model more than a hundred quiet successes. The UX must therefore be optimized for *mistake recovery*, not just successful operation.

There are various concrete UX implications to this:

- 

**Every consequential action should be reversible from the UI:** The Side-Effect Auditor (Agent 37) provides the rollback machinery, and the UX must expose it. A "undo this" button next to a side effect is worth more than ten percent improvement in correctness.

- 

**The agent should announce what it's about to do** for state-modifying actions, with a confirm step the user can decline. The 90% case where the user agrees feels like one extra click. The 10% case where the user catches a mistake builds enormous trust.

- 

**Failures should be informative, not generic:** "I couldn't complete that" is useless. "I tried to access your calendar but Google returned 403 — your authentication may have expired. Try reconnecting." is actionable.

- 

**The agent should know when it doesn't know:** This is the Refusal Calibrator (54) and Memory-of-Self (27) showing up in the UX. The agent that says "this is outside what I'm confident in, here's how to escalate" is the agent that earns repeat use.

#### 16.5 Streaming, latency, and the patience curve

Users have a finite patience budget per interaction. Empirical observation: most users abandon agent sessions that exceed about 30 seconds without visible progress. This sets a hard constraint on architecture.

For agents that take longer than 30 seconds, **streaming intermediate output is mandatory**. Show the reasoning as it happens, show the plan before execution, and show each step's result as it completes.

The patience budget refreshes when the user sees progress. A 5-minute task with continuous visible progress feels like five minutes. A 5-minute task with a spinner feels like an hour.

Finally, the **latency budget should be designed into the architecture**, not discovered. The Resource-Aware Scheduler (Agent 21) handles cost budgets, and latency budgets follow the same discipline. If your pattern stack produces a 60-second median latency, your UX must support 60-second sessions or your architecture is wrong.

#### 16.6 Conversational vs. agentic surfaces

A common confusion: chat-style UX vs. agent-style UX. They're different surfaces with different expectations.

- 

**Chat-style:** Turn-by-turn dialogue. Each turn is complete. The user can revise their previous message. The agent's response is read like a message.

- 

**Agent-style:** A task is given, the agent works on it, and the result is delivered. The agent is doing work, not chatting. The user expects the agent to *act*, not just respond.

Many products mix these awkwardly: a chat interface that occasionally takes action and the user can't tell when. The right discipline is to make the surface clear about which mode it's in. When the agent is acting, show it acting (Progress surface, Section 16.1). When the agent is conversing, show it conversing.

#### 16.7 The product manager's questions

The five questions a product manager should ask before shipping an agent UX:

- 

**What can the user do without trusting the agent?** If the answer is "nothing useful," the agent is too high-trust for its current quality.

- 

**What does the user see while the agent works?** If the answer is "a spinner," the latency is wrong or the streaming isn't there.

- 

**What can the user revert?** If the answer is "nothing," the agent should not be making state-modifying actions.

- 

**What does the user see when the agent refuses?** If refusal is presented as failure, the UX punishes the agent for being honest.

- 

**How does the user know what the agent did?** If the answer is "they read the output text," the audit story is too thin.

A product team that can answer these five concretely has thought through agent UX. A team that can't will discover the answers after launch.

### Chapter 17 — Teams, Roles, and Ownership

Agent engineering is a multi-discipline activity. Building one agent end-to-end requires expertise in prompt design, infrastructure, model selection, evaluation, observability, security, legal/compliance, product, and ops. No single engineer has all of this, and no single team contains all of it. Agents that try to be one team's project fail at the seams where the disciplines don't quite meet.

#### 17.1 The seven roles every serious agent has

A serious production agent has at least seven distinct roles to staff, regardless of whether they map to separate people or to one person wearing multiple hats:

- 

**The agent owner:** Single point of accountability for "is the agent doing its job?" Owns the agent's roadmap, owns the evaluation criteria, and signs off on releases. In small teams, this is usually a tech lead. In larger orgs, it's a product manager paired with an engineering lead.

- 

**The prompt engineer:** Owns the prompts as versioned artifacts. Writes new prompts, validates revisions against eval sets, and manages prompt-version rollout. This is its own discipline, and treating it as "anyone can edit the system prompt" is how prompts degrade.

- 

**The infrastructure engineer:** Owns the gateway (Chapter 2), the model provider relationships, rate limits, secrets management, observability infrastructure, and the tool execution sandbox. Their work is invisible when it works and visible when it doesn't.

- 

**The evaluation engineer:** Owns the eval harness (Chapter 14). Curates labeled sets, calibrates judges, maintains trajectory simulators, and runs adversarial audits. This role is the most under-staffed in the field,a nd teams that staff it well outperform their peers.

- 

**The data steward:** Owns what data the agent sees, what it retains, and for how long. Interfaces with legal/compliance. Implements Privacy-Preserving (Agent 57), Forgetting-Policy (Agent 26), and Persistent Identity (Agent 29) at the policy level.

- 

**The on-call operator:** Owns the runbook (Chapter 18). Responds to alerts, triages incidents, and runs rollbacks. In small teams, this rotates among engineers. In larger ops, it's a dedicated SRE function.

- 

**The security reviewer:** Owns the threat model. Audits the agent for prompt-injection, tool-spoofing, and data-exfiltration risks. Runs (or commissions) red-team exercises. The Red-Team Auditor (Agent 56) is their tool.

Small teams collapse these into 2–3 humans. Larger orgs separate them. The point isn't the org chart. The point is that every role's responsibilities must be owned by someone explicitly.

#### 17.2 The artifacts each role owns

Each role owns versioned artifacts. Listing the artifacts makes the ownership concrete:

- 

**Agent owner** owns: the agent's mission statement, the success metrics, the release schedule, and the priority backlog.

- 

**Prompt engineer** owns: every prompt (system / role / task / frame layers, Chapter 3) with version history.

- 

**Infrastructure engineer** owns: the gateway service, the tool registry, the sandbox config, the observability config, and the secrets vault.

- 

**Evaluation engineer** owns: the labeled eval sets, the rubrics, the judge calibration data, the regression suite, and the dashboards.

- 

**Data steward** owns: the retention policy document, the per-field privacy classification, the consent flows, and the deletion/export endpoints.

- 

**On-call operator** owns: the runbook, the escalation tree, the rollback procedures, and the postmortem archive.

- 

**Security reviewer** owns: the threat model document, the red-team finding archive, and the security regression suite.

A team that doesn't have explicit owners for these artifacts will discover that nobody updates them. Drift is the default, but ownership is the antidote.

#### 17.3 Common ownership failures

There are three common failures of agent-team ownership.

The first is keeping prompts as "anyone can edit." When prompts are shared in a Notion page or a Slack thread, they degrade. Engineer A makes a small change to fix one case, engineer B makes another small change for another case, and six revisions later the prompt is a mess and nobody remembers why.

The fix is to put prompts in version control with a designated owner.

**The second is treating eval as "the QA team's problem",** something done after engineering is done. The result is that the eval set ages out of relevance, judges drift uncalibrated, and the team has no way to detect regressions before users do.

The fix is to make evaluation co-equal with engineering, with the eval engineer at the design table from day one.

The third is thinking "we'll do a security review before launch." Security thinking has to be present at the architecture stage. Adding red-team checks after the agent is built means rewriting parts of the architecture when the checks fail.

The fix is to embed the security reviewer in design discussions, not just acceptance.

#### 17.4 The agent-engineering organization at three scales

There are three plausible team shapes for agents at different organizational scales.

First, you have the solo engineer / small startup. One engineer wears all seven hats. The risk is that every artifact has a single point of failure.

The discipline: write everything down. Treat the prompts, evals, and runbook as if you were going to hand them off tomorrow, because you are. The next engineer is your future self in three weeks who has forgotten everything.

Next, you have a small team (3–8 engineers). Roles cluster into 2–3 people. A typical split: one person on prompt + eval, one person on infrastructure + ops, one person on agent-owner + product + security. This works for a single agent. It doesn't scale to a portfolio.

Then you have an agent platform team (15+ engineers). Roles start to separate. A platform team builds the gateway, the eval infrastructure, the observability stack, the deployment tooling. Agent-product teams consume the platform and own the per-agent prompts, evals, and ops.

The platform vs. agent-product split is the load-bearing decision. Teams that try to have every agent-product team rebuild infrastructure replicate work and ship slower.

#### 17.5 The hand-off problem

Agents in production change hands. The engineer who built the agent leaves, the product manager rotates, or the on-call operator was someone else last week. Each hand-off is an opportunity for institutional knowledge to disappear.

The discipline that prevents this is *documentation as deliverable*. For each agent, create:

- 

A **design document** that explains the capability profile, the patterns selected, and the rationale for each.

- 

A **runbook** that lists incident playbooks, escalation paths, and rollback procedures.

- 

A **release notes archive** that documents every release with what changed and why.

- 

An **eval rubric document** that specifies the questions the eval set is grading and the agreement-rate target.

Treat these documents as code. Version them. Require updates as part of pull requests. Review them on a schedule. A team that does this has agents that survive hand-offs, while a team that doesn't has agents that break when the original engineer takes vacation.

### Chapter 18 — Observability and Incident Response

An agent in production is a service. It has uptime, latency, error rate, cost, and a population of users whose experience depends on its quality.

Most agent teams understand this and instrument the basics: request rate, error rate, latency. The patterns in this chapter go further: what observability is *agent-specific*, and what an incident-response workflow looks like when the thing being incident-ed is non-deterministic.

#### 18.1 The four levels of agent observability

A serious agent has observability at four levels:

- 

**Service-level (the agent as a service):** Request rate, success rate, p50/p90/p99 latency, total cost, error rate by type. The same things you'd watch for any service.

- 

**Session-level (per-session metrics):** Steps per session, tool calls per session, escalation rate, completion rate, cost per session. The Session is the unit (Chapter 14), and this layer measures it.

- 

**Step-level (per-step metrics):** Model latency, prompt token count, completion token count, tool invocation latency, tool success rate. Enables debugging when a session goes wrong.

- 

**Content-level (what the agent said and did):** The full prompt, the full response, the tool calls and results. Required for replay and for forensic incident investigation.

The minimum bar is all four. Teams that have only the first two can detect that something is wrong, but they can't diagnose what. Teams that have all four can diagnose any incident from the recorded data alone.

#### 18.2 The on-call alerts that matter

Not every metric deserves an alert. Here are the alerts that have proven worth waking someone up for:

- 

**Hard error rate** above baseline (the agent is failing to produce any output).

- 

**Refusal rate** sharply rising (the agent has become over-refusing — common after a model upgrade or prompt revision).

- 

**Refusal rate** sharply falling (the agent has become over-compliant — possible safety incident).

- 

**Cost per session** rising more than 2× over baseline (a pattern in the stack is misbehaving. The budget will exceed the operational allocation by end of day).

- 

**Tool error rate** rising on a specific tool (a downstream API or service is degraded).

- 

**Drift Detector (Agent 59) alarm** crossing the critical threshold (input or output distribution shift. Usually a leading indicator of quality regression).

- 

**Side-Effect Auditor (Agent 37) rollback rate** rising (operators are reverting actions. The agent is making mistakes faster than usual).

- 

**Escalation rate** rising (the agent is meeting more out-of-scope requests. Usually a user-population shift).

Alerts that *don't* deserve to be on-call:

- 

Individual model errors. These happen, and they're transient.

- 

Single-session high latency. Could be a long prompt, but not actionable per-session.

- 

Per-step retries below threshold. Retries are normal.

The cardinal rule: every alert must have a documented response in the runbook. An alert without a response is a notification, so treat it accordingly.

#### 18.3 The agent-incident runbook

When an alert fires, what does the on-call do? The runbook should have these sections, in order:

- 

**Triage:** What is the user-facing impact? Are users currently broken, partially broken, or unaffected? Is the agent producing wrong outputs, no outputs, expensive outputs, or unsafe outputs?

- 

**Containment:** What's the smallest action that stops the bleeding? Options in order of severity: throttle to lower-quality model, disable the offending pattern, disable the offending tool, freeze the prompt to the last known-good version, take the agent offline.

- 

**Diagnosis:** Pull representative sessions from the incident window. Use the replay harness (Chapter 4) to reproduce. Identify which pattern, prompt, model, or external dependency changed or failed.

- 

**Mitigation:** Apply the smallest fix that resolves the incident. Roll back to last known-good, hotfix the prompt, route around the failing tool, and so on.

- 

**Postmortem:** Within 48 hours: write up the timeline, root cause, blast radius, and prevention measures. Add the failure mode to the regression suite. Update the runbook.

A team that has this discipline turns every incident into systemic improvement. A team without it has the same incident every six months.

#### 18.4 The agent-specific incident categories

Agent incidents fall into recognizable categories, and each has its own playbook.

First, we have the quality regression incident. Outputs are correct in form but wrong in substance.

The cause: usually a prompt revision, model upgrade, eval set drift, or upstream data quality.

The mitigation: rollback prompt or model, verify against eval set, and identify which patterns are affected.

Then we have the cost incident. Per-session cost has spiked.

The cause: usually a working-memory leak, a loop somewhere in the pattern stack, a new tool with high latency, or a model price change.

The mitigation: identify the cost-multiplying pattern, throttle or disable it, and reset the budget enforcer.

Next we have the safety incident. The agent produced output it should have refused.

The cause: usually a prompt-injection vulnerability, a refusal-calibrator threshold drift, or a new input distribution the constitution didn't cover.

The mitigation: tighten refusal threshol, add the case to the red-team suite, and update the constitution.

Then there's the side-effect incident. The agent took an action it shouldn't have.

The cause: usually a constitutional clause that didn't fire, a side-effect auditor that failed to record, or a tool that was added without proper review.

The mitigation: rollback the side effects via the auditor, tighten the constitution, and review tool authorization.

Lastly, there's the availability incident. The agent is up but unusable (latency too high, error rate too high).

The cause: usually an upstream model provider issue or a tool dependency.

The mitigation: fail over to the secondary provider, route around the failing tool, and degrade gracefully.

Each category has different containment, diagnostic, and mitigation playbooks. The runbook should organize by category, not by chronological recipe.

#### 18.5 Trace retention and forensics

Incident investigation requires replay. Replay requires retained traces. There are two competing pressures:

- 

**Retain enough to investigate:** Every session, every step, every prompt, every response.

- 

**Retain only what privacy/compliance allows:** PII can't be retained indefinitely and user-data deletion requests must be honored.

The resolution: tiered retention. Recent traces (last 30 days) retained in full for incident investigation, older traces aggregated to metrics-only after redaction, and user-data-deletion requests propagate to the trace store.

The Privacy-Preserving (Agent 57) and Forgetting-Policy (Agent 26) patterns govern the policy, and the infrastructure engineer owns the enforcement.

#### 18.6 The "blameless postmortem" applied to agents

A blameless postmortem culture is standard in modern SRE. It applies to agents with a small adjustment: the agent itself is not a person, but the *prompt* is an authored artifact, the *evaluation set* is a curated artifact, and the *patterns selected* are design decisions.

Each was authored by someone. The discipline is to make those decisions visible without blaming the authors. Ask instead: what context made this decision look reasonable at the time?

A useful postmortem question structure for agent incidents:

- 

What was the failure?

- 

Which pattern (or composition of patterns) failed?

- 

What signal could have caught this earlier?

- 

What process change makes this less likely next time?

- 

What test, eval case, or red-team case do we add so this never recurs silently?

The last item is what turns an incident into systemic improvement.

### Chapter 19 — Versioning, Deployment, and Rollback

An agent has many simultaneously-versioned artifacts: the model, the prompts, the tools, the constitution, the evaluation set, the framework, and the underlying libraries. Each can change independently, and each can cause an incident.

Most agent teams discover the versioning problem after their first bad rollout. This chapter is the version of the lesson you can learn before that incident.

#### 19.1 What you version

There are six things to version on every serious agent:

- 

**The model identifier:** Provider, model name, exact model version. "claude-sonnet-4-6-20251022" not "claude". When the provider updates the model under a fixed alias, your agent's behavior changes silently, so version the exact identifier.

- 

**Every prompt:** The four layers (invariant, role, task, frame) each have their own version. Treat them as code: store in version control and require pull requests for changes.

- 

**The tool registry:** Each tool has a version. When the tool's signature, behavior, or permission scope changes, the version bumps.

- 

**The constitution:** A versioned document. Clauses can be added or removed, existing clauses can be modified, and every change has a release note.

- 

**The evaluation set:** Versioned. Cases can be added, and existing cases are immutable. Rubric changes bump the version.

- 

**The framework dependencies:** If you use LangChain, AutoGen, and so on, pin the version. Don't run "the latest". You'll discover that the latest changed semantics.

A change to any of these is a potential incident. Versioning is what makes the change *attributable* and *reversible*.

#### 19.2 The release shape

A canonical agent release has these stages:

- 

**Local development:** Engineer makes a change and tests against a development eval set.

- 

**Pull request:** Reviewer checks the change. Automated CI runs the full eval set. The PR can't merge if eval scores regress beyond threshold.

- 

**Staging deployment:** Change deploys to a staging environment. Synthetic traffic exercises the change. Operator confirms the change behaves as expected.

- 

**Canary rollout:** Change deploys to a small fraction of production traffic (1–5%). Metrics are monitored for a fixed canary window (1–24 hours depending on stakes). The canary either promotes or rolls back automatically based on monitored metrics.

- 

**Progressive rollout:** Change ramps from canary share to full traffic over a defined window (hours to days). Monitoring continues, and the rollout can pause or reverse at any stage.

- 

**Full deployment:** The change is in production.

A team that doesn't have these stages discovers that all changes are "full deployments" — and that every change carries the full risk of a bad change to all users at once.

#### 19.3 What can be rolled back, and how fast

Each artifact has different rollback dynamics.

Prompts can roll back near-instantly. You just re-deploy the previous prompt version. The agent uses it on the next call. Rollback time: seconds.

Models roll back fast. You just update the model identifier, and the gateway routes new calls to the previous model. Rollback time: minutes (cache warmup may take longer).

Rollback time for tools is variable. A tool removed from the registry is rolled back fast, while a tool whose behavior changed is harder (as in-flight sessions may have used the broken behavior).

Constitutions can be rolled back near-instantly. The constitution is a document, and reverting it takes seconds.

Side effects are the hardest to roll back. The agent has already acted. The Side-Effect Auditor (Agent 37) is the rollback machinery here. Rollback time: depends on what actions were taken and whether the inverse operations succeed.

The design implication: side effects are the most expensive thing to get wrong. Plan releases to surface side-effect risks first.

#### 19.4 The "shadow run" technique

Here's a powerful technique for evaluating model upgrades without risking production: run the candidate model in shadow alongside the production model. Both see the same input. But the production model's output is the one users see, and the candidate's output is captured for comparison. After a sufficient sample, compare the candidate vs. production outputs offline.

![Pattern 097 — 19.4 The "shadow run" technique](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5df86c87334148155120_codex-pattern-097-19-4-the-shadow-run-technique.png)

```python
# deployment/shadow.py
async def shadow_run(input, production_model, candidate_model, recorder):
    # Production produces the user-facing response
    production_task = asyncio.create_task(production_model.call(input))
    # Candidate runs in parallel for evaluation
    candidate_task = asyncio.create_task(candidate_model.call(input))
    
    production_response = await production_task
    # Don't await candidate; record when ready
    candidate_task.add_done_callback(
        lambda t: recorder.record_shadow(input, production_response, t.result())
    )
    return production_response
```

The shadow run lets you evaluate candidate changes against real production traffic at zero user risk. The cost is double inference, but the candidate runs can be sampled rather than run on every call.

#### 19.5 Multi-tenant rollout discipline

If the agent serves multiple tenants (customers, teams, business units), rollout discipline must be per-tenant aware.

There are two relevant patterns.

First, you have tenant-tiered rollout. Free-tier tenants get changes first (lower stakes), and paid-tier tenants get changes after a defined soak period. Enterprise tenants get changes after another soak. Bug discovery happens on lower-stakes tenants first.

Then you have tenant-opt-out. Specific tenants can pin to a prior version for compliance, contractual, or just preference reasons. The versioning system supports per-tenant pinning, and the agent reads the tenant's pinned version on each call.

A team without this discipline ships changes that occasionally lose enterprise customers their service-level agreements.

#### 19.6 The deployment runbook

Every agent should have a deployment runbook covering:

- 

How to deploy a prompt change.

- 

How to deploy a model change.

- 

How to deploy a tool change.

- 

How to deploy a constitution change.

- 

How to roll back each of the above.

- 

How to run a shadow comparison.

- 

How to canary a change.

- 

How to investigate a metrics regression detected during canary.

This is one document. Probably 5–10 pages. It's the single most-read document on the team. It's also the document teams most often skip writing until after their first deployment incident.

### Chapter 20 — Long-Running Autonomy

The book's first three parts treat agents as session-shaped: a user submits a goal, the agent works on it, the session completes.

Many real production agents don't fit this shape. They run continuously: a monitoring agent watching a stream of events, a research agent investigating a topic over days, or an operations agent maintaining a system on the user's behalf indefinitely. The patterns are mostly the same, but the *operational* characteristics are different.

#### 20.1 What changes at long time scales

Six things change when the agent's session is measured in days rather than minutes:

- 

**State becomes the load-bearing concern:** A short session's state fits in working memory. A long-running session's state must persist across crashes, deploys, and model upgrades.

- 

**Drift in the environment becomes routine:** The world changes around the agent during its session. APIs change, vendors deprecate, the corpus the agent depends on gets updated. The Drift Detector (Agent 59) graduates from "useful pattern" to "required infrastructure."

- 

**Cost compounds:** A 5-minute session at 10 cents costs 10 cents. A 10-day session at the same per-step rate costs hundreds of dollars. The Resource-Aware Scheduler (Agent 21) becomes essential, not optional.

- 

**Human re-engagement is a feature:** Users forget what they asked the agent to do. The agent needs to remind them, surface what's happened, and re-engage them when input is needed.

- 

**Goal drift is more likely:** The longer the session, the more opportunity for the agent to optimize toward something slightly different than the original goal. The original goal needs to be preserved and re-checked.

- 

**Off-switch responsiveness is harder to maintain:** A long-running agent has many places where the stop-check might not fire. The Off-Switch-Compatible (Agent 60) pattern requires more disciplined application.

#### 20.2 Checkpoint / resume as a first-class capability

A session that may live for days must be able to crash and resume without losing work. This requires various features.

First, periodic state checkpoints. At each meaningful step, the agent's state (working memory, episodic buffer, current plan, side-effect log) is serialized and written to durable storage.

Second, a resume protocol. Given a checkpoint, a fresh agent process can reconstruct enough state to continue. The resume protocol must handle environmental drift: the world may have changed since the checkpoint.

Third, idempotent steps. Each step must be safe to retry after a resume. If the agent crashed mid-step, the resumed agent should either complete the step idempotently or roll back any partial state.

![Pattern 098 — 20.2 Checkpoint / resume as a first-class capability](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5df8e06dd9d9b178f42c_codex-pattern-098-20-2-checkpoint-resume-as-a-first-class-capability.png)

```python
# long_running/checkpoint.py
@dataclass
class Checkpoint:
    session_id: str
    checkpoint_id: str
    timestamp: datetime
    working_memory_snapshot: dict
    episodic_pointer: int
    plan_state: dict
    pending_actions: list[dict]
    last_completed_step: int

class CheckpointingAgent:
    def __init__(self, store, checkpoint_interval_steps=10):
        self.store = store
        self.checkpoint_interval = checkpoint_interval_steps
    
    async def run(self, session_id, goal):
        # Try to resume from existing checkpoint
        existing = self.store.latest_for_session(session_id)
        if existing:
            state = self._restore(existing)
            start_step = existing.last_completed_step + 1
        else:
            state = self._initial_state(goal)
            start_step = 0
        
        for step in range(start_step, MAX_STEPS):
            state = await self._execute_step(state, step)
            if step % self.checkpoint_interval == 0:
                self._save_checkpoint(session_id, step, state)
        
        return state.final_output
```

#### 20.3 Periodic re-grounding

A long-running agent's view of the world goes stale. Periodic re-grounding is the discipline of refreshing what the agent knows:

- 

Re-query the ambient context (Agent 6) on each meaningful step.

- 

Re-validate retrieved sources before citing them in later steps.

- 

Re-confirm the goal with the user at major checkpoint boundaries (daily for week-long sessions, hourly for shorter ones).

- 

Re-verify tool authorizations before each batch of state-modifying actions.

The pattern is mechanical: any "fact" the agent relies on across a long horizon must be re-checked, not assumed.

#### 20.4 Human re-engagement

A long-running agent works on the user's behalf when the user isn't watching. When user input is needed, the re-engagement design becomes critical.

There are three failure modes:

- 

**The re-engagement is missed:** The agent needed input, the user didn't see the notification, the agent stalled.

- 

**The re-engagement is annoying:** The agent asks for input too often, the user disengages.

- 

**The re-engagement loses context:** The user has forgotten what the agent was doing, the question makes no sense without context.

The fix is a deliberate re-engagement design:

- 

**Notify through the right channel for the urgency:** Email for non-urgent, push notification for time-sensitive, and phone call for emergency.

- 

**Always include context:** The notification must remind the user what the agent was doing, why this input is needed, and what the consequence is.

- 

**Make the input structured and easy:** A one-tap choice between three options, not a free-form text response.

- 

**Have a default if the user doesn't respond:** The Human-in-the-Loop Liaison (Agent 42) pattern's "default-and-flag" policy handles this. The long-running version is to define the default at session-start, not inferred per-question.

#### 20.5 Long-term memory hygiene

Long-running agents accumulate state. Without hygiene, the state grows unbounded.

The episodic buffer (Agent 23) fills with events that are no longer relevant. The semantic memory (Agent 24) accumulates facts that contradict newer observations. The skill library (Agent 48) accumulates skills that are no longer valid because their underlying tools changed. The vector store (Agent 28) accumulates documents the agent no longer needs.

The Forgetting-Policy (Agent 26) is the canonical pattern. The long-running application is to run it on a schedule, not on-demand. A weekly hygiene pass over each memory layer keeps the agent's state actionable.

#### 20.6 The "weekend test"

A useful operational test for long-running agents: leave the agent running over a weekend, with no human intervention. Come back Monday. The agent should be in one of three states:

- 

**Still working productively** on the assigned goal, with meaningful progress recorded in the episodic buffer.

- 

**Paused awaiting human input** on a specific question, with the question well-formed.

- 

**Completed** with a final output ready for review.

The agent should *not* be in any of these states:

- 

Looping on the same action repeatedly without progress.

- 

Crashed with no resume in progress.

- 

Burning budget on irrelevant exploration.

- 

Holding state that's now stale and producing wrong outputs against it.

The weekend test is a good integration test for long-running agents. Run it before letting a long-running agent run unsupervised in production.

#### 20.7 The "agent that lives forever" honest assessment

The book has implicit ambition that agents could run indefinitely with proper architecture. Honest assessment from current practice: indefinite autonomy at high quality is rare. Most "long-running" production agents are scheduled jobs that wake up, do work, and sleep — not continuous-running processes.

The patterns in this chapter are useful for the multi-hour and multi-day sessions that *are* shipping. The multi-month autonomous-research-agent shape that occupies research papers has not yet reliably produced a shipping product the author can recommend studying. Reach for these patterns when you have a multi-day session need. Treat indefinite-autonomy as research territory and don't bet a product on it.

## Epilogue — The Capability-Composition Frontier

The patterns in this book are the patterns of the current era. They will outlast specific models and specific frameworks. They have already outlasted three generations of each. What they will not outlast — what nothing should be expected to — is the move from individual patterns to fluent composition.

Two things are happening at once.

First, the patterns themselves are stabilizing. The working set of architectural moves that practitioners use is converging across teams, vendors, and academic groups. The list of patterns is not infinite, the names are settling, and the next edition of this catalogue will look much like this one with refinements rather than upheavals.

The "next big thing" in this space isn't a new pattern. It's a deeper understanding of which patterns to combine in which order for which kinds of problems.

Second, the difficulty of building useful agents is migrating out of the patterns and into the composition. The interesting questions are no longer "which retrieval architecture do I use" but "which six patterns do I wire together for this problem, in what order, with what failure boundaries, and how do I evaluate the whole thing."

The pattern is the alphabet and the composition is the language. The teams that ship working agents in 2026 aren't the teams with the most patterns in their repertoire. They're the teams whose compositions are inspectable, evaluable, and tunable.

The **capability-composition frontier** is where the next decade of agent engineering lives. It includes:

- 

**Formalization of pattern stacks** as inspectable artifacts: versioned, evaluable, comparable across teams. The shape of a "stack" diagram in Chapter 13 will become standard documentation, like API contracts are today.

- 

**Compositional safety.** Alignment patterns that compose with the rest of the stack rather than being applied after the fact. The book makes the case for this, and the next generation of frameworks will make it the default.

- 

**Evaluation systems that grade compositions, not outputs.** The session-level evaluation argued for in Chapter 14 becomes the standard.

- 

**Meta-agents that compose other agents.** Agents whose policy is the construction of pattern stacks from a capability profile. The early versions exist in research labs, and the production versions will follow. This frontier is closer than it sounds. After all, the patterns for it are already in this book.

What doesn't change at the frontier is the discipline. An agent is software. An environment is a software surface. A pattern is a typed contract between subsystems. A composition is an artifact that engineers maintain. The agents that fail in production fail because their builders forgot one of those four things. The agents that succeed succeed because their builders did not.

Build deliberately. Compose explicitly. Evaluate the composition. Off-switches stay on.

The patterns in this book are tools, not principles. The principles (the four things in the preceding paragraph) are what make the tools useful. Hold them. The rest follows.

## Appendix A — Quick Reference: All 60 Patterns

#
Pattern
Capability
One-line tagline

1
Multimodal Grounding
Perception
Aligns linguistic references to visual/audio referents

2
Document Layout
Perception
Turns PDFs into typed region trees

3
Temporal Sensor-Fusion
Perception
Aligns asynchronous streams onto one timeline

4
Anomaly-Spotter
Perception
Surfaces deviations from expected patterns

5
Visual Question Decomposition
Perception
Breaks compound visual queries into sub-queries

6
Ambient Context
Perception
Passively integrates environmental signals

7
Schema-Inference
Perception
Discovers the structure of an unknown data source

8
Chain-of-Thought Auditor
Reasoning
Verifies each step in a reasoning trace

9
Counterfactual Reasoner
Reasoning
Runs "what-if" branches against current state

10
Analogical Mapping
Reasoning
Finds structural parallels to prior cases

11
Constraint-Satisfaction
Reasoning
Narrows the feasible region with a real solver

12
Causal Graph Builder
Reasoning
Induces causal structure for intervention reasoning

13
Symbolic-Neural Bridge
Reasoning
Translates problems to formal expressions and back

14
Probabilistic Belief Updater
Reasoning
Maintains and revises posterior beliefs

15
Self-Consistency Voter
Reasoning
Runs N chains and aggregates by majority

16
Hierarchical Decomposer
Planning
Breaks goals into recursive subgoal trees

17
ReAct Loop
Planning
Interleaves reasoning and action with bounds

18
Tree-of-Thought Explorer
Planning
Branches and prunes a search tree of plans

19
Plan-Then-Execute
Planning
Plans upfront, executes under monitoring

20
Adaptive Replanner
Planning
Rebuilds the plan on detected deviation

21
Resource-Aware Scheduler
Planning
Plans under compute/time/budget constraints

22
Backward Goal-Regression
Planning
Plans from goal state backward

23
Episodic Buffer
Memory
Stores time-and-actor-indexed events

24
Semantic Memory Curator
Memory
Distills episodes into stable facts

25
Working-Memory Manager
Memory
Reshapes context per step

26
Forgetting-Policy
Memory
Prunes memory by relevance decay

27
Memory-of-Self
Memory
Maintains a self-model of capabilities

28
Vector-Store Curator
Memory
Maintains embedding store quality over time

29
Persistent Identity
Memory
Resolves identity across surfaces and sessions

30
Tool Selector
Tool Use
Picks from a large registry without prompt bloat

31
API-Schema Adapter
Tool Use
Derives tools from OpenAPI at runtime

32
Code-Execution Sandbox
Tool Use
Runs model code in isolation

33
Shell-Operator
Tool Use
Drives a shell with safety and rollback

34
Browser-Driver
Tool Use
Navigates web UIs via accessibility trees

35
DB Query Synthesizer
Tool Use
Translates intent to SQL with safety checks

36
File-System Curator
Tool Use
Maintains a directory as a living asset

37
Side-Effect Auditor
Tool Use
Records every side effect with rollback

38
Router/Dispatcher
Coordination
Routes tasks to specialist agents

39
Debate Moderator
Coordination
Adversarial debate between reasoners

40
Consensus-Builder
Coordination
Aggregates heterogeneous outputs

41
Pipeline Orchestrator
Coordination
Sequences agents into producer-consumer chains

42
Human-in-the-Loop Liaison
Coordination
Structured human-in-the-loop integration

43
Negotiation
Coordination
Inter-principal bargaining with utility functions

44
Auctioneer
Coordination
Market mechanism for task allocation

45
Supervisor-Worker
Coordination
Manages a pool of identical workers

46
Feedback Loop
Learning
Accumulates user corrections

47
Reflection
Learning
Self-critique and revise before delivery

48
Skill-Library Builder
Learning
Saves successful procedures as reusable skills

49
Curriculum Designer
Learning
Sequences experience for accelerated growth

50
Few-Shot Prompt Tuner
Learning
Dynamic example selection per call

51
Distillation
Learning
Compresses teacher into student

52
Active Learner
Learning
Picks high-value cases for human labeling

53
Constitution-Bound
Alignment
Per-action structural rule enforcement

54
Refusal Calibrator
Alignment
Measured refusal behavior

55
Provenance Tracker
Alignment
Citations on every load-bearing claim

56
Red-Team Auditor
Alignment
Continuous adversarial evaluation

57
Privacy-Preserving
Alignment
Minimization and de-identification at boundaries

58
Explainer
Alignment
Honest post-hoc decision rationales

59
Drift Detector
Alignment
Monitors input/output distribution shift

60
Off-Switch-Compatible
Alignment
Graceful human override at any point

## Appendix B — Composition Decision Cheat Sheet

If your agent...
Reach for these patterns

...reads complex documents
Document Layout (2), Provenance Tracker (55), Schema-Inference (7)

...takes consequential actions
Constitution-Bound (53), Side-Effect Auditor (37), Off-Switch (60), Human-in-the-Loop Liaison (42)

...handles long sessions
Working-Memory Manager (25), Episodic Buffer (23), Hierarchical Decomposer (16)

...operates on multi-tenant data
Privacy-Preserving (57), Persistent Identity (29), Forgetting-Policy (26)

...makes high-stakes decisions
Self-Consistency Voter (15), Debate Moderator (39), Counterfactual Reasoner (9), Explainer (58)

...handles many APIs
Tool Selector (30), API-Schema Adapter (31), Side-Effect Auditor (37)

...needs to improve over time
Feedback Loop (46), Skill-Library Builder (48), Active Learner (52), Distillation (51)

...crosses agent/principal boundaries
Negotiation (43), Auctioneer (44), Router (38)

...operates under regulation
Constitution (53), Provenance (55), Privacy (57), Explainer (58), Off-Switch (60), Red-Team Auditor (56)

...processes many parallel items
Supervisor-Worker (45), Pipeline Orchestrator (41)

## Appendix C — Patterns We Did Not Include

A book defining sixty patterns implicitly claims the list is exhaustive. It isn't. This appendix lists patterns considered for the catalog and excluded, with the reason for each exclusion. The list is itself a useful map of the design space the book operates in.

### Excluded as Too Immature

These are patterns being explored but not yet ship-shape enough to recommend as canonical:

- 

**Self-improving meta-agent:** An agent that modifies its own prompts or skill library autonomously based on performance signal. Active research area. Current implementations are brittle and require human oversight that defeats the "self" framing.

- 

**Compositional reasoning planner:** An agent that constructs its own composition from a capability profile (a meta-agent for the patterns in this book). Discussed in the Epilogue as a future direction. No production-shape implementation has been demonstrated.

- 

**Verbal self-reflection at scale:** Agents that maintain rich narratives about their own state across long horizons. Useful in research. Production teams find the maintenance cost prohibitive.

- 

**Reward-modeling agent:** An agent that learns user preferences via implicit feedback and updates a reward model. Research-grade. Deployment requires more infrastructure than most teams have.

### Excluded as Duplicates of Named Patterns

These exist in the literature but reduce to patterns already in the catalog:

- 

**"Reflexion."** A specific variant of Reflection (Agent 47). Treated as a variant in the Deeper Dive.

- 

**"Auto-CoT" / "Zero-shot CoT."** A prompting technique for the Chain-of-Thought Auditor's reasoner, not a separate pattern.

- 

**"Toolformer."** A training-time pattern for inducing tool-use in a model. Different abstraction level than the catalog.

- 

**"PAL" / "Program-Aided Language Models."** A specific implementation of Symbolic-Neural Bridge (Agent 13).

- 

**"ReWOO" / "ReACT-with-planning."** A specific composition of ReAct (17) and Plan-Then-Execute (19), covered in Chapter 13.

### Excluded as Anti-patterns

These have been proposed but the book treats them as patterns to avoid:

- 

**Unbounded autonomous agent:** A level-4 agent with no step budget, no constitution, and no off-switch. The Auto-GPT-shaped pattern that briefly captured attention in 2023 and produced almost no shipping products. Excluded because it doesn't survive contact with the failure modes in Chapter 15.

- 

**Personality-as-architecture:** Building agents primarily through character/persona rather than capability composition. Excluded because the resulting agents lack the structural properties needed for production. Persona is an output-layer concern, not an architecture.

- 

**"AI orchestrator" without typed contracts:** Multi-agent systems where the agents coordinate via free-text passing. Excluded because the failure modes are unobservable and unfixable. Superseded by Pipeline Orchestrator (41) with typed contracts.

### Excluded as Out of Scope

These are real patterns but live at a different abstraction level than this book covers:

- 

**Training-time patterns** (RLHF, DPO, constitutional AI training): The book is about deployment-time agents. Training is adjacent but separate.

- 

**Model-routing-as-a-product:** Picking which model to use for which task is real engineering, but it lives outside the agent's policy and is better treated in infrastructure books.

- 

**Embedding-design patterns:** What to embed and how to chunk for retrieval is a substantial topic. The book treats it briefly in Vector-Store Curator and otherwise defers.

- 

**UI-level patterns** (turn rendering, streaming, mid-action interruption UX): The book is backend-shaped. These belong in a product-design companion.

### Excluded Because the Case is Still Being Made

These are patterns we've seen used productively but whose canonical shape is not yet clear:

- 

**Token-budget-aware decoding:** Adaptive sampling that adjusts based on remaining budget. Promising, but no stable formulation.

- 

**Cross-session adversarial replay:** Using one user's adversarial inputs to harden the agent for other users. Powerful, but raises privacy and consent questions that exceed the book's scope.

- 

**Continuous online distillation:** Distillation that runs as a streaming pipeline rather than as periodic batch. Real teams do this, but the canonical shape is still emerging.

This list is honest about the catalog's boundaries. A reader who has been deploying agents will recognize patterns they use that aren't in the book. That is expected. The sixty patterns in the catalog are the ones with the most-stable shapes, the clearest case studies, and the broadest applicability — not the only ones worth knowing.

## Appendix D — Bibliography

The references that appear in the *Theoretical roots* subsection of each Deeper Dive are compiled here for easy lookup.

Every reference below has been checked against a canonical source (the publication venue, arXiv, the author's own page, or (for the framework and failure-case entries) the official project page or a contemporaneous, reputable news report) and links directly to that source. Where a citation in an earlier draft of this book turned out to be imprecise, it's corrected here rather than merely flagged.

### Foundational References

- 

Baddeley, A. & Hitch, G. (1974). [*Working Memory.*](https://app.nova.edu/toolbox/instructionalproducts/edd8124/fall11/1974-Baddeley-and-Hitch.pdf) In *Psychology of Learning and Motivation*, Vol. 8, pp. 47–89 — the model behind the cognitive framing in Chapter 8.

- 

Bengio, Y., Louradour, J., Collobert, R., & Weston, J. (2009). [*Curriculum Learning.*](https://dl.acm.org/doi/10.1145/1553374.1553380) ICML 2009, pp. 41–48 — the curriculum-design lineage for Agent 49.

- 

Flavell, J. H. (1979). [*Metacognition and Cognitive Monitoring: A New Area of Cognitive-Developmental Inquiry.*](https://eric.ed.gov/?id=EJ217109) American Psychologist, 34(10), 906–911 — metacognition literature behind the Memory-of-Self (Agent 27).

- 

Fellegi, I. P. & Sunter, A. B. (1969). [*A Theory for Record Linkage.*](http://www2.stat.duke.edu/~rcs46/linkage/presentations/01-baiLi_FelleigSunter1969.pdf) Journal of the American Statistical Association, 64(328), 1183–1210 — the identity-resolution lineage for Agent 29.

- 

Gentner, D. (1983). [*Structure-Mapping: A Theoretical Framework for Analogy.*](https://onlinelibrary.wiley.com/doi/abs/10.1207/s15516709cog0702_3) Cognitive Science, 7(2), 155–170 — the analogical-reasoning lineage for Agent 10.

- 

Hinton, G., Vinyals, O., & Dean, J. (2015). [*Distilling the Knowledge in a Neural Network.*](https://arxiv.org/abs/1503.02531) arXiv:1503.02531 — the distillation lineage for Agent 51.

- 

Lewis, D. (1973). [*Counterfactuals.*](https://www.cambridge.org/core/journals/philosophy-of-science/article/abs/david-lewis-counterfactuals-cambridge-massachusetts-harvard-university-press-1973-x-150-pp-np/F54B879F7B4CD4AF3A3858D75C9B5EEB) Harvard University Press — possible-worlds semantics referenced for Agent 9.

- 

Mackworth, A. K. (1977). [*Consistency in Networks of Relations.*](https://www.cs.ubc.ca/~mack/Publications/b2hd-AI77.html) Artificial Intelligence, 8(1), 99–118 — arc-consistency lineage for Agent 11.

- 

Newell, A. & Simon, H. A. (1972). [*Human Problem Solving.*](https://archive.org/details/humanproblemsolv0000newe) Prentice-Hall — GPS and backward-search lineage for Agent 22.

- 

Pearl, J. (2009). [*Causality: Models, Reasoning, and Inference*](https://en.wikipedia.org/wiki/Causality_(book)) (2nd ed.). Cambridge University Press — causal-inference framework for Agent 12.

- 

Settles, B. (2009). [*Active Learning Literature Survey.*](https://burrsettles.com/pub/settles.activelearning.pdf) Computer Sciences Technical Report 1648, University of Wisconsin–Madison — the canonical survey for Agent 52.

- 

Tulving, E. (1972). [*Episodic and Semantic Memory.*](https://www.semanticscholar.org/paper/Episodic-and-semantic-memory-Tulving/d792562462dbb687015954805d31620240db57a1) In E. Tulving & W. Donaldson (Eds.), *Organization of Memory*, pp. 381–403, Academic Press — the cognitive distinction underlying Chapter 8.

- 

Vickrey, W. (1961). [*Counterspeculation, Auctions, and Competitive Sealed Tenders.*](https://ideas.repec.org/a/bla/jfinan/v16y1961i1p8-37.html) Journal of Finance, 16(1), 8–37 — auction-theory lineage for Agent 44.

- 

Vygotsky, L. S. (1978). [*Mind in Society.*](https://www.hup.harvard.edu/books/9780674576292) Harvard University Press — zone-of-proximal-development referenced for Agent 49.

### Agent-Engineering Era References

- 

Irving, G., Christiano, P., & Amodei, D. (2018). [*AI Safety via Debate.*](https://arxiv.org/abs/1805.00899) arXiv:1805.00899 — debate-as-oversight lineage for Agent 39.

- 

Madaan, A. et al. (2023). [*Self-Refine: Iterative Refinement with Self-Feedback.*](https://arxiv.org/abs/2303.17651) arXiv:2303.17651 — the modern Reflection lineage for Agent 47.

- 

Perez, E. et al. (2022). [*Red Teaming Language Models with Language Models.*](https://arxiv.org/abs/2202.03286) arXiv:2202.03286, EMNLP 2022 — red-team-auditor lineage for Agent 56.

- 

Wang, X. et al. (2022). [*Self-Consistency Improves Chain of Thought Reasoning in Language Models.*](https://arxiv.org/abs/2203.11171) arXiv:2203.11171 — the self-consistency-voting lineage for Agent 15.

- 

Wei, J. et al. (2022). [*Chain-of-Thought Prompting Elicits Reasoning in Large Language Models.*](https://arxiv.org/abs/2201.11903) arXiv:2201.11903 — CoT lineage for Agent 8.

- 

Yao, S. et al. (2023). [*ReAct: Synergizing Reasoning and Acting in Language Models.*](https://arxiv.org/abs/2210.03629) arXiv:2210.03629, ICLR 2023 — the ReAct lineage for Agent 17.

- 

Yao, S. et al. (2023). [*Tree of Thoughts: Deliberate Problem Solving with Large Language Models.*](https://arxiv.org/abs/2305.10601) arXiv:2305.10601 — ToT lineage for Agent 18.

### Frameworks and Tools Cited in the Book

- 

[Anthropic Claude tool-use API](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview), [OpenAI Assistants API](https://platform.openai.com/docs/api-reference/assistants), [Google Gemini API](https://ai.google.dev/gemini-api/docs) — the major frontier-model APIs underlying tool-using agents. (OpenAI has announced the Assistants API's retirement in favor of the Responses API — check current docs before building against it.)

- 

[LangChain](https://www.langchain.com/) / [LangGraph](https://github.com/langchain-ai/langgraph) — coordination-heavy framework.

- 

[AutoGen](https://github.com/microsoft/autogen) (Microsoft) — multi-agent coordination framework. Now in maintenance mode, superseded by [Microsoft Agent Framework](https://github.com/microsoft/agent-framework) for new projects.

- 

[DSPy](https://github.com/stanfordnlp/dspy) (Stanford, led by Omar Khattab) — prompts-as-compiled-programs framework.

- 

[CrewAI](https://github.com/crewAIInc/crewAI) — lightweight multi-agent framework.

- 

[Pydantic AI](https://ai.pydantic.dev/) — typed-output framework.

- 

[Haystack](https://github.com/deepset-ai/haystack) (deepset) — retrieval-and-pipeline framework.

- 

[Temporal](https://temporal.io/) — durable workflow substrate suitable for agent execution.

### Benchmarks Cited

- 

[SWE-bench](https://github.com/swe-bench/SWE-bench) / [SWE-bench Verified](https://openai.com/index/introducing-swe-bench-verified/) (Jimenez et al., 2023; Verified subset released by OpenAI, 2024)

- 

[GAIA](https://arxiv.org/abs/2311.12983) (Mialon et al., 2023, Meta / HuggingFace / AutoGPT)

- 

[AgentBench](https://arxiv.org/abs/2308.03688) (Liu et al., 2023)

- 

[WebArena](https://github.com/web-arena-x/webarena) (Zhou et al., 2023)

- 

[OSWorld](https://os-world.github.io/) (Xie et al., 2024)

- 

[τ-bench](https://github.com/sierra-research/tau-bench) (Yao et al., 2024, Sierra)

- 

[BIRD-SQL](https://bird-bench.github.io/) (Li et al., 2023)

- 

[Spider](https://yale-lily.github.io/spider) (Yu et al., 2018)

- 

[MMLU](https://arxiv.org/abs/2009.03300) (Hendrycks et al., 2020)

- 

[HELM](https://crfm.stanford.edu/helm/) (Liang et al., 2022, Stanford CRFM)

### Failure-case References

- 

[*Moffatt v. Air Canada*, 2024 BCCRT 149](https://www.cbc.ca/news/canada/british-columbia/air-canada-chatbot-lawsuit-1.7116416) — British Columbia Civil Resolution Tribunal — chatbot promise enforceability.

- 

[*Mata v. Avianca, Inc.*](https://en.wikipedia.org/wiki/Mata_v._Avianca,_Inc.) (2023) — fabricated case citations by counsel using ChatGPT.

- 

[*NYC MyCity chatbot reporting*](https://themarkup.org/artificial-intelligence/2024/03/29/nycs-ai-chatbot-tells-businesses-to-break-the-law) (The Markup, 2024) — government chatbot generating illegal-advice content.

- 

[*Replit Agent production-database deletion*](https://fortune.com/2025/07/23/ai-coding-tool-replit-wiped-database-called-it-a-catastrophic-failure/) (2025) — coding agent deleted a live production database during a code freeze.

- 

[*Microsoft Tay incident reporting*](https://time.com/4270684/microsoft-tay-chatbot-racism/) (2016) — early large-scale alignment-failure case.

- 

[*Devin's benchmark claims and the scrutiny that followed*](https://blog.pragmaticengineer.com/the-ai-developer/) — independent analysis of Cognition's demo-vs-benchmark gap.

The bibliography is provided to point the reader toward real, checkable bodies of work. Links can rot, so if one goes dead, search the title and authors above rather than assuming the claim itself is unsupported.

## Appendix E — Glossary

A short glossary of book-specific terminology and the standard terms used in non-standard ways.

- 

**Agent:** A program with three properties: it observes an environment, maintains state across observations, and emits actions whose effects feed back into its next observation. In this book, "agent" usually refers to an LLM-driven agent. Non-LLM agents share the architecture but most patterns assume an LLM in the policy slot.

- 

**Capability:** One of the eight high-level functional categories the book uses to organize patterns: perception, reasoning, planning, memory, tool use, coordination, learning, and alignment. Capabilities are deliberately broad, while patterns are specific architectures within a capability.

- 

**Capability profile:** A one-page summary of which capabilities a given agent exercises and which patterns it uses within each. The first artifact produced when scoping a new agent.

- 

**Composition:** The act of combining multiple patterns into a single agent. The book argues that composition is the primary skill of senior agent engineers.

- 

**Constitution:** A human-readable but machine-evaluable rule-set that the agent's actions are checked against. See Constitution-Bound (Agent 53).

- 

**Deployment-alignment:** The book's usage of "alignment." Refers to the engineering of agents that behave correctly within a deployed application — distinct from the AI-safety-research sense of alignment.

- 

**Failure boundary:** The point in a composition where one pattern's failure must not propagate to the next. The book argues that failure boundaries should be made explicit, not assumed.

- 

**Gateway pattern:** The thin internal service in front of model providers that handles rate limiting, cost attribution, observability, and model swaps. Discussed in Chapter 2.

- 

**Harness:** The deterministic Python wrapping the (stochastic) LLM policy. The harness owns the loop, the tool registry, the memory layer, and the observability layer. See Chapter 1.

- 

**Idempotency key:** A unique value attached to a tool invocation so that retries don't produce duplicate side effects. Required infrastructure for any agent whose tools modify external state.

- 

**Load-bearing claim:** A factual claim in an agent's output that the user's downstream decision depends on. Distinct from incidental claims. The Provenance Tracker (Agent 55) attaches citations to load-bearing claims specifically.

- 

**Pattern:** A reusable architectural decision with a defined shape, interface, code skeleton, and failure profile. The book contains sixty named patterns. See Appendix C for what was excluded.

- 

**Pattern stack:** The rendered composition of patterns in a specific agent, with data shapes flowing between them and failure boundaries between subsystems.

- 

**Policy:** The deciding component of an agent — the function from state to action. Usually backed by an LLM call. Distinct from the harness, which is deterministic.

- 

**Provenance:** The traceable connection from a claim in an agent's output back to the observation or computation that supports it. The Provenance Tracker (Agent 55) makes this explicit.

- 

**Refusal class:** A category of refusal (safety, capability, policy, identity) used by the Refusal Calibrator (Agent 54). Structured refusals make refusal a designed behavior rather than an emergent one.

- 

**Side-effect class:** The classification of a tool by what kind of effect it has on external state: read-only, state-modifying, destructive. Used by the Side-Effect Auditor (Agent 37) and the Constitution-Bound Agent (Agent 53).

- 

**Skill:** A reusable named procedure extracted from successful agent traces and stored in the Skill Library (Agent 48). Skills are composite tools the policy can invoke.

- 

**Substrate:** The model and infrastructure layer beneath the agent: the LLM, the embedding model, the vector store, the tool execution environment. Chapter 4A discusses how substrate shifts change which patterns are worth deploying.

- 

**Tool:** A typed external interface the agent can invoke to act on the world. Tools have names, descriptions, parameter schemas, and side-effect classes.

- 

**Trace:** A structured record of an agent's execution: each step's prompt, response, tool calls, observations, costs, and timing. The unit of replay (Chapter 4) and the substrate for evaluation (Chapter 14).

- 

**Typed contract:** An interface between agent subsystems specified by input and output schemas, not by free-text passing. Typed contracts are the book's recurring discipline for making compositions inspectable.

- 

**Working memory:** The contents of the current prompt window: the part of the agent's state visible to the model on the current call. Distinct from persistent memory, which is external to the prompt and queried as needed. See Working-Memory Manager (Agent 25).

## Appendix F — Operator Dashboard Sketches

The book repeatedly says "instrument X, Y, Z." This appendix is concrete: what does an operator's dashboard actually look like for a production agent? Three sketches at different scales, each rendered in monospace ASCII to convey the layout without committing to specific dashboard technology (Grafana, Datadog, in-house — all can render the same shape).

### F.1 The Single-agent Operator Dashboard

For a single deployed agent. The view an on-call operator pulls up first when an alert fires:

![Pattern 099 — F.1 The Single-agent Operator Dashboard](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5df8aa8f4fd98dfcfb27_codex-pattern-099-f-1-the-single-agent-operator-dashboard.png)

```plaintext
═══════════════════════════════════════════════════════════════════════
  AGENT: research-assistant-v3.2    │   STATUS: ●  HEALTHY (last 1h)
═══════════════════════════════════════════════════════════════════════

  TRAFFIC (last 1h)                  HEALTH (last 1h)
  ─────────────────────────────      ──────────────────────────────
  Sessions:        1,247            Success rate:      94.2%  ✓
  Active now:           23           Refusal rate:       3.8%  ✓
  P50 latency:      8.2s             Escalation rate:    2.1%  ✓
  P99 latency:     34.5s             Hard error rate:    0.4%  ✓

  COST (last 1h)                     DRIFT SIGNALS (last 24h)
  ─────────────────────────────      ──────────────────────────────
  Total spend:    $48.20             Input distribution:    ●  ok
  Per-session:    $0.039             Output distribution:   ●  ok
  vs. baseline:   +12%   ⚠           Refusal-class mix:     ●  ok
  Worst session:  $0.41              Tool-call distribution: ⚠ warn
                                     Cost-per-session:      ⚠ warn

  TOP TOOLS USED (last 1h)           ALERTS (last 24h)
  ─────────────────────────────      ──────────────────────────────
  search_web        38%              [12:14] WARN: cost/session +15%
  fetch_doc         24%              [10:02] INFO: drift on tool mix
  summarize         18%              [08:30] INFO: model upgrade
  query_db          12%              
  other             8%
═══════════════════════════════════════════════════════════════════════
  Quick actions:  [ Pause agent ]  [ Rollback to v3.1 ]  [ Pull traces ]
═══════════════════════════════════════════════════════════════════════
```

Notes on this layout:

- 

**Status traffic light at top-right:** First thing the operator sees. Green if all alarms are below warn, yellow if any warn, red if any critical.

- 

**Six panels in a 2×3 grid:** Each panel is one operational concern. The 2×3 layout is the most-information-per-glance shape.

- 

**Quick actions at the bottom:** The three actions an operator most often takes in an incident: pause the agent, roll back, pull recent traces for investigation. One click each.

- 

**No "session detail" panel:** The dashboard is for aggregate signals, session detail belongs in a separate drill-down view.

### F.2 The Session-detail Drill-down

![Lines of code displayed on a black computer screen](https://images.unsplash.com/photo-1743090660977-babf07732432?w=1600&q=80&fm=jpg&fit=crop)

When the operator clicks "pull traces" or a specific session ID, this is what comes up:

![Pattern 100 — F.2 The Session-detail Drill-down](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5df8c289ca370bc0f847_codex-pattern-100-f-2-the-session-detail-drill-down.png)

```plaintext
═══════════════════════════════════════════════════════════════════════
  SESSION: sess_2026_05_28_142331    │   USER: u_4f8c2a    │   ●  failed
═══════════════════════════════════════════════════════════════════════

  GOAL:  "Compare Q3 revenue across product lines and identify outliers"
  
  TIMELINE                                                    cost  outcome
  ─────────────────────────────────────────────────────────  ─────  ───────
  T+00.0  perceive: read dashboard           [working memory]  $.01    ok
  T+00.5  plan: 5-step research plan         [decomposer]     $.01    ok
  T+01.0  retrieve: Q3 revenue by product    [search_db]      $.02    ok
  T+02.5  retrieve: historical comparisons   [search_db]      $.02    ok
  T+04.0  analyze: identify outliers         [voter N=5]      $.18    ok
  T+09.0  audit: chain-of-thought check      [auditor]        $.04    ⚠ flagged
  T+09.5  revise: from invalid step #3       [reviser]        $.05    ok
  T+12.5  draft: synthesis with citations    [provenance]     $.06    ok
  T+15.0  reflect: review draft              [reflector]      $.04    ⚠ infinite loop
  T+47.0  TERMINATED: step budget exhausted                   $.34

  TOTAL:  $0.81 (4.5× session baseline)      47 steps          failed

  ROOT CAUSE (auto-suggested):  Reflection step entered a loop at T+15.
                                Last 5 steps were near-identical revisions.
  
  REMEDIATION OPTIONS:  
    [1] Replay with reflection disabled
    [2] Replay with model fallback to v3.1
    [3] Inspect prompt at T+15
    [4] Flag for human review
═══════════════════════════════════════════════════════════════════════
```

Notes:

- 

**Timeline format:** Every step gets one row with cost, outcome, and tool. Operator can scan vertically and spot the anomaly (the $0.18 voting spike, the loop after T+15).

- 

**Auto-suggested root cause:** The replay system tries to identify the failure mode. Usually right. If wrong, the operator still has the full timeline.

- 

**Remediation options listed:** Each is one click to start a re-run with the variation applied.

### F.3 The Agent-portfolio Dashboard

For organizations operating multiple agents. The view for the platform-team lead or VP-Eng:

![Pattern 101 — F.3 The Agent-portfolio Dashboard](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5df887f2457e355367b2_codex-pattern-101-f-3-the-agent-portfolio-dashboard.png)

```plaintext
═══════════════════════════════════════════════════════════════════════
  AGENT PORTFOLIO     │   FLEET: 7 agents    │   STATUS: 5 healthy, 1 warn, 1 critical
═══════════════════════════════════════════════════════════════════════

                              traffic  success  cost/sess  trend
  ─────────────────────────  ───────  ───────  ─────────  ──────
  ● customer-support-v7      14.2K/d   97.1%   $0.024     ↑
  ● research-assistant-v3.2  1.2K/d    94.2%   $0.039     →
  ● underwriting-bot-v2      340/d     99.3%   $0.18      →
  ⚠ sales-email-drafter-v4   8.7K/d    71.4%   $0.06      ↓  (regression suspected)
  ● dev-tools-agent-v1.1     2.4K/d    91.0%   $0.04      →
  ● analytics-copilot-v2     5.6K/d    88.3%   $0.07      ↑
  ● contract-redliner-v1.3   180/d     96.1%   $0.31      →

  PORTFOLIO-LEVEL SIGNALS                      RECENT INCIDENTS
  ───────────────────────────────────         ─────────────────────
  Total daily spend:        $1,840            05/27  sales-email v4 deploy
  Daily session volume:    32.5K              05/24  customer-support drift
  P99 cross-fleet latency:  41s               05/20  dev-tools cost spike
  Open incidents:           1                 05/18  underwriting refusal calibrate

  PATTERN COVERAGE ACROSS FLEET                COMPLIANCE STATUS
  ───────────────────────────────────         ─────────────────────
  Off-Switch (60):      7/7  ✓ all            HIPAA agents:   3/3 ✓
  Side-Effect Auditor:  6/7  ⚠ missing on cs  SOX-bound:      2/2 ✓
  Constitution (53):    7/7  ✓ all            GDPR endpoints: 7/7 ✓
  Provenance (55):      5/7  ⚠ missing on 2   Audit retention: 7/7 ✓
═══════════════════════════════════════════════════════════════════════
```

Notes:

- 

**Per-agent traffic-light rows:** One line per agent. Operator can see fleet health at a glance.

- 

**Portfolio-level signals:** Daily spend across the fleet, daily session volume — for capacity and budget planning.

- 

**Pattern coverage:** Which agents have which load-bearing patterns. This is the executive-level view of "which agents are at structural risk."

- 

**Compliance status:** The bottom-right panel is what the data steward and legal/compliance team need to see weekly.

### F.4 What These Dashboards Have in Common

Three design principles for any agent operational dashboard:

- 

**One screen at a time, no scrolling for primary view:** If the operator has to scroll to see the warning, the warning may as well not exist. Fit the critical signal density to one screen at each scale.

- 

**Color is reserved for severity, not for decoration:** Green / yellow / red carry meaning. Don't use color for anything else. Dashboards that color-code by category exhaust the visual vocabulary that should be reserved for "this needs attention."

- 

**Every signal is actionable or it doesn't belong:** If a metric trending up doesn't change what the operator does, drop the metric. Dashboards that show ten metrics nobody acts on train operators to ignore dashboards.

These sketches are starting points. Every team will adapt them. The principles outlast the layouts.
