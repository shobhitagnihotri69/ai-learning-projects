"""Composite reward function combining test verification, AST syntax check, and patch penalties."""

from typing import Dict, List, Optional, Tuple
from environments.base import BaseCodingEnv
from rewards.syntax import SyntaxReward
from rewards.verifier import TestRunnerReward


class CompositeReward:
    """Calculates granular multi-faceted reward for RL coding agent rollouts."""

    def __init__(
        self,
        test_reward: Optional[TestRunnerReward] = None,
        syntax_reward: Optional[SyntaxReward] = None,
        no_patch_penalty: float = -0.2,
        syntax_weight: float = 0.2,
        test_weight: float = 0.8
    ):
        self.test_reward = test_reward or TestRunnerReward()
        self.syntax_reward = syntax_reward or SyntaxReward()
        self.no_patch_penalty = no_patch_penalty
        self.syntax_weight = syntax_weight
        self.test_weight = test_weight

    def evaluate(
        self,
        env: BaseCodingEnv,
        patch: str,
        files: Optional[Dict[str, str]] = None,
        expected_passing_tests: Optional[List[str]] = None
    ) -> Dict[str, any]:
        """Compute composite reward score and breakdown.
        
        Returns:
            Dictionary with 'total_reward', 'test_score', 'syntax_score', 'passed', and 'details'.
        """
        breakdown = {
            "patch_present": bool(patch.strip()),
            "syntax_score": 0.0,
            "test_score": 0.0,
            "passed": False,
            "test_output": "",
            "syntax_details": {}
        }

        # 1. Patch presence check
        if not patch.strip():
            breakdown["total_reward"] = self.no_patch_penalty
            breakdown["reason"] = "No modifications or patch made."
            return breakdown

        # 2. Syntax verification
        if files:
            syn_score, syn_details = self.syntax_reward.evaluate_files(files)
            breakdown["syntax_score"] = syn_score
            breakdown["syntax_details"] = syn_details

        # 3. Test verification
        t_score, t_output, passed = self.test_reward.evaluate(env, expected_passing_tests)
        breakdown["test_score"] = t_score
        breakdown["test_output"] = t_output
        breakdown["passed"] = passed

        # Weighted total reward
        total = (self.test_weight * t_score) + (self.syntax_weight * breakdown["syntax_score"])
        breakdown["total_reward"] = round(float(total), 3)
        return breakdown
