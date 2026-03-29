# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Video Subtitle Remover (VSR) v1.1.1 — AI-powered tool to remove hardcoded subtitles from videos and images using inpainting. Supports three inpainting algorithms (STTN, LAMA, ProPainter) with GUI and CLI interfaces.

## Running

```bash
# CLI — process a single video or image
python backend/main.py
# then enter the file path when prompted

# GUI
python gui.py

# HKAI podcast script (preconfigured subtitle area for 1280x720)
python run_hkai.py <video_path>
python run_hkai.py --all <directory>
python run_hkai.py --list <path1> <path2>
```

Output files are written as `<filename>_no_sub.mp4` alongside the input.

## Setup

```bash
# Python 3.11+ required. Install in a virtual environment:
pip install -r requirements.txt
# PyTorch and PaddlePaddle must be installed separately per your GPU setup (see SETUP_GPU.md)
# Docker images available for CUDA 11.8/12.6/12.8 and DirectML
```

Model weights live in `backend/models/` and may need assembly from split files on first run (handled automatically via `fsplit`).

## Architecture

**Entry points:** `backend/main.py` (CLI), `gui.py` (PySimpleGUI), `run_hkai.py` (batch script)

**Core classes in `backend/main.py`:**
- `SubtitleDetect` — PaddleOCR-based text detection, converts Paddle→ONNX for hardware acceleration, extracts per-frame subtitle coordinates
- `SubtitleRemover` — Main orchestrator. Dispatches to mode-specific methods (`sttn_mode()`, `lama_mode()`, `propainter_mode()`), handles frame I/O via OpenCV, audio extraction/merge via FFmpeg

**Inpainting algorithms in `backend/inpaint/`:**
- `sttn_inpaint.py` — STTN: fast, video-optimized, supports skip-detection. Default mode.
- `lama_inpaint.py` — LAMA: per-frame, good for animation. Uses TorchScript models.
- `video_inpaint.py` — ProPainter: RAFT optical flow + recurrent inpainting. High VRAM, best for extreme motion.

**Processing pipeline:** Frame extraction → OCR detection (optional) → Scene split (optional) → Batch inpainting → Video write → FFmpeg audio merge → Cleanup temp files

**Configuration:** `backend/config.py` controls algorithm selection (`MODE`), device detection (CUDA/DirectML/CPU), model paths, and tuning parameters (batch sizes, reference frames, detection thresholds). Parameters in the "可以改" (editable) section are safe to modify.

**Scene detection:** `backend/scenedetect/` is a bundled PySceneDetect fork used to split videos at scene cuts for better inpainting context.

**Utilities:** `backend/tools/` contains mask creation helpers, batch inference tools, video merge, and STTN training scripts.
