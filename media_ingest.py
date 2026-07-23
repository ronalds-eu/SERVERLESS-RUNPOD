"""
Download image/video URLs into ComfyUI's input folder and wire filenames into the workflow.

Used by handler.py (wraps official worker-comfyui). Middleware can send small JSON:

  {
    "workflow": { ... API format ... },
    "images": [
      { "name": "figure1.png", "url": "https://cdn.example/a.png" },
      { "name": "legacy.png", "image": "<base64 or data URI>" }   // still supported
    ],
    "videos": [
      { "name": "ref.mp4", "url": "https://cdn.example/v.mp4" }
    ],
    "media": [
      {
        "type": "image",           // or "video"
        "url": "https://...",
        "name": "figure1.png",     // filename on disk + in Load* nodes
        "node_ids": ["1390"]       // optional: force-set those node inputs
      }
    ],
    "media_bindings": {
      "1390": { "url": "https://...", "type": "image", "name": "figure1.png" },
      "12":   { "url": "https://...", "type": "video", "name": "clip.mp4" }
    }
  }

If the workflow already references name "figure1.png" in LoadImage, downloading
that file into /comfyui/input is enough — node_ids are optional overrides.
"""
from __future__ import annotations

import logging
import mimetypes
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

logger = logging.getLogger("media_ingest")

# ComfyUI input directory (worker-comfyui layout)
COMFY_INPUT_DIR = Path(os.environ.get("COMFY_INPUT_DIR", "/comfyui/input"))
MEDIA_MAX_BYTES = int(os.environ.get("MEDIA_MAX_BYTES", str(500 * 1024 * 1024)))  # 500 MB
MEDIA_TIMEOUT_S = int(os.environ.get("MEDIA_TIMEOUT_S", "120"))

IMAGE_CLASS_TYPES = {
    "LoadImage",
    "LoadAndResizeImage",
    "LoadImageMask",
    "LoadImageOutput",
}
# input field name(s) that hold the filename
IMAGE_INPUT_KEYS = ("image", "image_path", "file", "filename")

VIDEO_CLASS_TYPES = {
    "VHS_LoadVideo",
    "VHS_LoadVideoPath",
    "VHS_LoadVideoFFmpeg",
    "VHS_LoadVideoFFmpegPath",
    "LoadVideo",
    "LoadVideoUpload",
    "LoadVideoPath",
}
VIDEO_INPUT_KEYS = ("video", "video_path", "file", "path", "filename", "url_or_path")


def _safe_name(name: str) -> str:
    name = (name or "").strip()
    if not name:
        raise ValueError("media item missing 'name'")
    # basename only — no path traversal
    name = Path(name).name
    if not name or name in (".", "..") or "/" in name or "\\" in name:
        raise ValueError(f"invalid media name: {name!r}")
    return name


def _guess_name_from_url(url: str, default: str) -> str:
    path = urlparse(url).path
    base = Path(path).name
    if base and "." in base:
        return _safe_name(base)
    return default


def download_url_to_input(url: str, name: str) -> Path:
    """Stream-download url into Comfy input dir as `name`. Returns absolute path."""
    name = _safe_name(name)
    if not url or not isinstance(url, str):
        raise ValueError(f"invalid url for {name}")
    if not (url.startswith("http://") or url.startswith("https://")):
        raise ValueError(f"only http(s) urls allowed for {name}: {url[:80]}")

    COMFY_INPUT_DIR.mkdir(parents=True, exist_ok=True)
    dest = COMFY_INPUT_DIR / name

    logger.info("Downloading %s -> %s", url[:120], dest)
    with requests.get(url, stream=True, timeout=MEDIA_TIMEOUT_S) as resp:
        resp.raise_for_status()
        # optional content-length check
        cl = resp.headers.get("Content-Length")
        if cl and cl.isdigit() and int(cl) > MEDIA_MAX_BYTES:
            raise ValueError(
                f"{name}: remote file {cl} bytes exceeds MEDIA_MAX_BYTES={MEDIA_MAX_BYTES}"
            )
        written = 0
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                written += len(chunk)
                if written > MEDIA_MAX_BYTES:
                    f.close()
                    dest.unlink(missing_ok=True)
                    raise ValueError(
                        f"{name}: download exceeded MEDIA_MAX_BYTES={MEDIA_MAX_BYTES}"
                    )
                f.write(chunk)

    if written == 0:
        dest.unlink(missing_ok=True)
        raise ValueError(f"{name}: empty download from {url[:80]}")

    logger.info("Saved %s (%d bytes)", dest, written)
    return dest


def _set_node_media_filename(node: dict, name: str, media_type: str) -> bool:
    """Set the filename field on a Load* node. Returns True if patched."""
    if not isinstance(node, dict) or "class_type" not in node:
        return False
    inputs = node.setdefault("inputs", {})
    ct = node.get("class_type") or ""

    if media_type == "image":
        keys = IMAGE_INPUT_KEYS
        if ct not in IMAGE_CLASS_TYPES and not any(k in inputs for k in keys):
            # still try common key
            keys = IMAGE_INPUT_KEYS
    else:
        keys = VIDEO_INPUT_KEYS

    for k in keys:
        if k in inputs or ct in IMAGE_CLASS_TYPES or ct in VIDEO_CLASS_TYPES:
            # Prefer known fields; for matching class types set primary key
            pass

    if media_type == "image":
        if ct in IMAGE_CLASS_TYPES or "image" in inputs:
            inputs["image"] = name
            return True
        for k in IMAGE_INPUT_KEYS:
            if k in inputs:
                inputs[k] = name
                return True
    else:
        if ct in VIDEO_CLASS_TYPES:
            if "video" in inputs or ct.startswith("VHS_LoadVideo"):
                inputs["video"] = name
                return True
            if "path" in inputs:
                # absolute path for Path loaders
                inputs["path"] = str(COMFY_INPUT_DIR / name)
                return True
            if "video_path" in inputs:
                inputs["video_path"] = str(COMFY_INPUT_DIR / name)
                return True
            # default
            inputs["video"] = name
            return True
        for k in VIDEO_INPUT_KEYS:
            if k in inputs:
                if k in ("path", "video_path", "url_or_path"):
                    inputs[k] = str(COMFY_INPUT_DIR / name)
                else:
                    inputs[k] = name
                return True
    return False


def patch_workflow_nodes(
    workflow: dict,
    name: str,
    media_type: str,
    node_ids: list[str] | None,
) -> int:
    """
    Force-set Load* node inputs to `name`.
    If node_ids given, only those nodes; else no-op (caller relies on matching names).
    Returns number of nodes patched.
    """
    if not node_ids:
        return 0
    n = 0
    for nid in node_ids:
        key = str(nid)
        node = workflow.get(key)
        if node is None:
            logger.warning("media node_id %s not in workflow", key)
            continue
        if _set_node_media_filename(node, name, media_type):
            n += 1
            logger.info("Patched node %s (%s) -> %s", key, node.get("class_type"), name)
        else:
            logger.warning(
                "Could not patch node %s class_type=%s for %s",
                key,
                node.get("class_type"),
                media_type,
            )
    return n


def _normalize_item(item: dict, default_type: str) -> dict:
    if not isinstance(item, dict):
        raise ValueError("media item must be an object")
    url = item.get("url")
    name = item.get("name")
    media_type = (item.get("type") or default_type).lower()
    if media_type not in ("image", "video"):
        raise ValueError(f"type must be image|video, got {media_type}")
    if not name and url:
        ext = ".png" if media_type == "image" else ".mp4"
        name = _guess_name_from_url(url, f"media{ext}")
    name = _safe_name(name)
    node_ids = item.get("node_ids") or item.get("nodes")
    if node_ids is not None and not isinstance(node_ids, list):
        node_ids = [node_ids]
    node_ids = [str(x) for x in (node_ids or [])]
    return {
        "url": url,
        "name": name,
        "type": media_type,
        "node_ids": node_ids,
        "image": item.get("image"),  # base64 optional
    }


def collect_media_jobs(job_input: dict) -> list[dict]:
    """Flatten images/videos/media/media_bindings into download jobs."""
    jobs: list[dict] = []

    for item in job_input.get("media") or []:
        jobs.append(_normalize_item(item, item.get("type") or "image"))

    for item in job_input.get("images") or []:
        if not isinstance(item, dict):
            continue
        if item.get("url"):
            jobs.append(_normalize_item({**item, "type": "image"}, "image"))
        # base64-only items are left for stock handler

    for item in job_input.get("videos") or []:
        jobs.append(_normalize_item({**item, "type": "video"}, "video"))

    bindings = job_input.get("media_bindings") or {}
    if isinstance(bindings, dict):
        for nid, spec in bindings.items():
            if not isinstance(spec, dict):
                continue
            media_type = (spec.get("type") or "image").lower()
            name = spec.get("name")
            url = spec.get("url")
            if not name and url:
                ext = ".png" if media_type == "image" else ".mp4"
                name = _guess_name_from_url(url, f"node_{nid}{ext}")
            jobs.append(
                _normalize_item(
                    {
                        "url": url,
                        "name": name,
                        "type": media_type,
                        "node_ids": [str(nid)],
                        "image": spec.get("image"),
                    },
                    media_type,
                )
            )

    return jobs


def enrich_job_input(job_input: Any) -> dict:
    """
    Mutate/return job input:
      - download all URL media into /comfyui/input
      - optional node_id patches on workflow
      - strip URL-only entries from images so stock handler only sees base64 items
      - remove videos/media/media_bindings (already applied)
    """
    if job_input is None:
        raise ValueError("Please provide input")
    if isinstance(job_input, str):
        import json

        job_input = json.loads(job_input)
    if not isinstance(job_input, dict):
        raise ValueError("input must be an object")

    # shallow copy top-level so we don't surprise callers
    out = dict(job_input)
    workflow = out.get("workflow")
    if workflow is None:
        raise ValueError("Missing 'workflow' parameter")
    if not isinstance(workflow, dict):
        raise ValueError("'workflow' must be an object (Comfy API format)")

    media_jobs = collect_media_jobs(out)
    for job in media_jobs:
        url = job.get("url")
        name = job["name"]
        if url:
            download_url_to_input(url, name)
        elif job.get("image") and job["type"] == "image":
            # base64 with explicit node binding only — leave for stock upload,
            # but still patch node names if requested
            pass
        else:
            raise ValueError(f"media {name}: need url (or base64 image for images[])")

        if job.get("node_ids"):
            patch_workflow_nodes(workflow, name, job["type"], job["node_ids"])

    # Keep only base64 images for the stock uploader
    raw_images = out.get("images")
    if raw_images is not None:
        kept = []
        for item in raw_images:
            if not isinstance(item, dict):
                continue
            if item.get("image") and not item.get("url"):
                kept.append({"name": _safe_name(item["name"]), "image": item["image"]})
            elif item.get("image") and item.get("url"):
                # prefer file already on disk from url; skip base64 path
                pass
        out["images"] = kept if kept else None

    # Clean custom keys so stock validate_input is happy
    for k in ("videos", "media", "media_bindings"):
        out.pop(k, None)

    out["workflow"] = workflow
    return out
