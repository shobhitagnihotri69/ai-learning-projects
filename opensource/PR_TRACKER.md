# 🚀 Open Source PR & Merge Velocity Tracker

> **Campaign Started:** September 8, 2026  
> **First PR Merged Milestone:** September 15, 2026 (Day 7 🎉)  
> **Second PR Merged Milestone:** September 18, 2026 (Day 10 🎉)  
> **Status:** All dead/dormant repositories purged. 100% active YC & a16z startup pipeline.

---

## 🏆 Major Milestones

| Milestone | Date | Days from Kickoff | Details |
| :--- | :---: | :---: | :--- |
| **Campaign Kickoff** | 2026-09-08 | Day 0 | Started targeted open-source contributions across YC & AI agent repos |
| 🥇 **FIRST PR MERGED** | **2026-09-15** | **Day 7** | **`uselemma/lemma#81`** merged into main branch! |
| 🥈 **SECOND PR MERGED** | **2026-09-18** | **Day 10** | **`Hebbian-Robotics/hflow#559`** merged into main branch! (< 24h turnaround) |
| 🥉 **THIRD PR MERGED** | **2026-09-19** | **Day 11** | **`preloop/preloop#796`** merged by founder `@d-mo`! (*"Thank you for the contribution!"*) |
| 🏅 **FOURTH PR MERGED** | **2026-09-19** | **Day 11** | **`preloop/preloop#808`** merged by founder `@d-mo` after CI & review signoff! |

---

## 📊 Summary Metrics (As of September 19, 2026)

- **Total Active Portfolio PRs:** 30 (100% active, zero dead baggage)
- **Merged PRs:** 4 🎉 (`uselemma/lemma#81`, `Hebbian-Robotics/hflow#559`, `preloop/preloop#796`, `preloop/preloop#808`)
- **Active Open Upstream PRs:** 15 (Currently live on upstream repos)
- **Tested & Pushed Branches (Ready to Open / In Queue):** 7 (including `preloop:fix/805-mcp-session-rollback`)
- **Sequential Staged Batches (Lemma):** 4 (Verified & pushed to fork, queued for sequential release)
- **Dead / Inactive Repositories:** **0** (All 8 dead PRs permanently removed from tracking)
- **Average Turnaround for Merged PRs:** **2.3 days** (Lemma: 6d, Hflow: <1d, Preloop #796: 1d, Preloop #808: <1d)
- **Maintainer Sentiment:** High praise from both Hebbian robotics (*"Staging the validation ahead of the writes is the right shape... Your slot is free again"*) and Preloop founder `@d-mo` (*"Thank you for the contribution!"*).

---

## 🟣 Merged Pull Requests (4 PRs)

| # | Repository & PR | Submission Date | Merge Date | Turnaround | Impact & Summary |
| :-: | :--- | :---: | :---: | :---: | :--- | :--- |
| 1 | **[uselemma/lemma#81](https://github.com/uselemma/lemma/pull/81)** | 2026-09-09 | **2026-09-15** | **6 days** | `fix(tracing): detect success: false and status: error tool failure payload` — Fixed critical tool call failure detection in agent tracing telemetry. |
| 2 | **[Hebbian-Robotics/hflow#559](https://github.com/Hebbian-Robotics/hflow/pull/559)** | 2026-09-17 | **2026-09-18** | **< 1 day** | `fix(lerobot): refuse task_index referencing unpublished tasks before destination file writes` — Fixed critical dataset exporter corruption (Fixes #529). Maintainer approved & praised mutation resilience. |
| 3 | **[preloop/preloop#796](https://github.com/preloop/preloop/pull/796)** | 2026-09-18 | **2026-09-19** | **~1 day** | `fix(ask_user): drop unsupported item keys and validate schema item resilience` — Founder `@d-mo` approved & merged (*"Thank you for the contribution!"*). |
| 4 | **[preloop/preloop#808](https://github.com/preloop/preloop/pull/808)** | 2026-09-18 | **2026-09-19** | **< 1 day** | `fix(cli): one OAuth lineage per Codex CLI enrollment (#799)` — Founder `@d-mo` review approved and merged into main branch! |

---

## 🟢 Active Open Pull Requests Pipeline (16 Upstream PRs)

| # | Repository & PR | Submission Date | Days Live | Status & Focus |
| :-: | :--- | :---: | :---: | :--- |
| 1 | **[BoundaryML/baml#4904](https://github.com/BoundaryML/baml/pull/4904)** | 2026-09-17 | 1 day | `fix(engine): allow integral host return values to satisfy declared float` — Fixes #4901; reviewed by CodeRabbit |
| 2 | **[onyx-dot-app/onyx#14860](https://github.com/onyx-dot-app/onyx/pull/14860)** | 2026-09-17 | 1 day | `fix(auth): promote EXT_PERM_USER placeholders and include in admin user list` — Fixes #14858; addressed cubic review with atomic locking |
| 3 | **[mem0ai/mem0#7357](https://github.com/mem0ai/mem0/pull/7357)** | 2026-09-17 | 1 day | `fix(config): scope OpenAI default model, baseURL, and apiKey to OpenAI providers` — Fixes #7349; CLA signed, in queue for maintainer triage |
| 4 | **[opslane/opslane#534](https://github.com/opslane/opslane/pull/534)** | 2026-09-17 | 1 day | `fix(worker): stop score_sync retrying when fix job predates tracing or exceeds retry bound` — Fixes #523; addressed CodeRabbit review |
| 5 | **[usemoss/moss#526](https://github.com/usemoss/moss/pull/526)** | 2026-09-17 | 1 day | `test(integrations): add offline unit tests for elevenlabs-moss and pipecat-moss` — Fixes #521; 29/29 tests pass |
| 6 | **[deepnote/vscode-deepnote#532](https://github.com/deepnote/vscode-deepnote/pull/532)** | 2026-09-17 | 1 day | `fix(toolkit): reinstall kernel spec if it launches stale interpreter` — Fixes #472; typecheck & lint green |
| 7 | **[firecrawl/cli#247](https://github.com/firecrawl/cli/pull/247)** | 2026-09-17 | 1 day | `fix(web-defaults): safely parse JSON with strings containing slashes and comments` — Fixes #219; 506/506 tests green |
| 8 | **[modaic-ai/modaic#200](https://github.com/modaic-ai/modaic/pull/200)** | 2026-09-17 | 1 day | `fix(tests): skip arbiter git push tests cleanly when user lacks org write permissions` — Fixes #74 |
| 9 | **[RunanywhereAI/runanywhere-sdks#954](https://github.com/RunanywhereAI/runanywhere-sdks/pull/954)** | 2026-09-17 | 1 day | `fix(python): allow unnormalized embeddings with normalize=False` |
| 10 | **[huggingface/Repo2RLEnv#137](https://github.com/huggingface/Repo2RLEnv/pull/137)** | 2026-09-17 | 1 day | `fix(reward): ignore git extended headers and mode lines in diff normalization` — Collaborator review addressed (`32b297a`) |
| 11 | **[burtenshaw/training-agents#31](https://github.com/burtenshaw/training-agents/pull/31)** | 2026-09-16 | 2 days | `fix(launcher): prevent file descriptor leaks during cloudflared tunnel polling` |
| 12 | **[RunanywhereAI/wally#112](https://github.com/RunanywhereAI/wally/pull/112)** | 2026-09-16 | 2 days | `fix(install): fallback to sha256sum if shasum is not installed` |
| 13 | **[uselemma/lemma#84](https://github.com/uselemma/lemma/pull/84)** | 2026-09-15 | 3 days | `fix(tracing): preserve open-time attributes and metadata on SpanHandle.end()` — Passed CodeRabbit verification |
| 14 | **[trycua/cua#3911](https://github.com/trycua/cua/pull/3911)** | 2026-09-17 | 1 day | `fix(lume): shell-escape remote command arguments in lume ssh (#3879)` |
| 15 | **[hud-evals/hud-python#669](https://github.com/hud-evals/hud-python/pull/669)** | 2026-09-16 | 2 days | `feat(graders): add ASTCodeGrader for AST-level syntax and structure validation` |
| 16 | **[hud-evals/hud-python#663](https://github.com/hud-evals/hud-python/pull/663)** | 2026-09-14 | 4 days | `fix(openai): persist refusal explanations in OpenAIAgent response` |

---

## 🟡 Tested & Pushed Branches (Ready to Open / In Queue — 6 PRs)

| # | Repository & Compare Link | Branch Name | Tests & Verification | Focus |
| :-: | :--- | :--- | :---: | :--- |
| 1 | **[preloop/preloop](https://github.com/preloop/preloop/compare/main...shobhitagnihotri69:preloop:fix/805-mcp-session-rollback?expand=1)** | `fix/805-mcp-session-rollback` | 20/20 Pass ✅, pre-commit ✅ | `fix(mcp): roll back DB session on tool error and sanitize DB errors (#805)` |
| 2 | **[evidentlyai/evidently](https://github.com/evidentlyai/evidently/compare/main...shobhitagnihotri69:evidently:fix/1914-g-test-sample-size-normalization?expand=1)** | `fix/1914-g-test-sample-size-normalization` | 100% Green (Regression test) | `fix(g_test): normalize expected frequencies for different sample sizes (fixes #1914)` |
| 3 | **[humanlayer/homebrew-humanlayer](https://github.com/humanlayer/homebrew-humanlayer/compare/main...shobhitagnihotri69:homebrew-humanlayer:chore/remove-deprecated-verified-parameter?expand=1)** | `chore/remove-deprecated-verified-parameter` | `ruby -c` Verified | `chore(casks): remove deprecated verified parameter from url stanzas (fixes #8)` |
| 4 | **[mistralai/client-python](https://github.com/mistralai/client-python/compare/main...shobhitagnihotri69:client-python:fix/624-workflow-encoding-async-sse-stream?expand=1)** | `fix/624-workflow-encoding-async-sse-stream` | 31/31 Pass ✅ | `fix(sse): resolve event loop stall in async workflow SSE stream (fixes #624)` |
| 5 | **[Corgea/cli](https://github.com/Corgea/cli/compare/main...shobhitagnihotri69:cli-1:fix/128-local-tarball-detection?expand=1)** | `fix/128-local-tarball-detection` | 55/55 Pass ✅ | `fix(scanner): correct local npm tarball package misclassification (fixes #128)` |
| 6 | **[Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify/compare/v8...shobhitagnihotri69:graphify:fix/3641-pin-pythonhashseed-default?expand=1)** | `fix/3641-pin-pythonhashseed-default` | 14/14 Pass ✅ | `fix(cli): pin PYTHONHASHSEED to prevent graph non-determinism (fixes #3641)` |

---

## 🔵 Sequential Staged Batches — Lemma (4 PRs)

*Pre-tested, committed, and pushed to fork. Staged for sequential submission after PR #84 merges:*

| # | Repository & Compare Link | Branch Name | Tests | Focus |
| :-: | :--- | :--- | :---: | :--- |
| 1 | **[uselemma/lemma (Batch 1)](https://github.com/uselemma/lemma/compare/main...shobhitagnihotri69:lemma:fix/object-and-pydantic-payload-normalization?expand=1)** | `fix/object-and-pydantic-payload-normalization` | 211/211 Pass ✅ | Support Pydantic models and objects in `tool_result_error` & `normalize_token_usage` |
| 2 | **[uselemma/lemma (Batch 2)](https://github.com/uselemma/lemma/compare/main...shobhitagnihotri69:lemma:fix/open-span-attributes-and-transport-resilience?expand=1)** | `fix/open-span-attributes-and-transport-resilience` | 213/213 Pass ✅ | Apply SDK attributes to open spans, preserve lowercase User-Agent, and harden transport |
| 3 | **[uselemma/lemma (Batch 3)](https://github.com/uselemma/lemma/compare/main...shobhitagnihotri69:lemma:fix/root-span-dedup-and-turn-journal-resilience?expand=1)** | `fix/root-span-dedup-and-turn-journal-resilience` | 212/212 Pass ✅ | Support root trace span dedup, parentSpanId, and attached span attribute merge |
| 4 | **[uselemma/lemma (Batch 4)](https://github.com/uselemma/lemma/compare/main...shobhitagnihotri69:lemma:fix/langchain-retriever-error-deferred-owner?expand=1)** | `fix/langchain-retriever-error-deferred-owner` | 210/210 Pass ✅ | Finalize deferred owner trace on LangChain retriever error |

---

## 📈 Velocity Insights & Learnings
- **First-Merge Lead Time:** Exactly **1 week** from sprint kick-off (7 days).
- **PR #81 Cycle Time:** 6 calendar days from submission to merge.
- **PR #559 Cycle Time:** < 24 hours from submission to merge (Hebbian Robotics).
- **Maintainer Interaction Pattern:** YC startups with active release pipelines (`uselemma`, `Hebbian-Robotics`) review and merge surgical telemetry and bug fixes rapidly when accompanied by unit tests.
