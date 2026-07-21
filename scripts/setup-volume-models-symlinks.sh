#!/usr/bin/env bash
# Run ONCE on your GPU pod (volume mounted at /workspace).
# Creates relative symlinks so Serverless sees /runpod-volume/models/...
# while the pod keeps using /workspace/ComfyUI/models/...
set -euo pipefail

ROOT="${1:-/workspace}"
COMFY_MODELS="${ROOT}/ComfyUI/models"
TARGET="${ROOT}/models"

if [ ! -d "$COMFY_MODELS" ]; then
  echo "ERROR: $COMFY_MODELS not found. Adjust ROOT or path."
  exit 1
fi

mkdir -p "$TARGET"
cd "$TARGET"

# Link common Comfy model folders if they exist
for dir in \
  checkpoints diffusion_models text_encoders clip clip_vision \
  vae loras controlnet upscale_models embeddings unet \
  style_models animatediff_models ipadapter; do
  if [ -d "$COMFY_MODELS/$dir" ]; then
    ln -sfn "../ComfyUI/models/$dir" "$dir"
    echo "linked models/$dir -> ../ComfyUI/models/$dir"
  fi
done

echo
echo "Done. Verify:"
echo "  ls -la $TARGET"
echo "  ls $TARGET/checkpoints | head"
echo
echo "On Serverless this is: /runpod-volume/models/..."
echo "Official worker expects: /runpod-volume/models/<folder>/filename"
