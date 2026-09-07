# 🧠 World Model from Scratch

> Implementation of **Ha & Schmidhuber 2018 — "World Models"** on MiniPong.  
> A neural network that learns the physics of a Pong game **purely from pixels**, then runs as its own virtual game with the engine turned OFF.

<div align="center">

| Architecture | Parameters | Train Time | Cost |
|:---:|:---:|:---:|:---:|
| V (CNN Autoencoder) + M (GRU) | ~167k | ~10 min CPU | Free |

</div>

---

## What This Is

> *"Can a neural network learn how a world works, just by watching it?"*

Two small networks trained end-to-end on 24,000 frames of MiniPong:

- **Network V** — compresses 3,072 pixels → 12 numbers → reconstructs 3,072 pixels
- **Network M** — reads the 12-number sequence over time, maintains a 128-dim GRU memory, predicts the next 12 numbers

Close the loop → the networks **ARE** the game. Game engine turns OFF.

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Train everything + run dream (one command!)
python run_all.py

# 3. See a beautiful results dashboard
python visualize.py --show

# 4. Test interactively with custom action sequences
python test_model.py --test dream --actions "222200001111"
```

### Fast mode (for testing, ~1 min):
```bash
python run_all.py --quick
```

### Resuming (skip already-done stages):
```bash
python run_all.py --skip-v          # V already trained
python run_all.py --skip-v --skip-m # Only re-run closed-loop + dream
python run_all.py --dream-only       # Just dream with saved model
```

---

## Project Structure

| File | Purpose |
|:---|:---|
| `pong_env.py` | The game: deterministic MiniPong, 32×32, Gaussian ball glow |
| `collect_dataset.py` | Data: 200 episodes × 120 steps = 24,000 frames |
| `network_v.py` | VNet architecture: Conv encoder + 12-dim code + ConvTranspose decoder |
| `train_v.py` | Train V with 4 tricks (redness weighting, decoder noise, smoothness, L2) |
| `network_m.py` | MNet architecture: GRU (128-dim) + residual prediction head |
| `train_m.py` | Train M + memory experiment (the prediction-error cliff at t=3) |
| `closed_loop_finetune.py` | Curriculum fine-tune M on K=5 then K=15 self-fed rollouts |
| `dream.py` | Deploy: game engine OFF — V+M run closed-loop |
| **`run_all.py`** | **One-command pipeline runner with flags** |
| **`visualize.py`** | **Beautiful results dashboard (dark theme)** |
| **`test_model.py`** | **Interactive model testing tool** |

---

## The 4 Tricks in V Training

| Trick | What it does | Why it's needed |
|---|---|---|
| **Red-pixel weighting** (`1 + 40×redness`) | Ball pixels weighted 41× more | Ball is only 15/1024 pixels — plain loss ignores it |
| **Deterministic code** (`z = μ`, no sampling) | Same frame → same code always | M can only predict as precisely as V computes |
| **Decoder noise** (`z = μ + 0.1·noise`) | Decoder trains on slightly-wrong codes | M's predictions land *near* real codes, not exactly on them |
| **Smoothness loss** (`‖code(t) - code(t+1)‖²`) | Consecutive frames → nearby codes | Without this: V scatters codes, M must predict huge jumps |

## The 2 Tricks in M Training

| Trick | What it does | Why it's needed |
|---|---|---|
| **Code normalization** (mean=0, std=1) | All 12 dims contribute equally | Paddle dims dominate loss without this; ball dims ignored |
| **Residual prediction** (predict `Δz`, not `z`) | Uncertain M predicts zero change | "Ball stays visible" beats "average frame" as a failure mode |

---

## Architecture

```
Frame (32×32×3 = 3,072 numbers)
      ↓  V Encoder: Conv(3→16) + Conv(16→32) + Flatten + Linear
Code z (12 numbers)
      ↓  M: GRU(15→128) reads [z, one_hot(action)] sequence
Δz (12 numbers)   ← predicted change
      ↓  z_next = z + Δz
      ↓  V Decoder: Linear + ConvTranspose(32→16) + ConvTranspose(16→3)
Next Frame (32×32×3)   ← fed back as next input (the dream)
```

| Component | Parameters |
|---|---|
| V (encoder + decoder) | 93,787 |
| M (GRU + head) | 73,740 |
| **Total** | **~167,527** |

---

## Results

After ~10 minutes of CPU training:

| Metric | Value |
|---|---|
| V reconstruction PSNR | ~28–32 dB |
| M prediction error at t=1 | ~0.09 (high — velocity unknown) |
| M prediction error at t=3 | ~0.03 (↓67% — velocity learned from 2 frames) |
| Dream stability | ~20–30 steps before ball drifts |

---

## Interactive Testing

```bash
# Test 1: Reconstruction quality + error map
python test_model.py --test recon

# Test 2: Memory experiment plot (the cliff at t=3)
python test_model.py --test memory

# Test 3: Custom dream sequence
python test_model.py --test dream --actions "2222200000011111"
#   2 = press right,  0 = press left,  1 = stay

# Test 4: Visualize what each of the 12 codes encodes
python test_model.py --test codes

# All tests at once
python test_model.py --test all
```

---

## Experiments to Try

1. **Kill the ball:** Change ball color to `[0.2, 0.5, 0.2]` in `pong_env.py` (remove red channel). Retrain V. Ball disappears from reconstructions — redness weighting breaks.
2. **Remove smoothness:** Set `smooth = 0` in `train_v.py`. Code space becomes scattered; M gets ~40% worse.
3. **Skip closed-loop:** Comment out `closed_loop_finetune.py`. Dream collapses in ~5 steps instead of ~25.
4. **Longer dream:** In `dream.py`, make `script_dream` 80 steps. Watch error compound — this IS the open problem.
5. **Bigger memory:** In `network_m.py`, change `H = 128` to `H = 512`. Does the dream last longer?

---

## Paper Reference

**Ha, D. & Schmidhuber, J. (2018). Recurrent World Models Facilitate Policy Evolution.**  
[arxiv.org/abs/1803.10122](https://arxiv.org/abs/1803.10122)


