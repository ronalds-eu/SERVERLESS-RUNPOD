# Workflows

Place **API-format** exports here:

1. On the pod, open a **minimal** LTX 2.3 I2V graph that already works.
2. Menu: **Workflow → Export (API)**
3. Save as `ltx23-i2v-api.json` in this folder.

Requirements for Serverless:

- Model loaders use the **same filenames** as on the network volume.
- `Load Image` node filename matches `--image-name` in `scripts/run_test.py` (default `input.png`) **or** you set the node to that name in the graph.
- Avoid nodes not installed in the Dockerfile until you add those packages.

A full “10Eros / multi-guide” graph needs more custom nodes than this basic image includes.
