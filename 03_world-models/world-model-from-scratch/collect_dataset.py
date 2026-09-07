"""
collect_dataset.py  —  PIECE 2: Collect the Training Dataset

What this does:
  Play 200 episodes of MiniPong with a RANDOM player.
  Record ONLY: (frame, action) at every timestep.
  No labels. No rewards. No ball position. No velocity.
  The world model must discover all of that from pixels alone.

Two critical decisions:
  1. WHY RANDOM PLAYER?
     The world model learns HOW THE WORLD WORKS, not HOW TO WIN.
     Physics (ball bouncing, wall reflections) doesn't care if the player is skilled.
     Random play visits a wide variety of situations — good for learning physics.

  2. WHY HOLD EACH KEY (25% switch rate)?
     At deployment, humans HOLD keys — left for 5 steps, then right for 8.
     If training data only shows rapid key-twitching every step,
     the model never sees "paddle held against left wall for 6 steps straight"
     and will fail exactly in those situations.
     Training distribution must match deployment distribution.
     This ONE LINE fixed a real failure.

Dataset size:
  200 episodes × 120 steps = 24,000 frames
  Each frame = 32×32×3 = 3,072 floats
  Total: ~300 MB in RAM
"""
import math, random, time
import numpy as np
import torch
import matplotlib.pyplot as plt

from pong_env import MiniPong

# ── Reproducibility ──────────────────────────────────────────────────────────
# Same seed = same random weights, same shuffles, same training trajectory.
# This is how the lecture slides can show EXACT numbers like "error at t=1 = 0.094".
SEED = 0
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("device:", device)

# ── Dataset parameters ───────────────────────────────────────────────────────
EPISODES = 200    # number of game episodes to record
T        = 120    # timesteps per episode

# ── Pre-allocate storage arrays ──────────────────────────────────────────────
# Pre-allocating (zeros then fill) is faster than appending in a loop.
# frames[episode, timestep] = 32×32×3 image
# actions[episode, timestep] = integer action (0/1/2)
frames  = np.zeros((EPISODES, T, 32, 32, 3), np.float32)
actions = np.zeros((EPISODES, T), np.int64)

# ── Collect data ─────────────────────────────────────────────────────────────
env = MiniPong(seed=SEED)
rng = np.random.default_rng(SEED)

for e in range(EPISODES):
    obs = env.reset()
    a = int(rng.integers(0, 3))    # pick an initial random action

    for t in range(T):
        # ── KEY HOLD MECHANIC ──────────────────────────────────────────────
        # Only change key with 25% probability each step.
        # On average: hold each key for 4 steps in a row.
        # This mimics how humans play (they press and HOLD, not tap-tap-tap).
        if rng.random() < 0.25:
            a = int(rng.integers(0, 3))

        # Record current (frame, action)
        frames[e, t]  = obs    # store the frame we're ABOUT to act on
        actions[e, t] = a      # store the action we chose

        # Step the environment
        obs, done = env.step(a)
        # Note: we store the frame BEFORE stepping.
        # So frames[e,t] paired with actions[e,t] shows:
        # "given THIS frame, I pressed THIS key, and the world became frames[e,t+1]"

print(f"Dataset collected:")
print(f"  {EPISODES} episodes × {T} steps = {EPISODES*T:,} frames")
print(f"  frames array: {frames.shape}  ({frames.nbytes/1e6:.0f} MB)")
print(f"  actions array: {actions.shape}")

# ── Visualize 8 sample frames ────────────────────────────────────────────────
# Look at these and try to tell which way the ball is moving.
# You CAN'T — and neither can the model from a single frame.
# This is exactly why Network M needs a MEMORY across frames.
fig, axes = plt.subplots(1, 8, figsize=(13, 1.9))
for i in range(8):
    axes[i].imshow(frames[i, i * 13])   # episode i, staggered timestep
    axes[i].axis("off")
fig.suptitle("MiniPong — 8 raw observations. Can you tell ball direction? No. Neither can the model.",
             y=1.12)
plt.tight_layout()
plt.savefig("plot_01_dataset_frames.png", dpi=150, bbox_inches="tight")
plt.show()
print("Saved: plot_01_dataset_frames.png")
