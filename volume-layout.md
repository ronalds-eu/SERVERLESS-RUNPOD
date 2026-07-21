# Network volume layout for official worker-comfyui

## On your GPU pod (now)

```text
/workspace/
  ComfyUI/
    models/
      checkpoints/          # put LTX-2.3 / ltx-2.x .safetensors here (or already there)
      text_encoders/        # Gemma etc. if loader expects this folder
      ...
  models/                   # CREATE via setup-volume-models-symlinks.sh
    checkpoints -> ../ComfyUI/models/checkpoints
    ...
```

## On Serverless (same volume attached)

```text
/runpod-volume/
  ComfyUI/models/...        # real files
  models/...                # symlinks (what the worker reads)
```

Official docs: models at `/runpod-volume/models/...`  
See: https://github.com/runpod-workers/worker-comfyui/blob/main/docs/network-volumes.md

## LTX “dev” filename

Workflows and loaders must use the **exact filename** as on disk, e.g.:

- `ltx-2.3-22b-dev.safetensors`
- or whatever you have under `checkpoints/` / `diffusion_models/`

If your pod loads from `checkpoints/` but the file is only under another folder, symlink or move once on the volume.

## Gemma / text encoder

I2V LTX graphs often need a **text encoder** (Gemma) as well as the LTX checkpoint.  
If inference works on the pod, those files are already somewhere under `ComfyUI/models/` — include that folder in the symlink script.
