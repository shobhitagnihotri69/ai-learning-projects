"""Unit tests for environments, rewards, and TRL adapter."""

import pytest
from environments.local_sandbox import LocalSandboxEnv
from rewards.syntax import SyntaxReward
from rewards.verifier import TestRunnerReward
from rewards.composite import CompositeReward
from trl_bridge.openenv_adapter import OpenEnvCodingAdapter


def test_local_sandbox_lifecycle():
    """Verify LocalSandboxEnv initializes git repo, runs commands, and computes diff."""
    env = LocalSandboxEnv(timeout=10)
    try:
        initial_files = {
            "calculator.py": "def add(a, b):\n    return a - b\n",
            "test_calc.py": "from calculator import add\ndef test_add():\n    assert add(1, 2) == 3\n"
        }
        obs = env.reset(initial_files)
        assert "Environment initialized" in obs

        # Check git status / ls
        ls_out = env.run("ls")
        assert "calculator.py" in ls_out
        assert "test_calc.py" in ls_out

        # Check patch initially empty
        assert env.patch() == ""

        # Make a modification fixing the bug
        fix_cmd = "cat > calculator.py << 'EOF'\ndef add(a, b):\n    return a + b\nEOF"
        env.run(fix_cmd)

        # Check git diff shows the change
        diff = env.patch()
        assert "return a + b" in diff
        assert "-    return a - b" in diff

        # Run pytest inside sandbox
        test_out = env.run("python -m pytest test_calc.py")
        assert "1 passed" in test_out
    finally:
        env.close()


def test_syntax_reward():
    """Verify SyntaxReward identifies valid and invalid Python ASTs."""
    reward = SyntaxReward(valid_reward=0.2, invalid_penalty=-0.5)

    valid_code = "def foo(x):\n    return x * 2\n"
    score, msg = reward.evaluate_code(valid_code)
    assert score == 0.2
    assert "Valid" in msg

    invalid_code = "def foo(x\n    return x *"
    score, msg = reward.evaluate_code(invalid_code)
    assert score == -0.5
    assert "SyntaxError" in msg


def test_composite_reward():
    """Verify CompositeReward correctly scores rollouts."""
    env = LocalSandboxEnv(timeout=10)
    try:
        initial_files = {
            "math_mod.py": "def multiply(x, y):\n    return 0\n",
            "test_math.py": "from math_mod import multiply\ndef test_multiply():\n    assert multiply(3, 4) == 12\n"
        }
        env.reset(initial_files)

        reward_fn = CompositeReward(
            test_reward=TestRunnerReward(test_command="python -m pytest test_math.py"),
            syntax_reward=SyntaxReward()
        )

        # Scenario 1: Empty patch -> penalized
        res1 = reward_fn.evaluate(env=env, patch="")
        assert res1["total_reward"] == -0.2

        # Scenario 2: Fixed code -> full reward
        env.run("cat > math_mod.py << 'EOF'\ndef multiply(x, y):\n    return x * y\nEOF")
        diff = env.patch()
        res2 = reward_fn.evaluate(
            env=env,
            patch=diff,
            files={"math_mod.py": "def multiply(x, y):\n    return x * y\n"}
        )
        assert res2["passed"] is True
        assert res2["total_reward"] > 0.8
    finally:
        env.close()


def test_trl_openenv_adapter():
    """Verify OpenEnvCodingAdapter reset and step protocol."""
    task = {
        "instance_id": "test-task-1",
        "files": {
            "hello.py": "print('hello')\n"
        }
    }
    adapter = OpenEnvCodingAdapter(task_instance=task, use_docker=False)
    try:
        obs, info = adapter.reset()
        assert info["task_id"] == "test-task-1"

        obs, reward, term, trunc, info = adapter.step("python hello.py")
        assert "hello" in obs
        assert not term
        assert not trunc
    finally:
        adapter.close()
