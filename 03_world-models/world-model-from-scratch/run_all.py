"""
run_all.py  —  ONE COMMAND to train and run the entire world model

Usage:
    python run_all.py              # train everything + run dream
    python run_all.py --skip-v    # skip V training (use saved checkpoint)
    python run_all.py --skip-m    # skip M training (use saved checkpoint)
    python run_all.py --dream-only # just run dream.py using saved pong_wm.pt
    python run_all.py --quick     # fast mode: fewer epochs (for testing)

What it does (in order):
  1. Collect 200 episodes of MiniPong data
  2. Train Network V  (autoencoder: 3072 pixels <-> 12 codes)
  3. Train Network M  (GRU memory: predicts next code from sequence)
  4. Fine-tune M in closed loop (curriculum K=5 then K=15)
  5. Run the dream  (game engine OFF, model runs solo)
  6. Save a beautiful summary plot

Total time: ~10 min on CPU, ~2 min on GPU
"""
import argparse
import os
import sys
import time

def header(title: str):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)


def run_step(step_name: str, module_name: str, skip: bool = False):
    """Import and run a pipeline step as a module."""
    if skip:
        print(f"  [SKIP] {step_name}")
        return
    header(step_name)
    t0 = time.time()
    # Run module as __main__ by exec-ing it
    import importlib
    mod = importlib.import_module(module_name)
    elapsed = time.time() - t0
    print(f"\n  Done in {elapsed:.0f}s")


def main():
    parser = argparse.ArgumentParser(
        description="Train the full World Model (Ha & Schmidhuber 2018) on MiniPong",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--skip-v",     action="store_true", help="Skip V training (use vnet_checkpoint.pt)")
    parser.add_argument("--skip-m",     action="store_true", help="Skip M training (use mnet_checkpoint.pt)")
    parser.add_argument("--skip-cl",    action="store_true", help="Skip closed-loop fine-tuning")
    parser.add_argument("--dream-only", action="store_true", help="Only run dream.py (needs pong_wm.pt)")
    parser.add_argument("--quick",      action="store_true", help="Quick mode: fewer epochs for testing")
    args = parser.parse_args()

    if args.dream_only:
        if not os.path.exists("pong_wm.pt"):
            print("ERROR: pong_wm.pt not found. Run full training first.")
            sys.exit(1)
        header("Running Dream")
        os.system("python dream.py")
        return

    # ── Patch epoch counts for quick mode ────────────────────────────────────
    if args.quick:
        print("\n[QUICK MODE] Using reduced epochs: V=5, M=5, CL=3+2")
        import collect_dataset
        import train_v
        import train_m
        import closed_loop_finetune
        # Monkey-patch epoch counts
        train_v.EPOCHS = 5
        train_m.EPOCHS = 5
        closed_loop_finetune.STAGES = [(5, 1e-3, 3), (15, 3e-4, 2)]

    print("\n" + "="*60)
    print("  World Model from Scratch — Full Training Pipeline")
    print("  Paper: Ha & Schmidhuber 2018 'World Models'")
    print("="*60)

    t_total = time.time()

    # Step 1: Collect dataset (always runs — fast, ~5s)
    header("Step 1/5: Collecting Dataset (200 episodes × 120 steps)")
    import collect_dataset  # noqa: F401  (runs on import)
    print(f"  Frames: {collect_dataset.frames.shape}")

    # Step 2: Train V
    if not args.skip_v:
        header("Step 2/5: Training Network V (Autoencoder)")
        print("  3,072 pixels → 12 codes → 3,072 pixels")
        print("  4 tricks: redness weighting, decoder noise, smoothness, L2")
        import train_v  # noqa
    else:
        print("\n  [SKIP] V training — using vnet_checkpoint.pt")
        if not os.path.exists("vnet_checkpoint.pt"):
            print("  ERROR: vnet_checkpoint.pt not found! Remove --skip-v")
            sys.exit(1)

    # Step 3: Train M
    if not args.skip_m:
        header("Step 3/5: Training Network M (GRU Memory + Predictor)")
        print("  Predicts Δz (code change) from sequence of codes + actions")
        print("  Memory experiment: error drops sharply after seeing 2 frames")
        import train_m  # noqa
    else:
        print("\n  [SKIP] M training — using mnet_checkpoint.pt")
        if not os.path.exists("mnet_checkpoint.pt"):
            print("  ERROR: mnet_checkpoint.pt not found! Remove --skip-m")
            sys.exit(1)

    # Step 4: Closed-loop fine-tuning
    if not args.skip_cl:
        header("Step 4/5: Closed-Loop Fine-Tuning")
        print("  Teaching M to handle its OWN predictions as input (not just real codes)")
        print("  Curriculum: K=5 steps → K=15 steps")
        import closed_loop_finetune  # noqa
    else:
        print("\n  [SKIP] Closed-loop fine-tuning")
        if not os.path.exists("pong_wm.pt"):
            # Try to build pong_wm.pt from checkpoints
            import torch
            from network_v import VNet
            from network_m import MNet
            vnet = VNet()
            vnet.load_state_dict(torch.load("vnet_checkpoint.pt", map_location="cpu"))
            mnet_ckpt = torch.load("mnet_checkpoint.pt", map_location="cpu")
            mnet = MNet()
            mnet.load_state_dict(mnet_ckpt["mnet"])
            torch.save({
                "vnet": vnet.state_dict(),
                "mnet": mnet.state_dict(),
                "z_mean": mnet_ckpt["z_mean"],
                "z_std": mnet_ckpt["z_std"],
            }, "pong_wm.pt")
            print("  Built pong_wm.pt from checkpoints.")

    # Step 5: Dream
    header("Step 5/5: Dreaming (Game Engine OFF)")
    print("  V + M run closed-loop with NO help from the real game")
    import dream  # noqa

    # Summary
    total = time.time() - t_total
    header(f"DONE! Total time: {total/60:.1f} minutes")
    print("  Output plots:")
    plots = [
        ("plot_01_dataset_frames.png",     "8 raw frames (can you tell ball direction?)"),
        ("plot_02_v_reconstruction.png",   "V: original vs reconstructed from 12 numbers"),
        ("plot_03_memory_experiment.png",  "M: prediction error vs timestep (the memory cliff)"),
        ("plot_04_one_step_prediction.png","M: one-step prediction vs reality"),
        ("plot_05_dream.png",              "The dream: real vs engine-OFF hallucination"),
    ]
    for fname, desc in plots:
        exists = "✓" if os.path.exists(fname) else "✗"
        print(f"  {exists} {fname}")
        print(f"      → {desc}")

    print("\n  Model checkpoints:")
    for f in ["vnet_checkpoint.pt", "mnet_checkpoint.pt", "pong_wm.pt"]:
        exists = "✓" if os.path.exists(f) else "✗"
        print(f"  {exists} {f}")

    print("\n  To run JUST the dream again (fast):")
    print("    python run_all.py --dream-only")
    print("\n  To retrain only M (e.g., after tuning hyperparams):")
    print("    python run_all.py --skip-v")


if __name__ == "__main__":
    main()
