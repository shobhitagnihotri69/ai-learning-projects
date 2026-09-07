"""
dream.py  —  PIECE 8: Run the World Model (The Dream)

What this does:
  Turn the game engine OFF.
  Warm up the model on 3 real frames.
  Then loop with NO help from the real game at all:
    1. Player presses a key
    2. M updates its memory and predicts the next code
    3. V decodes the code → a frame (what the player sees)
    4. The PREDICTED code is fed back as next input → repeat

  The model IS the game. It runs entirely in its own imagination.

Why this is hard:
  Each step's prediction is slightly wrong.
  That slightly-wrong code becomes the next step's input.
  Errors compound. After ~20-30 steps, the ball may fade or jump.
  This is THE central open problem of world models (solved in Dreamer V2/V3).

What you'll see:
  - Paddle obeys every key press — forever (simple, deterministic)
  - Ball holds correctly for ~10 steps
  - Ball gradually drifts after ~20-30 steps (error compounding)
  The drift is not a bug — it's the physics of imperfect closed-loop prediction.
"""
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import matplotlib.pyplot as plt

from pong_env import MiniPong
from network_v import VNet, Z
from network_m import MNet, H
from collect_dataset import frames, actions, EPISODES, T, device, SEED

# ── Load trained world model ──────────────────────────────────────────────────
ckpt = torch.load("pong_wm.pt", map_location=device)

vnet = VNet().to(device)
vnet.load_state_dict(ckpt["vnet"])
vnet.eval()

mnet = MNet().to(device)
mnet.load_state_dict(ckpt["mnet"])
mnet.eval()

Z_MEAN = ckpt["z_mean"].to(device)
Z_STD  = ckpt["z_std"].to(device)

print("World model loaded. Game engine will be turned OFF.")

# ── Re-compute normalized codes for warm-up episodes ─────────────────────────
flat = torch.tensor(frames.reshape(-1, 32, 32, 3))
with torch.no_grad():
    zs_list = []
    for i in range(0, len(flat), 4096):
        mu, _ = vnet.encode(flat[i:i+4096].to(device))
        zs_list.append(mu.cpu())
zs_raw = torch.cat(zs_list).view(EPISODES, T, Z)
zs_norm = (zs_raw - Z_MEAN.cpu()) / Z_STD.cpu()
a1h = F.one_hot(torch.tensor(actions), num_classes=3).float()

# ── DEMO 1: One-step prediction (open loop) ──────────────────────────────────
# At every step, M sees the REAL code and predicts the NEXT frame.
# This is still open-loop (not dreaming yet) but shows M is working.
print("\nDemo 1: One-step prediction (real codes in, predicted next frame out)...")

env = MiniPong(seed=8)   # fresh episode, model has never seen this seed
obs = env.reset()
real = [obs]
script = [2]*6 + [0]*7 + [1]*4 + [2]*5   # scripted key sequence: right, left, stay, right
for a in [1, 1] + script:
    obs, _ = env.step(a)
    real.append(obs)

with torch.no_grad():
    real_t = torch.tensor(np.stack(real), dtype=torch.float32).to(device)
    mu, _  = vnet.encode(real_t)
    zt     = (mu - Z_MEAN) / Z_STD   # normalize

    acts  = [1, 1] + script
    a_all = F.one_hot(torch.tensor([acts]), num_classes=3).float().to(device)

    # M predicts changes for all timesteps at once
    delta_seq, _ = mnet(zt[None, :-1], a_all[:, :len(zt)-1])
    znext        = zt[None, :-1] + delta_seq           # predicted next codes
    painted      = vnet.decode(znext[0] * Z_STD + Z_MEAN).cpu().numpy()

offs = 2   # skip 2 warm-up steps (before ball direction is known)
glyph = {0: "←left", 1: "stay", 2: "right→"}
show  = list(range(0, len(script), 3))

fig, axes = plt.subplots(2, len(show), figsize=(13, 4.0))
for i, t in enumerate(show):
    axes[0, i].imshow(np.clip(real[offs+1+t], 0, 1)); axes[0, i].axis("off")
    axes[0, i].set_title(f"t={t+1} · {glyph[script[t]]}", fontsize=8)
    axes[1, i].imshow(np.clip(painted[offs+t], 0, 1)); axes[1, i].axis("off")
fig.text(0.075, 0.72, "what really\nhappened", fontsize=10, ha="right", fontweight="bold")
fig.text(0.075, 0.27, "painted by M\nbefore it happened", fontsize=10, ha="right", fontweight="bold")
fig.suptitle("Demo 1: M paints the NEXT frame before the game shows it", y=0.99)
plt.subplots_adjust(left=0.10, wspace=0.06)
plt.savefig("plot_04_one_step_prediction.png", dpi=150, bbox_inches="tight")
plt.show()
print("Saved: plot_04_one_step_prediction.png")

# ── DEMO 2: Full dream (closed loop — game engine OFF) ────────────────────────
# This is the real deployment. M eats its own predictions.
print("\nDemo 2: Full dream — game engine is OFF, M runs alone...")

def dream(actions_list, warm_ep=2, warm_steps=3):
    """
    Run the world model closed-loop with a given action sequence.
    Returns: list of decoded frames (the "dream")

    ALIGNMENT NOTE: warm-up consumes codes 0..warm_steps-1.
    The first closed-loop input MUST be the real code at index warm_steps.
    If you accidentally start from code warm_steps-1 (already seen by GRU),
    the model's internal time pointer is off by 1 → subtle but real bug.
    """
    with torch.no_grad():
        # Warm up: feed warm_steps real codes to initialize the memory
        _, h = mnet(
            zs_norm[warm_ep:warm_ep+1, :warm_steps].to(device),
            a1h[warm_ep:warm_ep+1, :warm_steps].to(device)
        )
        # Start from the real code at index warm_steps (NOT warm_steps-1)
        z = zs_norm[warm_ep:warm_ep+1, warm_steps:warm_steps+1].to(device)

        out_frames = []
        for act in actions_list:
            ah = F.one_hot(torch.tensor([[act]]), num_classes=3).float().to(device)

            # M predicts code change + updates memory
            delta, h = mnet(z, ah, h)

            # Apply change: z = z + Δz
            z = z + delta[:, -1:]   # note: delta[:, -1:] to keep shape (batch, 1, Z)

            # Decode to pixel frame
            z_denorm = z[:, 0] * Z_STD + Z_MEAN   # undo normalization
            frame    = vnet.decode(z_denorm)[0].cpu()
            out_frames.append(frame)

        return torch.stack(out_frames)   # shape: (n_steps, 32, 32, 3)


# Script: hold right, hold left, then stay
script_dream = [2]*5 + [0]*5 + [1]*4

# Run SAME script through real game (to compare side by side)
env = MiniPong(seed=11)
obs = env.reset()
real_dream = [obs]
for a in [1, 1, 1] + script_dream:   # 3 warm-up steps, then script
    obs, _ = env.step(a)
    real_dream.append(obs)

# Run dream
dreamed = dream(script_dream)

show = list(range(0, len(script_dream), 2))
glyph = {0: "←left", 1: "stay", 2: "right→"}

fig, axes = plt.subplots(2, len(show), figsize=(13, 4.0))
for i, t in enumerate(show):
    axes[0, i].imshow(np.clip(real_dream[4+t], 0, 1)); axes[0, i].axis("off")
    axes[0, i].set_title(f"t={t+1} · {glyph[script_dream[t]]}", fontsize=8)
    axes[1, i].imshow(dreamed[t].clamp(0, 1)); axes[1, i].axis("off")
fig.text(0.075, 0.72, "real game\n(engine ON)", fontsize=10, ha="right", fontweight="bold")
fig.text(0.075, 0.27, "the dream\n(engine OFF)", fontsize=10, ha="right", fontweight="bold")
fig.suptitle("Demo 2: Same keys, two worlds — bottom is the network's IMAGINATION", y=0.99)
plt.subplots_adjust(left=0.10, wspace=0.06)
plt.savefig("plot_05_dream.png", dpi=150, bbox_inches="tight")
plt.show()
print("Saved: plot_05_dream.png")

print("\nWhat to observe:")
print("  ✓ Paddle obeys every key press — correct forever")
print("  ✓ Ball position is correct for first ~10 steps")
print("  ~ Ball gradually drifts after ~20 steps (error compounding)")
print("  → This drift is THE central open problem of world models")
print("  → Solution: train V + M JOINTLY (DreamerV1/V2/V3) — next lecture!")
