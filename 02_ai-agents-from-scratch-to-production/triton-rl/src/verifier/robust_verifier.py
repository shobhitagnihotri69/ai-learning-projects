"""
robust_verifier.py — Multi-Layer Verification System from TritonRL paper
Computes:
  - R_correct(g, o) = valid(o) * correct(g, o)
  - R_speedup(g, o) = valid(o) * clip(speedup(g, o), 2.0)
  where:
  - valid(o) = syntax(o) * func(o)
  - speedup(g, o) = tau(PyTorch, x) / tau(Triton, x) * correct(g, o)
"""

import time
import torch
from typing import Dict, Any, Callable, Tuple
from .ast_linter import verify_validity

class RobustVerifier:
    def __init__(self, atol: float = 1e-3, rtol: float = 1e-3, speedup_clip: float = 2.0):
        self.atol = atol
        self.rtol = rtol
        self.speedup_clip = speedup_clip

    def verify_and_score(
        self,
        generated_code: str,
        reference_fn: Callable,
        sample_inputs_fn: Callable[[], Tuple],
        entrypoint_name: str = "triton_entry",
        num_timing_runs: int = 10,
        warmup_runs: int = 3
    ) -> Dict[str, Any]:
        """
        Executes the multi-layered verification protocol:
        1. valid(o): syntax & functional anti-cheat verification
        2. correct(g, o): dynamic numerical correctness against reference_fn
        3. speedup(g, o): runtime latency comparison, clipped at 2.0
        """
        result = {
            "valid": 0.0,
            "syntax": 0.0,
            "func": 0.0,
            "correct": 0.0,
            "speedup": 0.0,
            "r_correct": 0.0,
            "r_speedup": 0.0,
            "details": ""
        }

        # Step 1: Valid check (syntax + functional anti-cheat)
        is_valid, reason = verify_validity(generated_code)
        if not is_valid:
            result["details"] = f"Validity check failed: {reason}"
            return result

        result["valid"] = 1.0
        result["syntax"] = 1.0
        result["func"] = 1.0

        # Step 2: Safe execution of generated code in dynamic scope
        local_scope = {}
        try:
            exec(generated_code, {"torch": torch}, local_scope)
            if entrypoint_name not in local_scope:
                result["details"] = f"Entrypoint '{entrypoint_name}' not found in code."
                return result
            triton_candidate = local_scope[entrypoint_name]
        except Exception as e:
            result["details"] = f"Compilation/Import execution failed: {str(e)}"
            return result

        # Step 3: Numerical Correctness Test across multiple sample inputs
        try:
            inputs = sample_inputs_fn()
            ref_out = reference_fn(*inputs)
            cand_out = triton_candidate(*inputs)

            if not isinstance(cand_out, torch.Tensor) or not isinstance(ref_out, torch.Tensor):
                result["details"] = "Output is not a valid torch.Tensor"
                return result

            # Check close
            if not torch.allclose(cand_out, ref_out, atol=self.atol, rtol=self.rtol):
                max_diff = (cand_out - ref_out).abs().max().item()
                result["details"] = f"Numerical mismatch: max_diff = {max_diff}"
                return result

            result["correct"] = 1.0
            result["r_correct"] = 1.0
        except Exception as e:
            result["details"] = f"Runtime execution failed: {str(e)}"
            return result

        # Step 4: Speedup Measurement (tau_ref / tau_triton)
        try:
            # Warmup
            for _ in range(warmup_runs):
                _ = reference_fn(*inputs)
                _ = triton_candidate(*inputs)

            # Measure Reference PyTorch latency
            t0 = time.perf_counter()
            for _ in range(num_timing_runs):
                _ = reference_fn(*inputs)
            tau_ref = (time.perf_counter() - t0) / num_timing_runs

            # Measure Triton candidate latency
            t1 = time.perf_counter()
            for _ in range(num_timing_runs):
                _ = triton_candidate(*inputs)
            tau_cand = (time.perf_counter() - t1) / num_timing_runs

            raw_speedup = tau_ref / max(tau_cand, 1e-9)
            clipped_speedup = min(raw_speedup, self.speedup_clip)

            result["speedup"] = raw_speedup
            result["r_speedup"] = result["valid"] * clipped_speedup
            result["details"] = f"Success! Speedup: {raw_speedup:.2f}x (clipped: {clipped_speedup:.2f}x)"
        except Exception as e:
            result["details"] = f"Timing failed: {str(e)}"

        return result
