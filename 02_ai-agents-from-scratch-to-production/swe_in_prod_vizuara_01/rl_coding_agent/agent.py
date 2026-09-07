"""RL Coding Agent - GRPO Step
This script demonstrates one step of Group Relative Policy Optimization (GRPO)
for a coding agent, streamlined for readability and deployment.

It performs the following:
1. Loads a coding task (SWE-bench).
2. Sets up a Language Model (Qwen 0.5B).
3. Samples a group of rollouts (the agent attempting the task).
4. Scores the agent's performance.
5. Updates the model weights based on the scores using LoRA.
"""

import json
import os
import random
import urllib.request

import numpy as np
import pandas as pd
import torch
from datasets import load_dataset
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer

# Import utilities from the utils.py file (which should be in the same folder)
if not os.path.exists("utils.py"):
    urllib.request.urlretrieve(
        "https://raw.githubusercontent.com/abgoswam/swe_in_prod_vizuara_01/main/utils.py",
        "utils.py"
    )

from utils import NO_COMMAND, SYSTEM, MockEnv, first_bash_block, generate

# --- Configuration ---
MODEL = "Qwen/Qwen2.5-Coder-0.5B-Instruct"
GROUP_SIZE = 4  # Reduced for faster Vercel execution / testing
MAX_TURNS = 3
TEMPERATURE = 1.0
LR = 1e-5
SEED = 0

def load_task():
    """Loads one simple coding task from the SWE-bench dataset."""
    print("Loading coding task...")
    ds = load_dataset("princeton-nlp/SWE-bench_Verified", split="test")
    cands = [i for i, r in enumerate(ds)
             if r["patch"].count("diff --git") == 1 and len(r["patch"]) < 1800]
    inst = ds[cands[0]]
    return inst, json.loads(inst["FAIL_TO_PASS"])

def load_policy(device):
    """Loads the base LLM model and tokenizer."""
    print(f"Loading model {MODEL} onto {device}...")
    tok = AutoTokenizer.from_pretrained(MODEL)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        MODEL, torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        attn_implementation="sdpa"
    ).to(device)

    print("Model loaded successfully.")
    return model, tok

def run_agent(model, tok, inst, fail_to_pass, max_turns=MAX_TURNS, temperature=TEMPERATURE):
    """Runs the agent through the environment for a set number of turns."""
    env = MockEnv(fail_to_pass)
    context = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": f"ISSUE:\n{inst['problem_statement'][:1500]}"}
    ]

    for _ in range(max_turns):
        prompt = tok.apply_chat_template(context, tokenize=False, add_generation_prompt=True)
        reply = generate(model, tok, prompt, temperature=temperature)
        action = first_bash_block(reply)
        obs = env.run(action) if action else NO_COMMAND
        
        context += [
            {"role": "assistant", "content": reply},
            {"role": "user", "content": obs[:800]}
        ]

    return {"messages": context, "patch": env.patch(), "final": dict(env.fs), "calls": env.calls}

def reward_random(patch, rng):
    """A placeholder reward function: gives points if the agent made any patch."""
    if not patch:
        return 0.0
    return round(float(rng.random()), 3)

def add_lora(model):
    """Adds Low-Rank Adaptation (LoRA) layers so we can train the model efficiently."""
    print("Adding LoRA adapters for training...")
    config = LoraConfig(
        r=8, lora_alpha=16, lora_dropout=0.0, bias="none", task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"]
    )
    model = get_peft_model(model, config)
    return model

def build_masked(messages, tokenizer, max_len=3072):
    """Prepares tokens for training, masking out non-assistant turns."""
    ids, labels, prev = [], [], ""
    for i, m in enumerate(messages):
        cur = tokenizer.apply_chat_template(messages[:i + 1], tokenize=False)
        seg = tokenizer(cur[len(prev):], add_special_tokens=False)["input_ids"]
        ids += seg
        labels += seg if m["role"] == "assistant" else [-100] * len(seg)
        prev = cur
    return ids[:max_len], labels[:max_len]

def seq_logprob(model, tok, messages, device):
    """Calculates the probability of the sequence given the model's current weights."""
    ids, labs = build_masked(messages, tok)
    t = torch.tensor([ids], device=device)
    msk = torch.tensor([[0. if l == -100 else 1. for l in labs]], device=device)[:, 1:]
    logits = model(t).logits[:, :-1]
    lp = torch.log_softmax(logits.float(), -1).gather(-1, t[:, 1:].unsqueeze(-1)).squeeze(-1)
    return (lp * msk).sum() / msk.sum().clamp(min=1), msk.sum().item()

def grpo_step(model, tok, group, reward, device, lr=LR):
    """Performs one Group Relative Policy Optimization (GRPO) training step."""
    rewards = torch.tensor(reward, dtype=torch.float)
    adv = (rewards - rewards.mean()) / (rewards.std(unbiased=False) + 1e-5)

    print(f"\n--- Training Step ---")
    print(f"Mean Reward: {rewards.mean():.3f} | Std Dev: {rewards.std(unbiased=False):.3f}")
    
    # Train step
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
    print("Training step completed successfully!\n")

def main():
    """Main execution function."""
    random.seed(SEED)
    torch.manual_seed(SEED)
    device = "cuda" if torch.cuda.is_available() else "cpu"

    print("=== Starting RL Coding Agent ===")
    
    # 1. Load Task
    inst, fail_to_pass = load_task()
    
    # 2. Load Model
    model, tok = load_policy(device)

    # 3. Sample Rollouts
    print("\nStarting rollouts (Agent attempting task)...")
    rng = np.random.default_rng(SEED)
    group, reward = [], []
    for i in range(GROUP_SIZE):
        rollout = run_agent(model, tok, inst, fail_to_pass)
        score = reward_random(rollout["patch"], rng)
        group.append(rollout)
        reward.append(score)
        print(f"Rollout {i}: {len(rollout['calls'])} commands issued | Patch created: {'Yes' if rollout['patch'] else 'No'} | Reward: {score}")

    # 4. Add LoRA layers for training
    model = add_lora(model)

    # 5. Train Model (GRPO Step)
    grpo_step(model, tok, group, reward, device)
    
    print("=== RL Coding Agent execution finished ===")
    return "Success"

if __name__ == "__main__":
    main()
