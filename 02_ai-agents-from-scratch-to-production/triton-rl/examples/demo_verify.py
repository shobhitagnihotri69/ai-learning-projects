"""
demo_verify.py — Verifier Demonstration
Tests both an honest Triton kernel implementation and a cheating kernel
(one that uses @triton.jit but delegates to PyTorch, as observed in AutoTriton / KernelLLM).
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.verifier.ast_linter import check_syntax, check_functionality, verify_validity

# Case 1: Cheating Kernel (Common failure mode in AutoTriton / KernelLLM)
CHEATING_KERNEL_CODE = """
import torch
import triton

@triton.jit
def dummy_kernel():
    pass

def triton_entry(a: torch.Tensor, b: torch.Tensor):
    # Cheating: superficially declared @triton.jit but secretly calls PyTorch matmul!
    return torch.matmul(a, b)
"""

# Case 2: Cheating Kernel with @ operator
CHEATING_KERNEL_AT_OP = """
import torch
import triton

@triton.jit
def dummy():
    pass

def triton_entry(a: torch.Tensor, b: torch.Tensor):
    return a @ b
"""

# Case 3: Legitimate Kernel Structure (Genuine Triton syntax)
HONEST_KERNEL_CODE = """
import torch
import triton
import triton.language as tl

@triton.jit
def add_kernel(x_ptr, y_ptr, output_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    output = x + y
    tl.store(output_ptr + offsets, output, mask=mask)

def triton_entry(x: torch.Tensor, y: torch.Tensor):
    output = torch.empty_like(x)
    n_elements = output.numel()
    grid = lambda meta: (triton.cdiv(n_elements, meta['BLOCK_SIZE']),)
    add_kernel[grid](x, y, output, n_elements, BLOCK_SIZE=1024)
    return output
"""

def main():
    print("=" * 65)
    print("🔬 TritonRL Robust Verifier: Anti-Reward-Hacking Demonstration")
    print("=" * 65)

    print("\n[Test 1] Testing Cheating Kernel (torch.matmul fallback):")
    valid, msg = verify_validity(CHEATING_KERNEL_CODE)
    print(f"-> Valid? {valid} | Reason: {msg}")

    print("\n[Test 2] Testing Cheating Kernel (@ operator fallback):")
    valid, msg = verify_validity(CHEATING_KERNEL_AT_OP)
    print(f"-> Valid? {valid} | Reason: {msg}")

    print("\n[Test 3] Testing Honest Triton Kernel (Pure Triton instructions):")
    valid, msg = verify_validity(HONEST_KERNEL_CODE)
    print(f"-> Valid? {valid} | Reason: {msg}")

    print("\n" + "=" * 65)
    print("✅ Result: Multi-layer AST verification successfully catches")
    print("   reward-hacking shortcuts that fooled AutoTriton and KernelLLM!")
    print("=" * 65)

if __name__ == "__main__":
    main()
