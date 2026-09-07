# SETUP.md — How to Run Dreamer 4 on CoinRun

A complete step-by-step guide. The README has the 4 commands; this has everything around them.

---

## Prerequisites

| Requirement | Why |
|---|---|
| Python 3.10 or 3.11 | see note on version split below |
| [Modal account](https://modal.com) (free tier works) | training runs on Modal cloud GPUs |
| ~$150 in Modal credits | full pipeline cost |
| Internet access to GitHub | to clone `open-dreamer` |

> **Python version note**: CoinRun data generation needs `procgen`, which only has wheels up to Python 3.10.
> Training (`open-dreamer`) requires Python 3.11. These run in separate Modal Docker images so your local version doesn't matter — but pick 3.11 locally for IDE tooling.

---

## Step 0 — Environment Setup (local machine, one-time)

```bash
# 1. Install modal and authenticate
pip install modal
modal setup          # opens browser → log in → token saved

# 2. Clone open-dreamer (their terms apply — all-rights-reserved, research only)
git clone https://github.com/next-state/open-dreamer.git
# open-dreamer/ is in .gitignore — stays local only

# 3. Clone this repo (if you haven't)
git clone https://github.com/shobhitagnihotri69/dreamer4-coinrun.git
cd dreamer4-coinrun
```

---

## Step 1 — Verify the environment (smoke test, ~2 min, free)

```bash
# Test that JAX sees the GPU inside Modal's container
modal run modal_dreamer.py::smoke

# Test that procgen and the datagen image work
modal run modal_dreamer.py::datagen_smoke
```

Expected output from `smoke`:
```
jax 0.4.x  jaxlib 0.4.x
devices: [CudaDevice(id=0)]
flax/grain/optax/ott ok
dreamer imports ok
matmul ok: ...
```

If `devices:` shows `[CpuDevice]` → JAX is on CPU → **do NOT proceed**. This means the CUDA base image was used. The `train_img` in `modal_dreamer.py` must use `debian_slim` (not `nvidia/cuda`).

---

## Step 2 — Generate the dataset (~$15, ~45 min)

```bash
modal run --detach modal_dreamer.py::gen_data
```

This fans out 440 Modal CPU containers in parallel, each rolling out 25 CoinRun episodes.
Result: **9.6M frames** in `ArrayRecord` shards on a Modal Volume (`open-dreamer`).

> ⚠️ Their shipped `generate_coinrun_dataset.py` crashes (unknown kwarg to `ShardWriter`)
> and writes msgpack while the reader expects pickle. We rewrote this entirely in `modal_dreamer.py::_gen_shard`.

After it finishes, verify:
```bash
modal run modal_dreamer.py::verify_shards
```
Expected: `VERIFY OK` with `TOTAL FRAMES: ~9,600,000`.

---

## Step 3 — Train the tokenizer (~$6, 1h35m on H100)

```bash
modal run --detach modal_dreamer.py::train_tokenizer --steps 10000 --batch 32
```

This trains a **causal video tokenizer** (MAE encoder-decoder) that compresses 64×64×3 frames into 32 latent vectors of 16 dimensions each.

Target: **PSNR ≥ 38** (we got **40.41**, vs GenieRedux 38.25).

> ℹ️ `n_latents=32` (not the default 512) — CoinRun is 64×64, so 512 latents would EXPAND (not compress) the representation. 32 gives 24× compression.

---

## Step 4 — Compute latent statistics (~$1, 5 min on H100)

```bash
modal run --detach modal_dreamer.py::latent_stats
```

The dynamics model normalizes latents by their per-channel mean and std.
`coinrun.yaml` doesn't define these (they normally come from the Minecraft-only tokenize script).
This step computes them from our trained tokenizer and saves them to the Modal Volume.

Output (example):
```
LATENT_MEAN=[-0.211, -0.127, 0.142, ...]
LATENT_STD=[0.358, 0.413, 0.385, ...]
```

---

## Step 5 — Train dynamics + evaluate (full pipeline, ~$120–$150)

**Option A: Full unattended pipeline (recommended)**
```bash
modal run --detach modal_dreamer.py::pipeline
```
This runs dynamics training (80k steps) → FVD eval → saves rollouts.
Resumable: if the job hits Modal's 24h limit, re-run the same command — it skips completed stages.

**Option B: Train dynamics only**
```bash
modal run --detach modal_dreamer.py::train_dynamics --steps 80000 --batch 16
```

**Option C: Eval only (after training)**
```bash
modal run modal_dreamer.py::eval_only
```

> ⚠️ **Use H200, not H100** for dynamics. H100 OOMs by 26 GiB with batch=16.
> The `pipeline` function already targets H200. Change `train_dynamics` manually if needed.

> ⚠️ **Use single GPU.** We tried 8×H200 data-parallel and hit an NCCL rendezvous deadlock that looked healthy (all workers stuck waiting) while burning $36/hr.

---

## Expected Results

| Metric | Our Result | GenieRedux baseline |
|---|---|---|
| Tokenizer PSNR | **40.41** | 38.25 |
| FVD end-to-end | **32.19** | — |
| FVD tokenizer only | 16.59 | — |
| Rollout length | **144 frames, no collapse** | — |

---

## Architecture Summary

```
Stage 1: Data Engine
  10,000 CoinRun episodes × random-action rollout
  → 9.6M frames in ArrayRecord shards (pickle-serialized)
  Cost: ~$15

Stage 2: Causal Video Tokenizer (MAE)
  Input:  64×64×3 frames (12,288 values)
  Output: 32 latents × 16 dims (512 values) — 24× compression
  Steps:  10,000 | Batch: 32 | GPU: H100 | Time: 1h35m
  Cost: ~$6

Stage 3: Latent Stats
  Compute per-channel mean/std of tokenizer outputs
  Required by dynamics normalization
  Cost: ~$1

Stage 4: Dynamics Transformer (1.57B parameters)
  Input:  sequence of latent frames + action labels
  Output: next-frame latents (action-conditioned)
  Method: flow matching + shortcut forcing (real-time in one phase)
  Steps:  80,000 (phase 1: flow matching | phase 2: shortcut forcing)
  Batch:  16 | GPU: H200 | Time: ~21h
  Cost: ~$120–$150
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `JAX devices: [CpuDevice]` | Base image has `nvidia/cuda` — use `debian_slim` in `modal_dreamer.py` |
| `NCCL deadlock` on multi-GPU | Use single GPU only. Multi-GPU broken for this workload |
| `ShardWriter unknown kwarg` | Use our rewritten `_gen_shard` (not their `generate_coinrun_dataset.py`) |
| `assert cfg.dataset.num_binary_actions == NUM_BINARY_ACTIONS` | Patched at image build — verify with `grep 'patched: action space' open-dreamer/scripts/train_dynamics.py` |
| `ImportError: av` in eval | Patched — `_uv("uv pip install av")` runs before eval |
| Modal 24h job cap | Use `--detach` and the resumable `pipeline` function |
| `decord` 500s on pip install | Patched — removed from `pyproject.toml` at build time |
| `grain` multiprocessing fails | Set `num_workers=0` for standalone scripts |

---

## Cost Breakdown

| Stage | GPU | Time | Cost |
|---|---|---|---|
| Data generation | CPU (440 containers) | ~45 min | ~$15 |
| Tokenizer training | 1×H100 | 1h35m | ~$6 |
| Latent stats | 1×H100 | ~5 min | ~$1 |
| Dynamics training | 1×H200 | ~21h | ~$120 |
| **Total** | | | **~$142** |
