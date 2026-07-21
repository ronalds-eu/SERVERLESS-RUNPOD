# Official RunPod worker-comfyui base + nodes for LTX-2.x I2V
# Docs: https://github.com/runpod-workers/worker-comfyui/blob/main/docs/customization.md
# Deploy: https://github.com/runpod-workers/worker-comfyui/blob/main/docs/deployment.md
#
# IMPORTANT:
# - Real serverless handler lives in the BASE IMAGE (CMD ["/start.sh"]).
# - handler.py in this repo is for RunPod GitHub "handler found" scan only.
# - Models stay on the network volume (/runpod-volume/models via symlinks).

FROM runpod/worker-comfyui:5.1.0-base

# Do NOT override CMD — keep official: /start.sh (ComfyUI + real handler)
# CMD ["/start.sh"]

# Registry installers when available
RUN comfy-node-install comfyui-kjnodes || true
RUN comfy-node-install comfyui-videohelpersuite || true

# LTX + helpers from GitHub (paths under /comfyui in official image)
WORKDIR /comfyui/custom_nodes

RUN git clone --depth 1 https://github.com/Lightricks/ComfyUI-LTXVideo.git \
 && if [ -f ComfyUI-LTXVideo/requirements.txt ]; then \
      pip install --no-cache-dir -r ComfyUI-LTXVideo/requirements.txt; \
    fi

RUN if [ ! -d ComfyUI-VideoHelperSuite ]; then \
      git clone --depth 1 https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git; \
    fi \
 && if [ -f ComfyUI-VideoHelperSuite/requirements.txt ]; then \
      pip install --no-cache-dir -r ComfyUI-VideoHelperSuite/requirements.txt; \
    fi

RUN if [ ! -d ComfyUI-KJNodes ]; then \
      git clone --depth 1 https://github.com/kijai/ComfyUI-KJNodes.git; \
    fi \
 && if [ -f ComfyUI-KJNodes/requirements.txt ]; then \
      pip install --no-cache-dir -r ComfyUI-KJNodes/requirements.txt; \
    fi

WORKDIR /

# Explicitly keep official entrypoint (handler + Comfy)
CMD ["/start.sh"]
