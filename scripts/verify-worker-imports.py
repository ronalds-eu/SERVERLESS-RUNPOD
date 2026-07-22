#!/usr/bin/env python3
"""Fail the Docker build if packages that broke production still fail to import."""
import importlib
import sys
from pathlib import Path

errors = []

for mod in ("cv2", "imageio_ffmpeg", "kornia"):
    try:
        importlib.import_module(mod)
        print(f"OK import {mod}")
    except Exception as e:
        errors.append(f"{mod}: {e}")

try:
    from kornia.geometry.transform.pyramid import pad  # noqa: F401

    print("OK kornia.geometry.transform.pyramid.pad")
except Exception:
    try:
        from kornia.core import pad  # noqa: F401

        print("OK kornia.core.pad (pyramid re-export missing; patch should handle)")
    except Exception as e:
        errors.append(f"kornia pad: {e}")

pb = Path("/comfyui/custom_nodes/ComfyUI-LTXVideo/pyramid_blending.py")
if pb.is_file():
    try:
        compile(pb.read_text(), str(pb), "exec")
        print("OK ComfyUI-LTXVideo/pyramid_blending.py compiles")
    except Exception as e:
        errors.append(f"pyramid_blending compile: {e}")
else:
    errors.append(f"missing {pb}")

vhs = Path("/comfyui/custom_nodes/comfyui-videohelpersuite")
if not vhs.is_dir():
    # alternate clone name
    alt = Path("/comfyui/custom_nodes/ComfyUI-VideoHelperSuite")
    if not alt.is_dir():
        print("WARN: VideoHelperSuite folder not found (may still be ok if unused)")
    else:
        print(f"OK found {alt}")
else:
    print(f"OK found {vhs}")

if errors:
    print("BUILD IMPORT CHECK FAILED:")
    for e in errors:
        print(" -", e)
    sys.exit(1)

print("All critical dependency import checks passed.")
