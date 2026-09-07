"""
app.py - Gradio Web UI for World Model
Hosted on Hugging Face Spaces
"""
import os
import torch
import torch.nn.functional as F
import numpy as np
import gradio as gr
import imageio

# Force CPU
os.environ["CUDA_VISIBLE_DEVICES"] = ""

from network_v import VNet, Z
from network_m import MNet
from collect_dataset import frames, actions, EPISODES, T

print("Loading dataset for warmup frames...")
flat = torch.tensor(frames.reshape(-1, 32, 32, 3))
a1h  = F.one_hot(torch.tensor(actions), num_classes=3).float()

print("Loading trained World Model...")
ckpt = torch.load("pong_wm.pt", map_location="cpu")
vnet = VNet()
vnet.load_state_dict(ckpt["vnet"])
vnet.eval()

mnet = MNet()
mnet.load_state_dict(ckpt["mnet"])
mnet.eval()

Z_MEAN = ckpt["z_mean"]
Z_STD  = ckpt["z_std"]

# Pre-compute codes for episode 5 (used as warmup)
warm_ep = 5
with torch.no_grad():
    codes = []
    for i in range(0, len(flat), 512):
        mu, _ = vnet.encode(flat[i:i+512])
        codes.append(mu)
    codes = torch.cat(codes).view(EPISODES, T, Z)
    zn = (codes - Z_MEAN) / Z_STD


def generate_dream(action_str):
    """Run closed-loop dream and return path to GIF."""
    action_list = []
    for c in action_str:
        if c == "0": action_list.append(0) # Left
        elif c == "1": action_list.append(1) # Stay
        elif c == "2": action_list.append(2) # Right
    
    if not action_list:
        action_list = [1]*10  # default
        
    warm_steps = 3
    dream_frames = []
    
    with torch.no_grad():
        # Warmup
        _, h = mnet(zn[warm_ep:warm_ep+1, :warm_steps],
                    a1h[warm_ep:warm_ep+1, :warm_steps])
        z = zn[warm_ep:warm_ep+1, warm_steps:warm_steps+1]

        # Dream loop
        for a in action_list:
            ah = F.one_hot(torch.tensor([[a]]), num_classes=3).float()
            delta, h = mnet(z, ah, h)
            z = z + delta[:, -1:]
            
            # Decode
            z_denorm = z[:, 0] * Z_STD + Z_MEAN
            frame = vnet.decode(z_denorm)[0].clamp(0, 1).numpy()
            
            # Convert to uint8 for GIF
            frame_uint8 = (frame * 255).astype(np.uint8)
            
            # Upscale image 4x for better visibility in UI
            frame_large = np.repeat(np.repeat(frame_uint8, 4, axis=0), 4, axis=1)
            dream_frames.append(frame_large)
            
    # Save GIF
    gif_path = "dream.gif"
    imageio.mimsave(gif_path, dream_frames, fps=5)
    return gif_path


# ── Gradio UI ─────────────────────────────────────────────────────────────────
css = """
body { font-family: 'Courier New', Courier, monospace; }
"""

with gr.Blocks(theme=gr.themes.Monochrome(), css=css) as demo:
    gr.Markdown("# 🧠 World Model from Scratch")
    gr.Markdown(
        "This AI learned the physics of a game purely by watching pixels. "
        "**The game engine is turned OFF.** What you are seeing below is the neural network *hallucinating* the game frame-by-frame based on your commands."
    )
    
    with gr.Row():
        with gr.Column():
            gr.Markdown("### 🎮 Controls")
            gr.Markdown("Enter a sequence of numbers to control the paddle:")
            gr.Markdown("- `0` = Move Left\n- `1` = Stay\n- `2` = Move Right")
            action_input = gr.Textbox(
                label="Action Sequence", 
                value="2222220000001111",
                placeholder="e.g. 2220011"
            )
            btn = gr.Button("🔮 Generate Dream", variant="primary")
            
            gr.Markdown(
                "*(Note: Because the model is small (~167k params), the hallucinated ball will begin to drift after ~20 steps!)*"
            )
            
        with gr.Column():
            output_gif = gr.Image(label="AI Hallucinated Game (Engine OFF)")

    btn.click(fn=generate_dream, inputs=action_input, outputs=output_gif)

if __name__ == "__main__":
    demo.launch()
