"""RL Coding Agent - GRPO Step with Verifiable Sandboxes & Real Test Execution.

Features:
1. Verifiable Execution Sandboxes: LocalSandboxEnv (subprocess + git) & DockerSandboxEnv.
2. Real Multi-Faceted Rewards: AST syntax check + pytest execution verifier.
3. Hugging Face TRL / OpenEnv compatibility.
4. GRPO policy optimization with LoRA adapters.
"""

import argparse
import json
import os
import random
import sys
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer

from environments import BaseCodingEnv, LocalSandboxEnv, DockerSandboxEnv, get_environment
from rewards import CompositeReward, SyntaxReward, TestRunnerReward
from utils import NO_COMMAND, SYSTEM, MockEnv, first_bash_block, generate, TARGET, MOCK_FILE

# Default Task: Astropy Separable Bug (SWE-bench verified candidate)
SAMPLE_TEST_CODE = '''import numpy as np
import pytest
from astropy.modeling.separable import _cstack

def test_cstack_symmetry():
    # Bug: cleft assigns left, cright assigns 1 instead of right
    left = np.ones((2, 2)) * 3
    right = np.ones((2, 2)) * 5
    res = _cstack(left, right)
    # The right half should contain elements from right (5), not 1s
    assert np.all(res[:, 2:] == 5), f"Expected 5, got {res[:, 2:]}"
'''

SAMPLE_TASK = {
    "instance_id": "astropy__astropy-12907",
    "problem_statement": (
        "In `astropy/modeling/separable.py`, function `_cstack(left, right)` has an asymmetry: "
        "when right is not an instance of Model, `cright[-right.shape[0]:, -right.shape[1]:] = 1` "
        "is executed instead of assigning `right`. Fix this bug so `cright` correctly receives `right`."
    ),
    "files": {
        TARGET: MOCK_FILE,
        "tests/test_separable.py": SAMPLE_TEST_CODE,
        "setup.py": "from setuptools import setup, find_packages\nsetup(name='astropy_mock', packages=find_packages())"
    },
    "FAIL_TO_PASS": ["test_cstack_symmetry"]
}

# --- Configuration ---
MODEL_NAME = "Qwen/Qwen2.5-Coder-0.5B-Instruct"
GROUP_SIZE = 4
MAX_TURNS = 3
TEMPERATURE = 0.8
LR = 1e-5
SEED = 42


def load_task(from_swebench: bool = False) -> Tuple[Dict[str, Any], List[str]]:
    """Loads coding task (SWE-bench verified or built-in verified sample)."""
    if from_swebench:
        try:
            from datasets import load_dataset
            print("Fetching SWE-bench Verified dataset from Hugging Face...")
            ds = load_dataset("princeton-nlp/SWE-bench_Verified", split="test")
            cands = [i for i, r in enumerate(ds)
                     if r["patch"].count("diff --git") == 1 and len(r["patch"]) < 1800]
            inst = ds[cands[0]]
            return inst, json.loads(inst["FAIL_TO_PASS"])
        except Exception as e:
            print(f"[Warning] Failed to load from SWE-bench ({e}). Falling back to sample task.")
    
    return SAMPLE_TASK, SAMPLE_TASK["FAIL_TO_PASS"]


def load_policy(device: str, model_name: str = MODEL_NAME):
    """Loads base LLM model and tokenizer."""
    print(f"Loading {model_name} onto {device}...")
    tok = AutoTokenizer.from_pretrained(model_name)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    dtype = torch.float16 if device == "cuda" else (torch.bfloat16 if torch.backends.mps.is_available() else torch.float32)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=dtype,
        attn_implementation="sdpa" if hasattr(torch.nn.functional, "scaled_dot_product_attention") else "eager"
    ).to(device)

    print("Model loaded successfully.")
    return model, tok


def run_agent(
    model,
    tok,
    inst: Dict[str, Any],
    env: Optional[BaseCodingEnv] = None,
    use_docker: bool = False,
    max_turns: int = MAX_TURNS,
    temperature: float = TEMPERATURE
) -> Dict[str, Any]:
    """Runs the agent through a live sandbox environment for a fixed number of turns."""
    should_close_env = False
    if env is None:
        env = get_environment(use_docker=use_docker)
        should_close_env = True

    initial_files = inst.get("files", {TARGET: MOCK_FILE})
    env.reset(initial_files=initial_files)

    context = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": f"ISSUE:\n{inst['problem_statement'][:1500]}"}
    ]

    try:
        for turn_i in range(max_turns):
            prompt = tok.apply_chat_template(context, tokenize=False, add_generation_prompt=True)
            reply = generate(model, tok, prompt, temperature=temperature)
            action = first_bash_block(reply)

            obs = env.run(action) if action else NO_COMMAND
            context += [
                {"role": "assistant", "content": reply},
                {"role": "user", "content": obs[:800]}
            ]

        patch = env.patch()
        calls = list(env.calls)
    finally:
        if should_close_env:
            env.close()

    return {
        "messages": context,
        "patch": patch,
        "calls": calls
    }


def add_lora(model):
    """Adds Low-Rank Adaptation (LoRA) layers for parameter-efficient fine-tuning."""
    print("Adding LoRA trainable adapters...")
    config = LoraConfig(
        r=8,
        lora_alpha=16,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"]
    )
    return get_peft_model(model, config)


def build_masked(messages, tokenizer, max_len=3072):
    """Prepares token IDs with prompt tokens masked to -100."""
    ids, labels, prev = [], [], ""
    for i, m in enumerate(messages):
        cur = tokenizer.apply_chat_template(messages[:i + 1], tokenize=False)
        seg = tokenizer(cur[len(prev):], add_special_tokens=False)["input_ids"]
        ids += seg
        labels += seg if m["role"] == "assistant" else [-100] * len(seg)
        prev = cur
    return ids[:max_len], labels[:max_len]


def seq_logprob(model, tok, messages, device):
    """Calculates log-likelihood of agent actions."""
    ids, labs = build_masked(messages, tok)
    t = torch.tensor([ids], device=device)
    msk = torch.tensor([[0.0 if l == -100 else 1.0 for l in labs]], device=device)[:, 1:]
    logits = model(t).logits[:, :-1]
    lp = torch.log_softmax(logits.float(), -1).gather(-1, t[:, 1:].unsqueeze(-1)).squeeze(-1)
    return (lp * msk).sum() / msk.sum().clamp(min=1), msk.sum().item()


def grpo_step(model, tok, group: List[Dict[str, Any]], rewards: List[float], device: str, lr: float = LR):
    """Performs one Group Relative Policy Optimization (GRPO) training update."""
    r_tensor = torch.tensor(rewards, dtype=torch.float)
    std = r_tensor.std(unbiased=False)
    adv = (r_tensor - r_tensor.mean()) / (std + 1e-5)

    print("\n--- GRPO Training Update ---")
    print(f"Rewards: {[round(r, 3) for r in rewards]}")
    print(f"Mean: {r_tensor.mean().item():.3f} | Std: {std.item():.3f}")
    print(f"Advantages: {[round(a.item(), 3) for a in adv]}")

    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=lr)
    model.train()
    opt.zero_grad(set_to_none=True)

    loss_total = 0.0
    for g, a in zip(group, adv):
        lp, _ = seq_logprob(model, tok, g["messages"], device)
        loss = -(a.to(device) * lp) / len(group)
        loss.backward()
        loss_total += loss.item()

    torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad], 1.0)
    opt.step()

    print(f"Total Loss: {loss_total:+.5f}")
    return loss_total


def main(group_size: int = GROUP_SIZE, use_docker: bool = False, use_mock: bool = False):
    """Main execution function."""
    random.seed(SEED)
    torch.manual_seed(SEED)
    np.random.seed(SEED)

    device = "cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu")
    print(f"=== Starting RL Coding Agent on {device} ===")

    # 1. Load Task & Test Suite
    inst, fail_to_pass = load_task(from_swebench=False)

    # 2. Setup Real Sandbox and Verifier
    if use_mock:
        print("Using legacy MockEnv...")
        env_factory = lambda: MockEnv(fail_to_pass)
    else:
        env_name = "DockerSandboxEnv" if use_docker else "LocalSandboxEnv"
        print(f"Using Verifiable Sandbox: {env_name}")
        env_factory = lambda: get_environment(use_docker=use_docker)

    test_reward = TestRunnerReward(test_command="python -m pytest tests/test_separable.py -q")
    reward_calc = CompositeReward(test_reward=test_reward)

    # 3. Load Model
    model, tok = load_policy(device)

    # 4. Generate Group Rollouts in Sandbox
    print(f"\nSampling {group_size} rollouts...")
    group, rewards, evaluations = [], [], []

    for i in range(group_size):
        env = env_factory()
        try:
            rollout = run_agent(model, tok, inst, env=env, max_turns=MAX_TURNS)
            eval_res = reward_calc.evaluate(
                env=env,
                patch=rollout["patch"],
                files=getattr(env, "fs", None) or inst.get("files"),
                expected_passing_tests=fail_to_pass
            )
            score = eval_res["total_reward"]
        finally:
            env.close()

        group.append(rollout)
        rewards.append(score)
        evaluations.append(eval_res)

        print(f"Rollout {i}: Commands={len(rollout['calls'])} | Patch={'Yes' if rollout['patch'] else 'No'} | Reward={score:.3f} (Passed: {eval_res['passed']})")

    # 5. Add LoRA Adapters
    model = add_lora(model)

    # 6. GRPO Policy Update
    loss = grpo_step(model, tok, group, rewards, device)

    print("=== RL Coding Agent execution completed successfully ===")
    return {
        "status": "Success",
        "rewards": rewards,
        "loss": loss,
        "group_size": group_size
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RL Coding Agent with Verifiable Sandboxes")
    parser.add_argument("--docker", action="store_true", help="Use Docker container sandbox")
    parser.add_argument("--mock", action="store_true", help="Use legacy mock environment")
    parser.add_argument("--group-size", type=int, default=GROUP_SIZE, help="Number of rollouts per GRPO group")
    args = parser.parse_args()

    main(group_size=args.group_size, use_docker=args.docker, use_mock=args.mock)
