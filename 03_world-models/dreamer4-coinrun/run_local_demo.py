"""
run_local_demo.py  —  Local visualizer for saved CoinRun rollouts

What this does:
  Loads the pre-saved rollout frames from the rollouts/ directory
  and plays them back side-by-side: real game (left) vs dream (right).

  No GPU needed. No Modal needed. No open-dreamer clone needed.
  Just: pip install -r requirements-local.txt && python run_local_demo.py

This does NOT run the world model live — it shows the SAVED rollouts.
To run the world model live, deploy modal_app.py on Modal and open client.html.

Requirements:
  pip install -r requirements-local.txt
"""
import os
import sys
import glob
import argparse
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import imageio


def list_rollouts(rollouts_dir: str = "rollouts") -> list[str]:
    """Find all rollout video files or frame directories."""
    # Look for MP4 files
    mp4s = sorted(glob.glob(os.path.join(rollouts_dir, "**", "*.mp4"), recursive=True))
    if mp4s:
        return mp4s

    # Look for PNG frame directories
    dirs = []
    for entry in os.scandir(rollouts_dir):
        if entry.is_dir():
            frames = glob.glob(os.path.join(entry.path, "*.png"))
            if frames:
                dirs.append(entry.path)
    return sorted(dirs)


def load_from_mp4(path: str) -> np.ndarray:
    """Load frames from MP4 file. Returns (T, H, W, 3) uint8 array."""
    reader = imageio.get_reader(path)
    frames = [f for f in reader]
    return np.stack(frames, axis=0)


def load_from_dir(path: str) -> np.ndarray:
    """Load frames from a directory of PNGs. Returns (T, H, W, 3) array."""
    pngs = sorted(glob.glob(os.path.join(path, "*.png")))
    if not pngs:
        raise ValueError(f"No PNG files found in {path}")
    frames = [np.array(imageio.imread(p)) for p in pngs]
    return np.stack(frames, axis=0)


def load_rollout(path: str) -> np.ndarray:
    """Load a rollout from either MP4 or PNG directory."""
    if os.path.isfile(path) and path.endswith(".mp4"):
        return load_from_mp4(path)
    elif os.path.isdir(path):
        return load_from_dir(path)
    else:
        raise ValueError(f"Cannot load rollout from: {path}")


def play_rollout(path: str, fps: int = 8, save_gif: str = None):
    """
    Display a rollout as an animation.

    If the rollout has width > 2×height, assumes it's already a side-by-side
    (real | dream) composite. Otherwise shows it as-is.

    Args:
        path:     path to MP4 or PNG directory
        fps:      playback speed in frames per second
        save_gif: if provided, save animation to this .gif file
    """
    print(f"Loading rollout from: {path}")
    frames = load_rollout(path)
    T, H, W, C = frames.shape
    print(f"  {T} frames, {H}×{W}×{C}")

    is_composite = W >= 2 * H
    if is_composite:
        title = f"Dreamer 4 CoinRun — Real (left) vs Dream (right) — {T} frames"
    else:
        title = f"Dreamer 4 CoinRun — {T} frames"

    fig, ax = plt.subplots(figsize=(12 if is_composite else 6, 5))
    ax.axis("off")
    fig.suptitle(title, fontsize=12, y=0.98)

    im = ax.imshow(frames[0], interpolation="nearest")

    def update(t):
        im.set_data(frames[t])
        ax.set_title(f"frame {t+1}/{T}", fontsize=9)
        return [im]

    ani = animation.FuncAnimation(
        fig, update, frames=T, interval=1000 // fps, blit=True, repeat=True
    )

    if save_gif:
        print(f"Saving animation to: {save_gif}")
        writer = animation.PillowWriter(fps=fps)
        ani.save(save_gif, writer=writer)
        print("Saved!")

    plt.tight_layout()
    plt.show()


def show_frame_grid(path: str, n_rows: int = 4, step: int = 4):
    """
    Show a grid of frames sampled from the rollout.
    Useful for quick quality inspection without playing the animation.

    Args:
        path:   path to MP4 or PNG directory
        n_rows: number of rows in the grid
        step:   show every `step`-th frame
    """
    frames = load_rollout(path)
    T, H, W, C = frames.shape

    sampled = frames[::step][:n_rows * 8]  # at most n_rows*8 frames
    n_cols = min(8, len(sampled))
    n_rows_actual = (len(sampled) + n_cols - 1) // n_cols

    fig, axes = plt.subplots(n_rows_actual, n_cols,
                              figsize=(2 * n_cols, 2 * n_rows_actual))
    axes = np.array(axes).flatten()

    for i, frame in enumerate(sampled):
        axes[i].imshow(frame, interpolation="nearest")
        axes[i].set_title(f"t={i * step}", fontsize=7)
        axes[i].axis("off")

    for j in range(len(sampled), len(axes)):
        axes[j].axis("off")

    fig.suptitle(
        f"Dreamer 4 CoinRun — every {step}th frame from {os.path.basename(path)}",
        y=1.01, fontsize=11
    )
    plt.tight_layout()
    plt.savefig("rollout_grid.png", dpi=150, bbox_inches="tight")
    plt.show()
    print("Saved: rollout_grid.png")


def summarize_rollouts(rollouts_dir: str = "rollouts"):
    """Print a summary of all available rollouts."""
    items = list_rollouts(rollouts_dir)
    if not items:
        print(f"No rollouts found in '{rollouts_dir}/'")
        print("Train the world model first (see SETUP.md) or check rollouts/ directory.")
        return

    print(f"\nFound {len(items)} rollout(s) in '{rollouts_dir}/':\n")
    for i, path in enumerate(items):
        try:
            frames = load_rollout(path)
            T, H, W, C = frames.shape
            print(f"  [{i}] {os.path.relpath(path)}  →  {T}×{H}×{W} px")
        except Exception as e:
            print(f"  [{i}] {os.path.relpath(path)}  →  ⚠️ {e}")

    print("\nUsage:")
    print("  python run_local_demo.py --idx 0          # play rollout 0")
    print("  python run_local_demo.py --idx 0 --grid   # show frame grid")
    print("  python run_local_demo.py --idx 0 --save dream.gif")


def main():
    parser = argparse.ArgumentParser(
        description="Local viewer for Dreamer 4 CoinRun rollouts",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--rollouts-dir", default="rollouts",
        help="Directory containing rollout MP4s or frame directories (default: rollouts/)"
    )
    parser.add_argument(
        "--idx", type=int, default=None,
        help="Index of rollout to play (run without --idx to list all)"
    )
    parser.add_argument(
        "--path", type=str, default=None,
        help="Direct path to a rollout MP4 or frame directory"
    )
    parser.add_argument(
        "--fps", type=int, default=8,
        help="Playback speed in frames per second (default: 8)"
    )
    parser.add_argument(
        "--grid", action="store_true",
        help="Show a grid of frames instead of playing animation"
    )
    parser.add_argument(
        "--step", type=int, default=4,
        help="Frame step for grid mode (default: 4, every 4th frame)"
    )
    parser.add_argument(
        "--save", type=str, default=None,
        help="Save animation as GIF to this path"
    )
    args = parser.parse_args()

    # If a direct path is given, use it
    if args.path:
        target = args.path
    elif args.idx is not None:
        items = list_rollouts(args.rollouts_dir)
        if not items:
            print(f"No rollouts found in '{args.rollouts_dir}/'")
            sys.exit(1)
        if args.idx >= len(items):
            print(f"Index {args.idx} out of range (found {len(items)} rollouts)")
            sys.exit(1)
        target = items[args.idx]
    else:
        # No selection — list all rollouts
        summarize_rollouts(args.rollouts_dir)
        return

    if args.grid:
        show_frame_grid(target, step=args.step)
    else:
        play_rollout(target, fps=args.fps, save_gif=args.save)


if __name__ == "__main__":
    main()
