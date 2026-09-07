<div align="center">

# RL Coding Agent

**An autonomous bug-fixing agent trained with GRPO, deployable as a Vercel serverless function.**

<a href="https://pytorch.org"><img src="https://img.shields.io/badge/PyTorch-%23EE4C2C.svg?logo=pytorch&logoColor=white" alt="PyTorch"></a>
<a href="https://vercel.com"><img src="https://img.shields.io/badge/Vercel-Deploy-black?logo=vercel" alt="Vercel"></a>

</div>

---

## What It Does

1. Loads a real coding issue from **SWE-bench** (Princeton NLP)
2. Runs **Qwen 2.5 Coder 0.5B** as an autonomous agent inside a mock shell environment
3. Samples multiple rollouts of the agent attempting to fix the bug
4. Scores each rollout with a reward function (patch quality, test pass rate)
5. Performs one **GRPO training step** using LoRA — updating the model to prefer higher-reward actions

---

## Project Structure

```
rl_coding_agent/
├── agent.py            # Core logic: load model, run agent loop, GRPO update
├── utils.py            # MockEnv, generate(), shell parser, system prompt
├── api/
│   └── index.py        # Vercel serverless entry point
├── requirements.txt    # Python dependencies
├── vercel.json         # Vercel deployment config
└── README.md
```

---

## Run Locally

```bash
pip install -r requirements.txt
python agent.py
```

## Deploy to Vercel

```bash
npm i -g vercel
vercel --prod
```

---

## How GRPO Works

```
1. Run agent N times on same bug  →  N rollouts
2. Score each rollout              →  N rewards
3. Advantage = reward − mean       →  no critic needed
4. ∇θ log π(a|s) × advantage      →  LoRA weight update
```

No value network. No critic. Just group-relative comparison — the same algorithm behind DeepSeek-R1.

---

## Tech Stack

| Component | Tool |
|:---|:---|
| **Policy LLM** | `Qwen/Qwen2.5-Coder-0.5B-Instruct` |
| **RL Algorithm** | GRPO (Group Relative Policy Optimization) |
| **Fine-tuning** | LoRA via `peft` |
| **Task Source** | SWE-bench Verified (`princeton-nlp/SWE-bench_Verified`) |
| **Deployment** | Vercel Python Serverless |
