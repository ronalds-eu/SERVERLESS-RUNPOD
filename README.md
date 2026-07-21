# SERVERLESS-RUNPOD (LTX / Comfy worker)

## Handler detection (RunPod GitHub)

RunPod looks for a Serverless handler in the **repo**, like [worker-basic](https://github.com/runpod-workers/worker-basic):

- **`rp_handler.py`** with `runpod.serverless.start({"handler": handler})`
- **`Dockerfile`**
- **`requirements.txt`** (includes `runpod`)

## Runtime (real ComfyUI)

`Dockerfile` is based on official:

`FROM runpod/worker-comfyui:5.1.0-base`

and keeps **`CMD ["/start.sh"]`** so the real Comfy handler runs.

Models: network volume at `/runpod-volume/models` (see volume setup on your pod).

## If GitHub still says "handler not found"

Use **Path B** in `DEPLOY.md`: fork `runpod-workers/worker-comfyui` and add LTX nodes there (that repo already has a full `handler.py`).
