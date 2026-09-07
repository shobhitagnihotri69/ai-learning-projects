# 60 AI Agent Patterns

A personal reference I've been building while studying and implementing autonomous AI systems from scratch.

**Core philosophy: 100% vanilla Python — no LangChain, no LangGraph, no CrewAI, no black-box frameworks.**

Every pattern here is something I've either read about, experimented with, or built myself while working through agent architectures. The code prioritises clarity and correctness over framework cleverness.

---

## Structure

```
60-ai-agent-patterns/
├── patterns_reference.md               # Full technical notes for all 60 patterns
├── 01_foundations/                     # Core abstractions: substrate, loops, prompting, deployment
├── 02_perception_agents_01_07/        # Perception: grounding, layout, sensor fusion, anomaly
├── 03_reasoning_agents_08_15/         # Reasoning: CoT, self-consistency, causal, symbolic
├── 04_planning_agents_16_22/          # Planning: ReAct, hierarchical, tree-of-thought, resource
├── 05_memory_agents_23_29/            # Memory: working, episodic, semantic, consolidation
├── 06_tool_use_agents_30_37/          # Tool use: registry, selectors, code exec, DB query
├── 07_coordination_agents_38_45/      # Coordination: routing, debate, consensus, orchestration
├── 08_learning_agents_46_52/          # Learning: feedback loops, reflection, curriculum, distillation
├── 09_alignment_agents_53_60/         # Alignment: constitution, refusal, red-team, privacy
├── 10_composition_and_eval/           # Composition patterns + evaluation frameworks
└── 11_production_operations/          # Production: observability, incident response, operator UX
```

---

## Pattern Index

Every pattern includes:
- **The architectural problem** it solves
- **Why naive approaches break** at production scale
- **A clean Python implementation** with typed interfaces
- **Real failure modes** I've encountered or studied
- **Which patterns to pair it with**

### 👁️ Perception (Agents 1–7)

| # | Pattern | Notes | Code |
| :--- | :--- | :--- | :--- |
| 01 | Multimodal Grounding Agent | [notes](02_perception_agents_01_07/agent_01_the_multimodal_grounding_agent.md) | [code](02_perception_agents_01_07/agent_01_the_multimodal_grounding_agent.py) |
| 02 | Document Layout Agent | [notes](02_perception_agents_01_07/agent_02_the_document_layout_agent.md) | [code](02_perception_agents_01_07/agent_02_the_document_layout_agent.py) |
| 03 | Temporal Sensor-Fusion Agent | [notes](02_perception_agents_01_07/agent_03_the_temporal_sensor_fusion_agent.md) | [code](02_perception_agents_01_07/agent_03_the_temporal_sensor_fusion_agent.py) |
| 04 | Anomaly-Spotter Agent | [notes](02_perception_agents_01_07/agent_04_the_anomaly_spotter_agent.md) | [code](02_perception_agents_01_07/agent_04_the_anomaly_spotter_agent.py) |
| 05 | Visual Question Decomposition Agent | [notes](02_perception_agents_01_07/agent_05_the_visual_question_decomposition_agent.md) | [code](02_perception_agents_01_07/agent_05_the_visual_question_decomposition_agent.py) |
| 06 | Ambient Context Agent | [notes](02_perception_agents_01_07/agent_06_the_ambient_context_agent.md) | [code](02_perception_agents_01_07/agent_06_the_ambient_context_agent.py) |
| 07 | Schema-Inference Agent | [notes](02_perception_agents_01_07/agent_07_the_schema_inference_agent.md) | [code](02_perception_agents_01_07/agent_07_the_schema_inference_agent.py) |

### 🧠 Reasoning (Agents 8–15)

| # | Pattern | Notes | Code |
| :--- | :--- | :--- | :--- |
| 08 | Chain-of-Thought Reasoner | [notes](03_reasoning_agents_08_15/agent_08_the_chain_of_thought_reasoner_agent.md) | [code](03_reasoning_agents_08_15/agent_08_the_chain_of_thought_reasoner_agent.py) |
| 09 | Self-Consistency Sampler | [notes](03_reasoning_agents_08_15/agent_09_the_self_consistency_sampler_agent.md) | [code](03_reasoning_agents_08_15/agent_09_the_self_consistency_sampler_agent.py) |
| 10 | Analogical Mapping Agent | [notes](03_reasoning_agents_08_15/agent_10_the_analogical_mapping_agent.md) | [code](03_reasoning_agents_08_15/agent_10_the_analogical_mapping_agent.py) |
| 11 | Constraint Satisfaction Agent | [notes](03_reasoning_agents_08_15/agent_11_the_constraint_satisfaction_agent.md) | [code](03_reasoning_agents_08_15/agent_11_the_constraint_satisfaction_agent.py) |
| 12 | Causal Graph Builder | [notes](03_reasoning_agents_08_15/agent_12_the_causal_graph_builder_agent.md) | [code](03_reasoning_agents_08_15/agent_12_the_causal_graph_builder_agent.py) |
| 13 | Symbolic-Neural Bridge Agent | [notes](03_reasoning_agents_08_15/agent_13_the_symbolic_neural_bridge_agent.md) | [code](03_reasoning_agents_08_15/agent_13_the_symbolic_neural_bridge_agent.py) |
| 14 | Deductive Rule-Verifier | [notes](03_reasoning_agents_08_15/agent_14_the_deductive_rule_verifier_agent.md) | [code](03_reasoning_agents_08_15/agent_14_the_deductive_rule_verifier_agent.py) |
| 15 | Counterfactual Simulator | [notes](03_reasoning_agents_08_15/agent_15_the_counterfactual_simulator_agent.md) | [code](03_reasoning_agents_08_15/agent_15_the_counterfactual_simulator_agent.py) |

### 📋 Planning (Agents 16–22)

| # | Pattern | Notes | Code |
| :--- | :--- | :--- | :--- |
| 16 | Hierarchical Decomposer | [notes](04_planning_agents_16_22/agent_16_the_hierarchical_decomposer_agent.md) | [code](04_planning_agents_16_22/agent_16_the_hierarchical_decomposer_agent.py) |
| 17 | ReAct Loop Agent | [notes](04_planning_agents_16_22/agent_17_the_react_loop_agent.md) | [code](04_planning_agents_16_22/agent_17_the_react_loop_agent.py) |
| 18 | Tree-of-Thought Explorer | [notes](04_planning_agents_16_22/agent_18_the_tree_of_thought_explorer_agent.md) | [code](04_planning_agents_16_22/agent_18_the_tree_of_thought_explorer_agent.py) |
| 19 | Plan-then-Execute Agent | [notes](04_planning_agents_16_22/agent_19_the_plan_then_execute_agent.md) | [code](04_planning_agents_16_22/agent_19_the_plan_then_execute_agent.py) |
| 20 | Adaptive Replanner | [notes](04_planning_agents_16_22/agent_20_the_adaptive_replanner_agent.md) | [code](04_planning_agents_16_22/agent_20_the_adaptive_replanner_agent.py) |
| 21 | Resource-Aware Scheduler | [notes](04_planning_agents_16_22/agent_21_the_resource_aware_scheduler_agent.md) | [code](04_planning_agents_16_22/agent_21_the_resource_aware_scheduler_agent.py) |
| 22 | Backward Goal Regression Agent | [notes](04_planning_agents_16_22/agent_22_the_backward_goal_regression_agent.md) | [code](04_planning_agents_16_22/agent_22_the_backward_goal_regression_agent.py) |

### 🧩 Memory (Agents 23–29)

| # | Pattern | Notes | Code |
| :--- | :--- | :--- | :--- |
| 23 | Working Memory Buffer | [notes](05_memory_agents_23_29/agent_23_the_working_memory_agent.md) | [code](05_memory_agents_23_29/agent_23_the_working_memory_agent.py) |
| 24 | Episodic Memory Agent | [notes](05_memory_agents_23_29/agent_24_the_episodic_memory_agent.md) | [code](05_memory_agents_23_29/agent_24_the_episodic_memory_agent.py) |
| 25 | Semantic Memory Agent | [notes](05_memory_agents_23_29/agent_25_the_semantic_memory_agent.md) | [code](05_memory_agents_23_29/agent_25_the_semantic_memory_agent.py) |
| 26 | Hierarchical Memory Agent | [notes](05_memory_agents_23_29/agent_26_the_hierarchical_memory_agent.md) | [code](05_memory_agents_23_29/agent_26_the_hierarchical_memory_agent.py) |
| 27 | Memory-of-Self Agent | [notes](05_memory_agents_23_29/agent_27_the_memory_of_self_agent.md) | [code](05_memory_agents_23_29/agent_27_the_memory_of_self_agent.py) |
| 28 | Prospective Memory Agent | [notes](05_memory_agents_23_29/agent_28_the_prospective_memory_agent.md) | [code](05_memory_agents_23_29/agent_28_the_prospective_memory_agent.py) |
| 29 | Memory Consolidation Agent | [notes](05_memory_agents_23_29/agent_29_the_memory_consolidation_agent.md) | [code](05_memory_agents_23_29/agent_29_the_memory_consolidation_agent.py) |

### 🔧 Tool Use (Agents 30–37)

| # | Pattern | Notes | Code |
| :--- | :--- | :--- | :--- |
| 30 | Tool Registry Agent | [notes](06_tool_use_agents_30_37/agent_30_the_tool_registry_agent.md) | [code](06_tool_use_agents_30_37/agent_30_the_tool_registry_agent.py) |
| 31 | Dynamic Tool Selector | [notes](06_tool_use_agents_30_37/agent_31_the_dynamic_tool_selector_agent.md) | [code](06_tool_use_agents_30_37/agent_31_the_dynamic_tool_selector_agent.py) |
| 32 | Tool-Chain Executor | [notes](06_tool_use_agents_30_37/agent_32_the_tool_chain_executor_agent.md) | [code](06_tool_use_agents_30_37/agent_32_the_tool_chain_executor_agent.py) |
| 33 | Shell Operator Agent | [notes](06_tool_use_agents_30_37/agent_33_the_shell_operator_agent.md) | [code](06_tool_use_agents_30_37/agent_33_the_shell_operator_agent.py) |
| 34 | API Composition Agent | [notes](06_tool_use_agents_30_37/agent_34_the_api_composition_agent.md) | [code](06_tool_use_agents_30_37/agent_34_the_api_composition_agent.py) |
| 35 | Database Query Synthesizer | [notes](06_tool_use_agents_30_37/agent_35_the_database_query_synthesizer_agent.md) | [code](06_tool_use_agents_30_37/agent_35_the_database_query_synthesizer_agent.py) |
| 36 | File-System Curator Agent | [notes](06_tool_use_agents_30_37/agent_36_the_file_system_curator_agent.md) | [code](06_tool_use_agents_30_37/agent_36_the_file_system_curator_agent.py) |
| 37 | Side-Effect Auditor Agent | [notes](06_tool_use_agents_30_37/agent_37_the_side_effect_auditor_agent.md) | [code](06_tool_use_agents_30_37/agent_37_the_side_effect_auditor_agent.py) |

### 🤝 Coordination (Agents 38–45)

| # | Pattern | Notes | Code |
| :--- | :--- | :--- | :--- |
| 38 | Router/Dispatcher Agent | [notes](07_coordination_agents_38_45/agent_38_the_router_dispatcher_agent.md) | [code](07_coordination_agents_38_45/agent_38_the_router_dispatcher_agent.py) |
| 39 | Debate Moderator Agent | [notes](07_coordination_agents_38_45/agent_39_the_debate_moderator_agent.md) | [code](07_coordination_agents_38_45/agent_39_the_debate_moderator_agent.py) |
| 40 | Consensus-Builder Agent | [notes](07_coordination_agents_38_45/agent_40_the_consensus_builder_agent.md) | [code](07_coordination_agents_38_45/agent_40_the_consensus_builder_agent.py) |
| 41 | Pipeline Orchestrator | [notes](07_coordination_agents_38_45/agent_41_the_pipeline_orchestrator_agent.md) | [code](07_coordination_agents_38_45/agent_41_the_pipeline_orchestrator_agent.py) |
| 42 | Human-in-the-Loop Liaison | [notes](07_coordination_agents_38_45/agent_42_the_human_in_the_loop_liaison_agent.md) | [code](07_coordination_agents_38_45/agent_42_the_human_in_the_loop_liaison_agent.py) |
| 43 | Negotiation Agent | [notes](07_coordination_agents_38_45/agent_43_the_negotiation_agent.md) | [code](07_coordination_agents_38_45/agent_43_the_negotiation_agent.py) |
| 44 | Auctioneer Agent | [notes](07_coordination_agents_38_45/agent_44_the_auctioneer_agent.md) | [code](07_coordination_agents_38_45/agent_44_the_auctioneer_agent.py) |
| 45 | Supervisor-Worker Agent | [notes](07_coordination_agents_38_45/agent_45_the_supervisor_worker_agent.md) | [code](07_coordination_agents_38_45/agent_45_the_supervisor_worker_agent.py) |

### 🔄 Learning & Reflection (Agents 46–52)

| # | Pattern | Notes | Code |
| :--- | :--- | :--- | :--- |
| 46 | Feedback Loop Agent | [notes](08_learning_agents_46_52/agent_46_the_feedback_loop_agent.md) | [code](08_learning_agents_46_52/agent_46_the_feedback_loop_agent.py) |
| 47 | Reflection Agent | [notes](08_learning_agents_46_52/agent_47_the_reflection_agent.md) | [code](08_learning_agents_46_52/agent_47_the_reflection_agent.py) |
| 48 | Skill-Library Builder | [notes](08_learning_agents_46_52/agent_48_the_skill_library_builder_agent.md) | [code](08_learning_agents_46_52/agent_48_the_skill_library_builder_agent.py) |
| 49 | Curriculum Designer Agent | [notes](08_learning_agents_46_52/agent_49_the_curriculum_designer_agent.md) | [code](08_learning_agents_46_52/agent_49_the_curriculum_designer_agent.py) |
| 50 | Few-Shot Prompt Tuner | [notes](08_learning_agents_46_52/agent_50_the_few_shot_prompt_tuner_agent.md) | [code](08_learning_agents_46_52/agent_50_the_few_shot_prompt_tuner_agent.py) |
| 51 | Distillation Agent | [notes](08_learning_agents_46_52/agent_51_the_distillation_agent.md) | [code](08_learning_agents_46_52/agent_51_the_distillation_agent.py) |
| 52 | Active Learner Agent | [notes](08_learning_agents_46_52/agent_52_the_active_learner_agent.md) | [code](08_learning_agents_46_52/agent_52_the_active_learner_agent.py) |

### 🛡️ Alignment & Safety (Agents 53–60)

| # | Pattern | Notes | Code |
| :--- | :--- | :--- | :--- |
| 53 | Constitution-Bound Agent | [notes](09_alignment_agents_53_60/agent_53_the_constitution_bound_agent.md) | [code](09_alignment_agents_53_60/agent_53_the_constitution_bound_agent.py) |
| 54 | Refusal-Calibrator Agent | [notes](09_alignment_agents_53_60/agent_54_the_refusal_calibrator_agent.md) | [code](09_alignment_agents_53_60/agent_54_the_refusal_calibrator_agent.py) |
| 55 | Provenance Tracker Agent | [notes](09_alignment_agents_53_60/agent_55_the_provenance_tracker_agent.md) | [code](09_alignment_agents_53_60/agent_55_the_provenance_tracker_agent.py) |
| 56 | Red-Team Auditor Agent | [notes](09_alignment_agents_53_60/agent_56_the_red_team_auditor_agent.md) | [code](09_alignment_agents_53_60/agent_56_the_red_team_auditor_agent.py) |
| 57 | Privacy-Preserving Agent | [notes](09_alignment_agents_53_60/agent_57_the_privacy_preserving_agent.md) | [code](09_alignment_agents_53_60/agent_57_the_privacy_preserving_agent.py) |
| 58 | Explainer Agent | [notes](09_alignment_agents_53_60/agent_58_the_explainer_agent.md) | [code](09_alignment_agents_53_60/agent_58_the_explainer_agent.py) |
| 59 | Drift-Detector Agent | [notes](09_alignment_agents_53_60/agent_59_the_drift_detector_agent.md) | [code](09_alignment_agents_53_60/agent_59_the_drift_detector_agent.py) |
| 60 | Off-Switch-Compatible Agent | [notes](09_alignment_agents_53_60/agent_60_the_off_switch_compatible_agent.md) | [code](09_alignment_agents_53_60/agent_60_the_off_switch_compatible_agent.py) |

---

## Why Vanilla Python?

- **Prompt Caching**: Frameworks inject hidden preambles that break Anthropic/OpenAI exact-prefix caching — making runs 10x slower and more expensive. Plain Python gives you full byte control.
- **Transparent Debugging**: No 25-frame stack traces through `langchain_core`. A Python exception points straight to the line.
- **Real Flexibility**: Branching, loops, human-in-the-loop = just `while`, `match`, and `if`.
- **Zero Dependency Hell**: Built entirely on the Python standard library, `@dataclass`, typed schemas, and official API SDKs.

---

## Running Patterns

```bash
# Clone
git clone https://github.com/shobhitagnihotri69/60-ai-agent-patterns.git
cd 60-ai-agent-patterns

# Install minimal deps
pip install openai anthropic

# Run any pattern
python 02_perception_agents_01_07/agent_01_the_multimodal_grounding_agent.py
```

Set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` as environment variables depending on the pattern.
