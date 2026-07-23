"""Download WLASL clips (direct MP4 + YouTube via yt-dlp) and trim to gloss segments."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None  # type: ignore


def is_youtube_url(url: str) -> bool:
    if not url:
        return False
    lower = url.lower()
    return "youtube.com" in lower or "youtu.be" in lower


def youtube_video_key(url: str) -> str | None:
    """Stable cache key for a YouTube source video."""
    if "youtu.be/" in url:
        return url.rstrip("/").split("/")[-1].split("?")[0]
    match = re.search(r"[?&]v=([^&]+)", url)
    return match.group(1) if match else None


def download_youtube(url: str, dest: Path) -> bool:
    """Download YouTube video with yt-dlp."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 10_000:
        return True

    try:
        import yt_dlp
    except ImportError:
        print("Install yt-dlp: pip install yt-dlp")
        return False

    ydl_opts = {
        "format": "best[height<=480][ext=mp4]/best[ext=mp4]/best",
        "outtmpl": str(dest.with_suffix("")),
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4",
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        # yt-dlp may write dest without extension
        if not dest.exists():
            for candidate in dest.parent.glob(dest.stem + ".*"):
                if candidate.suffix in {".mp4", ".mkv", ".webm"}:
                    candidate.rename(dest)
                    break
        return dest.exists() and dest.stat().st_size > 10_000
    except Exception as exc:
        print(f"  yt-dlp failed {url}: {exc}")
        return False


def extract_wlasl_segment(
    source: Path,
    dest: Path,
    frame_start: int,
    frame_end: int,
    fps: float = 25.0,
) -> bool:
    """
    Extract WLASL gloss segment from a source video.

    WLASL frame indices are 1-based at 25 FPS (see WLASL README).
    """
    if cv2 is None:
        raise RuntimeError("opencv required for clip extraction")

    cap = cv2.VideoCapture(str(source))
    if not cap.isOpened():
        return False

    src_fps = cap.get(cv2.CAP_PROP_FPS) or fps
    start_sec = max(0, (frame_start - 1) / fps)
    end_sec = (frame_end / fps) if frame_end and frame_end > 0 else None

    cap.set(cv2.CAP_PROP_POS_MSEC, start_sec * 1000.0)

    dest.parent.mkdir(parents=True, exist_ok=True)
    writer = None
    written = 0
    max_frames = 300

    while written < max_frames:
        ok, frame = cap.read()
        if not ok:
            break
        pos_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
        if end_sec is not None and pos_ms > end_sec * 1000.0:
            break
        if writer is None:
            h, w = frame.shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(str(dest), fourcc, src_fps, (w, h))
        writer.write(frame)
        written += 1

    cap.release()
    if writer:
        writer.release()
    return dest.exists() and dest.stat().st_size > 1000


def prepare_instance_clip(
    inst: dict[str, Any],
    cache_dir: Path,
    raw_dir: Path | None = None,
) -> Path | None:
    """Return path to a per-instance MP4 clip, downloading/trimming as needed."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    clip_id = f"wlasl_{inst['video_id']}"
    clip_path = cache_dir / f"{clip_id}.mp4"
    if clip_path.exists():
        return clip_path

    url = inst.get("url", "")
    frame_start = int(inst.get("frame_start") or 1)
    frame_end = int(inst.get("frame_end") or -1)

    if is_youtube_url(url):
        key = youtube_video_key(url)
        if not key:
            return None
        raw_dir = raw_dir or cache_dir / "raw_youtube"
        raw_dir.mkdir(parents=True, exist_ok=True)
        raw_path = raw_dir / f"{key}.mp4"
        if not download_youtube(url, raw_path):
            return None
        if extract_wlasl_segment(raw_path, clip_path, frame_start, frame_end):
            return clip_path
        return None

    if url.lower().endswith((".mp4", ".mov", ".webm")):
        from signora.data.wlasl import is_direct_video_url
        from urllib.request import Request, urlopen

        if not is_direct_video_url(url):
            return None
        if not clip_path.exists():
            req = Request(url, headers={"User-Agent": "SignOra/0.8"})
            with urlopen(req, timeout=120) as resp:
                clip_path.write_bytes(resp.read())
        return clip_path if clip_path.exists() else None

    return None


def _pose_backend(name: str):
    if name == "ensemble":
        from signora.pose.ensemble import ReferenceEnsemble

        return ReferenceEnsemble()
    if name == "optical_flow":
        from signora.pose.backends.optical_flow import OpticalFlowBackend

        return OpticalFlowBackend()
    from signora.pose.backends.mediapipe_backend import MediaPipeBackend

    backend = MediaPipeBackend()
    if not backend.available():
        from signora.pose.backends.optical_flow import OpticalFlowBackend

        flow = OpticalFlowBackend()
        if flow.available():
            print("MediaPipe unavailable — using optical_flow for WLASL poses")
            return flow
    return backend


def _video_instance_priority(inst: dict[str, Any]) -> tuple[int, str]:
    from signora.data.wlasl import is_direct_video_url

    url = inst.get("url", "")
    if is_youtube_url(url):
        return (0, url)
    if url.startswith("http://"):
        return (1, url)
    if is_direct_video_url(url):
        return (2, url)
    return (9, url)


def build_wlasl_video_pairs(
    metadata_path: Path,
    max_samples: int = 5,
    subset: str = "WLASL100",
    cache_dir: Path | None = None,
    pose_backend: str = "mediapipe",
) -> list[dict[str, Any]]:
    """
    Download WLASL-linked clips (YouTube or direct MP4), extract poses, return training pairs.

    WLASL video is **ASL**; pose backends are general hand/face trackers.
    """
    from signora.data.wlasl import fetch_wlasl_json, iter_instances
    from signora.pose.extractor import synthetic_pose_submission

    data = fetch_wlasl_json(metadata_path)
    instances = iter_instances(data, subset=subset, split="train")
    instances = sorted(instances, key=_video_instance_priority)
    cache_dir = cache_dir or metadata_path.parent / "wlasl_clips"
    backend = _pose_backend(pose_backend)

    pairs: list[dict[str, Any]] = []
    for inst in instances:
        if len(pairs) >= max_samples:
            break

        clip_id = f"wlasl_{inst['video_id']}"
        text = inst["text"]
        try:
            clip_path = prepare_instance_clip(inst, cache_dir=cache_dir)
        except Exception as exc:
            print(f"  skip {clip_id}: download error ({exc})")
            continue

        if clip_path is None:
            print(f"  skip {clip_id}: could not fetch clip ({inst.get('url', '')[:60]})")
            continue

        print(f"  pose {clip_id} ← {clip_path.name}")
        try:
            pose = backend.extract_from_path(str(clip_path), clip_id, stage=2)
        except Exception as exc:
            print(f"  pose failed {clip_id}: {exc}")
            pose = synthetic_pose_submission(clip_id, stage=2, num_frames=24)

        pairs.append({"pose": pose.to_dict(), "text": text})

    return pairs
