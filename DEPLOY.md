# Deploy LTX 2.3 basic I2V on RunPod Serverless

I cannot create the endpoint inside **your** RunPod account from this machine.  
Follow the official worker flow below; this folder is the custom image + volume prep.

## If you see: `runpod.serverless.start() handler not found`

RunPod’s **GitHub** deploy **scans your repo source** for a handler.  
A thin repo that only has `FROM runpod/worker-comfyui` has the **real** handler inside the **Docker image**, not in git — so the UI warns.

**Fix (already in this package):**

1. Ensure repo root has `handler.py` containing `runpod.serverless.start` (stub is fine for the scan).
2. Ensure `Dockerfile` keeps base image **`CMD ["/start.sh"]`** (real Comfy worker).
3. `git add handler.py Dockerfile && git commit && git push`
4. Create/redeploy the endpoint from GitHub again.

**Alternative (no GitHub scan):** Serverless → Template → set **Container image** to a built image name (Docker Hub), not “import repo only.”

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

```bash
cd serverless-ltx-i2v

# pin version if you prefer a newer base tag from:
# https://github.com/runpod-workers/worker-comfyui/releases

docker build --platform linux/amd64 -t YOUR_DOCKERHUB_USER/worker-comfyui-ltx-i2v:v1 .

docker login
docker push YOUR_DOCKERHUB_USER/worker-comfyui-ltx-i2v:v1
```

**Or** push this folder to GitHub and use RunPod **Start from GitHub Repo** (builds Dockerfile for you).

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
