"""OpenCodingEnv: Open-Source Verifiable RL Environment for Coding Agents.

Interactive Showcase & Playground for Hugging Face Spaces.
Demonstrates dual-sandbox execution (Local/Docker), AST syntax validation,
real pytest suite verification, and GRPO group advantage calculation.
"""

import html
import json
import os
import sys
import pandas as pd

from environments.local_sandbox import LocalSandboxEnv
from rewards.composite import CompositeReward
from rewards.syntax import SyntaxReward
from rewards.verifier import TestRunnerReward
from utils import TARGET, MOCK_FILE

try:
    import gradio as gr
except ImportError:
    gr = None

# Sample Preset Tasks
PRESET_TASKS = {
    "Astropy Separable Bug (astropy__astropy-12907)": {
        "problem_statement": (
            "In `astropy/modeling/separable.py`, function `_cstack(left, right)` has an asymmetry: "
            "when right is not an instance of Model, `cright[-right.shape[0]:, -right.shape[1]:] = 1` "
            "is executed instead of assigning `right`. Fix this bug so `cright` correctly receives `right`."
        ),
        "files": {
            TARGET: MOCK_FILE,
            "tests/test_separable.py": (
                "import numpy as np\n"
                "from astropy.modeling.separable import _cstack\n\n"
                "def test_cstack_symmetry():\n"
                "    left = np.ones((2, 2)) * 3\n"
                "    right = np.ones((2, 2)) * 5\n"
                "    res = _cstack(left, right)\n"
                "    assert np.all(res[:, 2:] == 5), f'Expected 5, got {res[:, 2:]}'\n"
            )
        },
        "solution_patch": (
            "cat > astropy/modeling/separable.py << 'EOF'\n"
            + MOCK_FILE.replace(
                "cright[-right.shape[0]:, -right.shape[1]:] = 1",
                "cright[-right.shape[0]:, -right.shape[1]:] = right"
            )
            + "\nEOF"
        )
    },
    "Simple Calculator Bug": {
        "problem_statement": (
            "In `calculator.py`, `add(a, b)` mistakenly subtracts `a - b`. "
            "Fix the operator so it correctly returns `a + b`."
        ),
        "files": {
            "calculator.py": "def add(a, b):\n    return a - b\n",
            "tests/test_calc.py": "from calculator import add\ndef test_add():\n    assert add(1, 2) == 3\n"
        },
        "solution_patch": (
            "cat > calculator.py << 'EOF'\n"
            "def add(a, b):\n"
            "    return a + b\n"
            "EOF"
        )
    }
}


def run_single_rollout(preset_name, agent_behavior):
    """Execute a rollout inside LocalSandboxEnv and compute verifiable rewards."""
    task = PRESET_TASKS.get(preset_name, PRESET_TASKS["Astropy Separable Bug (astropy__astropy-12907)"])
    env = LocalSandboxEnv(timeout=15)
    env.reset(initial_files=task["files"])

    terminal_logs = []
    terminal_logs.append(f"$ [Setup] Initialized sandbox workspace with {len(task['files'])} files.\n")

    # Determine command sequence based on selected agent behavior
    if agent_behavior == "Successful Bug Fix Agent":
        commands = [
            "ls",
            f"cat {list(task['files'].keys())[0]}",
            task["solution_patch"],
            "python -m pytest"
        ]
    elif agent_behavior == "Syntax Error Agent":
        commands = [
            "ls",
            "cat > bug_edit.py << 'EOF'\ndef broken_func(:\n    return\nEOF",
            "python -m pytest"
        ]
    elif agent_behavior == "Explore-Only Agent (No Patch)":
        commands = [
            "ls -la",
            "git status",
            "python -m pytest"
        ]
    else:  # Failing Fix
        commands = [
            "ls",
            f"cat > {list(task['files'].keys())[0]} << 'EOF'\n# Random failed attempt\nEOF",
            "python -m pytest"
        ]

    for cmd in commands:
        obs = env.run(cmd)
        display_cmd = cmd.splitlines()[0] + ("..." if "\n" in cmd else "")
        terminal_logs.append(f"$ {display_cmd}\n{obs}\n")

    patch = env.patch()
    
    # Calculate Verifiable Reward
    reward_fn = CompositeReward(
        test_reward=TestRunnerReward(test_command="python -m pytest"),
        syntax_reward=SyntaxReward()
    )
    eval_res = reward_fn.evaluate(
        env=env,
        patch=patch,
        files=task["files"]
    )
    env.close()

    logs_text = "\n".join(terminal_logs)
    patch_text = patch if patch else "(No changes made to files)"
    
    breakdown_md = (
        f"### Verifiable Reward Breakdown\n\n"
        f"- **Total Reward**: `{eval_res['total_reward']:+.3f}`\n"
        f"- **Test Suite Passed**: `{'✅ Yes' if eval_res['passed'] else '❌ No'}` (Score: `{eval_res['test_score']:+.2f}`)\n"
        f"- **AST Syntax Score**: `{eval_res['syntax_score']:+.2f}`\n"
        f"- **Patch Generated**: `{'✅ Yes' if eval_res['patch_present'] else '❌ No'}`\n"
    )

    return logs_text, patch_text, breakdown_md


def run_grpo_group(preset_name):
    """Run a group of 4 rollouts and calculate GRPO advantage normalization."""
    task = PRESET_TASKS.get(preset_name, PRESET_TASKS["Astropy Separable Bug (astropy__astropy-12907)"])
    behaviors = [
        "Successful Bug Fix Agent",
        "Failing Attempt Agent",
        "Explore-Only Agent (No Patch)",
        "Syntax Error Agent"
    ]

    rollouts = []
    for i, b in enumerate(behaviors):
        env = LocalSandboxEnv(timeout=15)
        env.reset(initial_files=task["files"])
        
        if b == "Successful Bug Fix Agent":
            env.run(task["solution_patch"])
        elif b == "Syntax Error Agent":
            env.run("cat > bad.py << 'EOF'\ndef err(\nEOF")
        elif b == "Failing Attempt Agent":
            env.run(f"cat > {list(task['files'].keys())[0]} << 'EOF'\n# Incorrect\nEOF")
            
        patch = env.patch()
        reward_fn = CompositeReward(test_reward=TestRunnerReward(test_command="python -m pytest"))
        eval_res = reward_fn.evaluate(env=env, patch=patch, files=task["files"])
        env.close()

        rollouts.append({
            "Rollout": f"Rollout #{i+1}",
            "Agent Policy Trajectory": b,
            "Patch Lines": len(patch.splitlines()) if patch else 0,
            "Passed Tests": "✅ Pass" if eval_res["passed"] else "❌ Fail",
            "Raw Reward (r_i)": eval_res["total_reward"]
        })

    df = pd.DataFrame(rollouts)
    raw_rewards = df["Raw Reward (r_i)"].tolist()
    mean_r = sum(raw_rewards) / len(raw_rewards)
    std_r = (sum((x - mean_r) ** 2 for x in raw_rewards) / len(raw_rewards)) ** 0.5 + 1e-5

    advantages = [round((r - mean_r) / std_r, 3) for r in raw_rewards]
    df["Advantage A_i = (r_i - μ) / σ"] = advantages
    df["Policy Gradient Direction"] = [
        "🚀 Boost Probability (Positive Advantage)" if a > 0 else "🔻 Penalize Policy (Negative Advantage)"
        for a in advantages
    ]

    summary_md = (
        f"### GRPO Group Statistics (Group Size = 4)\n\n"
        f"- **Mean Reward (μ)**: `{mean_r:.3f}`\n"
        f"- **Std Deviation (σ)**: `{std_r:.3f}`\n"
        f"- **Key Insight**: Unlike standard PPO, GRPO uses no separate Critic/Value network. "
        f"It normalizes rewards directly across the group of rollouts sampled from the same policy!"
    )

    return df, summary_md


def create_demo():
    if gr is None:
        raise RuntimeError("Gradio is not installed. Please run: pip install gradio")

    theme = gr.themes.Soft(
        primary_hue="blue",
        secondary_hue="slate"
    )

    with gr.Blocks(theme=theme, title="OpenCodingEnv - RL Coding Sandbox") as demo:
        gr.Markdown(
            """
            # 🚀 OpenCodingEnv: Open-Source Verifiable RL Environment for Coding Agents
            **A lightweight, zero-dependency verifiable RL sandbox built for Hugging Face Spaces & TRL.**
            *Run dual sandboxes (Local Subprocess / Docker), AST anti-cheat syntax graders, real PyTest verification, and GRPO advantage updates.*
            """
        )

        with gr.Tabs():
            with gr.TabItem("🧪 Interactive Rollout Sandbox"):
                with gr.Row():
                    with gr.Column(scale=1):
                        task_dropdown = gr.Dropdown(
                            label="Select Coding Task",
                            choices=list(PRESET_TASKS.keys()),
                            value=list(PRESET_TASKS.keys())[0]
                        )
                        behavior_dropdown = gr.Dropdown(
                            label="Simulate Agent Trajectory",
                            choices=[
                                "Successful Bug Fix Agent",
                                "Failing Attempt Agent",
                                "Explore-Only Agent (No Patch)",
                                "Syntax Error Agent"
                            ],
                            value="Successful Bug Fix Agent"
                        )
                        run_btn = gr.Button("⚡ Run Sandbox Rollout", variant="primary")
                        
                        reward_output = gr.Markdown(label="Reward Breakdown")

                    with gr.Column(scale=2):
                        terminal_box = gr.Textbox(
                            label="Sandbox Terminal Execution Logs",
                            lines=12,
                            interactive=False
                        )
                        diff_box = gr.Textbox(
                            label="Candidate Unified Diff (git diff HEAD)",
                            lines=8,
                            interactive=False
                        )

                run_btn.click(
                    fn=run_single_rollout,
                    inputs=[task_dropdown, behavior_dropdown],
                    outputs=[terminal_box, diff_box, reward_output]
                )

            with gr.TabItem("📊 GRPO Group Advantage Inspector"):
                gr.Markdown(
                    """
                    ### Group Relative Policy Optimization (GRPO)
                    Sample a group of parallel rollouts for the same task, score each using the real test verifier, 
                    and compute normalized advantages $A_i = \\frac{r_i - \\mu}{\\sigma}$ without needing a Critic network!
                    """
                )
                with gr.Row():
                    grpo_task_dropdown = gr.Dropdown(
                        label="Task",
                        choices=list(PRESET_TASKS.keys()),
                        value=list(PRESET_TASKS.keys())[0]
                    )
                    grpo_btn = gr.Button("🎲 Sample GRPO Group (4 Rollouts)", variant="primary")

                grpo_stats_output = gr.Markdown()
                grpo_table_output = gr.Dataframe(label="Group Rollouts & Advantage Normalization")

                grpo_btn.click(
                    fn=run_grpo_group,
                    inputs=[grpo_task_dropdown],
                    outputs=[grpo_table_output, grpo_stats_output]
                )

            with gr.TabItem("🔌 Hugging Face TRL 1-Line Integration"):
                gr.Markdown(
                    """
                    ### Use with Hugging Face `trl.GRPOTrainer`
                    You can plug `OpenCodingEnv` into Hugging Face TRL in **1 line** using our OpenEnv adapter:

                    ```python
                    from trl import GRPOTrainer, GRPOConfig
                    from trl_bridge import OpenEnvCodingAdapter

                    # 1. Wrap your task into OpenCodingEnv
                    env = OpenEnvCodingAdapter(task_instance=my_task, use_docker=False)

                    # 2. Train with Hugging Face GRPOTrainer
                    trainer = GRPOTrainer(
                        model="Qwen/Qwen2.5-Coder-0.5B-Instruct",
                        reward_funcs=[env.reward_fn.evaluate],
                        args=GRPOConfig(output_dir="./output", max_prompt_length=1024)
                    )
                    trainer.train()
                    ```
                    """
                )

    return demo


if __name__ == "__main__":
    demo = create_demo()
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
