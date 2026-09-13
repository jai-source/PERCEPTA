"""
PERCEPTA Model Download Script
Automatically downloads required YOLO model weights into the models/ directory.

Models downloaded:
  1. yolov8n-pose.pt   — Official Ultralytics body pose (17 keypoints)
  2. yolov8n-face.pt   — Community face detection + 5 facial keypoints
  3. yolov8n.pt        — Official Ultralytics base object detection (fallback)
  4. yolov8n-hand.pt   — Community hand detection (if available)

Usage:
  python scripts/download_models.py
  python scripts/download_models.py --models-dir ./models
"""

import argparse
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

# ─── Model URLs ─────────────────────────────────────────────────────────────

MODELS = {
    # Official Ultralytics — always reliable
    "yolov8n-pose.pt": {
        "url": None,  # Downloaded via ultralytics hub
        "method": "ultralytics",
        "description": "YOLOv8 Nano Pose — 17-keypoint body pose (official)",
        "required": True,
    },
    "yolov8n.pt": {
        "url": None,
        "method": "ultralytics",
        "description": "YOLOv8 Nano — object detection fallback (official)",
        "required": True,
    },
    # Community face model with 5 facial keypoints
    "yolov8n-face.pt": {
        "url": "https://github.com/akanametov/yolo-face/releases/download/1.0.0/yolov8n-face.pt",
        "method": "http",
        "description": "YOLOv8 Nano Face — face detection + 5 facial keypoints (community)",
        "required": False,  # Falls back to pose model if missing
    },
    # Hand detection model
    "yolov8n-hand.pt": {
        "url": "https://rndml-team-cv.obs.ru-moscow-1.hc.sbercloud.ru/datasets/hagrid_v2/models/YOLOv10n_gestures.pt",
        "method": "http",
        "alt_url": None,
        "description": "YOLOv8 Nano Hand — hand detection (community)",
        "required": False,  # Falls back to pose wrist keypoints if missing
    },
}


def print_banner():
    print("\n" + "=" * 60)
    print("  PERCEPTA — Model Download Script")
    print("  Perceptual Computing Interface")
    print("=" * 60 + "\n")


def download_ultralytics(model_name: str, dest_path: Path) -> bool:
    """Download model via ultralytics auto-download mechanism."""
    try:
        from ultralytics import YOLO
        print(f"  → Downloading via Ultralytics Hub: {model_name}")
        # This triggers auto-download to the ultralytics cache, then we copy
        model = YOLO(model_name)
        # Ultralytics downloads to ~/.cache/ultralytics or similar
        # Find the downloaded file and copy to our models dir
        import shutil
        # Try common cache locations
        cache_dirs = [
            Path.home() / ".cache" / "ultralytics" / "hub" / model_name,
            Path.home() / "AppData" / "Roaming" / "Ultralytics" / model_name,
            Path(model_name),  # Sometimes downloads to CWD
        ]
        for cache_path in cache_dirs:
            if cache_path.exists():
                shutil.copy2(cache_path, dest_path)
                print(f"  ✓ Copied from cache: {cache_path}")
                return True

        # If model.pt file created in current dir
        local_pt = Path(model_name)
        if local_pt.exists():
            import shutil
            shutil.move(str(local_pt), str(dest_path))
            return True

        # Check if ultralytics auto-placed it somewhere accessible
        # Just verify the model loads correctly
        print(f"  ✓ Model available via Ultralytics (cached): {model_name}")
        # Create a symlink or reference file
        dest_path.write_text(f"# ultralytics:{model_name}\n# This model is loaded via Ultralytics hub\n")
        return True

    except ImportError:
        print("  ✗ ultralytics package not installed. Run: pip install ultralytics")
        return False
    except Exception as e:
        print(f"  ✗ Ultralytics download failed: {e}")
        return False


def download_http(model_name: str, url: str, dest_path: Path) -> bool:
    """Download model from HTTP URL with progress indicator."""
    print(f"  → Downloading: {url}")

    def progress_hook(block_count, block_size, total_size):
        if total_size > 0:
            downloaded = block_count * block_size
            percent = min(100, downloaded * 100 // total_size)
            mb_downloaded = downloaded / (1024 * 1024)
            mb_total = total_size / (1024 * 1024)
            bar = "█" * (percent // 5) + "░" * (20 - percent // 5)
            print(f"\r  [{bar}] {percent}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)", end="", flush=True)

    try:
        urllib.request.urlretrieve(url, dest_path, reporthook=progress_hook)
        print()  # newline after progress
        print(f"  ✓ Downloaded: {dest_path.name}")
        return True
    except urllib.error.URLError as e:
        print(f"\n  ✗ Download failed: {e}")
        return False
    except Exception as e:
        print(f"\n  ✗ Unexpected error: {e}")
        return False


def verify_model(model_path: Path, model_name: str) -> bool:
    """Basic verification that model file looks valid."""
    if not model_path.exists():
        return False
    size = model_path.stat().st_size
    # Minimum plausible model size: 1MB
    if size < 1_000_000:
        # Might be an ultralytics reference file, not actual weights
        content = model_path.read_text(errors="ignore")
        if "ultralytics:" in content:
            return True  # Will be loaded via hub
        return False
    print(f"  ✓ Verified: {model_name} ({size / (1024*1024):.1f} MB)")
    return True


def main():
    print_banner()

    parser = argparse.ArgumentParser(description="Download PERCEPTA YOLO models")
    parser.add_argument(
        "--models-dir",
        type=str,
        default=str(Path(__file__).parent.parent / "models"),
        help="Directory to save models (default: ../models/)",
    )
    parser.add_argument(
        "--skip-optional",
        action="store_true",
        help="Skip optional/community models, only download required ones",
    )
    args = parser.parse_args()

    models_dir = Path(args.models_dir)
    models_dir.mkdir(parents=True, exist_ok=True)
    print(f"Models directory: {models_dir.resolve()}\n")

    results = {}

    for model_name, info in MODELS.items():
        if args.skip_optional and not info["required"]:
            print(f"⏭  Skipping optional: {model_name}")
            continue

        dest_path = models_dir / model_name
        tag = "REQUIRED" if info["required"] else "OPTIONAL"
        print(f"\n[{tag}] {model_name}")
        print(f"  {info['description']}")

        # Check if already exists
        if verify_model(dest_path, model_name):
            print(f"  → Already present, skipping download.")
            results[model_name] = True
            continue

        # Download
        success = False
        if info["method"] == "ultralytics":
            success = download_ultralytics(model_name, dest_path)
        elif info["method"] == "http" and info.get("url"):
            success = download_http(model_name, info["url"], dest_path)
            # Try alternate URL if primary failed
            if not success and info.get("alt_url"):
                print(f"  → Trying alternate URL...")
                success = download_http(model_name, info["alt_url"], dest_path)

        if not success:
            if info["required"]:
                print(f"  ✗ CRITICAL: Failed to download required model {model_name}")
            else:
                print(f"  ⚠ WARNING: Optional model {model_name} unavailable — will use fallback")
        results[model_name] = success

    # Summary
    print("\n" + "=" * 60)
    print("  Download Summary")
    print("=" * 60)
    all_required_ok = True
    for model_name, success in results.items():
        info = MODELS[model_name]
        tag = "✓" if success else ("✗" if info["required"] else "⚠")
        status = "OK" if success else ("FAILED" if info["required"] else "SKIPPED/FALLBACK")
        print(f"  {tag} {model_name:30s} {status}")
        if info["required"] and not success:
            all_required_ok = False

    print()
    if all_required_ok:
        print("  ✓ All required models ready. PERCEPTA can start.")
    else:
        print("  ✗ Some required models are missing. Please install manually.")
        print("    See README.md for manual download instructions.")
        sys.exit(1)

    print()


if __name__ == "__main__":
    main()
