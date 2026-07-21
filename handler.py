"""
RunPod GitHub integration scans the repo for `runpod.serverless.start()`.

The real ComfyUI worker is started by the official base image CMD:
  /start.sh  (ComfyUI + official handler inside runpod/worker-comfyui)

This file satisfies the GitHub "handler found" check. At runtime the container
uses the base image entrypoint, not this stub — unless you change CMD.
"""
import runpod


def handler(event):
    # Should not be invoked when using official worker-comfyui base CMD.
    return {
        "error": (
            "Stub handler only. Image must use CMD from "
            "runpod/worker-comfyui ( /start.sh ). Check Dockerfile FROM/CMD."
        )
    }


if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
