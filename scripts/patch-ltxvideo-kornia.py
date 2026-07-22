#!/usr/bin/env python3
"""Make ComfyUI-LTXVideo import pad on newer kornia (no re-export on pyramid)."""
from pathlib import Path

p = Path("/comfyui/custom_nodes/ComfyUI-LTXVideo/pyramid_blending.py")
if not p.is_file():
    raise SystemExit(f"missing {p}")

text = p.read_text()
old = """from kornia.geometry.transform.pyramid import (
    PyrUp,
    build_laplacian_pyramid,
    build_pyramid,
    find_next_powerof_two,
    is_powerof_two,
    pad,
)"""
new = """try:
    from kornia.geometry.transform.pyramid import (
        PyrUp,
        build_laplacian_pyramid,
        build_pyramid,
        find_next_powerof_two,
        is_powerof_two,
        pad,
    )
except ImportError:  # newer kornia: pad lives on kornia.core
    from kornia.geometry.transform.pyramid import (
        PyrUp,
        build_laplacian_pyramid,
        build_pyramid,
        find_next_powerof_two,
        is_powerof_two,
    )
    try:
        from kornia.core import pad
    except ImportError:
        from torch.nn.functional import pad
"""

if old in text:
    p.write_text(text.replace(old, new, 1))
    print("patched pyramid_blending.py for kornia pad")
elif "except ImportError" in text and "kornia.core import pad" in text:
    print("already patched")
else:
    print("WARNING: import block changed upstream; leaving as-is")
    # still exit 0 — pin kornia==0.8.1 is the primary fix
