"""
network_m.py  —  PIECE 5: Network M (Memory + Prediction)

What this does:
  Reads the sequence of 12-number codes (from V) + actions over time.
  Maintains a 128-number MEMORY that persists across timesteps.
  Predicts the NEXT code at each step.

The core problem this solves:
  A single frame shows WHERE the ball is, never WHERE IT'S GOING.
  If you give a network ONE code and ask "predict the next code",
  it sees ball at position (10, 8) but has no idea: left? right? up? down?
  Its best guess: "stay put" — which is wrong 100% of the time.

The fix — MEMORY:
  A vector h of 128 numbers that persists across timesteps.
  After seeing code(t=1) and code(t=2):
    Memory holds: "ball moved from (10,8) to (11,9) → velocity = (+1,+1)"
  At t=3, it can now predict: ball will be at approximately (12, 10).
  Nobody programmed "velocity" — the network discovered it was useful.

The updating mechanism — GRU (Gated Recurrent Unit):
  At each step, GRU reads: (old memory h, new code z, action a)
  Two internal "gates" decide:
    - Reset gate:  "How much of old memory to FORGET?"
    - Update gate: "How much to blend old memory vs new input?"
  These gates are LEARNED from data, not hand-coded.
  The GRU learns on its own that keeping position-difference = velocity
  is the most useful thing it can do, because that's what minimizes prediction loss.

Dataflow at each timestep t:
  IN:  memory h(t) + code z(t) + one-hot action a(t)
  GRU: h(t+1) = GRU(h(t), z(t), a(t))      ← memory updated
  HEAD: Δz = head(h(t+1))                   ← predicted CHANGE in code
  OUT: predicted z(t+1) = z(t) + Δz
"""
import torch
import torch.nn as nn
import torch.nn.functional as F

from network_v import Z   # Z=12: code dimension

# ── Memory size ───────────────────────────────────────────────────────────────
H = 128   # 128 numbers in the hidden state (memory)
          # Why 128? Small enough to train fast. Large enough to hold velocity.


class MNet(nn.Module):
    """
    GRU-based memory network that predicts next latent code from current code + action.
    """

    def __init__(self):
        super().__init__()

        # ── NETWORK 1: Memory update (GRU) ──────────────────────────────
        # Input at each step: code z (12 numbers) + one-hot action (3 numbers)
        #   → total input size = Z + 3 = 15
        #
        # Why one-hot action?
        #   Action 0→left: [1, 0, 0]
        #   Action 1→stay: [0, 1, 0]
        #   Action 2→right:[0, 0, 1]
        #   M needs to know what key was pressed! The action changes:
        #   - where the paddle moves
        #   - whether the ball deflects (if contact during bounce)
        #   Encoding as one-hot (not raw integer) treats each action symmetrically.
        #
        # batch_first=True: input shape is (batch, time, features)
        #   instead of (time, batch, features) — matches how we organize data
        self.gru = nn.GRU(Z + 3, H, batch_first=True)

        # ── NETWORK 2: Prediction head ───────────────────────────────────
        # Reads the updated memory (128 numbers) and predicts the code CHANGE.
        # Two layers with ELU activation (similar to ReLU but smooth around 0).
        #
        # WHY PREDICT CHANGE (Δz) INSTEAD OF NEXT CODE (z)?
        #   Residual prediction trick:
        #   If M is uncertain, MSE-optimal answer for "what Δz to predict?" = "0"
        #     → predicted z = current z + 0 = "nothing moved" → ball stays visible
        #   If M predicts raw next code, uncertain answer = dataset average
        #     → "average frame" = smeared invisible ball
        #   Same loss, same data — very different failure mode.
        self.head = nn.Sequential(
            nn.Linear(H, 128),   # 128 memory → 128 hidden
            nn.ELU(),            # non-linearity: max(x, α(eˣ-1))
            nn.Linear(128, Z)    # → 12 predicted code changes (Δz)
        )

    def forward(self, z_seq, a_seq, h0=None):
        """
        z_seq: (batch, T, 12)  — sequence of codes
        a_seq: (batch, T, 3)   — sequence of one-hot actions
        h0:    (1, batch, 128) — initial memory (None = all zeros)

        Returns:
          delta_z: (batch, T, 12) — predicted code CHANGES at each step
          hN:      (1, batch, 128) — final memory state (for continuing the sequence)

        Usage:
          z_next = z_current + delta_z
        """
        # Concatenate code and action along the feature dimension
        # z_seq:  (batch, T, 12)
        # a_seq:  (batch, T,  3)
        # inp:    (batch, T, 15)
        inp = torch.cat([z_seq, a_seq], dim=-1)

        # GRU processes the entire sequence at once
        # out: (batch, T, 128)  — memory state at EVERY timestep
        # hN:  (1, batch, 128)  — memory at the LAST timestep
        out, hN = self.gru(inp, h0)

        # Prediction head: for each timestep's memory → predict code change
        # delta_z: (batch, T, 12)
        delta_z = self.head(out)

        return delta_z, hN


# ── Quick architecture sanity check ──────────────────────────────────────────
if __name__ == "__main__":
    mnet = MNet()
    total = sum(p.numel() for p in mnet.parameters())
    print(f"MNet architecture check:")
    print(f"  Total parameters: {total:,}")
    print(f"  (paper reference: ~73,740)")

    # Test forward pass: batch=4, sequence_length=10
    z_dummy = torch.randn(4, 10, Z)     # 4 sequences of 10 codes
    a_dummy = torch.randn(4, 10, 3)     # 4 sequences of 10 one-hot actions
    delta, hN = mnet(z_dummy, a_dummy)
    print(f"  Input code seq shape:   {z_dummy.shape}")
    print(f"  Output delta_z shape:   {delta.shape}  (should be [4, 10, 12])")
    print(f"  Final memory hN shape:  {hN.shape}     (should be [1, 4, 128])")

    # Test residual prediction
    z_next_predicted = z_dummy + delta
    print(f"  z_next shape:           {z_next_predicted.shape}  (same as input — good)")
    print("  Shapes OK!")
