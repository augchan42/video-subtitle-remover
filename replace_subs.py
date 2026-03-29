"""
Replace subtitle band in a video using frames from a clean reference video.

Instead of AI inpainting, this pastes the subtitle region from a raw (clean)
video onto the subtitled video, with optional color matching.

Usage:
    python replace_subs.py <subtitled_video> <raw_video>
    python replace_subs.py <subtitled_video> <raw_video> --offset 5
    python replace_subs.py <subtitled_video> <raw_video> --no-color-match

Options:
    --offset N        Frame offset if raw video starts earlier/later (default: auto-detect)
    --no-color-match  Skip color correction between videos
    --blend N         Blend margin in pixels for smooth transition (default: 10)
    --sub-area Y1,Y2,X1,X2  Subtitle region (default: 450,555,0,1280 for HKAI)

Output: <filename>_no_sub.mp4 in data/clean/
"""

import sys
import os
import argparse
import cv2
import numpy as np


# HKAI podcast subtitle area (1280x720)
DEFAULT_SUB_AREA = (450, 555, 0, 1280)


def compute_frame_offset(cap_sub, cap_raw, sub_area, max_search=300):
    """Find frame offset between two videos by matching non-subtitle regions."""
    y1, y2, x1, x2 = sub_area
    best_offset = 0
    best_score = float('inf')

    # Read first frame from subtitled video
    cap_sub.set(cv2.CAP_PROP_POS_FRAMES, 0)
    ret, frame_sub = cap_sub.read()
    if not ret:
        return 0

    # Create comparison mask (exclude subtitle area)
    h, w = frame_sub.shape[:2]
    gray_sub = cv2.cvtColor(frame_sub, cv2.COLOR_BGR2GRAY)
    # Use region above subtitles for matching
    region_sub = gray_sub[0:y1, :]

    # Search through raw video frames
    cap_raw.set(cv2.CAP_PROP_POS_FRAMES, 0)
    for i in range(max_search):
        ret, frame_raw = cap_raw.read()
        if not ret:
            break
        gray_raw = cv2.cvtColor(frame_raw, cv2.COLOR_BGR2GRAY)
        region_raw = gray_raw[0:y1, :]

        # Resize if needed
        if region_raw.shape != region_sub.shape:
            region_raw = cv2.resize(region_raw, (region_sub.shape[1], region_sub.shape[0]))

        score = np.mean(np.abs(region_raw.astype(float) - region_sub.astype(float)))
        if score < best_score:
            best_score = score
            best_offset = i

    cap_sub.set(cv2.CAP_PROP_POS_FRAMES, 0)
    cap_raw.set(cv2.CAP_PROP_POS_FRAMES, 0)
    print(f"Auto-detected frame offset: {best_offset} (score: {best_score:.1f})")
    return best_offset


def color_match_strip(strip_raw, frame_sub, sub_area, margin=30):
    """Adjust color of raw strip to match subtitled video's color grading.
    Uses pixels just above the subtitle area as reference."""
    y1, y2, x1, x2 = sub_area
    ref_y1 = max(0, y1 - margin)

    ref_sub = frame_sub[ref_y1:y1, x1:x2].astype(np.float32)
    ref_raw_full = frame_sub.copy()  # we need the raw frame for this
    # We actually need the raw frame's region above subs
    return strip_raw  # placeholder - implemented below


def color_match_frames(frame_raw, frame_sub, sub_area, margin=50):
    """Match raw frame's colors to subtitled frame using area above subtitles."""
    y1, y2, x1, x2 = sub_area
    ref_y1 = max(0, y1 - margin)

    # Reference region above subtitles (should be identical content, different grading)
    ref_sub = frame_sub[ref_y1:y1, x1:x2].astype(np.float64)
    ref_raw = frame_raw[ref_y1:y1, x1:x2].astype(np.float64)

    if ref_sub.size == 0 or ref_raw.size == 0:
        return frame_raw[y1:y2, x1:x2]

    # Per-channel mean/std matching
    strip = frame_raw[y1:y2, x1:x2].astype(np.float64)
    for c in range(3):
        mean_sub = np.mean(ref_sub[:, :, c])
        std_sub = np.std(ref_sub[:, :, c]) + 1e-6
        mean_raw = np.mean(ref_raw[:, :, c])
        std_raw = np.std(ref_raw[:, :, c]) + 1e-6

        strip[:, :, c] = (strip[:, :, c] - mean_raw) * (std_sub / std_raw) + mean_sub

    return np.clip(strip, 0, 255).astype(np.uint8)


def create_blend_mask(h, w, blend_px):
    """Create a vertical gradient mask for smooth blending at top/bottom edges."""
    mask = np.ones((h, w, 1), dtype=np.float32)
    if blend_px <= 0 or blend_px * 2 >= h:
        return mask
    # Top fade
    for i in range(blend_px):
        mask[i, :, :] = i / blend_px
    # Bottom fade
    for i in range(blend_px):
        mask[h - 1 - i, :, :] = i / blend_px
    return mask


def replace_subtitle_band(sub_path, raw_path, sub_area=DEFAULT_SUB_AREA,
                          frame_offset=None, color_match=True, blend_px=10):
    y1, y2, x1, x2 = sub_area

    cap_sub = cv2.VideoCapture(sub_path)
    cap_raw = cv2.VideoCapture(raw_path)

    fps = cap_sub.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap_sub.get(cv2.CAP_PROP_FRAME_COUNT))
    w = int(cap_sub.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap_sub.get(cv2.CAP_PROP_FRAME_HEIGHT))
    raw_total = int(cap_raw.get(cv2.CAP_PROP_FRAME_COUNT))

    print(f"Subtitled video: {total_frames} frames, {w}x{h}, {fps:.1f} fps")
    print(f"Raw video:       {raw_total} frames, "
          f"{int(cap_raw.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap_raw.get(cv2.CAP_PROP_FRAME_HEIGHT))}, "
          f"{cap_raw.get(cv2.CAP_PROP_FPS):.1f} fps")
    print(f"Subtitle area:   y={y1}-{y2}, x={x1}-{x2}")

    # Auto-detect frame offset if not specified
    if frame_offset is None:
        frame_offset = compute_frame_offset(cap_sub, cap_raw, sub_area)
    else:
        print(f"Using manual frame offset: {frame_offset}")

    # Skip to offset in raw video
    if frame_offset > 0:
        cap_raw.set(cv2.CAP_PROP_POS_FRAMES, frame_offset)

    # Setup output
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, 'data', 'clean')
    os.makedirs(output_dir, exist_ok=True)

    base_name = os.path.splitext(os.path.basename(sub_path))[0]
    temp_video = os.path.join(output_dir, f'{base_name}_no_sub_temp.mp4')
    final_output = os.path.join(output_dir, f'{base_name}_no_sub.mp4')

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(temp_video, fourcc, fps, (w, h))

    blend_mask = create_blend_mask(y2 - y1, x2 - x1, blend_px)

    replaced = 0
    passthrough = 0

    for i in range(total_frames):
        ret_sub, frame_sub = cap_sub.read()
        if not ret_sub:
            break

        ret_raw, frame_raw = cap_raw.read()

        if ret_raw:
            # Resize raw frame if different resolution
            raw_h, raw_w = frame_raw.shape[:2]
            if raw_w != w or raw_h != h:
                frame_raw = cv2.resize(frame_raw, (w, h))

            # Get the clean strip from raw video
            if color_match:
                clean_strip = color_match_frames(frame_raw, frame_sub, sub_area)
            else:
                clean_strip = frame_raw[y1:y2, x1:x2]

            # Blend at edges for smooth transition
            original_strip = frame_sub[y1:y2, x1:x2].astype(np.float32)
            clean_float = clean_strip.astype(np.float32)
            blended = (blend_mask * clean_float + (1 - blend_mask) * original_strip)
            frame_sub[y1:y2, x1:x2] = blended.astype(np.uint8)
            replaced += 1
        else:
            # Raw video ran out of frames, pass through as-is
            passthrough += 1

        writer.write(frame_sub)

        if (i + 1) % 500 == 0 or i == total_frames - 1:
            pct = (i + 1) / total_frames * 100
            print(f"Progress: {i+1}/{total_frames} ({pct:.1f}%) - replaced: {replaced}, passthrough: {passthrough}")

    writer.release()
    cap_sub.release()
    cap_raw.release()

    # Merge audio from original subtitled video
    import shutil
    ffmpeg = shutil.which('ffmpeg') or 'ffmpeg'
    audio_cmd = (
        f'{ffmpeg} -y -i "{temp_video}" -i "{sub_path}" '
        f'-c:v copy -c:a aac -map 0:v:0 -map 1:a:0 '
        f'-shortest "{final_output}"'
    )
    print(f"\nMerging audio...")
    ret = os.system(audio_cmd)
    if ret == 0:
        os.remove(temp_video)
        size_mb = os.path.getsize(final_output) / 1e6
        print(f"\nOutput: {final_output} ({size_mb:.1f} MB)")
    else:
        print(f"\nFFmpeg failed. Temp video at: {temp_video}")


def main():
    parser = argparse.ArgumentParser(description='Replace subtitle band using clean reference video')
    parser.add_argument('subtitled', help='Path to subtitled video')
    parser.add_argument('raw', help='Path to raw (clean) video')
    parser.add_argument('--offset', type=int, default=None, help='Frame offset (default: auto-detect)')
    parser.add_argument('--no-color-match', action='store_true', help='Skip color matching')
    parser.add_argument('--blend', type=int, default=10, help='Blend margin pixels (default: 10)')
    parser.add_argument('--sub-area', type=str, default=None,
                        help='Subtitle area as Y1,Y2,X1,X2 (default: 450,555,0,1280)')

    args = parser.parse_args()

    sub_area = DEFAULT_SUB_AREA
    if args.sub_area:
        parts = [int(x) for x in args.sub_area.split(',')]
        sub_area = tuple(parts)

    replace_subtitle_band(
        args.subtitled,
        args.raw,
        sub_area=sub_area,
        frame_offset=args.offset,
        color_match=not args.no_color_match,
        blend_px=args.blend,
    )


if __name__ == '__main__':
    main()
