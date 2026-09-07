<div align="center">

# SWE-in-Production: RL for Software Engineering

**Training a coding agent with Reinforcement Learning (GRPO) to autonomously fix real-world bugs from SWE-bench.**

<a href="https://pytorch.org"><img src="https://img.shields.io/badge/PyTorch-%23EE4C2C.svg?logo=pytorch&logoColor=white" alt="PyTorch"></a>
<a href="https://huggingface.co"><img src="https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-FFC107?logo=hugging%20face&logoColor=black" alt="Hugging Face"></a>
<a href="https://vercel.com"><img src="https://img.shields.io/badge/Vercel-Deploy-black?logo=vercel" alt="Vercel"></a>
<a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-green.svg" alt="MIT License"></a>

</div>

---

## What This Is

An end-to-end pipeline that takes a pre-trained code LLM (**Qwen 2.5 Coder 0.5B**), puts it in a shell-like environment with a real bug, and uses **Group Relative Policy Optimization (GRPO)** — a critic-free RL algorithm — to teach it to write better patches.

> *"Sample N rollouts → score them → update the model to prefer the ones that worked."*

This repo contains:
- A **GRPO training script** that runs one full RL step on a SWE-bench task
- A **deployable RL coding agent** (Vercel serverless) that demonstrates the trained policy
- A **mock environment** simulating a shell interface for the agent

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  SWE-bench Task                 │
│  (real bug from astropy, django, sympy, etc.)   │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│              MockEnv (utils.py)                 │
│  Simulates: cat file, apply patch, run tests    │
└─────────────────┬───────────────────────────────┘
                  │ observation
                  ▼
┌─────────────────────────────────────────────────┐
│     Qwen 2.5 Coder 0.5B + LoRA adapter         │
│  Generates bash commands to diagnose & fix      │
└─────────────────┬───────────────────────────────┘
                  │ N rollouts
                  ▼
┌─────────────────────────────────────────────────┐
│              GRPO Update Step                   │
│  reward per rollout → advantage → policy grad   │
│  No critic. No value network. Just comparison.  │
└─────────────────────────────────────────────────┘
```

---

## Project Structure

| File | Purpose |
|:---|:---|
| `swe_grpo_one_step.py` | Full GRPO training loop — load task, sample rollouts, compute rewards, update weights |
| `swe_grpo_one_step.ipynb` | Interactive notebook version with step-by-step explanations |
| `utils.py` | MockEnv, system prompt, shell parser, `generate()` sampling utility |
| `rl_coding_agent/agent.py` | Deployable agent — streamlined for Vercel serverless |
| `rl_coding_agent/api/index.py` | Vercel serverless entry point |
| `tasks/` | Task configurations and test cases |

---

## Quick Start

### Run the GRPO training step locally
```bash
# Install dependencies
pip install "transformers>=4.44" "datasets>=2.20" "accelerate>=0.33" "peft>=0.12" torch

# Run one full GRPO step
python swe_grpo_one_step.py
```

### Deploy the agent to Vercel
```bash
cd rl_coding_agent
npm i -g vercel
vercel --prod
```

---

## How GRPO Works

| Step | What happens |
|:---|:---|
| **1. Sample** | Run the agent N times (default 6) on the same bug → get N rollouts |
| **2. Score** | Reward each rollout: did the patch match? did it apply cleanly? |
| **3. Advantage** | `advantage = reward - mean(rewards)` — no critic needed |
| **4. Update** | Increase log-probability of high-advantage actions via LoRA |

This is the same algorithm used by DeepSeek-R1 for reasoning, applied here to code generation.

---

## Key Configuration

| Parameter | Default | Description |
|:---|:---|:---|
| `MODEL` | `Qwen/Qwen2.5-Coder-0.5B-Instruct` | Base policy LLM |
| `GROUP_SIZE` | 6 | Number of rollouts per GRPO step |
| `MAX_TURNS` | 4 | Max agent-environment interaction turns |
| `TEMPERATURE` | 1.0 | Sampling temperature for diversity |
| `LR` | 1e-5 | LoRA learning rate |

---

## References

- **GRPO**: Shao et al., "DeepSeekMath: Pushing the Limits of Mathematical Reasoning in Open Language Models" (2024)
- **SWE-bench**: Jimenez et al., "SWE-bench: Can Language Models Resolve Real-World GitHub Issues?" (2024)

