"""Test runner verification reward for SWE-bench style tasks."""

from typing import List, Optional, Tuple
from environments.base import BaseCodingEnv


class TestRunnerReward:
    """Runs test suites inside the environment to verify whether the agent solved the bug."""

    __test__ = False

    def __init__(
        self,
        test_command: str = "python -m pytest",
        pass_reward: float = 1.0,
        fail_penalty: float = 0.0
    ):
        self.test_command = test_command
        self.pass_reward = pass_reward
        self.fail_penalty = fail_penalty

    def evaluate(
        self,
        env: BaseCodingEnv,
        expected_passing_tests: Optional[List[str]] = None
    ) -> Tuple[float, str, bool]:
        """Execute test command inside environment and determine reward.
        
        Args:
            env: Active sandbox environment.
            expected_passing_tests: List of test names that must pass (e.g. FAIL_TO_PASS in SWE-bench).
            
        Returns:
            (reward, test_output, passed_all)
        """
        output = env.run(self.test_command)

        # Check for pytest success or specific test passes
        # Pytest output typically has: "X passed" or "=== 1 passed ===" and no "FAILED"
        has_failed = "FAILED" in output or "ERROR" in output
        has_passed = "passed" in output.lower()

        if expected_passing_tests:
            # Check every expected test passed
            passed_all = True
            for tname in expected_passing_tests:
                # SWE-bench format: check if test was reported as PASSED
                if f"PASSED {tname}" not in output and f"{tname} PASSED" not in output:
                    if has_failed:
                        passed_all = False
                        break
            if passed_all and not has_failed:
                return self.pass_reward, output, True
            return self.fail_penalty, output, False

        # Fallback to general pytest outcome
        if has_passed and not has_failed:
            return self.pass_reward, output, True
        return self.fail_penalty, output, False
