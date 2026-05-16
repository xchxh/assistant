"""GET /v1/models — list available models."""

from __future__ import annotations

import time

from fastapi import APIRouter

from api.scraper import fetch_upstream_models

router = APIRouter()


@router.get("/v1/models")
async def list_models() -> dict:
    """Return only active (non-disabled) models by default."""
    now = int(time.time())
    model_map = await fetch_upstream_models()
    active_models = {k: v["id"] for k, v in model_map.items() if not v["disabled"]}
    
    data = [
        {
            "id": short_name,
            "object": "model",
            "created": now,
            "owned_by": full_id.split("/")[0],
        }
        for short_name, full_id in active_models.items()
    ]
    return {"object": "list", "data": data}


@router.get("/v1/models/all")
async def list_all_models() -> dict:
    """Return all models including disabled ones (with status)."""
    now = int(time.time())
    model_map = await fetch_upstream_models()
    
    data = [
        {
            "id": short_name,
            "object": "model",
            "created": now,
            "owned_by": info["id"].split("/")[0],
            "disabled": info["disabled"],
            "context_window": info["context_window"],
        }
        for short_name, info in model_map.items()
    ]
    return {"object": "list", "data": data}
