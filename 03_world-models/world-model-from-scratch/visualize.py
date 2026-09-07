"""
visualize.py  —  Beautiful result dashboard for the World Model

Run this AFTER training is complete to get a single summary figure
showing everything: dataset, reconstruction, memory experiment, and dream.

Usage:
    python visualize.py                    # generates world_model_dashboard.png
    python visualize.py --show             # also opens the plot interactively
    python visualize.py --save results/    # save to specific directory
"""
import os
import argparse
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyArrowPatch
import torch
import torch.nn.functional as F

# ─────────────────────────────────────────────────────────────────────────────
# Style
# ─────────────────────────────────────────────────────────────────────────────
DARK_BG   = "#0d1117"
PANEL_BG  = "#161b22"
ACCENT    = "#58a6ff"
GREEN     = "#3fb950"
YELLOW    = "#d29922"
RED       = "#f85149"
TEXT      = "#e6edf3"
SUBTEXT   = "#8b949e"

plt.rcParams.update({
    "figure.facecolor":  DARK_BG,
    "axes.facecolor":    PANEL_BG,
    "axes.edgecolor":    "#30363d",
    "axes.labelcolor":   TEXT,
    "axes.titlecolor":   TEXT,
    "xtick.color":       SUBTEXT,
    "ytick.color":       SUBTEXT,
    "text.color":        TEXT,
    "grid.color":        "#21262d",
    "grid.linestyle":    "--",
    "grid.alpha":        0.6,
    "font.family":       "monospace",
    "figure.dpi":        150,
})


def load_world_model():
    """Load trained V and M from pong_wm.pt."""
    from network_v import VNet
    from network_m import MNet

    if not os.path.exists("pong_wm.pt"):
        raise FileNotFoundError(
            "pong_wm.pt not found. Run training first:\n"
            "  python run_all.py"
        )

    ckpt = torch.load("pong_wm.pt", map_location="cpu")
    vnet = VNet(); vnet.load_state_dict(ckpt["vnet"]); vnet.eval()
    mnet = MNet(); mnet.load_state_dict(ckpt["mnet"]); mnet.eval()
    z_mean = ckpt["z_mean"]
    z_std  = ckpt["z_std"]
    return vnet, mnet, z_mean, z_std


def load_dataset():
    """Load or regenerate the dataset."""
    from collect_dataset import frames, actions, EPISODES, T
    flat = torch.tensor(frames.reshape(-1, 32, 32, 3))
    a1h  = F.one_hot(torch.tensor(actions), num_classes=3).float()
    return frames, actions, flat, a1h, EPISODES, T


def compute_codes(vnet, flat):
    """Encode all frames into 12-dim codes."""
    codes = []
    with torch.no_grad():
        for i in range(0, len(flat), 512):
            mu, _ = vnet.encode(flat[i:i+512])
            codes.append(mu)
    return torch.cat(codes)


def compute_memory_curve(mnet, vnet, flat, a1h, EPISODES, T):
    """Return mean prediction error at each timestep."""
    from network_v import Z
    codes = compute_codes(vnet, flat).view(EPISODES, T, Z)
    z_mean = codes.reshape(-1, Z).mean(0)
    z_std  = codes.reshape(-1, Z).std(0).clamp_min(1e-4)
    zn     = (codes - z_mean) / z_std

    with torch.no_grad():
        delta, _ = mnet(zn[:, :-1], a1h[:, :-1])
        err = ((zn[:, :-1] + delta - zn[:, 1:]) ** 2).mean(-1)  # (EPISODES, T-1)

    return err.mean(0).numpy(), zn, z_mean, z_std


def run_dream(mnet, vnet, zn, z_mean, z_std, warm_ep=3, warm_steps=3, n_steps=20):
    """Run closed-loop dream and return (real_frames, dream_frames)."""
    from pong_env import MiniPong
    from network_v import Z

    # Get real frames for comparison
    env  = MiniPong(seed=42)
    obs  = env.reset()
    real = [obs]
    actions_list = [1]*warm_steps + [2]*5 + [0]*5 + [1]*3 + [2]*4 + [0]*3
    for a in actions_list:
        obs, _ = env.step(a)
        real.append(obs)
    real = np.stack(real[warm_steps:warm_steps+n_steps])

    # Dream
    dreamed = []
    with torch.no_grad():
        _, h = mnet(zn[warm_ep:warm_ep+1, :warm_steps],
                    F.one_hot(torch.zeros(1, warm_steps, dtype=torch.long), 3).float())
        z = zn[warm_ep:warm_ep+1, warm_steps:warm_steps+1]

        for i, a in enumerate(actions_list[warm_steps:warm_steps+n_steps]):
            ah = F.one_hot(torch.tensor([[a]]), num_classes=3).float()
            delta, h = mnet(z, ah, h)
            z = z + delta[:, -1:]
            z_denorm = z[:, 0] * z_std + z_mean
            frame = vnet.decode(z_denorm)[0].numpy()
            dreamed.append(np.clip(frame, 0, 1))

    return real[:n_steps], np.stack(dreamed)


def build_dashboard(save_dir=".", show=False):
    """Build the full results dashboard."""

    print("Loading world model...")
    vnet, mnet, z_mean, z_std = load_world_model()

    print("Loading dataset...")
    frames, actions, flat, a1h, EPISODES, T = load_dataset()

    print("Computing memory experiment...")
    err_curve, zn, z_mean_norm, z_std_norm = compute_memory_curve(
        mnet, vnet, flat, a1h, EPISODES, T
    )

    print("Running dream sequence...")
    real_frames, dream_frames = run_dream(
        mnet, vnet, zn, z_mean, z_std, n_steps=12
    )

    print("Computing reconstructions...")
    test_indices = [500, 3000, 7000, 12000, 18000, 23000]
    test_frames  = flat[test_indices]
    with torch.no_grad():
        mu, _ = vnet.encode(test_frames)
        recons = vnet.decode(mu).numpy()
    originals = test_frames.numpy()

    # ─── Figure layout ────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(20, 14))
    fig.patch.set_facecolor(DARK_BG)

    gs = gridspec.GridSpec(
        4, 1,
        figure=fig,
        hspace=0.45,
        height_ratios=[0.15, 0.30, 0.25, 0.30]
    )

    # ── Panel 0: Title ────────────────────────────────────────────────────────
    ax_title = fig.add_subplot(gs[0])
    ax_title.set_facecolor(DARK_BG)
    ax_title.axis("off")
    ax_title.text(0.5, 0.80, "World Model from Scratch",
                  ha="center", va="center", fontsize=22, fontweight="bold",
                  color=ACCENT, transform=ax_title.transAxes)
    ax_title.text(0.5, 0.35,
                  "Ha & Schmidhuber 2018 · MiniPong 32×32 · V (CNN) + M (GRU) · ~167k parameters",
                  ha="center", va="center", fontsize=11, color=SUBTEXT,
                  transform=ax_title.transAxes)

    # Architecture boxes
    boxes = [
        ("Raw Frame\n3,072 px", RED,    0.12),
        ("V Encoder\nCNN",      ACCENT, 0.28),
        ("Code z\n12 numbers",  GREEN,  0.44),
        ("M (GRU)\nMemory",     YELLOW, 0.60),
        ("Δz pred\nnext code",  YELLOW, 0.76),
        ("V Decoder\nCNN",      ACCENT, 0.88),
    ]
    for label, color, x in boxes:
        ax_title.text(x, -0.08, label,
                      ha="center", va="center", fontsize=8.5,
                      color=color, fontweight="bold",
                      bbox=dict(boxstyle="round,pad=0.4", facecolor=PANEL_BG,
                                edgecolor=color, linewidth=1.5),
                      transform=ax_title.transAxes)

    # ── Panel 1: Reconstruction ───────────────────────────────────────────────
    n_show = len(test_indices)
    gs1 = gridspec.GridSpecFromSubplotSpec(
        2, n_show, subplot_spec=gs[1], wspace=0.05, hspace=0.1
    )
    for i in range(n_show):
        ax_orig = fig.add_subplot(gs1[0, i])
        ax_rec  = fig.add_subplot(gs1[1, i])
        ax_orig.imshow(originals[i].clip(0, 1))
        ax_rec.imshow(recons[i].clip(0, 1))
        ax_orig.axis("off"); ax_rec.axis("off")
        if i == 0:
            ax_orig.set_ylabel("original", color=SUBTEXT, fontsize=9, labelpad=4)
            ax_rec.set_ylabel("from\n12 codes", color=GREEN, fontsize=9, labelpad=4)
    fig.text(0.5, 0.74,
             "Network V: 3,072 pixels → 12 numbers → 3,072 pixels",
             ha="center", fontsize=12, color=TEXT, fontweight="bold")
    fig.text(0.5, 0.717,
             "Each column: same frame, top row = original, bottom = reconstructed from only 12 numbers",
             ha="center", fontsize=9.5, color=SUBTEXT)

    # ── Panel 2: Memory Experiment ─────────────────────────────────────────────
    ax_mem = fig.add_subplot(gs[2])
    steps  = np.arange(1, len(err_curve) + 1)
    show_n = min(15, len(err_curve))

    ax_mem.plot(steps[:show_n], err_curve[:show_n],
                color=ACCENT, lw=2.5, marker="o", ms=5, zorder=3)
    ax_mem.fill_between(steps[:show_n], 0, err_curve[:show_n],
                        alpha=0.15, color=ACCENT)

    # Annotate the cliff
    cliff_t = 2
    ax_mem.axvline(cliff_t, color=GREEN, lw=1.5, ls="--", alpha=0.7)
    ax_mem.text(cliff_t + 0.2, err_curve[:show_n].max() * 0.90,
                "← cliff: velocity\nlearned from 2 frames",
                color=GREEN, fontsize=8.5, va="top")

    ax_mem.axhline(err_curve[0], color=RED, lw=1, ls=":", alpha=0.6)
    ax_mem.text(show_n * 0.75, err_curve[0] * 1.02,
                "t=1: high error\n(velocity unknown)",
                color=RED, fontsize=8.5, va="bottom")

    ax_mem.set_xlabel("Timestep being predicted", fontsize=10)
    ax_mem.set_ylabel("Prediction error (MSE)", fontsize=10)
    ax_mem.set_title(
        "Network M Memory Experiment — error drops sharply after seeing 2 frames",
        fontsize=12, fontweight="bold", color=TEXT, pad=8
    )
    ax_mem.set_xticks(steps[:show_n])
    ax_mem.grid(True)
    ax_mem.set_xlim(0.5, show_n + 0.5)

    e1 = err_curve[0]
    e3 = err_curve[min(2, len(err_curve)-1)]
    fig.text(0.5, 0.385,
             f"Error at t=1: {e1:.3f}  →  Error at t=3: {e3:.3f}  "
             f"(↓{(1-e3/e1)*100:.0f}% drop — memory found velocity in 2 frames)",
             ha="center", fontsize=9.5, color=SUBTEXT)

    # ── Panel 3: Dream ────────────────────────────────────────────────────────
    n_dream = min(12, len(real_frames), len(dream_frames))
    gs3 = gridspec.GridSpecFromSubplotSpec(
        2, n_dream, subplot_spec=gs[3], wspace=0.05, hspace=0.1
    )
    glyph = {0: "←", 1: "·", 2: "→"}
    action_seq = [1]*3 + [2]*5 + [0]*5 + [1]*3 + [2]*4 + [0]*3
    for i in range(n_dream):
        ax_real  = fig.add_subplot(gs3[0, i])
        ax_dream = fig.add_subplot(gs3[1, i])
        ax_real.imshow(real_frames[i].clip(0, 1))
        ax_dream.imshow(dream_frames[i].clip(0, 1))
        ax_real.axis("off"); ax_dream.axis("off")
        a = action_seq[i] if i < len(action_seq) else 1
        ax_real.set_title(f"t={i+1} {glyph[a]}", fontsize=7.5,
                          color=SUBTEXT, pad=2)
        if i == 0:
            ax_real.set_ylabel("real\ngame", color=SUBTEXT, fontsize=9, labelpad=4)
            ax_dream.set_ylabel("dream\n(no engine)", color=YELLOW, fontsize=9, labelpad=4)

    fig.text(0.5, 0.215,
             "The Dream: game engine is OFF — V + M run closed-loop",
             ha="center", fontsize=12, color=TEXT, fontweight="bold")
    fig.text(0.5, 0.192,
             "Paddle responds to every key press  ·  Ball tracks correctly for ~10+ frames  ·  "
             "Drift after ~20 steps = error compounding (the open problem)",
             ha="center", fontsize=9.5, color=SUBTEXT)

    # Save
    os.makedirs(save_dir, exist_ok=True)
    out_path = os.path.join(save_dir, "world_model_dashboard.png")
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=DARK_BG)
    print(f"\nSaved dashboard: {out_path}")

    if show:
        plt.show()

    plt.close()
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", default=".", help="Directory to save dashboard")
    parser.add_argument("--show", action="store_true", help="Show plot interactively")
    args = parser.parse_args()
    build_dashboard(save_dir=args.save, show=args.show)
