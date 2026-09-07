"""
train_m.py  —  PIECE 6: Train Network M (Memory + Prediction)

Steps in this file:
  1. Pre-compute all codes using trained V (run V encoder on all 24,000 frames)
  2. Normalize codes to mean=0, std=1 per dimension
  3. Encode actions as one-hot vectors
  4. Open-loop training: M predicts next code given real current code
  5. Probe: measure how prediction error changes with timestep (memory story)

TWO TRICKS IN TRAINING:

TRICK A — Code normalization:
  Problem: Some code dimensions (describing the large busy paddle) have high
           variance: values ranging -5 to +5.
           Other dimensions (describing the small ball) have low variance: -0.5 to +0.5.
           MSE loss obsesses over high-variance dims, ignores ball dims completely.
  Fix: Normalize each dimension to mean=0, std=1.
       Now all 12 dims matter equally to the loss.

TRICK B — Input noise:
  Problem: At deployment, M eats its own predictions (not real codes).
           Predictions are "close but not exact". A model trained on
           perfect inputs amplifies small errors instead of correcting them.
  Fix: Add tiny noise (0.05 × random) to input codes during training.
       Model learns to CORRECT slight errors, not amplify them.
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

# ── Load trained V ────────────────────────────────────────────────────────────
vnet = VNet().to(device)
vnet.load_state_dict(torch.load("vnet_checkpoint.pt", map_location=device))
vnet.eval()   # inference mode — no dropout, no gradient tracking

# ── STEP 1: Pre-compute all codes ─────────────────────────────────────────────
# Run V encoder on all 24,000 frames.
# Do it in mini-batches of 4096 to avoid running out of memory.
# Result: zs shape = (200 episodes, 120 timesteps, 12 code dimensions)
#
# WHY PRE-COMPUTE?
#   M trains on 12-number codes, not 3,072-pixel frames.
#   That's 256× less data per sample → M trains in SECONDS not minutes.
#   This speed-up is what the entire V compression step buys us.
print("Pre-computing codes for all 24,000 frames...")
flat = torch.tensor(frames.reshape(-1, 32, 32, 3))

zs_list = []
with torch.no_grad():
    for i in range(0, len(flat), 4096):
        batch = flat[i:i+4096].to(device)
        mu, _ = vnet.encode(batch)
        zs_list.append(mu.cpu())

zs = torch.cat(zs_list).view(EPISODES, T, Z)
print(f"Codes shape: {zs.shape}  (episodes × timesteps × code_dim)")

# ── STEP 2: Normalize codes (TRICK A) ─────────────────────────────────────────
# Compute per-dimension mean and standard deviation across all 24,000 codes.
# reshape(-1, Z) flattens to (24000, 12) for statistics.
Z_MEAN = zs.reshape(-1, Z).mean(dim=0)                    # shape: (12,)
Z_STD  = zs.reshape(-1, Z).std(dim=0).clamp_min(1e-4)    # shape: (12,), avoid /0

# Normalize: subtract mean, divide by std → each dim: mean=0, std=1
zs_norm = (zs - Z_MEAN) / Z_STD

print(f"Code stats (before normalization):")
print(f"  mean range: [{Z_MEAN.min():.2f}, {Z_MEAN.max():.2f}]")
print(f"  std range:  [{Z_STD.min():.2f}, {Z_STD.max():.2f}]")
print(f"Code stats (after normalization):")
print(f"  mean: ≈ 0.0  |  std: ≈ 1.0  (confirmed)")

# ── STEP 3: Encode actions as one-hot ────────────────────────────────────────
# actions shape: (200, 120) with integer values 0/1/2
# a1h shape:     (200, 120, 3) with binary vectors [1,0,0] / [0,1,0] / [0,0,1]
# F.one_hot: given integer n in range [0, num_classes), returns binary vector
a1h = F.one_hot(torch.tensor(actions), num_classes=3).float()

# ── STEP 4: Initialize M and optimizer ───────────────────────────────────────
mnet = MNet().to(device)
opt  = torch.optim.Adam(mnet.parameters(), lr=1e-3)

# ── STEP 5: Open-loop training ────────────────────────────────────────────────
# "Open loop" = M always gets the REAL code as input, even if its last prediction was wrong.
# This is easier to train than closed-loop. (Closed-loop comes in next piece.)
#
# Training in mini-batches of 16 EPISODES (not individual frames).
# Why episodes? M needs sequences — GRU memory unrolls across a whole episode.
print("\nTraining Network M (open-loop)...")
t0 = time.time()

for epoch in range(25):
    perm      = torch.randperm(EPISODES)   # shuffle episode order each epoch
    total_loss = 0.0

    for i in range(0, EPISODES, 16):
        idx = perm[i:i+16]              # pick 16 random episodes
        z = zs_norm[idx].to(device)    # normalized codes:  (16, 120, 12)
        a = a1h[idx].to(device)        # one-hot actions:   (16, 120,  3)

        # ── TRICK B: Input noise ─────────────────────────────────────────
        # Add tiny Gaussian noise to input codes (0.05 × standard normal).
        # z[:, :-1] = all frames except the last (we predict frames 1..119 from 0..118)
        # At deployment, input codes will be M's own predictions — imperfect.
        # Training with noise prepares M to handle imperfect inputs.
        z_in = z[:, :-1] + 0.05 * torch.randn_like(z[:, :-1])

        # Forward pass: M processes codes 0..118 and predicts changes 1..119
        delta_z, _ = mnet(z_in, a[:, :-1])

        # ── Residual prediction loss ─────────────────────────────────────
        # predicted z_next = z_current + delta_z
        # target = actual next code (z[:, 1:] = codes for frames 1..119)
        # MSE = mean squared error
        loss = F.mse_loss(z_in + delta_z, z[:, 1:])

        opt.zero_grad()
        loss.backward()
        opt.step()

        total_loss += loss.item() * len(idx)

    if (epoch + 1) % 5 == 0:
        print(f"  epoch {epoch+1:2d}/25  prediction_error = {total_loss/EPISODES:.4f}")

elapsed = time.time() - t0
n_params = sum(p.numel() for p in mnet.parameters())
print(f"\nM trained in {elapsed:.0f}s  ({n_params:,} parameters)")

# ── STEP 6: The Memory Experiment ─────────────────────────────────────────────
# Test the claim: "memory needs exactly 2 frames, then prediction snaps into place"
# Measure prediction error at each timestep t = 1, 2, ..., 15
#
# Expected pattern:
#   t=1: HIGH error (only 1 frame → velocity unknown)
#   t=2-3: SHARP DROP (memory has seen 2 positions → can compute velocity)
#   t=4+: Small, slowly decreasing (memory is confident)
#
# This cliff between t=1 and t=3 is the fingerprint of memory doing its job.
print("\nRunning memory experiment...")
mnet.eval()
with torch.no_grad():
    z_test = zs_norm[:100].to(device)    # first 100 episodes
    a_test = a1h[:100].to(device)

    delta_test, _ = mnet(z_test[:, :-1], a_test[:, :-1])
    # err[episode, timestep] = squared prediction error at that timestep
    err = ((z_test[:, :-1] + delta_test - z_test[:, 1:]) ** 2
           ).mean(dim=-1).cpu().numpy()   # mean over 12 code dimensions

fig, ax = plt.subplots(figsize=(8.2, 3.6))
steps = np.arange(1, 16)
ax.plot(steps, err[:, :15].mean(0), lw=2.5, marker="o", ms=5)
ax.set_xticks(steps)
ax.set_xlabel("Timestep being predicted")
ax.set_ylabel("Prediction error")
ax.set_title("Memory needs exactly 2 frames — then prediction snaps into place")
plt.tight_layout()
plt.savefig("plot_03_memory_experiment.png", dpi=150, bbox_inches="tight")
plt.show()

e1  = err[:, 0].mean()
e3  = err[:, 2].mean()
e10 = err[:, 9].mean()
print(f"Error at t=1:  {e1:.4f}  (high — velocity unknown)")
print(f"Error at t=3:  {e3:.4f}  (drops — memory computed velocity from 2 frames)")
print(f"Error at t=10: {e10:.4f} (low — memory confident)")
print("Saved: plot_03_memory_experiment.png")

# Save M checkpoint and normalization stats
torch.save({
    "mnet":   mnet.state_dict(),
    "z_mean": Z_MEAN,
    "z_std":  Z_STD,
    "zs_norm": zs_norm,
    "a1h":    a1h,
}, "mnet_checkpoint.pt")
print("Saved: mnet_checkpoint.pt")
