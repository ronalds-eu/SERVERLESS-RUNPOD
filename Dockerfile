# Official RunPod worker-comfyui base + nodes for LTX-2.x I2V
# Docs: https://github.com/runpod-workers/worker-comfyui/blob/main/docs/customization.md
# Deploy: https://github.com/runpod-workers/worker-comfyui/blob/main/docs/deployment.md
#
# Models stay on your network volume (not baked into this image).
# Pin base version to a release tag when you build for production.

FROM runpod/worker-comfyui:5.1.0-base

# Registry names when available (doc-recommended path)
# Failures here are OK if we also git-clone below; prefer building once and reading logs.
RUN comfy-node-install comfyui-kjnodes || true
RUN comfy-node-install comfyui-videohelpersuite || true

# LTX + common helpers from GitHub (not all on Comfy Registry)
# Paths inside the official image use /comfyui (worker-comfyui convention).
WORKDIR /comfyui/custom_nodes

# Lightricks official LTX Video nodes for ComfyUI
RUN git clone --depth 1 https://github.com/Lightricks/ComfyUI-LTXVideo.git \
 && if [ -f ComfyUI-LTXVideo/requirements.txt ]; then \
      pip install --no-cache-dir -r ComfyUI-LTXVideo/requirements.txt; \
    fi

# Video Helper Suite (VHS_VideoCombine, etc.)
RUN if [ ! -d ComfyUI-VideoHelperSuite ]; then \
      git clone --depth 1 https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git; \
    fi \
 && if [ -f ComfyUI-VideoHelperSuite/requirements.txt ]; then \
      pip install --no-cache-dir -r ComfyUI-VideoHelperSuite/requirements.txt; \
    fi

# KJNodes (ImageResizeKJ, PathchSageAttentionKJ, etc.)
RUN if [ ! -d ComfyUI-KJNodes ]; then \
      git clone --depth 1 https://github.com/kijai/ComfyUI-KJNodes.git; \
    fi \
 && if [ -f ComfyUI-KJNodes/requirements.txt ]; then \
      pip install --no-cache-dir -r ComfyUI-KJNodes/requirements.txt; \
    fi

WORKDIR /comfyui

# No large models in the image — attach network volume with /models layout.
# See volume-layout.md and scripts/setup-volume-models-symlinks.sh
