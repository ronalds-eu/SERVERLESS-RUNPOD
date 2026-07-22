#!/usr/bin/env python3
"""
List ComfyUI node types (and package hints) from a workflow JSON.

Supports:
  - UI export: { "nodes": [ { "type": "...", "properties": { "cnr_id": "..." } } ] }
  - API format: { "1": { "class_type": "...", "inputs": {} } }
  - RunPod body: { "input": { "workflow": { ... API format ... } } }

Usage:
  python scripts/analyze-workflow-deps.py path/to/workflow.json
  python scripts/analyze-workflow-deps.py a.json b.json --map

--map prints a suggested install list from a small built-in table (extend as needed).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

# Node type / class_type prefix → install hint for worker image
# Extend this when you adopt new custom node packs.
KNOWN_PACKS: dict[str, dict[str, str]] = {
    # Comfy registry id (cnr_id) or folder-style name
    "comfy-core": {
        "what": "Built into ComfyUI (no extra install)",
        "install": "",
    },
    "comfyui-videohelpersuite": {
        "what": "Video Helper Suite (VHS_*)",
        "install": "git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git",
    },
    "comfyui-kjnodes": {
        "what": "KJNodes for ComfyUI",
        "install": "git clone https://github.com/kijai/ComfyUI-KJNodes.git",
    },
    "comfyui-ltxvideo": {
        "what": "Lightricks ComfyUI-LTXVideo custom pack",
        "install": "git clone https://github.com/Lightricks/ComfyUI-LTXVideo.git",
    },
    "ComfyUI-LTXVideo": {
        "what": "Lightricks ComfyUI-LTXVideo custom pack",
        "install": "git clone https://github.com/Lightricks/ComfyUI-LTXVideo.git",
    },
    "licon-msr": {
        "what": "Licon MSR (multi-subject reference layout)",
        "install": "git clone https://github.com/liconstudio/ComfyUI-Licon-MSR.git",
    },
    "aux:kijai/ComfyUI-PromptRelay": {
        "what": "PromptRelayEncode",
        "install": "git clone https://github.com/kijai/ComfyUI-PromptRelay.git",
    },
    "aux:kijai/ComfyUI-KJNodes": {
        "what": "KJNodes for ComfyUI",
        "install": "git clone https://github.com/kijai/ComfyUI-KJNodes.git",
    },
    "aux:liconstudio/ComfyUI-Licon-MSR": {
        "what": "Licon MSR",
        "install": "git clone https://github.com/liconstudio/ComfyUI-Licon-MSR.git",
    },
}

# class_type / type name patterns → pack key
NODE_HINTS: list[tuple[str, str]] = [
    ("VHS_", "comfyui-videohelpersuite"),
    ("LTXV", "comfy-core"),  # many LTX* nodes are native in recent Comfy; pack adds extras
    ("LTXAV", "comfy-core"),
    ("EmptyLTXV", "comfy-core"),
    ("Impact", "comfyui-impact-pack"),
    ("IPAdapter", "comfyui-ipadapter-plus"),
    ("ControlNet", "comfy-core"),
    ("AnimateDiff", "comfyui-animatediff-evolved"),
    ("RIFE", "comfyui-frame-interpolation"),
    ("FilmVFI", "comfyui-frame-interpolation"),
    ("DWPreprocessor", "comfyui-controlnet-aux"),
    ("AIO_Preprocessor", "comfyui-controlnet-aux"),
    ("CR ", "comfyui-custom-scripts"),  # rough
    ("Easy", "comfyui-easy-use"),
]


def load_workflow(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "input" in data and isinstance(data["input"], dict):
        if "workflow" in data["input"]:
            return data["input"]["workflow"]
        if "prompt" in data["input"]:
            return data["input"]["prompt"]
    return data


def extract_from_ui(nodes: list) -> tuple[Counter, Counter, set[str]]:
    types: Counter = Counter()
    cnr: Counter = Counter()
    titles: set[str] = set()
    for n in nodes:
        if not isinstance(n, dict):
            continue
        t = n.get("type") or n.get("class_type")
        if t:
            types[t] += 1
        props = n.get("properties") or {}
        if "cnr_id" in props:
            cnr[str(props["cnr_id"])] += 1
        if "aux_id" in props:
            cnr[f"aux:{props['aux_id']}"] += 1
        title = n.get("title")
        if title:
            titles.add(str(title))
    return types, cnr, titles


def extract_from_api(workflow: dict) -> tuple[Counter, Counter, set[str]]:
    types: Counter = Counter()
    cnr: Counter = Counter()
    for _nid, node in workflow.items():
        if not isinstance(node, dict):
            continue
        ct = node.get("class_type")
        if ct:
            types[ct] += 1
        meta = node.get("_meta") or {}
        if "cnr_id" in meta:
            cnr[str(meta["cnr_id"])] += 1
    return types, cnr, set()


def analyze(path: Path) -> dict:
    raw = load_workflow(path)
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: expected JSON object")

    if "nodes" in raw and isinstance(raw["nodes"], list):
        fmt = "ui"
        types, cnr, titles = extract_from_ui(raw["nodes"])
    else:
        # API: keys are node ids
        sample = next((v for v in raw.values() if isinstance(v, dict)), None)
        if sample is not None and "class_type" in sample:
            fmt = "api"
            types, cnr, titles = extract_from_api(raw)
        else:
            raise ValueError(
                f"{path}: unrecognized workflow shape "
                "(need UI 'nodes' or API 'class_type' map)"
            )

    suggested: set[str] = set()
    for pack in cnr:
        if pack.startswith("aux:"):
            suggested.add(pack)
        else:
            suggested.add(pack)
    for t in types:
        for prefix, pack in NODE_HINTS:
            if t.startswith(prefix) or prefix in t:
                suggested.add(pack)
                break

    return {
        "path": str(path),
        "format": fmt,
        "types": types,
        "cnr": cnr,
        "titles": titles,
        "suggested": suggested,
    }


def print_report(info: dict, show_map: bool) -> None:
    print(f"\n=== {info['path']} ({info['format']}) ===")
    print(f"Unique node types: {len(info['types'])}")
    print("\nNode types (count name):")
    for name, count in info["types"].most_common():
        print(f"  {count:4d}  {name}")

    if info["cnr"]:
        print("\nPackage IDs from workflow properties (cnr_id / aux_id):")
        for name, count in info["cnr"].most_common():
            print(f"  {count:4d}  {name}")

    print("\nSuggested packs / install targets:")
    for pack in sorted(info["suggested"]):
        meta = KNOWN_PACKS.get(pack, {})
        what = meta.get("what", "(unknown — look up in ComfyUI Manager by node name)")
        install = meta.get("install", f"# search Manager / GitHub for: {pack}")
        print(f"  • {pack}")
        print(f"      {what}")
        if show_map and install:
            print(f"      install: {install}")

    # nodes not clearly mapped
    unknown = []
    for t in info["types"]:
        if t in ("MarkdownNote", "Note", "Reroute", "PrimitiveNode"):
            continue
        hit = any(t.startswith(p) or p in t for p, _ in NODE_HINTS)
        # comfy-core covers most bare names without custom prefix
        if not hit and not any(t.startswith(x) for x in ("VHS_", "Impact", "IPAdapter")):
            # still list custom-looking names
            if any(c.islower() and c.isupper() for c in t[:1]) is False and "_" in t and not t[0].isupper():
                unknown.append(t)
            elif t.startswith(("CR ", "easy", "Easy", "rgthree", "WAS_", "JW")):
                unknown.append(t)
    customish = [
        t
        for t in info["types"]
        if t.startswith(("VHS_", "Impact", "IPAdapter", "AnimateDiff", "DW", "AIO_", "RIFE", "easy", "Easy", "rgthree", "WAS_", "LayerUtility", "LayerMask"))
        or "Preprocessor" in t
    ]
    if customish:
        print("\nLikely custom-node types (verify in Manager if missing on worker):")
        for t in sorted(customish):
            print(f"  - {t}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("workflows", nargs="+", type=Path, help="Workflow JSON file(s)")
    ap.add_argument(
        "--map",
        action="store_true",
        help="Print install command hints from KNOWN_PACKS",
    )
    ap.add_argument(
        "--json",
        action="store_true",
        help="Machine-readable summary on stdout",
    )
    args = ap.parse_args()

    reports = []
    for path in args.workflows:
        if not path.is_file():
            print(f"ERROR: not a file: {path}", file=sys.stderr)
            return 1
        try:
            reports.append(analyze(path))
        except Exception as e:
            print(f"ERROR: {path}: {e}", file=sys.stderr)
            return 1

    if args.json:
        out = []
        for r in reports:
            out.append(
                {
                    "path": r["path"],
                    "format": r["format"],
                    "types": dict(r["types"]),
                    "cnr_ids": dict(r["cnr"]),
                    "suggested_packs": sorted(r["suggested"]),
                }
            )
        print(json.dumps(out, indent=2))
        return 0

    for r in reports:
        print_report(r, show_map=args.map)

    print(
        """
--- How to use this ---
1. Prefer UI-exported workflows: they often include properties.cnr_id (Comfy registry id).
2. On a full Comfy pod with Manager: missing nodes show red; Manager → Install Missing.
3. Map each pack → Dockerfile:
     RUN comfy-node-install <registry-name>
     or git clone into /comfyui/custom_nodes/ + pip install -r requirements.txt
4. Re-run this script after adding packs; only new custom prefixes should appear.
5. Models (checkpoints, loras, text_encoders) are NOT libraries — put those on the network volume.
"""
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
