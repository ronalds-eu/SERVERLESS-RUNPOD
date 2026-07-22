# Official worker-comfyui + force-install ComfyUI-LTXVideo (Lightricks)
# Docs: https://github.com/runpod-workers/worker-comfyui/blob/main/docs/customization.md
#
# Real handler: CMD /start.sh from base image
# Models: network volume at /runpod-volume/models (symlinks from your pod)

# Use a current official base (newer Comfy than 5.1.0 — better LTX / video nodes).
# Tags: https://github.com/runpod-workers/worker-comfyui/releases
# Images: runpod/worker-comfyui:<version>-base
FROM runpod/worker-comfyui:5.8.6-base

# Keep official entrypoint (Comfy + RunPod handler)
CMD ["/start.sh"]

# --- Install custom nodes into the same tree the worker uses ---
# Fail the BUILD if clone fails (no silent || true on the critical pack)
RUN set -eux; \
    ls -la /comfyui; \
    mkdir -p /comfyui/custom_nodes; \
    cd /comfyui/custom_nodes; \
    rm -rf ComfyUI-LTXVideo; \
    git clone --depth 1 https://github.com/Lightricks/ComfyUI-LTXVideo.git; \
    if [ -f ComfyUI-LTXVideo/requirements.txt ]; then \
      pip install --no-cache-dir -r ComfyUI-LTXVideo/requirements.txt; \
    fi; \
    ls -la /comfyui/custom_nodes/ComfyUI-LTXVideo | head

# Optional helpers (non-fatal if registry name differs)
RUN comfy-node-install comfyui-kjnodes || true
RUN comfy-node-install comfyui-videohelpersuite || \
    (cd /comfyui/custom_nodes && git clone --depth 1 https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git || true)

WORKDIR /
