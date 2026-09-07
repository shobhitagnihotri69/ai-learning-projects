"""
closed_loop_finetune.py  —  PIECE 7: Closed-Loop Fine-Tuning

The Problem with Open-Loop Training:
  During open-loop training, M always gets the REAL code as input.
  If M makes a mistake at step 5, step 6 still gets the real correct code.
  Mistakes do NOT compound.

  But at deployment, M eats its own output:
    Step 5 prediction is slightly wrong
    → slightly-wrong code fed to step 6
    → step 6 prediction is slightly-MORE wrong
    → slightly-more-wrong code fed to step 7
    → errors COMPOUND exponentially

  Training and deployment are different sports.
  We must PRACTICE the deployment condition.

The Solution — Closed-Loop Rollouts:
  Fine-tune M on short sequences where it feeds itself:
    1. Run M for K steps, each step feeding previous prediction as next input
    2. Compute loss: how far are predictions from real codes?
    3. Also decode each predicted code and check pixel accuracy (with ball weighting)
    4. Backpropagate through the ENTIRE K-step chain

Curriculum (easy → hard):
  Stage 1: K=5  steps  (lr=1e-3, 25 epochs)  — survive 5 self-fed steps
  Stage 2: K=15 steps  (lr=3e-4, 15 epochs)  — survive 15 self-fed steps

IMPORTANT: Freeze V during fine-tuning.
  V's code space is fixed — we want M to learn to LIVE IN IT.
  If we unfreeze V, the two networks would co-adapt and renegotiate
  the code space, destroying the pre-computed codes we trained M on.
"""
import time
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import matplotlib.pyplot as plt

from network_v import VNet, Z
from network_m import MNet, H
from collect_dataset import frames, actions, EPISODES, T, device

# ── Load checkpoints ──────────────────────────────────────────────────────────
vnet = VNet().to(device)
vnet.load_state_dict(torch.load("vnet_checkpoint.pt", map_location=device))

mnet_ckpt = torch.load("mnet_checkpoint.pt", map_location=device)
mnet = MNet().to(device)
mnet.load_state_dict(mnet_ckpt["mnet"])

Z_MEAN   = mnet_ckpt["z_mean"].to(device)
Z_STD    = mnet_ckpt["z_std"].to(device)
zs_norm  = mnet_ckpt["zs_norm"]    # pre-normalized codes (200, 120, 12)
a1h      = mnet_ckpt["a1h"]        # one-hot actions (200, 120, 3)

# ── FREEZE V — don't let it adapt to M's errors ───────────────────────────────
# requires_grad_(False): tells PyTorch not to compute gradients for V's parameters.
# The optimizer will only update M's parameters.
for p in vnet.parameters():
    p.requires_grad_(False)
vnet.eval()   # also set eval mode (disables batch norm / dropout if any)

print("V is FROZEN. Only M's weights will be updated during fine-tuning.")

# ── Frame tensor (for pixel loss) ─────────────────────────────────────────────
# We need actual frames to compute pixel accuracy.
# frames shape: (200, 120, 32, 32, 3) as numpy → convert to torch
frames_t = torch.tensor(frames)   # keep on CPU to save GPU memory; move per-batch

# ── Optimizer (will update learning rate between stages) ──────────────────────
opt = torch.optim.Adam(mnet.parameters(), lr=1e-3)

# ── Curriculum stages ─────────────────────────────────────────────────────────
STAGES = [
    (5,  1e-3, 25),    # (rollout_length K, learning_rate, n_epochs)
    (15, 3e-4, 15),
]

print("\nStarting closed-loop fine-tuning...")
t0 = time.time()

for K, lr, n_epochs in STAGES:
    # Update learning rate for this stage
    for g in opt.param_groups:
        g["lr"] = lr

    print(f"\nStage: K={K} steps, lr={lr}, epochs={n_epochs}")

    for epoch in range(n_epochs):
        perm       = torch.randperm(EPISODES)
        total_loss = 0.0

        for i in range(0, EPISODES, 16):
            idx = perm[i:i+16]
            z = zs_norm[idx].to(device)         # codes: (16, 120, 12)
            a = a1h[idx].to(device)             # actions: (16, 120, 3)
            x = frames_t[idx.numpy()].to(device) # real frames: (16, 120, 32, 32, 3)

            # ── Random start point ─────────────────────────────────────────
            # Pick a random start in [4, T-K-1] so the rollout fits within episode.
            # (Start at 4+ to give some warmup context before the rollout.)
            t_start = int(torch.randint(4, T - K - 1, (1,)))

            # ── Warm up memory on real codes before rollout ────────────────
            # Run GRU on real codes from step 0..t_start.
            # This gives the memory realistic context about ball position/velocity.
            # After warm-up: h = memory state at t_start, ready for closed loop.
            _, h = mnet(z[:, :t_start], a[:, :t_start])

            # ── Start closed-loop at t_start ───────────────────────────────
            # zc = current code (will be replaced by prediction each step)
            zc   = z[:, t_start:t_start+1]   # shape: (16, 1, 12)
            loss = 0.0

            # ── K-step closed-loop rollout ─────────────────────────────────
            for k in range(K):
                # Predict: given current code + action → code change
                delta, h = mnet(zc, a[:, t_start+k:t_start+k+1], h)
                znext = zc + delta   # predicted next code: (16, 1, 12)

                # ── LOSS 1: Code accuracy ──────────────────────────────────
                # How close is the predicted code to the actual next code?
                loss = loss + F.mse_loss(
                    znext[:, 0],           # predicted: (16, 12)
                    z[:, t_start+k+1]      # actual:    (16, 12)
                )

                # ── LOSS 2: Pixel accuracy ─────────────────────────────────
                # Decode the predicted code and compare to the real next frame.
                # Why pixel loss? A code could be numerically close to the right
                # code but decode to a frame where the ball is invisible
                # (the encoder isn't perfectly smooth). Pixel loss is the real check.
                xk   = x[:, t_start+k+1]                              # real frame: (16, 32, 32, 3)
                z_denorm = znext[:, 0] * Z_STD + Z_MEAN               # undo normalization
                xhat = vnet.decode(z_denorm)                           # decode to frame

                # Ball weighting: same as in V's training (1 + 40 × redness)
                wpix = 1.0 + 40.0 * xk[..., :1]
                loss = loss + 0.002 * (
                    wpix * F.binary_cross_entropy(xhat, xk, reduction="none")
                ).sum() / len(idx)
                # 0.002 weight: pixel loss is louder than code loss numerically,
                # so we scale it down to keep them balanced.

                # ── THE CLOSED LOOP ────────────────────────────────────────
                # CRITICAL LINE: predicted code becomes the next input.
                # This is what makes it "closed loop" — M eats its own output.
                zc = znext

            # ── Gradient step ─────────────────────────────────────────────
            opt.zero_grad()
            loss.backward()   # backpropagate through the ENTIRE K-step chain
            opt.step()
            total_loss += loss.item() * len(idx)

        if (epoch + 1) % 5 == 0:
            print(f"  epoch {epoch+1:2d}/{n_epochs}  loss = {total_loss/EPISODES:.3f}")

elapsed = time.time() - t0
print(f"\nClosed-loop fine-tuning done in {elapsed:.0f}s")

# ── Save final model ──────────────────────────────────────────────────────────
torch.save({
    "vnet":   vnet.state_dict(),
    "mnet":   mnet.state_dict(),
    "z_mean": mnet_ckpt["z_mean"],   # keep on CPU for saving
    "z_std":  mnet_ckpt["z_std"],
}, "pong_wm.pt")
print("Saved: pong_wm.pt  (final world model checkpoint)")
print("This file is what the lecture demo GIFs are generated from.")
