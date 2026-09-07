---
title: World Model from Scratch
emoji: 🧠
colorFrom: indigo
colorTo: blue
sdk: docker
pinned: true
license: mit
short_description: A neural network that dreams a game — game engine is OFF
---

# 🧠 World Model from Scratch

> **The Pong game running below has its engine turned OFF.**  
> A neural network learned the physics of Pong by watching pixels — and is now hallucinating every frame from memory.

## Try It

Enter a sequence of actions using `0` (left), `1` (stay), `2` (right) and watch the network dream the game.

## What's Happening

Two tiny networks (~167k parameters total) were trained on 24,000 frames of MiniPong:

- **Network V** — Compresses each 32×32 frame into 12 numbers and reconstructs it back (CNN autoencoder)
- **Network M** — A GRU that reads those 12 numbers over time and predicts how they change given your action

Once trained, the loop runs with **no game code whatsoever**:

```
Your action → M predicts next latent state → V decodes it to a frame → repeat
```

The ball will start drifting after ~20 steps. That's the model's imagination degrading — which is itself fascinating.

## Results

| Model | Parameters | Train Time | Hardware |
|---|---|---|---|
| V-Net (visual tokenizer) | ~85k | ~5 min | CPU |
| M-Net (memory/dynamics) | ~82k | ~5 min | CPU |

## Based On

Ha & Schmidhuber (2018) — [World Models](https://arxiv.org/abs/1803.10122)

## Source Code

[github.com/shobhitagnihotri69/world-model-from-scratch](https://github.com/shobhitagnihotri69/world-model-from-scratch)
