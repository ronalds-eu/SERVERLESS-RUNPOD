# Official worker-comfyui + ComfyUI-LTXVideo + VideoHelperSuite deps
# Docs: https://github.com/runpod-workers/worker-comfyui/blob/main/docs/customization.md
#
# Real handler: CMD /start.sh from base image
# Models: network volume at /runpod-volume/models (symlinks from your pod)

# Use a current official base (newer Comfy — better LTX / video nodes).
# Tags: https://github.com/runpod-workers/worker-comfyui/releases
# Images: runpod/worker-comfyui:<version>-base
FROM runpod/worker-comfyui:5.8.6-base

# Keep official entrypoint (Comfy + RunPod handler)
CMD ["/start.sh"]

# --- Runtime deps missing from base (seen as IMPORT FAILED in worker logs) ---
# - opencv (cv2) + imageio-ffmpeg: required by comfyui-videohelpersuite
# - kornia pin: ComfyUI-LTXVideo imports pad from kornia.geometry.transform.pyramid;
#   newer kornia (base image) no longer re-exports pad there → whole pack fails to load.
COPY requirements.txt /tmp/worker-extra-requirements.txt
COPY scripts/patch-ltxvideo-kornia.py /tmp/patch-ltxvideo-kornia.py
COPY scripts/verify-worker-imports.py /tmp/verify-worker-imports.py

RUN pip install --no-cache-dir -r /tmp/worker-extra-requirements.txt

# --- Install custom nodes into the same tree the worker uses ---
# Fail the BUILD if LTXVideo clone fails (no silent || true on the critical pack)
RUN set -eux; \
    ls -la /comfyui; \
    mkdir -p /comfyui/custom_nodes; \
    cd /comfyui/custom_nodes; \
    rm -rf ComfyUI-LTXVideo; \
    git clone --depth 1 https://github.com/Lightricks/ComfyUI-LTXVideo.git; \
    if [ -f ComfyUI-LTXVideo/requirements.txt ]; then \
      pip install --no-cache-dir -r ComfyUI-LTXVideo/requirements.txt; \
    fi; \
    pip install --no-cache-dir "kornia==0.8.1"; \
    python /tmp/patch-ltxvideo-kornia.py; \
    ls -la /comfyui/custom_nodes/ComfyUI-LTXVideo | head

# Optional helpers (non-fatal if registry name differs)
RUN comfy-node-install comfyui-kjnodes || true
RUN comfy-node-install comfyui-videohelpersuite || \
    (cd /comfyui/custom_nodes && \
     git clone --depth 1 https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git comfyui-videohelpersuite)

# Fail the build early if the packages that broke production still fail to import
RUN python /tmp/verify-worker-imports.py \
    && rm -f /tmp/worker-extra-requirements.txt /tmp/patch-ltxvideo-kornia.py /tmp/verify-worker-imports.py

# Map network-volume model folders (includes text_encoders — missing in stock base)
COPY extra_model_paths.yaml /comfyui/extra_model_paths.yaml

WORKDIR /
