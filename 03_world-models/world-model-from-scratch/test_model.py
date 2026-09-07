"""
test_model.py  —  Interactively test your trained world model

Run this after training to probe the model in various ways.

Usage:
    python test_model.py --test all        # run all tests
    python test_model.py --test recon      # just reconstruction quality
    python test_model.py --test memory     # just memory experiment
    python test_model.py --test dream      # just dream with custom actions
    python test_model.py --test compare    # side-by-side: real vs dream
    python test_model.py --test codes      # visualize what the 12 codes mean

Examples:
    python test_model.py --test dream --actions "2222220000001111"
    # 2=right, 0=left, 1=stay
"""
import os
import sys
import argparse
import numpy as np
import matplotlib.pyplot as plt
import torch
import torch.nn.functional as F


# ── Load model ────────────────────────────────────────────────────────────────
def load():
    from network_v import VNet
    from network_m import MNet
    if not os.path.exists("pong_wm.pt"):
        print("ERROR: pong_wm.pt not found. Run: python run_all.py")
        sys.exit(1)
    ckpt = torch.load("pong_wm.pt", map_location="cpu")
    vnet = VNet(); vnet.load_state_dict(ckpt["vnet"]); vnet.eval()
    mnet = MNet(); mnet.load_state_dict(ckpt["mnet"]); mnet.eval()
    return vnet, mnet, ckpt["z_mean"], ckpt["z_std"]


def load_dataset():
    from collect_dataset import frames, actions, EPISODES, T
    from network_v import Z
    flat = torch.tensor(frames.reshape(-1, 32, 32, 3))
    a1h  = F.one_hot(torch.tensor(actions), num_classes=3).float()
    return frames, actions, flat, a1h, EPISODES, T


def encode_all(vnet, flat):
    from network_v import Z
    codes = []
    with torch.no_grad():
        for i in range(0, len(flat), 512):
            mu, _ = vnet.encode(flat[i:i+512])
            codes.append(mu)
    return torch.cat(codes)


# ── TEST: Reconstruction quality ──────────────────────────────────────────────
def test_reconstruction(vnet, flat, n=8):
    """Show original vs reconstructed frames at various timesteps."""
    idxs   = np.linspace(0, len(flat)-1, n, dtype=int)
    frames_ = flat[idxs]

    with torch.no_grad():
        mu, _ = vnet.encode(frames_)
        recon  = vnet.decode(mu).clamp(0, 1).numpy()

    # Compute pixel MSE and PSNR
    mse  = ((frames_.numpy() - recon) ** 2).mean(axis=(1, 2, 3))
    psnr = -10 * np.log10(mse + 1e-8)

    fig, axes = plt.subplots(3, n, figsize=(n * 1.9, 5.5))
    fig.patch.set_facecolor("#0d1117")
    for ax in axes.flat: ax.set_facecolor("#0d1117")

    for i in range(n):
        axes[0, i].imshow(frames_[i].numpy())
        axes[0, i].axis("off")
        if i == 0: axes[0, i].set_ylabel("original", color="white", fontsize=9)

        axes[1, i].imshow(recon[i])
        axes[1, i].axis("off")
        axes[1, i].set_title(f"PSNR\n{psnr[i]:.1f}dB", fontsize=7.5, color="#3fb950", pad=2)
        if i == 0: axes[1, i].set_ylabel("reconstructed\n(12 codes)", color="#3fb950", fontsize=9)

        # Error map (amplified)
        diff = np.abs(frames_[i].numpy() - recon[i])
        axes[2, i].imshow(diff * 5, vmin=0, vmax=1, cmap="hot")
        axes[2, i].axis("off")
        if i == 0: axes[2, i].set_ylabel("error × 5", color="#f85149", fontsize=9)

    fig.suptitle(
        f"Network V — Reconstruction Quality  |  Mean PSNR: {psnr.mean():.1f} dB",
        color="white", fontsize=12, fontweight="bold", y=1.01
    )
    plt.tight_layout()
    plt.savefig("test_reconstruction.png", dpi=150, bbox_inches="tight",
                facecolor="#0d1117")
    print(f"Saved: test_reconstruction.png  |  Mean PSNR: {psnr.mean():.1f} dB")
    plt.show()


# ── TEST: Memory experiment ────────────────────────────────────────────────────
def test_memory(mnet, vnet, flat, a1h, EPISODES, T):
    """Plot prediction error vs timestep — the memory cliff."""
    from network_v import Z
    codes = encode_all(vnet, flat).view(EPISODES, T, Z)
    z_mean = codes.reshape(-1, Z).mean(0)
    z_std  = codes.reshape(-1, Z).std(0).clamp_min(1e-4)
    zn     = (codes - z_mean) / z_std

    with torch.no_grad():
        delta, _ = mnet(zn[:, :-1], a1h[:, :-1])
        err = ((zn[:, :-1] + delta - zn[:, 1:]) ** 2).mean(-1).numpy()  # (EPISODES, T-1)

    mean_err = err.mean(0)
    std_err  = err.std(0)

    fig, ax = plt.subplots(figsize=(10, 4.5))
    fig.patch.set_facecolor("#0d1117"); ax.set_facecolor("#161b22")

    steps = np.arange(1, min(16, len(mean_err)) + 1)
    e     = mean_err[:15]
    s     = std_err[:15]

    ax.plot(steps, e, color="#58a6ff", lw=2.5, marker="o", ms=5, zorder=3)
    ax.fill_between(steps, e - s, e + s, alpha=0.15, color="#58a6ff")

    ax.axvline(2.5, color="#3fb950", lw=1.5, ls="--", alpha=0.7)
    ax.text(2.6, e.max() * 0.88,
            "← after 2 frames:\nvelocity known →\nerror drops",
            color="#3fb950", fontsize=9)

    for spine in ax.spines.values(): spine.set_edgecolor("#30363d")
    ax.set_xlabel("Timestep being predicted", color="#8b949e", fontsize=10)
    ax.set_ylabel("Prediction MSE (normalized codes)", color="#8b949e", fontsize=10)
    ax.set_title("Memory Experiment — GRU discovers velocity from position history",
                 color="white", fontsize=12, fontweight="bold")
    ax.set_xticks(steps)
    ax.tick_params(colors="#8b949e")
    ax.grid(True, color="#21262d", ls="--", alpha=0.5)
    ax.set_xlim(0.5, 15.5)

    txt = (f"t=1: {mean_err[0]:.4f}  →  "
           f"t=3: {mean_err[2]:.4f}  →  "
           f"t=10: {mean_err[9]:.4f}  |  "
           f"Drop: {(1-mean_err[2]/mean_err[0])*100:.0f}%")
    ax.set_xlabel(txt + "\n" + "Timestep being predicted", color="#8b949e", fontsize=9)

    plt.tight_layout()
    plt.savefig("test_memory.png", dpi=150, bbox_inches="tight", facecolor="#0d1117")
    print(f"Saved: test_memory.png")
    print(f"  t=1:  {mean_err[0]:.4f}")
    print(f"  t=3:  {mean_err[2]:.4f}  ({(1-mean_err[2]/mean_err[0])*100:.0f}% drop)")
    print(f"  t=10: {mean_err[9]:.4f}")
    plt.show()


# ── TEST: Dream with custom action sequence ────────────────────────────────────
def test_dream(mnet, vnet, z_mean, z_std, action_str="222200001111", warm_ep=5):
    """Run a dream with a custom action string (0=left, 1=stay, 2=right)."""
    from pong_env import MiniPong
    from collect_dataset import frames, actions, EPISODES, T
    from network_v import Z

    # Encode warmup frames
    flat = torch.tensor(frames.reshape(-1, 32, 32, 3))
    codes = encode_all(vnet, flat).view(EPISODES, T, Z)
    Z_MEAN = codes.reshape(-1, Z).mean(0)
    Z_STD  = codes.reshape(-1, Z).std(0).clamp_min(1e-4)
    zn     = (codes - Z_MEAN) / Z_STD
    a1h    = F.one_hot(torch.tensor(actions), num_classes=3).float()

    # Parse action string
    action_list = [int(c) for c in action_str if c in "012"]
    glyph = {0: "←left", 1: "stay·", 2: "right→"}

    # Get real frames for comparison
    env = MiniPong(seed=warm_ep)
    obs = env.reset()
    real = [obs]
    for a in action_list:
        obs, _ = env.step(a)
        real.append(obs)

    # Dream
    dream_frames = []
    with torch.no_grad():
        warm = 3
        _, h = mnet(zn[warm_ep:warm_ep+1, :warm],
                    a1h[warm_ep:warm_ep+1, :warm])
        z = zn[warm_ep:warm_ep+1, warm:warm+1]

        for a in action_list:
            ah = F.one_hot(torch.tensor([[a]]), num_classes=3).float()
            delta, h = mnet(z, ah, h)
            z = z + delta[:, -1:]
            z_d = z[:, 0] * Z_STD + Z_MEAN
            frame = vnet.decode(z_d)[0].clamp(0, 1).numpy()
            dream_frames.append(frame)

    n = len(action_list)
    fig, axes = plt.subplots(2, n, figsize=(max(12, n * 1.6), 4.5))
    fig.patch.set_facecolor("#0d1117")

    for i in range(n):
        for r, (ax, fr) in enumerate(zip([axes[0, i], axes[1, i]],
                                          [real[i+1], dream_frames[i]])):
            ax.imshow(fr.clip(0, 1))
            ax.axis("off")
            ax.set_title(glyph[action_list[i]], fontsize=7,
                         color="#d29922" if r == 1 else "#8b949e", pad=2)
        if i == 0:
            axes[0, i].set_ylabel("real", color="#8b949e", fontsize=9)
            axes[1, i].set_ylabel("dream", color="#d29922", fontsize=9)

    fig.suptitle(
        f'Dream — actions: "{action_str}"  |  0=left  1=stay  2=right',
        color="white", fontsize=11, fontweight="bold", y=1.02
    )
    plt.tight_layout()
    plt.savefig("test_dream.png", dpi=150, bbox_inches="tight", facecolor="#0d1117")
    print(f"Saved: test_dream.png  ({n} steps dreamed)")
    plt.show()


# ── TEST: Visualize what the 12 codes represent ───────────────────────────────
def test_codes(vnet, flat, n_frames=500):
    """Visualize the 12 latent codes and what each one responds to."""
    from network_v import Z
    sample = flat[::max(1, len(flat)//n_frames)][:n_frames]

    with torch.no_grad():
        mu, _ = vnet.encode(sample)

    codes_np = mu.numpy()  # (n_frames, 12)

    fig, axes = plt.subplots(3, 4, figsize=(14, 9))
    fig.patch.set_facecolor("#0d1117")
    fig.suptitle("The 12 Latent Codes — What Each Dimension Encodes",
                 color="white", fontsize=13, fontweight="bold")

    colors = plt.cm.rainbow(np.linspace(0, 1, 12))
    for i in range(12):
        ax = axes[i // 4][i % 4]
        ax.set_facecolor("#161b22")
        vals = codes_np[:, i]
        ax.hist(vals, bins=40, color=colors[i], alpha=0.8, edgecolor="none")
        ax.set_title(f"Code dim {i}  μ={vals.mean():.2f}  σ={vals.std():.2f}",
                     color="white", fontsize=9)
        ax.tick_params(colors="#8b949e", labelsize=7)
        for spine in ax.spines.values(): spine.set_edgecolor("#30363d")
        ax.set_xlabel("value", color="#8b949e", fontsize=8)
        ax.set_ylabel("count", color="#8b949e", fontsize=8)

    plt.tight_layout()
    plt.savefig("test_codes.png", dpi=150, bbox_inches="tight", facecolor="#0d1117")
    print(f"Saved: test_codes.png")
    print(f"Code stats (mean±std per dimension):")
    for i in range(12):
        v = codes_np[:, i]
        print(f"  dim {i:2d}: mean={v.mean():+.3f}  std={v.std():.3f}  "
              f"range=[{v.min():.2f}, {v.max():.2f}]")
    plt.show()


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test",    default="all",
                        choices=["all", "recon", "memory", "dream", "codes"],
                        help="Which test to run")
    parser.add_argument("--actions", default="22222200000011112222",
                        help="Action string for dream test (0=left,1=stay,2=right)")
    args = parser.parse_args()

    print("Loading model...")
    vnet, mnet, z_mean, z_std = load()

    print("Loading dataset...")
    frames, actions, flat, a1h, EPISODES, T = load_dataset()

    run_all = args.test == "all"

    if run_all or args.test == "recon":
        print("\n[TEST] Reconstruction quality")
        test_reconstruction(vnet, flat)

    if run_all or args.test == "memory":
        print("\n[TEST] Memory experiment")
        test_memory(mnet, vnet, flat, a1h, EPISODES, T)

    if run_all or args.test == "dream":
        print(f"\n[TEST] Dream — actions: {args.actions}")
        test_dream(mnet, vnet, z_mean, z_std, action_str=args.actions)

    if run_all or args.test == "codes":
        print("\n[TEST] Latent code analysis")
        test_codes(vnet, flat)

    print("\nAll tests done!")


if __name__ == "__main__":
    main()
