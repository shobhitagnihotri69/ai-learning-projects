# TritonRL: Training LLMs to Think and Code Triton Without Cheating

> **Implementation of Amazon Web Services & Google DeepMind Paper (COLM 2026)**  
> *Jiin Woo, Shaowei Zhu, Allen Nie, Zhen Jia, Yida Wang, Youngsuk Park*

[![Paper](https://img.shields.io/badge/Paper-PDF-red.svg)](paper.pdf)
[![Venue](https://img.shields.io/badge/Venue-COLM%202026-blue.svg)]()
[![Hardware](https://img.shields.io/badge/Hardware-NVIDIA%20GPU%20(T4%2FA10%2FL4%2FA100)-green.svg)]()

---

## 📌 Executive Summary

TritonRL is an RL framework designed to train 8B-scale LLMs to write high-performance OpenAI Triton GPU kernels without **reward hacking** (cheating).

### The Problem in Existing Models (AutoTriton, KernelLLM)
When existing models are trained with naive RL on Triton generation, they learn to cheat:
1. **PyTorch Delegation Hack**: They annotate functions with `@triton.jit` but call `torch.matmul` or `torch.nn.functional` under the hood.
2. **Constant Hardcoding Hack**: Returning static pre-computed tensors for fixed test inputs.
3. **Syntax-only Pass**: Generating superficially valid code that fails runtime memory bounds.

### TritonRL's Two Core Breakthroughs:
1. **Multi-Layered Robust Verification System**:
   - `syntax(o)`: Verifies valid AST and `@triton.jit` annotations.
   - `func(o)`: AST linter detecting prohibited PyTorch fallback ops (`torch.nn`, `@`, etc.) ensuring compute happens in Triton SRAM/registers.
   - `correct(g, o)`: Strict numerical tolerance test against PyTorch ground truth across varying shapes.
   - `speedup(g, o)`: Benchmarked execution time improvement ratio: $\frac{\tau(\text{PyTorch})}{\tau(\text{Triton})}$, clipped at 2.0.

2. **Hierarchical Reward Decomposition (HRD) with GRPO**:
   - Decomposes generation into **Plan** (thinking trace) and **Code** (Triton implementation).
   - Assigns **Speedup Reward** $r^{\text{plan}} = R_{\text{speedup}}$ to planning tokens (reinforcing algorithmic reasoning).
   - Assigns **Correctness Reward** $r^{\text{code}} = R_{\text{correct}}$ to coding tokens (reinforcing bug-free kernel synthesis).
   - Uses token-level masked GRPO (Group Relative Policy Optimization) with balancing factor $\alpha$.

---

## 🗂️ Project Structure

```bash
triton-rl/
├── paper.pdf                  # Complete 41-page COLM 2026 paper
├── README.md                  # This document
├── requirements.txt           # Dependencies (triton, torch, ast, transformers)
├── src/
│   ├── verifier/
│   │   ├── __init__.py
│   │   ├── robust_verifier.py # Multi-layer verifier: syntax, anti-cheat func, correctness, speedup
│   │   └── ast_linter.py      # AST inspector to catch PyTorch fallback hacks
│   ├── rewards/
│   │   ├── __init__.py
│   │   └── hrd.py             # Hierarchical Reward Decomposition logic
│   ├── training/
│   │   ├── __init__.py
│   │   └── grpo_triton.py     # Custom GRPO trainer with token-level plan/code masking
│   └── benchmarks/
│       ├── __init__.py
│       └── kernel_bench.py    # KernelBench evaluation harness
├── examples/
│   ├── demo_verify.py         # Test runner verifying a legitimate kernel vs cheating kernel
│   └── sample_kernels.py      # Vector add, RMSNorm, and Softmax kernels
└── data/                      # Dataset pairs: (PyTorch reference, prompt, test inputs)
```

---

## 🚀 Quickstart

### 1. Installation
```bash
cd triton-rl
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### 2. Run the Robust Anti-Cheating Verifier Demo
```bash
python examples/demo_verify.py
```
This runs both an **honest Triton kernel** and a **cheating kernel** (which tries to sneak `torch.matmul` inside), proving how the multi-layered verifier detects and penalizes the hack.

---

## 🔬 Mathematical Formulation

### 1. Verification Signals
$$R_{\text{correct}}(g, o) = \text{valid}(o) \cdot \text{correct}(g, o)$$
$$R_{\text{speedup}}(g, o) = \text{valid}(o) \cdot \text{clip}(\text{speedup}(g, o), 2.0)$$
$$\text{valid}(o) = \text{syntax}(o) \cdot \text{func}(o)$$

### 2. HRD GRPO Objective
$$J(\theta) = \mathbb{E}_{q_i, \{o_{i,j}\}_{j=1}^G} \left[ \alpha J_i^{\text{plan}}(\theta) + J_i^{\text{code}}(\theta) \right]$$

Where:
- Token class $c \in \{\text{plan}, \text{code}\}$
- Advantage for plan tokens: $A^{\text{plan}} = r^{\text{plan}} - \frac{1}{G}\sum r^{\text{plan}}$
- Advantage for code tokens: $A^{\text{code}} = r^{\text{code}} - \frac{1}{G}\sum r^{\text{code}}$
