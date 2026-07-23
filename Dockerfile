# Official worker-comfyui + custom nodes for LTX MSR / Ingredients workflows
# Docs: https://github.com/runpod-workers/worker-comfyui/blob/main/docs/customization.md
#
# Custom nodes for MSR / Ingredients workflows:
#   ComfyUI-LTXVideo, ComfyUI-VideoHelperSuite, Licon MSR,
#   KJNodes, ComfyUI-PromptRelay, ComfyUI-BFSNodes, ComfyUI-PainterNodes
#
# Models: network volume at /runpod-volume/models (symlinks from your pod)

FROM runpod/worker-comfyui:5.8.6-base

CMD ["/start.sh"]

# --- Shared Python deps (VHS + LTXVideo kornia pin) ---
COPY requirements.txt /tmp/worker-extra-requirements.txt
COPY scripts/patch-ltxvideo-kornia.py /tmp/patch-ltxvideo-kornia.py
COPY scripts/verify-worker-imports.py /tmp/verify-worker-imports.py

RUN pip install --no-cache-dir -r /tmp/worker-extra-requirements.txt

# --- Custom nodes (same tree the worker loads) ---
# Helper: clone or update, then pip install requirements if present
RUN set -eux; \
    mkdir -p /comfyui/custom_nodes; \
    cd /comfyui/custom_nodes; \
    \
    # 1) ComfyUI-LTXVideo (Lightricks) — IC-LoRA guides, etc.
    rm -rf ComfyUI-LTXVideo; \
    git clone --depth 1 https://github.com/Lightricks/ComfyUI-LTXVideo.git ComfyUI-LTXVideo; \
    if [ -f ComfyUI-LTXVideo/requirements.txt ]; then \
      pip install --no-cache-dir -r ComfyUI-LTXVideo/requirements.txt; \
    fi; \
    pip install --no-cache-dir "kornia==0.8.1"; \
    python /tmp/patch-ltxvideo-kornia.py; \
    \
    # 2) ComfyUI-VideoHelperSuite — VHS_VideoCombine
    rm -rf comfyui-videohelpersuite ComfyUI-VideoHelperSuite; \
    git clone --depth 1 https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git comfyui-videohelpersuite; \
    if [ -f comfyui-videohelpersuite/requirements.txt ]; then \
      pip install --no-cache-dir -r comfyui-videohelpersuite/requirements.txt; \
    fi; \
    \
    # 3) Licon MSR — LiconMSR node (multi-subject reference layout)
    rm -rf ComfyUI-Licon-MSR; \
    git clone --depth 1 https://github.com/liconstudio/ComfyUI-Licon-MSR.git ComfyUI-Licon-MSR; \
    if [ -f ComfyUI-Licon-MSR/requirements.txt ]; then \
      pip install --no-cache-dir -r ComfyUI-Licon-MSR/requirements.txt; \
    fi; \
    \
    # 4) KJNodes for ComfyUI — ImageResizeKJv2, VAELoaderKJ, LTX2* helpers
    rm -rf comfyui-kjnodes ComfyUI-KJNodes; \
    git clone --depth 1 https://github.com/kijai/ComfyUI-KJNodes.git comfyui-kjnodes; \
    if [ -f comfyui-kjnodes/requirements.txt ]; then \
      pip install --no-cache-dir -r comfyui-kjnodes/requirements.txt; \
    fi; \
    \
    # 5) ComfyUI-PromptRelay — PromptRelayEncode
    rm -rf ComfyUI-PromptRelay; \
    git clone --depth 1 https://github.com/kijai/ComfyUI-PromptRelay.git ComfyUI-PromptRelay; \
    if [ -f ComfyUI-PromptRelay/requirements.txt ]; then \
      pip install --no-cache-dir -r ComfyUI-PromptRelay/requirements.txt; \
    fi; \
    \
    # 6) ComfyUI-BFSNodes — https://github.com/alisson-anjos/ComfyUI-BFSNodes
    rm -rf ComfyUI-BFSNodes; \
    git clone --depth 1 https://github.com/alisson-anjos/ComfyUI-BFSNodes.git ComfyUI-BFSNodes; \
    if [ -f ComfyUI-BFSNodes/requirements.txt ]; then \
      pip install --no-cache-dir -r ComfyUI-BFSNodes/requirements.txt; \
    fi; \
    \
    # 7) ComfyUI-PainterNodes — https://github.com/princepainter/ComfyUI-PainterNodes
    rm -rf ComfyUI-PainterNodes; \
    git clone --depth 1 https://github.com/princepainter/ComfyUI-PainterNodes.git ComfyUI-PainterNodes; \
    if [ -f ComfyUI-PainterNodes/requirements.txt ]; then \
      pip install --no-cache-dir -r ComfyUI-PainterNodes/requirements.txt; \
    fi; \
    \
    # Re-assert opencv + kornia after any pack requirements
    # (BFSNodes pulls opencv-python; prefer headless on workers)
    pip install --no-cache-dir "kornia==0.8.1" opencv-python-headless imageio-ffmpeg; \
    \
    echo "=== custom_nodes ==="; \
    ls -la /comfyui/custom_nodes

# Fail the build if critical imports still break
RUN python /tmp/verify-worker-imports.py \
    && rm -f /tmp/worker-extra-requirements.txt /tmp/patch-ltxvideo-kornia.py /tmp/verify-worker-imports.py

# Network volume model paths (includes text_encoders)
COPY extra_model_paths.yaml /comfyui/extra_model_paths.yaml

# --- Handler: URL image/video ingest + stock worker-comfyui ---
# start.sh runs `python -u /handler.py`. Keep stock as handler_stock for wrap.
RUN cp /handler.py /handler_stock.py
COPY media_ingest.py /media_ingest.py
COPY handler.py /handler.py

WORKDIR /
