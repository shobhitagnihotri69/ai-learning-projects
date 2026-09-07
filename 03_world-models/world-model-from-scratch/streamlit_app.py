"""
streamlit_app.py — World Model from Scratch
A neural network that learned Pong from pixels. The game engine is OFF.
"""
import os
import torch
import torch.nn.functional as F
import numpy as np
import streamlit as st
import imageio

os.environ["CUDA_VISIBLE_DEVICES"] = ""

from network_v import VNet, Z
from network_m import MNet
from collect_dataset import frames, actions, EPISODES, T

st.set_page_config(
    page_title="World Model from Scratch",
    page_icon="🧠",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #0d1117; }
    .stApp { background-color: #0d1117; }
    h1 { color: #e6edf3 !important; font-family: 'Courier New', monospace !important; }
    h2, h3 { color: #79c0ff !important; }
    p, li, .stMarkdown { color: #8b949e !important; }
    .highlight { 
        background: linear-gradient(90deg, #1f2937, #111827);
        border-left: 3px solid #3b82f6;
        padding: 12px 16px;
        border-radius: 6px;
        color: #e6edf3 !important;
        font-size: 15px;
        margin: 8px 0;
    }
    .metric-box {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
    }
    .metric-val { font-size: 28px; font-weight: bold; color: #3b82f6; }
    .metric-label { font-size: 12px; color: #8b949e; margin-top: 4px; }
    .stButton > button {
        background: linear-gradient(135deg, #3b82f6, #1d4ed8) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: bold !important;
        padding: 10px 24px !important;
    }
    .stTextInput > div > div > input {
        background-color: #161b22 !important;
        color: #e6edf3 !important;
        border: 1px solid #30363d !important;
        border-radius: 6px !important;
        font-family: 'Courier New', monospace !important;
        font-size: 18px !important;
        letter-spacing: 4px !important;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource(show_spinner="Loading world model...")
def load_models():
    flat = torch.tensor(frames.reshape(-1, 32, 32, 3))
    a1h  = F.one_hot(torch.tensor(actions), num_classes=3).float()

    ckpt  = torch.load("pong_wm.pt", map_location="cpu")
    vnet  = VNet(); vnet.load_state_dict(ckpt["vnet"]); vnet.eval()
    mnet  = MNet(); mnet.load_state_dict(ckpt["mnet"]); mnet.eval()

    Z_MEAN = ckpt["z_mean"]
    Z_STD  = ckpt["z_std"]

    with torch.no_grad():
        codes = []
        for i in range(0, len(flat), 512):
            mu, _ = vnet.encode(flat[i:i+512])
            codes.append(mu)
        codes = torch.cat(codes).view(EPISODES, T, Z)
        zn = (codes - Z_MEAN) / Z_STD

    return vnet, mnet, zn, a1h, Z_MEAN, Z_STD

vnet, mnet, zn, a1h, Z_MEAN, Z_STD = load_models()

# ── Sidebar: Model Card ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🧠 Model Card")
    st.markdown("---")

    st.markdown("### What is running?")
    st.markdown("""
Two neural networks trained end-to-end on **24,000 frames** of MiniPong:

| Network | Role | Params |
|---|---|---|
| **V-Net** | Visual tokenizer (CNN autoencoder) | ~85k |
| **M-Net** | Dynamics model (GRU) | ~82k |
| **Total** | — | **~167k** |
""")

    st.markdown("### Architecture")
    st.markdown("""
**V-Net (Visual Tokenizer)**
- Input: 32×32×3 RGB frame
- Encoder: 3× Conv2d → 12-dim latent `z`
- Decoder: 3× ConvTranspose2d → reconstructed frame
- Loss: MSE reconstruction

**M-Net (Memory / Dynamics)**
- Input: latent `z` + one-hot action (3 classes)
- Core: 1-layer GRU, hidden dim 256
- Output: Δz (next latent delta)
- Loss: MSE on next-latent prediction
""")

    st.markdown("### Training")
    st.markdown("""
| | |
|---|---|
| **Data** | 24,000 frames of MiniPong |
| **Hardware** | CPU only |
| **Train time** | ~10 min total |
| **Framework** | PyTorch 2.0 |
| **Checkpoint** | `pong_wm.pt` (662KB) |
""")

    st.markdown("### Inference")
    st.markdown("""
```
1. Warm-up: feed M 3 real frames
   to prime its GRU hidden state
2. For each action you input:
   - M predicts next Δz
   - z = z + Δz
   - V decodes z → 32×32 frame
3. Upscale 8× → display
```
No game engine. No physics code.
Only neural network predictions.
""")

    st.markdown("### Known Limitations")
    st.markdown("""
- Ball drifts after ~20 steps (model's imagination degrading)
- Low resolution (32×32 native)
- Only 3 actions supported (left/stay/right)
""")

    st.markdown("### Paper")
    st.markdown("[Ha & Schmidhuber, 2018 — *World Models*](https://arxiv.org/abs/1803.10122)")

    st.markdown("### Code")
    st.markdown("[github.com/shobhitagnihotri69/world-model-from-scratch](https://github.com/shobhitagnihotri69/world-model-from-scratch)")

    st.markdown("### Author")
    st.markdown("[Shobhit Agnihotri](https://github.com/shobhitagnihotri69)")

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("# 🧠 World Model from Scratch")
st.markdown("""
<div class="highlight">
<b>The game engine below is turned OFF.</b><br>
Two tiny neural networks (~167k parameters total) learned the physics of Pong by watching 24,000 frames of pixel data.
They are now <em>hallucinating</em> the game frame-by-frame — predicting what the next frame should look like
purely from internal state. No game code is running.
</div>
""", unsafe_allow_html=True)

st.markdown("")

# ── Metrics ────────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
for col, val, label in [
    (c1, "167k", "Parameters"),
    (c2, "24,000", "Training Frames"),
    (c3, "~10 min", "Train Time"),
    (c4, "CPU", "Runtime"),
]:
    col.markdown(f"""
    <div class="metric-box">
        <div class="metric-val">{val}</div>
        <div class="metric-label">{label}</div>
    </div>""", unsafe_allow_html=True)

st.markdown("")
st.markdown("---")

# ── How It Works ───────────────────────────────────────────────────────────────
with st.expander("🔍 How does this work?", expanded=False):
    st.markdown("""
**Two networks working together:**

- **Network V** (Visual Tokenizer) — Compresses each 32×32 frame into just 12 numbers using a CNN autoencoder. Reconstruction is near-perfect.
- **Network M** (Memory/Dynamics) — A GRU that reads the 12-number "dream state" over time and predicts how it changes given your action.

**The "dreaming" loop:**
```
1. Warm-up: show M 3 real frames to prime its hidden state
2. For each action you give → M predicts next latent state
3. V decodes that latent back to a 32×32 frame
4. Repeat. Real game: OFF.
```

Because these networks are tiny (~167k params), the ball drifts after ~20 steps.
That's the model's imagination breaking down — which is fascinating in itself.
    """)

st.markdown("")

# ── Controls ───────────────────────────────────────────────────────────────────
st.markdown("### 🎮 Control the Hallucinated Game")
st.markdown("""
Enter a sequence of actions (up to 30). Each digit is one timestep:
- `0` → Move paddle **Left**  
- `1` → **Stay** still  
- `2` → Move paddle **Right**
""")

presets = {
    "🏓 Rally (center)": "1111111111111111",
    "⬅️ All Left": "0000000000000000",
    "➡️ All Right": "2222222222222222",
    "🎲 Mix": "2222110000112222",
    "🌀 Chaos": "2010210210210210",
}

preset_col, _ = st.columns([2, 1])
with preset_col:
    chosen_preset = st.selectbox("Quick presets:", list(presets.keys()), index=0)

action_str = st.text_input(
    "Or enter your own sequence (0, 1, 2):",
    value=presets[chosen_preset],
    max_chars=30
)

generate_btn = st.button("🔮 Dream It", type="primary", use_container_width=True)

# ── Output ─────────────────────────────────────────────────────────────────────
if generate_btn:
    action_list = [int(c) for c in action_str if c in "012"]
    if not action_list:
        st.warning("Enter a sequence of 0s, 1s, and 2s.")
    else:
        with st.spinner(f"Generating {len(action_list)}-step dream..."):
            warm_ep, warm_steps = 5, 3
            dream_frames = []

            with torch.no_grad():
                _, h = mnet(zn[warm_ep:warm_ep+1, :warm_steps],
                            a1h[warm_ep:warm_ep+1, :warm_steps])
                z = zn[warm_ep:warm_ep+1, warm_steps:warm_steps+1]

                for a in action_list:
                    ah = F.one_hot(torch.tensor([[a]]), num_classes=3).float()
                    delta, h = mnet(z, ah, h)
                    z = z + delta[:, -1:]
                    z_denorm = z[:, 0] * Z_STD + Z_MEAN
                    frame = vnet.decode(z_denorm)[0].clamp(0, 1).numpy()
                    frame_uint8 = (frame * 255).astype(np.uint8)
                    frame_large = np.repeat(np.repeat(frame_uint8, 8, axis=0), 8, axis=1)
                    dream_frames.append(frame_large)

        gif_path = "/tmp/dream.gif"
        imageio.mimsave(gif_path, dream_frames, fps=6)

        st.markdown("### 🎞️ Your Dream")
        st.image(gif_path, use_column_width=True, caption=f"{len(action_list)} frames hallucinated by a 167k parameter neural network")
        st.caption("⚠️ Notice the ball start to drift after ~20 steps — that's the model's imagination breaking down.")

        with open(gif_path, "rb") as f:
            st.download_button("⬇️ Download GIF", f, file_name="world_model_dream.gif", mime="image/gif")

st.markdown("---")

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center; color:#8b949e; font-size:13px; padding: 10px 0;">
Based on <a href="https://arxiv.org/abs/1803.10122" target="_blank" style="color:#3b82f6;">Ha & Schmidhuber 2018 "World Models"</a>
&nbsp;·&nbsp;
Built by <a href="https://github.com/shobhitagnihotri69" target="_blank" style="color:#3b82f6;">Shobhit Agnihotri</a>
&nbsp;·&nbsp;
<a href="https://github.com/shobhitagnihotri69/world-model-from-scratch" target="_blank" style="color:#3b82f6;">Source Code ↗</a>
</div>
""", unsafe_allow_html=True)
