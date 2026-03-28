"""
HKAI Podcast — Hardcoded subtitle removal script.

Configured for EP01-EP04 subtitle position (1280x720, subs at ~y=450-555).
Uses STTN inpainting with sub_area to only process the subtitle band.

Usage:
    python run_hkai.py <video_path>
    python run_hkai.py <video_path> --all     # process all .mp4 in same dir
    python run_hkai.py --list <path1> <path2>  # process specific files

Output: <filename>_no_sub.mp4 in the same directory as input.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend'))

# --- Subtitle area for HKAI podcast (1280x720) ---
# Measured from EP01 Part 1: text band at y=470-535, with padding y=450-555
# Format: (ymin, ymax, xmin, xmax)
SUB_AREA = (450, 555, 0, 1280)


def process_video(video_path):
    """Remove hardcoded subtitles from a single video."""
    import config
    from backend.main import SubtitleRemover

    if not os.path.isfile(video_path):
        print(f"File not found: {video_path}")
        return

    print(f"\n{'='*60}")
    print(f"Processing: {os.path.basename(video_path)}")
    print(f"Sub area:   y={SUB_AREA[0]}-{SUB_AREA[1]}, x={SUB_AREA[2]}-{SUB_AREA[3]}")
    print(f"Mode:       {config.MODE.value}")
    print(f"Device:     {config.device}")
    print(f"{'='*60}\n")

    sr = SubtitleRemover(video_path, sub_area=SUB_AREA)
    sr.run()

    out_name = os.path.splitext(video_path)[0] + "_no_sub.mp4"
    if os.path.exists(out_name):
        size_mb = os.path.getsize(out_name) / 1e6
        print(f"\nOutput: {out_name} ({size_mb:.1f} MB)")
    else:
        print(f"\nWarning: Expected output not found at {out_name}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    if sys.argv[1] == "--all":
        if len(sys.argv) < 3:
            print("Usage: python run_hkai.py --all <directory>")
            sys.exit(1)
        directory = sys.argv[2]
        videos = sorted([
            os.path.join(directory, f) for f in os.listdir(directory)
            if f.endswith('.mp4') and '_no_sub' not in f
        ])
        print(f"Found {len(videos)} videos in {directory}")
        for v in videos:
            process_video(v)
    elif sys.argv[1] == "--list":
        for path in sys.argv[2:]:
            process_video(path)
    else:
        process_video(sys.argv[1])


if __name__ == "__main__":
    main()
