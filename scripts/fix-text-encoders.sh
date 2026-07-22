#!/usr/bin/env bash
# Run on the GPU POD (volume at /workspace). Fixes empty text_encoders for Serverless.
set -euo pipefail

ROOT="${1:-/workspace}"
COMFY="${ROOT}/ComfyUI/models"
TE="${COMFY}/text_encoders"
TARGET_LINK="${ROOT}/models/text_encoders"

echo "== Find Gemma / text encoder files on volume =="
find "${COMFY}" -iname '*gemma*' 2>/dev/null | head -50 || true
echo
echo "== Current text_encoders dir =="
mkdir -p "${TE}"
ls -la "${TE}" | head -40 || true
echo

# Common locations people put Gemma
CANDIDATES=(
  "${COMFY}/text_encoders"
  "${COMFY}/clip"
  "${COMFY}/LLM"
  "${COMFY}/llm"
  "${COMFY}/checkpoints"
)

echo "== Looking for gemma_3_12B_it_fp4_mixed.safetensors =="
FOUND=$(find "${COMFY}" -name 'gemma_3_12B_it_fp4_mixed.safetensors' 2>/dev/null | head -5 || true)
if [ -n "${FOUND}" ]; then
  echo "FOUND:"
  echo "${FOUND}"
  SRC=$(echo "${FOUND}" | head -1)
  BASE=$(basename "${SRC}")
  if [ ! -e "${TE}/${BASE}" ]; then
    echo "Linking into text_encoders/ ..."
    ln -sfn "${SRC}" "${TE}/${BASE}" 2>/dev/null || cp -n "${SRC}" "${TE}/${BASE}" || \
      ln -sfn "$(realpath --relative-to="${TE}" "${SRC}" 2>/dev/null || echo "${SRC}")" "${TE}/${BASE}"
  fi
else
  echo "File gemma_3_12B_it_fp4_mixed.safetensors NOT found under ${COMFY}"
  echo "Search any .safetensors with gemma in name:"
  find "${COMFY}" -iname '*gemma*.safetensors' 2>/dev/null | head -30 || true
fi

echo
echo "== Ensure Serverless symlink models/text_encoders =="
mkdir -p "${ROOT}/models"
if [ -d "${TE}" ]; then
  ln -sfn "../ComfyUI/models/text_encoders" "${TARGET_LINK}"
  echo "OK ${TARGET_LINK} -> ../ComfyUI/models/text_encoders"
fi

echo
echo "== Final listing (what worker should see as text_encoders) =="
ls -la "${TE}"
echo
ls -la "${TARGET_LINK}" 2>/dev/null || true
echo
echo "If this list is still empty, copy your Gemma .safetensors into:"
echo "  ${TE}/"
echo "Exact filename must match the workflow text_encoder field."
