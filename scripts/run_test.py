#!/usr/bin/env python3
"""Send a Comfy API-format workflow to a RunPod Serverless worker-comfyui endpoint."""
from __future__ import annotations

import argparse
import base64
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--endpoint-id", required=True)
    p.add_argument("--api-key", required=True)
    p.add_argument("--workflow", required=True, type=Path, help="Comfy Workflow > Export (API) JSON")
    p.add_argument("--image", type=Path, default=None, help="Optional start frame for Load Image")
    p.add_argument("--image-name", default="input.png", help="Filename referenced in the workflow")
    p.add_argument("--async", dest="async_mode", action="store_true", help="Use /run instead of /runsync")
    args = p.parse_args()

    workflow = json.loads(args.workflow.read_text())
    # Export (API) is usually a flat dict of node_id -> {class_type, inputs}
    if "workflow" in workflow and isinstance(workflow["workflow"], dict):
        workflow = workflow["workflow"]

    payload: dict = {"input": {"workflow": workflow}}
    if args.image is not None:
        raw = args.image.read_bytes()
        b64 = base64.b64encode(raw).decode("ascii")
        payload["input"]["images"] = [{"name": args.image_name, "image": b64}]

    path = "run" if args.async_mode else "runsync"
    url = f"https://api.runpod.ai/v2/{args.endpoint_id}/{path}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {args.api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    print(f"POST {url}", file=sys.stderr)
    try:
        with urllib.request.urlopen(req, timeout=3600) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        print(err, file=sys.stderr)
        return 1

    out = json.loads(body)
    print(json.dumps(out, indent=2)[:5000])
    if len(json.dumps(out)) > 5000:
        print("\n... truncated ...", file=sys.stderr)

    # Save first base64 image if present
    images = (out.get("output") or {}).get("images") or []
    for i, img in enumerate(images):
        if img.get("type") == "base64" and img.get("data"):
            dest = Path(f"out_{i}_{img.get('filename', 'image.png')}")
            dest.write_bytes(base64.b64decode(img["data"]))
            print(f"Wrote {dest}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
