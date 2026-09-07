"""
pong_env.py  —  PIECE 1: The Game (MiniPong)

What this file does:
  This is the entire game. Only ~100 lines.
  The world model NEVER reads this code — it only watches PIXELS.
  It learns physics purely from images, like a human watching a screen.

Key design choices (both are intentional):
  1. DETERMINISTIC physics — no randomness after reset.
     A predictor can in principle be exact.
     (True randomness would force the model to predict "averages" — a smeared ball)
  2. CONTINUOUS motion with anti-aliased rendering (Gaussian ball glow).
     The ball's sub-pixel position encodes into pixel BRIGHTNESS.
     Nearby states → nearby pixels → nearby codes → easy for M to predict.

The game:
  - 32×32 RGB screen = 3,072 numbers per frame
  - Bright teal paddle at the bottom (controlled by 3 actions: left/stay/right)
  - Glowing yellow ball bouncing off 3 walls and the paddle
  - Ball velocity is INVISIBLE in a single frame → this forces Network M to need memory
"""
import numpy as np


class MiniPong:
    # ── Screen / object sizes ──────────────────────────────────────────────
    SIZE = 32            # 32×32 pixel grid
    ACTIONS = 3          # 0 = paddle left | 1 = stay | 2 = paddle right
    PADDLE_W = 8         # paddle width in pixels
    PADDLE_Y = 29        # paddle row (occupies rows 29–30)
    PADDLE_SPEED = 2     # how many pixels paddle moves per action

    # ── Colors as float RGB arrays (range 0.0 → 1.0) ──────────────────────
    BG     = np.array([0.05, 0.05, 0.08], np.float32)   # near-black background
    WALL   = np.array([0.35, 0.35, 0.40], np.float32)   # grey walls
    PADDLE = np.array([0.20, 0.85, 0.80], np.float32)   # bright TEAL (low red!)
    BALL   = np.array([1.00, 0.85, 0.30], np.float32)   # bright YELLOW (RED=1.0 ← highest!)

    # WHY THESE COLORS?
    # The ball has the highest RED channel (1.0) of ANYTHING on screen.
    # Later in training we use: weight = 1 + 40 × redness
    # This makes the loss care 40× more about ball pixels than background pixels.
    # If we didn't do this, the model would learn "perfect paddle, no ball" —
    # because the ball is only ~15 pixels out of 1,024 and a plain loss ignores it.

    # ── Pre-compute pixel coordinate grids (used in observe() every step) ──
    _YY, _XX = np.mgrid[0:32, 0:32].astype(np.float32)
    # _XX[row, col] = col   (x coordinate of each pixel)
    # _YY[row, col] = row   (y coordinate of each pixel)

    def __init__(self, seed=0):
        self.rng = np.random.default_rng(seed)
        self.reset()

    # ── reset() ─────────────────────────────────────────────────────────────
    def reset(self):
        """Start a new episode. Randomizes starting position and velocity."""
        # Paddle: random horizontal position
        self.px = float(self.rng.integers(6, self.SIZE - 6 - self.PADDLE_W))

        # Ball: random starting position near the TOP of the screen
        self.bx = float(self.rng.uniform(6, self.SIZE - 6))
        self.by = float(self.rng.uniform(4, 12))   # starts near top → travels down

        # Ball velocity: continuous, slightly-less-than-1 px per step
        # WHY NOT INTEGER VELOCITY?
        #   If vx=1 exactly, the ball snaps between integer positions.
        #   Sub-pixel positions (vx=0.73) cause the Gaussian glow brightness
        #   to encode fractional position → nearby states get nearby pixel values
        #   → nearby encoder codes → network M can predict smoothly.
        self.vx = float(self.rng.choice([-1, 1]) * self.rng.uniform(0.55, 0.95))
        self.vy = float(self.rng.uniform(0.55, 0.95))   # always starts going DOWN

        # After reset(): everything is DETERMINISTIC.
        # Same (px, bx, by, vx, vy) → same trajectory forever.
        # No mid-episode randomness. This means a perfect predictor CAN exist.
        self.t = 0
        return self.observe()

    # ── observe() ───────────────────────────────────────────────────────────
    def observe(self):
        """Render current game state as a 32×32×3 float image."""
        # Start with solid background
        img = np.tile(self.BG, (self.SIZE, self.SIZE, 1)).astype(np.float32)

        # Draw 3 walls (top + left + right)
        img[0, :]  = self.WALL   # top wall
        img[:, 0]  = self.WALL   # left wall
        img[:, -1] = self.WALL   # right wall

        # Draw paddle as a solid 8-pixel-wide rectangle (2 pixels tall)
        p = int(round(self.px))
        img[self.PADDLE_Y:self.PADDLE_Y + 2, p:p + self.PADDLE_W] = self.PADDLE

        # Draw ball as a SOFT GAUSSIAN GLOW centered at (bx, by)
        #
        # g[row, col] = 1.5 × exp(- distance² / (2 × 1.15²))
        #
        # For each pixel, compute squared distance from ball center,
        # then apply Gaussian decay. Result: bright at center, fading outward.
        #
        # WHY GAUSSIAN INSTEAD OF SOLID CIRCLE?
        #   A solid circle snaps to pixel grid (integer positions only).
        #   A Gaussian glow encodes sub-pixel position in relative brightness.
        #   Example: ball at bx=5.3 → pixel col=5 is 70% bright, col=6 is 30%.
        #   The encoder learns to read these brightness ratios to extract bx=5.3.
        g = 1.5 * np.exp(
            -(((self._XX - self.bx) ** 2 + (self._YY - self.by) ** 2)
              / (2 * 1.15 ** 2))
        )[..., None]   # add channel dim: shape (32, 32, 1) to broadcast with BALL color

        img = np.clip(img + g * self.BALL, 0.0, 1.0).astype(np.float32)
        return img

    # ── step() ──────────────────────────────────────────────────────────────
    def step(self, action):
        """Apply action, update physics, return (next_frame, episode_done)."""

        # ── PADDLE MOVEMENT ──────────────────────────────────────────
        # action=0 → (0-1)=-1 → move LEFT  by 2px
        # action=1 → (1-1)= 0 → STAY
        # action=2 → (2-1)=+1 → move RIGHT by 2px
        self.px += (action - 1) * self.PADDLE_SPEED
        self.px = float(np.clip(self.px, 1, self.SIZE - 1 - self.PADDLE_W))

        # ── BALL MOVEMENT (continuous) ───────────────────────────────
        self.bx += self.vx
        self.by += self.vy

        # ── WALL BOUNCES (mirror reflections) ───────────────────────
        # Mirror formula: if ball overshot wall by δ, place it δ past wall on other side.
        # Example: ball at bx=1.3 hits left wall at bx=2.0.
        #   overshoot = 2.0 - 1.3 = 0.7
        #   new bx = 2.0 + 0.7 = 2.7  → bx_new = 4.0 - bx_old
        if self.bx < 2.0:                           # left wall
            self.bx = 4.0 - self.bx
            self.vx = abs(self.vx)                  # ensure moving RIGHT
        if self.bx > self.SIZE - 3.0:               # right wall
            self.bx = 2 * (self.SIZE - 3.0) - self.bx
            self.vx = -abs(self.vx)                 # ensure moving LEFT
        if self.by < 2.0:                           # top wall
            self.by = 4.0 - self.by
            self.vy = abs(self.vy)                  # ensure moving DOWN

        # ── PADDLE BOUNCE + DIRECTIONAL DEFLECTION ──────────────────
        if self.vy > 0 and self.by >= self.PADDLE_Y - 1.5:
            # Only bounce if: ball is moving DOWN (vy>0) AND near paddle row
            if self.px - 1 <= self.bx <= self.px + self.PADDLE_W:
                # Ball is horizontally over the paddle → bounce
                self.by = 2 * (self.PADDLE_Y - 1.5) - self.by   # mirror upward
                self.vy = -abs(self.vy)                           # send ball UP

                # KEY PRESSED AT CONTACT BENDS THE BALL
                # This makes the action causally meaningful:
                # "press left at contact → ball goes left"
                # The world model must learn this from pixels alone!
                if action == 0:
                    self.vx = -0.9   # deflect strongly left
                elif action == 2:
                    self.vx = +0.9   # deflect strongly right

        # ── BOTTOM WALL BOUNCE (no death, no respawn) ───────────────
        # WHY NO DEATH?
        #   Death creates variable-length episodes (complicated training).
        #   Respawn would add randomness mid-episode (breaks determinism).
        #   Eternal bouncing keeps the game simple and the world learnable.
        if self.by > self.SIZE - 2.5:
            self.by = 2 * (self.SIZE - 2.5) - self.by
            self.vy = -abs(self.vy)

        self.t += 1
        return self.observe(), self.t >= 120   # episode ends at 120 steps


# ── Quick smoke test (run this file directly to verify) ─────────────────────
if __name__ == "__main__":
    env = MiniPong(seed=0)
    obs = env.reset()
    rng = np.random.default_rng(0)
    n_bounce = 0
    for t in range(240):
        vy_before = env.vy
        obs, done = env.step(int(rng.integers(0, 3)))
        if vy_before > 0 and env.vy < 0:
            n_bounce += 1
    print(f"smoke test OK: 240 steps, {n_bounce} paddle bounces, "
          f"ball at ({env.bx:.1f}, {env.by:.1f}), frame shape {obs.shape}")
