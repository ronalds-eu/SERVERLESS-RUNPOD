"""
RunPod handler: wraps official worker-comfyui handler with URL media ingest.

start.sh runs: python -u /handler.py

Dockerfile:
  RUN cp /handler.py /handler_stock.py
  COPY media_ingest.py handler.py /

Middleware sends small JSON with https URLs (see media_ingest.py docstring).
"""
from __future__ import annotations

import logging
import traceback

import runpod

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("handler")

# Official image ships network_volume next to handler; stock handler uses it.
try:
    import handler_stock as stock
except Exception as e:  # pragma: no cover
    raise SystemExit(
        f"Failed to import handler_stock (copy stock /handler.py to /handler_stock.py): {e}"
    ) from e

from media_ingest import enrich_job_input


def handler(job: dict):
    """
    Preprocess input (download image/video URLs → /comfyui/input, patch workflow),
    then run the stock worker-comfyui handler unchanged.
    """
    try:
        job_input = job.get("input")
        enriched = enrich_job_input(job_input)
        # Stock code expects job["input"]
        wrapped = {**job, "input": enriched}
        return stock.handler(wrapped)
    except Exception as e:
        logger.error("media ingest / handler failed: %s", e)
        logger.error(traceback.format_exc())
        return {"error": str(e)}


if __name__ == "__main__":
    logger.info("Starting handler (URL media ingest + worker-comfyui stock)")
    runpod.serverless.start({"handler": handler})
