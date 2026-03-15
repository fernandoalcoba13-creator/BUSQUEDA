import base64
import json
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware

from services.search_service import search_all
from services.image_service import get_client, PROMPT
from utils.cache import init_cache, get_cache, set_cache

app = FastAPI(title="Kmorra STL Search API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    await init_cache()


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": app.version}


@app.get("/api/search")
async def search(
    q: str = Query(..., min_length=1),
    filter: str = Query("all"),
    platforms: Optional[str] = Query(None),
):
    selected_platforms = (
        [p.strip().lower() for p in platforms.split(",") if p.strip()]
        if platforms
        else ["thingiverse", "printables", "myminifactory", "makerworld", "cults3d"]
    )

    cache_key = f"search::{q.lower().strip()}::{filter}::{','.join(selected_platforms)}"
    cached = await get_cache(cache_key)
    if cached:
        return cached

    payload = await search_all(q, selected_platforms, filter)
    await set_cache(cache_key, payload)
    return payload


@app.post("/api/search-by-image")
async def search_by_image(
    image: UploadFile = File(...),
    filter: str = Query("all"),
    platforms: Optional[str] = Query(None),
):
    raw = await image.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Imagen vacía")

    b64 = base64.b64encode(raw).decode("utf-8")
    client = get_client()

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": PROMPT},
                    {
                        "type": "input_image",
                        "image_url": f"data:{image.content_type or 'image/jpeg'};base64,{b64}",
                    },
                ],
            }
        ],
    )

    text = response.output_text.strip()
    try:
        parsed = json.loads(text)
        queries = parsed.get("queries", [])
    except Exception:
        queries = []

    if not queries:
        raise HTTPException(status_code=500, detail="No se pudieron generar queries desde la imagen")

    selected_platforms = (
        [p.strip().lower() for p in platforms.split(",") if p.strip()]
        if platforms
        else ["thingiverse", "printables", "myminifactory", "makerworld", "cults3d"]
    )

    merged_results = []
    stats = {name: 0 for name in selected_platforms}

    for query in queries[:3]:
        payload = await search_all(query, selected_platforms, filter)
        merged_results.extend(payload["results"])
        for key, value in payload["platform_stats"].items():
            stats[key] = stats.get(key, 0) + value

    return {
        "source": "image",
        "queries": queries,
        "filter": filter,
        "platform_stats": stats,
        "total": len(merged_results),
        "results": merged_results[:30],
    }
