"""Model scraper for assistant-ui.com."""

from __future__ import annotations

import asyncio
import re
import time
import httpx

from config import MODEL_MAP as FALLBACK_MODEL_MAP

# Cache variables
_cached_models: dict[str, dict] | None = None
_last_fetch_time: float = 0
CACHE_TTL = 3600  # 1 hour cache

async def fetch_upstream_models() -> dict[str, dict]:
    """Fetch the latest available models from assistant-ui.com."""
    global _cached_models, _last_fetch_time
    now = time.time()
    
    # Return cache if valid
    if _cached_models is not None and (now - _last_fetch_time) < CACHE_TTL:
        return _cached_models

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    
    try:
        async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
            # 1. Fetch main HTML page
            resp = await client.get("https://www.assistant-ui.com/")
            resp.raise_for_status()
            html = resp.text
            
            # 2. Extract Next.js chunk URLs
            chunk_paths = set(re.findall(r'src="(/_next/static/chunks/[^"]+\.js)"', html))
            if not chunk_paths:
                raise ValueError("No Next.js chunks found in HTML")
            
            # 3. Concurrently fetch all JS chunks
            tasks = []
            for path in chunk_paths:
                url = f"https://www.assistant-ui.com{path}"
                tasks.append(client.get(url))
                
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 4. Search for the models array in the JS responses
            for r in responses:
                if isinstance(r, Exception):
                    continue
                if r.status_code != 200:
                    continue
                    
                js = r.text
                matches = re.search(r'\[(?:\{name:"[^"]+",value:"[^"]+",icon:"[^"]+",disabled:!?[01],contextWindow:[\d\.e]+\},?)+\]', js)
                if matches:
                    array_str = matches.group(0)
                    model_pattern = r'\{name:"([^"]+)",value:"([^"]+)",icon:"[^"]+",disabled:(![01]),contextWindow:([\d\.e]+)\}'
                    model_matches = re.findall(model_pattern, array_str)
                    
                    models = {}
                    for name, value, disabled_str, cw_str in model_matches:
                        # short_name will be the last segment of the value ID
                        short_name = value.split("/")[-1]
                        
                        disabled = (disabled_str == '!0')
                        try:
                            cw = int(float(cw_str))
                        except Exception:
                            cw = 131072 # fallback
                            
                        models[short_name] = {
                            "id": value,
                            "disabled": disabled,
                            "context_window": cw,
                            "name": name
                        }
                    
                    if models:
                        # Update cache
                        _cached_models = models
                        _last_fetch_time = now
                        return models
                        
            raise ValueError("Model definitions not found in any JS chunk")
            
    except Exception as e:
        import logging
        logging.error(f"Failed to fetch upstream models: {e}")
        # Fallback to hardcoded models if fetch fails
        if _cached_models is not None:
            return _cached_models
        return FALLBACK_MODEL_MAP

