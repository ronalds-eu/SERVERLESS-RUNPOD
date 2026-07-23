# Image / video URL inputs (SaaS middleware → worker)

Your middleware stores user uploads and passes **HTTPS URLs** (or keys you turn into signed URLs). The worker downloads them into Comfy’s input folder, then runs the workflow.

Payload stays small (no multi‑MB base64 in the RunPod body).

## Job body

```json
{
  "input": {
    "workflow": { "...Comfy API-format nodes..." },

    "images": [
      {
        "name": "figure1.png",
        "url": "https://your-cdn.example/t/abc/figure1.png"
      },
      {
        "name": "figure2.png",
        "url": "https://your-cdn.example/t/abc/figure2.png"
      }
    ],

    "videos": [
      {
        "name": "ref.mp4",
        "url": "https://your-cdn.example/t/abc/ref.mp4"
      }
    ]
  }
}
```

### Rules

| Field | Meaning |
|--------|---------|
| `name` | Filename written under `/comfyui/input/` and used by `LoadImage` / video loaders |
| `url` | `http://` or `https://` only; worker streams download |
| Workflow | `LoadImage` (etc.) `inputs.image` must equal that **same name** |

Example node:

```json
"1390": {
  "class_type": "LoadImage",
  "inputs": { "image": "figure1.png" }
}
```

### Optional: force node IDs

If the export still has UUID filenames, bind by node id:

```json
{
  "input": {
    "workflow": { },
    "media_bindings": {
      "1390": {
        "type": "image",
        "name": "figure1.png",
        "url": "https://..."
      },
      "1391": {
        "type": "image",
        "name": "figure2.png",
        "url": "https://..."
      },
      "12": {
        "type": "video",
        "name": "clip.mp4",
        "url": "https://..."
      }
    }
  }
}
```

Or unified list:

```json
"media": [
  {
    "type": "image",
    "name": "figure1.png",
    "url": "https://...",
    "node_ids": ["1390"]
  },
  {
    "type": "video",
    "name": "ref.mp4",
    "url": "https://...",
    "node_ids": ["75"]
  }
]
```

### Still supported

Base64 (small files / legacy):

```json
"images": [
  { "name": "x.png", "image": "data:image/png;base64,...." }
]
```

URL and base64 can be mixed; URL items are downloaded first, base64 still go through the stock uploader.

## Middleware checklist

1. Accept user upload → store in S3/R2 → get HTTPS URL (presigned GET if private).  
2. Build or load Comfy **API** workflow.  
3. Set each `LoadImage` / video loader filename to a stable `name`.  
4. `POST https://api.runpod.ai/v2/{ENDPOINT_ID}/run` with body above.  
5. Poll status; handle image outputs as today (video return still separate).

## Worker env (optional)

| Variable | Default | Meaning |
|----------|---------|---------|
| `COMFY_INPUT_DIR` | `/comfyui/input` | Download target |
| `MEDIA_MAX_BYTES` | `524288000` (500MB) | Per-file cap |
| `MEDIA_TIMEOUT_S` | `120` | HTTP timeout |

## Image build

Dockerfile copies this handler over stock:

```dockerfile
RUN cp /handler.py /handler_stock.py
COPY media_ingest.py /media_ingest.py
COPY handler.py /handler.py
```

Rebuild/push the Serverless image after changing these files.

## Security notes

- Only `http`/`https` URLs.  
- Filenames are basenames only (no `../`).  
- Prefer **presigned URLs** scoped to the job, short TTL.  
- Worker must reach your CDN (public internet or private network as configured).
