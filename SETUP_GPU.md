# HKAI Podcast — Subtitle Removal on GPU Machine

## Quick Start

```bash
# 1. Clone/copy this folder to GPU machine
# 2. Create venv and install deps
uv venv .venv --python 3.12
source .venv/bin/activate

# 3. Install PyTorch with CUDA
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# 4. Install remaining dependencies
pip install -r requirements.txt matplotlib shapely

# 5. Assemble split model files (one-time)
python -c "
from fsplit.filesplit import Filesplit
import os
fs = Filesplit()
base = 'backend/models'
for d in ['big-lama', 'V4/ch_det', 'video']:
    path = os.path.join(base, d)
    if os.path.exists(os.path.join(path, 'fs_manifest.csv')):
        fs.merge(input_dir=path)
        print(f'Assembled: {d}')
"

# 6. Run on a single video
python run_hkai.py /path/to/video.mp4

# 7. Run on all videos in a directory
python run_hkai.py --all /path/to/videos/

# 8. Run on specific files
python run_hkai.py --list video1.mp4 video2.mp4
```

## What it does

- Removes hardcoded subtitles using STTN AI inpainting
- Only processes the subtitle band (y=450-555 in 720p) — rest of frame untouched
- Output: `<filename>_no_sub.mp4` in same directory

## Config (backend/config.py)

- `MODE = InpaintMode.STTN` — best for real-person video
- `STTN_SKIP_DETECTION = True` — skip OCR detection, use sub_area directly
- `STTN_MAX_LOAD_NUM = 50` — increase if you have lots of VRAM

## Subtitle position

Measured from EP01 Part 1 (1280x720):
- Text band: y=470 to y=535
- With padding: y=450 to y=555 (105px, ~14.5% of frame)
- sub_area format: (ymin, ymax, xmin, xmax) = (450, 555, 0, 1280)

If other episodes have different sub positions, edit `SUB_AREA` in `run_hkai.py`.

## Videos to process

Copy from `hongkongaipodcast-site/data/uploaded/`:
- Hong Kong AI Podcast EP01 Part 1 (Augustin Chan).mp4
- Hong Kong AI Podcast EP01 Part 2 (Augustin Chan).mp4
- Hong Kong AI Podcast EP02 Part 1 (Alexander Payne).mp4
- Hong Kong AI Podcast EP02 Part 2 (Alexander Payne).mp4
- (and any other episodes with hardcoded subs)
