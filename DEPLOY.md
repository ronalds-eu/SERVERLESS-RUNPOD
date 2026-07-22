# Deploy LTX 2.3 basic I2V on RunPod Serverless

I cannot create the endpoint inside **your** RunPod account from this machine.  
Follow the official worker flow below; this folder is the custom image + volume prep.

## If you see: `runpod.serverless.start() handler not found`

RunPod GitHub deploy scans the **repo** for a handler like [worker-basic](https://github.com/runpod-workers/worker-basic) (`rp_handler.py`).

### Path A — Fix this repo (try first)

Repo root must include:

| File | Purpose |
|------|--------|
| `rp_handler.py` | **Required name** — has `runpod.serverless.start` |
| `handler.py` | optional alias |
| `requirements.txt` | includes `runpod` |
| `test_input.json` | optional for local/tests |
| `Dockerfile` | `FROM worker-comfyui` + LTX nodes, **`CMD ["/start.sh"]`** |

```bash
git add rp_handler.py handler.py requirements.txt test_input.json Dockerfile README.md
git commit -m "Match worker-basic handler layout for RunPod GitHub scan"
git push origin main
```

Then in RunPod: **new** endpoint from GitHub (or rebuild), branch `main`, Dockerfile path `.` / `Dockerfile`.

If the UI **still** blocks, use Path B (more reliable for Comfy).

### Path B — Fork official worker-comfyui (recommended if A fails)

1. On GitHub: fork https://github.com/runpod-workers/worker-comfyui  
2. In your fork’s `Dockerfile` (after Comfy install / custom nodes section), add LTX clones, **or** append a small stage that installs:

```dockerfile
WORKDIR /comfyui/custom_nodes
RUN git clone --depth 1 https://github.com/Lightricks/ComfyUI-LTXVideo.git \
 && pip install -r ComfyUI-LTXVideo/requirements.txt || true
RUN git clone --depth 1 https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git || true
RUN git clone --depth 1 https://github.com/kijai/ComfyUI-KJNodes.git || true
WORKDIR /
```

3. Deploy **that fork** via RunPod GitHub — it already has real `handler.py` + `start.sh`.  
4. Attach network volume for models.

### Path C — No GitHub import

Build/push image elsewhere → Serverless **Template** → paste image name only (skips repo handler scan).

References:

- [worker-comfyui](https://github.com/runpod-workers/worker-comfyui)
- [Customization](https://github.com/runpod-workers/worker-comfyui/blob/main/docs/customization.md)
- [Deployment](https://github.com/runpod-workers/worker-comfyui/blob/main/docs/deployment.md)

---

## A. Prepare network volume (on GPU pod)

```bash
# copy script to pod or paste it
bash /workspace/serverless-ltx-i2v/scripts/setup-volume-models-symlinks.sh /workspace

# confirm LTX file is visible via models/
ls -la /workspace/models/checkpoints | head
# or diffusion_models if that's where LTX lives
ls /workspace/models/diffusion_models 2>/dev/null | head
```

Note the **exact** `.safetensors` name of LTX 2.3 dev.

Also confirm text encoder / Gemma path used by your working pod workflow.

---

## B. Build custom worker image (on a machine with Docker, linux/amd64)

The image installs **opencv-python-headless**, **imageio-ffmpeg**, and pins **kornia==0.8.1**,
plus custom nodes for MSR workflows:

| Manager name | GitHub |
|--------------|--------|
| ComfyUI-LTXVideo | Lightricks/ComfyUI-LTXVideo |
| ComfyUI-VideoHelperSuite | Kosinkadink/ComfyUI-VideoHelperSuite |
| Licon MSR | liconstudio/ComfyUI-Licon-MSR |
| KJNodes for ComfyUI | kijai/ComfyUI-KJNodes |
| ComfyUI-PromptRelay | kijai/ComfyUI-PromptRelay |

```bash
cd serverless-ltx-i2v

# pin version if you prefer a newer base tag from:
# https://github.com/runpod-workers/worker-comfyui/releases

# bump the tag whenever you change Dockerfile / requirements
docker build --platform linux/amd64 -t YOUR_DOCKERHUB_USER/worker-comfyui-ltx-i2v:v2 .

docker login
docker push YOUR_DOCKERHUB_USER/worker-comfyui-ltx-i2v:v2
```

Then point the Serverless **template** at the new tag (`:v2`) and save/redeploy the endpoint.

**Or** push this folder to GitHub and use RunPod **Start from GitHub Repo** (builds Dockerfile for you).

### After deploy — confirm custom nodes load

In worker logs you want:

- **no** `IMPORT FAILED: comfyui-videohelpersuite`
- **no** `Cannot import ... ComfyUI-LTXVideo ... pad`
- path line: `Adding extra search path text_encoders /runpod-volume/models/text_encoders`

Submit jobs with `{"input":{"workflow":...}}` only (see `workflows/payload-t2v.json`).

---

## C. RunPod template (Serverless)

Console → **Serverless → Templates → New Template**

| Field | Value |
|--------|--------|
| Type | **Serverless** |
| Container image | `YOUR_DOCKERHUB_USER/worker-comfyui-ltx-i2v:v1` |
| Container disk | **20–40 GB** (nodes + deps; models on volume) |
| Env (optional) | `NETWORK_VOLUME_DEBUG=true` for first tests |
| Env (optional) | `COMFY_LOG_LEVEL=DEBUG` |

Save template.

---

## D. Endpoint

**Serverless → Endpoints → New Endpoint**

| Field | Value |
|--------|--------|
| Name | e.g. `ltx-i2v` |
| Template | the one above |
| GPU | **48GB+** for LTX 2.3 (80GB class safer; match what works on your pod) |
| Active workers | `0` (cheap) or `1` (no cold start) |
| Max workers | `1–3` |
| GPUs / worker | `1` |
| Idle timeout | `5–10` min |
| Flash Boot | **enabled** |
| **Network volume** | **your existing volume (same region)** |

Deploy.

Copy **Endpoint ID** + create **API key** under User Settings.

---

## E. Workflow JSON (API format)

On the **pod** Comfy UI:

1. Build/open a **minimal** LTX 2.3 **image-to-video** graph that works there.  
2. **Workflow → Export (API)** (not only UI save).  
3. Put the file on your Mac as `workflows/ltx23-i2v-api.json`.  
4. In loaders, model filenames must match **volume** names (e.g. your ltx-2.3-dev file).

Your complex graphs (10Eros, multi-guide, etc.) need **extra** custom nodes in the Dockerfile before they will run on Serverless.

---

## F. Test request

```bash
export RUNPOD_API_KEY="..."
export ENDPOINT_ID="..."

# Minimal shape (official worker):
# input.workflow = API export object
# input.images = optional base64 inputs for Load Image nodes

python3 scripts/run_test.py \
  --endpoint-id "$ENDPOINT_ID" \
  --api-key "$RUNPOD_API_KEY" \
  --workflow workflows/ltx23-i2v-api.json \
  --image /path/to/start_frame.png
```

Or curl (workflow embedded):

```bash
curl -X POST "https://api.runpod.ai/v2/${ENDPOINT_ID}/runsync" \
  -H "Authorization: Bearer ${RUNPOD_API_KEY}" \
  -H "Content-Type: application/json" \
  -d @payload.json
```

Timeouts: first cold start with LTX can be **many minutes**. Prefer long `runsync` timeout or `/run` + poll `/status`.

---

## G. Sanity checklist

- [ ] Volume same **region** as endpoint  
- [ ] `/workspace/models` symlinks exist (relative)  
- [ ] LTX file name matches workflow  
- [ ] Gemma/text encoder available via `models/`  
- [ ] Image includes LTXVideo + VHS + KJNodes  
- [ ] Workflow is **API export**  
- [ ] GPU class large enough  

---

## What I cannot do from this chat

- Log into RunPod as you  
- Attach **your** volume ID  
- Push to **your** Docker Hub  
- Guarantee one universal I2V API JSON (node IDs depend on your graph)

After you export a minimal working I2V API JSON from the pod, drop it in `workflows/` and we can wire `payload.json` / node name fixes.
