# Required name/pattern for RunPod GitHub "handler found" detection.
# Matches https://github.com/runpod-workers/worker-basic
#
# Runtime for ComfyUI uses the base image CMD /start.sh (real worker-comfyui handler).
# This file is for GitHub integration scan + local SDK smoke tests.

import runpod


def handler(event):
    print("Worker Start (repo rp_handler — Comfy image should use /start.sh at runtime)")
    inp = event.get("input") or {}
    # Echo so /runsync can complete during RunPod's post-build test if this stub runs.
    return {
        "status": "ok",
        "note": "rp_handler stub; production Comfy worker is CMD /start.sh from worker-comfyui base",
        "received_keys": list(inp.keys()),
    }


if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
