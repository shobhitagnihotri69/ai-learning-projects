"""
network_v.py  —  PIECE 3: Network V (Visual Encoder-Decoder / Autoencoder)

What this does:
  Compresses every 32×32×3 frame (3,072 numbers) into a 12-number CODE,
  then reconstructs the full frame from that code alone.

  If reconstruction works → the 12 numbers contain EVERYTHING that matters.
  If it doesn't → something important was lost in compression.

Why compress at all?
  Network M (next piece) needs to PREDICT the next code.
  Predicting 12 numbers is vastly easier than predicting 3,072 pixels.
  This is the central design idea of Ha & Schmidhuber 2018 "World Models".

Architecture:
  ENCODER:
    Conv2d(3→16, kernel=4, stride=2, pad=1)   32×32 → 16×16   detect local shapes
    ReLU
    Conv2d(16→32, kernel=4, stride=2, pad=1)  16×16 → 8×8     detect higher patterns
    ReLU
    Flatten                                    → 2048 numbers
    Linear(2048 → 12)                          → CODE (mu)

  DECODER:
    Linear(12 → 2048)
    Reshape to (32, 8, 8)
    ConvTranspose2d(32→16)                     8×8 → 16×16     upsample
    ReLU
    ConvTranspose2d(16→3)                      16×16 → 32×32   upsample to full frame
    Sigmoid                                    pixels clamped to [0, 1]

Why Convolutions?
  The ball can appear at ANY position. A Conv filter detects "glowing blob"
  regardless of where on the screen it is (translation equivariance).
  A plain Linear layer would need to learn "ball at pixel 100" and
  "ball at pixel 500" as completely separate patterns — very inefficient.
"""
import torch
import torch.nn as nn
import torch.nn.functional as F

# ── Code dimension ────────────────────────────────────────────────────────────
Z = 12   # 12 numbers per frame
         # Why 12? Small enough → M's prediction task is tractable.
         #          Large enough → encodes ball xy, paddle x, velocity vx/vy.


class VNet(nn.Module):
    """
    Autoencoder that maps 32×32×3 frames ↔ 12-number codes.
    Trained simultaneously: encoder learns to compress,
    decoder proves nothing important was lost.
    """

    def __init__(self):
        super().__init__()

        # ── ENCODER: image (32×32×3) → flat vector (2048) ────────────────
        self.enc = nn.Sequential(
            # Layer 1: 3 channels → 16 feature maps, stride=2 halves spatial size
            # Input:  (batch, 3, 32, 32)
            # Output: (batch, 16, 16, 16)
            nn.Conv2d(3, 16, kernel_size=4, stride=2, padding=1),
            nn.ReLU(),    # zero out negatives → adds non-linearity

            # Layer 2: 16 → 32 feature maps, stride=2 halves again
            # Input:  (batch, 16, 16, 16)
            # Output: (batch, 32, 8, 8)
            nn.Conv2d(16, 32, kernel_size=4, stride=2, padding=1),
            nn.ReLU(),

            # Flatten: (batch, 32, 8, 8) → (batch, 2048)
            nn.Flatten()
        )

        # ── BOTTLENECK: flat vector → 12-number code ──────────────────────
        # mu = the actual code we use (deterministic)
        self.mu     = nn.Linear(2048, Z)

        # logvar = log(σ²) — used ONLY in training for noise injection trick
        # At deployment: we always use z = mu (no sampling)
        self.logvar = nn.Linear(2048, Z)

        # ── DECODER: code (12) → image (32×32×3) ─────────────────────────
        # Expand 12 → 2048 first (mirror of encoder bottleneck)
        self.fc = nn.Linear(Z, 2048)

        self.dec = nn.Sequential(
            # Reshape happens OUTSIDE this Sequential (in decode() method)
            # Input after reshape: (batch, 32, 8, 8)

            # Layer 1: upsample 8×8 → 16×16
            nn.ConvTranspose2d(32, 16, kernel_size=4, stride=2, padding=1),
            nn.ReLU(),

            # Layer 2: upsample 16×16 → 32×32
            nn.ConvTranspose2d(16, 3, kernel_size=4, stride=2, padding=1),

            # Sigmoid: forces all pixel values into [0, 1]
            # Without this, outputs could be negative or >1 (invalid pixel values)
            nn.Sigmoid()
        )

    def encode(self, x):
        """
        x: (batch, 32, 32, 3)  — frames in HWC format (height, width, channels)
        Returns: mu (batch, 12), logvar (batch, 12)

        x.permute(0, 3, 1, 2): reorder HWC → CHW
        PyTorch Conv2d REQUIRES channels-first format: (batch, C, H, W)
        Our frames are stored as (batch, H, W, C) — so we permute first.
        """
        h = self.enc(x.permute(0, 3, 1, 2))
        mu     = self.mu(h)
        logvar = self.logvar(h).clamp(-6, 2)   # clamp prevents numerical explosion
        return mu, logvar

    def decode(self, z):
        """
        z: (batch, 12)  — 12-number code
        Returns: (batch, 32, 32, 3)  — reconstructed frame in HWC format

        Steps:
          Linear: 12 → 2048
          view: reshape 2048 → (32 channels × 8 height × 8 width)
          dec: ConvTranspose up to (3 × 32 × 32)
          permute: CHW → HWC for display
        """
        h = self.fc(z).view(-1, 32, 8, 8)   # reshape to spatial format
        return self.dec(h).permute(0, 2, 3, 1)  # CHW → HWC


# ── Quick architecture sanity check ──────────────────────────────────────────
if __name__ == "__main__":
    vnet = VNet()
    total = sum(p.numel() for p in vnet.parameters())
    print(f"VNet architecture check:")
    print(f"  Total parameters: {total:,}")
    print(f"  (paper reference: ~93,787)")

    # Test forward pass
    dummy_frames = torch.randn(4, 32, 32, 3)   # batch of 4 fake frames
    mu, logvar = vnet.encode(dummy_frames)
    print(f"  Input frame shape:  {dummy_frames.shape}")
    print(f"  Encoded code shape: {mu.shape}   (should be [4, 12])")
    rec = vnet.decode(mu)
    print(f"  Decoded frame shape: {rec.shape}  (should be [4, 32, 32, 3])")
    print("  Shapes OK!")
