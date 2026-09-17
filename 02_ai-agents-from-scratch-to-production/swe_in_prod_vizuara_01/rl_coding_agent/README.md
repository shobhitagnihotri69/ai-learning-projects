# 🚀 OpenCodingEnv: Verifiable RL Environment for Coding Agents

<div align="center">

**An open-source, verifiable Reinforcement Learning (RL) execution sandbox & GRPO training harness for coding agents.**

[![Hugging Face Spaces](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Spaces-yellow)](https://huggingface.co/spaces/shobhitagnihotri/open-coding-env)
[![Live Demo](https://img.shields.io/badge/%F0%9F%9A%80%20Live%20Demo-OpenCodingEnv-blue)](https://huggingface.co/spaces/shobhitagnihotri/open-coding-env)
[![PyTorch](https://img.shields.io/badge/PyTorch-%23EE4C2C.svg?logo=pytorch&logoColor=white)](https://pytorch.org)
[![Hugging Face TRL](https://img.shields.io/badge/HF%20TRL-OpenEnv%20Compatible-blue)](https://github.com/huggingface/trl)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

</div>

---

## 🌟 Overview

**OpenCodingEnv** provides a **100% open-source, verifiable execution sandbox and GRPO training harness** that runs out-of-the-box anywhere — from **free Hugging Face Spaces and Google Colab** to isolated Docker environments.

```
                  +----------------------------------------------+
                  |            Coding Policy (e.g. Qwen)         |
                  +----------------------------------------------+
                                  |          ^
                      Action: bash|          | Observation: stdout/stderr
                                  v          |
                  +----------------------------------------------+
                  |         OpenCodingEnv Dual Sandbox           |
                  |  [LocalSubprocessEnv]   OR   [DockerEnv]     |
                  +----------------------------------------------+
                                  |
                                  | git diff HEAD + test execution
                                  v
                  +----------------------------------------------+
                  |          Verifiable Reward Engine            |
                  |  * AST Syntax Anti-Cheat  (+0.2)             |
                  |  * Real PyTest Suite      (+0.8 / 0.0)       |
                  +----------------------------------------------+
                                  |
                                  v
                  +----------------------------------------------+
                  |        GRPO Group Relative Update            |
                  |      Advantage = (r_i - mean) / std          |
                  +----------------------------------------------+
```

---

## ⚡ Key Features

1. **Dual-Sandbox Architecture**:
   - **`LocalSandboxEnv`**: Zero Docker dependencies. Uses isolated temporary directories, git tracking, subprocess timeouts, and environment isolation. **Runs seamlessly on Hugging Face Spaces Free Tier, Google Colab, and macOS.**
   - **`DockerSandboxEnv`**: Hardened container isolation with `--network none`, CPU quotas, and memory limits for production scaling.
2. **Real Verifiable Rewards**:
   - Replaces mock string matching with **real `pytest` test suite execution** against SWE-bench tasks.
   - Built-in **AST Syntax Anti-Cheat Grader** (`SyntaxReward`) to reward structurally sound Python and penalize unparseable rollouts.
3. **1-Line Hugging Face TRL & OpenEnv Bridge**:
   - Exposes standard gym / OpenEnv step protocols via `OpenEnvCodingAdapter` for direct use with `trl.GRPOTrainer`.
4. **Interactive Public Showcase (`app.py`)**:
   - Full Gradio application featuring live terminal logs, real-time Git Diff viewer, and GRPO Group Advantage Inspector ($A_i = \frac{r_i - \mu}{\sigma}$).

---

## 📂 Project Architecture

```
rl_coding_agent/
├── app.py                     # Hugging Face Space Gradio showcase application
├── agent.py                   # GRPO training loop, LoRA adapter, rollout sampler
├── utils.py                   # Shared formatting, bash parser, legacy helpers
├── environments/
│   ├── base.py                # BaseCodingEnv abstract interface
│   ├── local_sandbox.py       # Zero-dependency local subprocess + git sandbox
│   └── docker_sandbox.py      # Hardened ephemeral Docker container sandbox
├── rewards/
│   ├── syntax.py              # AST anti-cheat syntax parser
│   ├── verifier.py            # Real PyTest execution verifier
│   └── composite.py           # Multi-faceted weighted reward engine
├── trl_bridge/
│   └── openenv_adapter.py     # Hugging Face TRL GRPOTrainer / OpenEnv bridge
├── tests/
│   └── test_components.py     # Automated unit test suite
├── api/
│   └── index.py               # Vercel serverless function entrypoint
└── requirements.txt
```

---

## 🚀 Quickstart: Launch Interactive Showcase

Launch the local Gradio interface or deploy to Hugging Face Spaces in seconds:

```bash
pip install -r requirements.txt
python app.py
```

Open your browser at `http://localhost:7860` to simulate agent rollouts, inspect diffs, and view GRPO group advantage calculations.

---

## 🧪 Run Automated Tests

Run the comprehensive unit test suite covering sandboxes, rewards, and TRL adapters:

```bash
python -m pytest tests/test_components.py -v
```

---

## 🔌 1-Line Hugging Face TRL Integration

Train any Hugging Face model with `trl.GRPOTrainer` using `OpenCodingEnv`:

```python
from trl import GRPOTrainer, GRPOConfig
from trl_bridge import OpenEnvCodingAdapter

# Wrap your coding task into the verifiable sandbox
env = OpenEnvCodingAdapter(task_instance=my_swe_bench_task, use_docker=False)

# Train with GRPO — rewards computed automatically via pytest + AST
trainer = GRPOTrainer(
    model="Qwen/Qwen2.5-Coder-0.5B-Instruct",
    reward_funcs=[env.reward_fn.evaluate],
    args=GRPOConfig(
        output_dir="./qwen-rl-coder",
        learning_rate=1e-5,
        num_generations=4,
        max_prompt_length=1024,
    )
)
trainer.train()
```

---

## ☁️ Train Free on Google Colab / Kaggle

Because `LocalSandboxEnv` requires zero Docker daemon privileges, you can train a coding model on free Google Colab (T4 GPU) or Kaggle (P100 GPU):

```bash
!git clone https://github.com/shobhitagnihotri69/ai-learning-projects.git
%cd ai-learning-projects/02_ai-agents-from-scratch-to-production/swe_in_prod_vizuara_01/rl_coding_agent
!pip install -r requirements.txt
!python agent.py --group-size 4
```

---

## 📜 License

MIT License. Designed for open research, reproducible RL training, and community innovation.
