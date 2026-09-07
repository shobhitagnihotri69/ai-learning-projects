"""
hrd.py — Hierarchical Reward Decomposition (HRD) from TritonRL
Implements the paper's core credit assignment formulation:
  - Output o = [o_plan, o_code]
  - r_plan = R_speedup(g, o)   -> Rewards high-level algorithmic thinking & memory hierarchy
  - r_code = R_correct(g, o)   -> Rewards low-level syntax & numerical correctness
  - Joint GRPO objective: J(theta) = alpha * J_plan(theta) + J_code(theta)
"""

import torch
from typing import Dict, List, Tuple

class HierarchicalRewardDecomposer:
    def __init__(self, alpha: float = 0.5):
        """
        alpha: balancing factor in [0, 1] between planning and coding updates.
        """
        self.alpha = alpha

    def compute_group_advantages(
        self,
        group_results: List[Dict[str, float]]
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Given a group G of generations for the same prompt qi:
        r_plan = R_speedup
        r_code = R_correct
        Computes group-normalized advantages:
          A_plan = r_plan - mean(r_plan)
          A_code = r_code - mean(r_code)
        """
        r_plans = torch.tensor([res["r_speedup"] for res in group_results], dtype=torch.float32)
        r_codes = torch.tensor([res["r_correct"] for res in group_results], dtype=torch.float32)

        # Group-wise advantage normalization
        a_plan = r_plans - r_plans.mean()
        if r_plans.std() > 1e-8:
            a_plan = a_plan / (r_plans.std() + 1e-8)

        a_code = r_codes - r_codes.mean()
        if r_codes.std() > 1e-8:
            a_code = a_code / (r_codes.std() + 1e-8)

        return a_plan, a_code

    def segment_tokens(
        self,
        full_tokens: List[int],
        plan_end_token_id: int
    ) -> Tuple[List[int], List[int]]:
        """
        Splits token sequence into T_plan and T_code based on the delimiter token
        (e.g., </think> or ```python).
        """
        if plan_end_token_id in full_tokens:
            split_idx = full_tokens.index(plan_end_token_id) + 1
            return list(range(0, split_idx)), list(range(split_idx, len(full_tokens)))
        else:
            # Fallback if delimiter missing: treat all as code
            return [], list(range(0, len(full_tokens)))
