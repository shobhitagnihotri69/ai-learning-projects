"""
train_v.py  —  PIECE 4: Train Network V (The 4 Tricks)

What this does:
  Trains VNet to compress 3,072-pixel frames → 12-number codes and back.
  Simple in principle — but the naive version fails in 4 specific ways.
  Each trick below fixes one real failure we hit.

TRICK 1 — Red-pixel weighting (most important):
  Problem: The ball is only ~15 pixels out of 1,024.
           A plain loss ignores the ball and still gets 98.5% accuracy.
           First attempt: perfect paddle, NO BALL.
  Fix: weight = 1 + 40 × red_channel
       Ball pixels get 41× higher weight in the loss.
       Now dropping the ball is catastrophic to the loss.

TRICK 2 — Deterministic code (z = mu, no sampling):
  Problem: If z is a RANDOM sample around mu, the same frame gets
           a different code each time. Network M can only predict codes
           as accurately as V computes them → noisy codes → floor on accuracy.
  Fix: z IS mu. Same frame → same code, always.

TRICK 3 — Decoder noise injection (z = mu + 0.1·noise):
  Problem: At deployment, M predicts codes NEAR real codes, not ON them.
           If decoder only trains at exact codes, it fails on M's predictions.
  Fix: Train decoder with slightly fuzzed codes → learns the neighborhood too.

TRICK 4 — Smoothness loss:
  Problem: V is free to map consecutive frames to far-apart codes.
           Perfectly decodable, but M would need to predict huge code jumps.
           First attempt: code space was a "scattered island" nightmare for M.
  Fix: penalize ||code(t) - code(t+1)||² → consecutive frames → nearby codes.
"""
import time
import torch
import torch.nn as nn
import torch.nn.functional as F
import matplotlib.pyplot as plt

from pong_env import MiniPong
from network_v import VNet, Z
from collect_dataset import frames, actions, EPISODES, T, device, SEED

# ── Initialize model and optimizer ───────────────────────────────────────────
vnet = VNet().to(device)

# Adam optimizer: adapts learning rate per parameter.
# lr=1e-3 (0.001): standard starting point for neural nets.
opt = torch.optim.Adam(vnet.parameters(), lr=1e-3)

# ── Prepare data ──────────────────────────────────────────────────────────────
# Flatten: (200, 120, 32, 32, 3) → (24000, 32, 32, 3)
# All 24,000 frames in one big array for easy indexing.
flat = torch.tensor(frames.reshape(-1, 32, 32, 3))

# Build CONSECUTIVE PAIR indices (needed for the smoothness loss)
# pair_idx[i] = index of frame t
# pair_idx[i]+1 = index of frame t+1 (same episode)
# We SKIP the last frame of each episode (T-1=119) to avoid cross-episode pairs.
pair_idx = torch.tensor([
    e * T + t
    for e in range(EPISODES)
    for t in range(T - 1)   # 0..118, not 119
])
# Result: 200 episodes × 119 pairs = 23,800 valid consecutive pairs

# Mini-batch loader: randomly shuffles 256 pairs per batch.
loader = torch.utils.data.DataLoader(
    torch.utils.data.TensorDataset(pair_idx),
    batch_size=256,
    shuffle=True   # shuffle so batches don't always see same episodes together
)

# ── Training loop ─────────────────────────────────────────────────────────────
print("Training Network V (autoencoder)...")
print("Expected: ~5 min on CPU, ~1 min on GPU")
t0 = time.time()

for epoch in range(20):
    total_loss = 0.0
    for (bi,) in loader:
        # ── Load a batch of consecutive frame pairs ────────────────────────
        x  = flat[bi].to(device)       # frame at time t
        xn = flat[bi + 1].to(device)   # frame at time t+1 (same episode)

        # ── Encode BOTH frames ─────────────────────────────────────────────
        mu, logvar = vnet.encode(x)    # code for current frame
        mun, _     = vnet.encode(xn)   # code for next frame (only for smoothness)

        # ── TRICK 2 + TRICK 3: Deterministic code with decoder noise ──────
        # z = mu is the TRUE code (deterministic: same frame → same code always)
        # We add 0.1·noise ONLY for the decoder — teaches decoder to handle
        # codes that are slightly off (which M's predictions will be).
        # The noise does NOT affect mu — which stays the true, exact code.
        z = mu + 0.1 * torch.randn_like(mu)   # fuzz for decoder training only
        xhat = vnet.decode(z)                  # reconstruct frame from fuzzed code

        # ── TRICK 1: Red-pixel weighting ─────────────────────────────────
        # x[..., :1] = just the red channel of each pixel
        # Ball color: R=1.0 (highest on screen) → weight up to 1 + 40×1.0 = 41.0
        # Background: R≈0.05 → weight ≈ 1 + 40×0.05 = 3.0 (much lower)
        w = 1.0 + 40.0 * x[..., :1]   # weight tensor, same spatial shape as x

        # Binary cross-entropy measures reconstruction accuracy per pixel.
        # reduction="none" = keep per-pixel losses (don't average yet).
        # Multiply by weight, THEN sum and normalize.
        recon = (w * F.binary_cross_entropy(xhat, x, reduction="none")
                 ).sum() / len(x)

        # ── TRICK 4: Smoothness loss ─────────────────────────────────────
        # Penalize large differences between codes of consecutive frames.
        # (mu - mun) = code difference between frame t and frame t+1
        # .sum(1) = sum squared differences across the 12 code dimensions
        # .mean() = average over the batch
        smooth = ((mu - mun) ** 2).sum(1).mean()

        # ── L2 regularization ─────────────────────────────────────────────
        # Small penalty to keep codes near zero → prevents unbounded drift.
        # Without this, codes could slowly grow to very large values.
        l2 = 0.01 * (mu ** 2).sum(1).mean()

        # ── Total loss ────────────────────────────────────────────────────
        loss = recon + 1.0 * smooth + l2

        # ── Gradient step ─────────────────────────────────────────────────
        opt.zero_grad()   # clear gradients from previous batch
        loss.backward()   # compute gradients via backpropagation
        opt.step()        # update network weights

        total_loss += loss.item() * len(x)

    print(f"  epoch {epoch+1:2d}/20  avg_loss = {total_loss/len(flat):8.1f}")

elapsed = time.time() - t0
n_params = sum(p.numel() for p in vnet.parameters())
print(f"\nV trained in {elapsed:.0f}s  ({n_params:,} parameters)")

# ── Evaluate: reconstruct test frames ────────────────────────────────────────
print("\nEvaluating reconstruction quality...")
vnet.eval()
with torch.no_grad():
    # Pick 7 test frames spread across the dataset
    test = flat[5000:24000:2713][:7].to(device)
    mu_test, _ = vnet.encode(test)
    rec = vnet.decode(mu_test)

fig, axes = plt.subplots(2, 7, figsize=(12, 3.6))
for i in range(7):
    axes[0, i].imshow(test[i].cpu()); axes[0, i].axis("off")
    axes[1, i].imshow(rec[i].cpu().clamp(0, 1)); axes[1, i].axis("off")
axes[0, 0].set_title("original frame", loc="left")
axes[1, 0].set_title("redrawn from 12 numbers", loc="left")
fig.suptitle("Network V — 3,072 pixels → 12 numbers → 3,072 pixels", y=1.02)
plt.tight_layout()
plt.savefig("plot_02_v_reconstruction.png", dpi=150, bbox_inches="tight")
plt.show()
print("Saved: plot_02_v_reconstruction.png")
print("\nCheck: Is the ball present in every reconstructed frame? (bottom row)")
print("If YES → redness weighting worked. If NO → try increasing the 40× factor.")

# Save model for use in later pieces
torch.save(vnet.state_dict(), "vnet_checkpoint.pt")
print("Saved: vnet_checkpoint.pt")
