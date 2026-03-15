from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional, List
import os
import tempfile

# IMPORTS DESDE RAÍZ
from search_service import search_all
from image_service import search_by_image


app = FastAPI(
    title="Kmorra Search API",
    version="2.0.0"
)

# CORS abierto para que tu frontend pueda pegarle desde kmorra.com
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "Kmorra Search API running",
        "version": "2.0.0"
    }


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "version": "2.0.0"
    }


@app.get("/api/search")
async def api_search(
    q: str = Query(..., min_length=1, description="Texto de búsqueda"),
    filter: str = Query("all", description="Filtro general"),
    platforms: Optional[str] = Query(
        None,
        description="Lista separada por comas: thingiverse,printables,myminifactory,makerworld,cults3d"
    ),
    limit: int = Query(30, ge=1, le=100)
):
    try:
        platform_list: Optional[List[str]] = None

        if platforms:
            platform_list = [
                p.strip().lower()
                for p in platforms.split(",")
                if p.strip()
            ]

        results = await search_all(
            query=q,
            filter_by=filter,
            platforms=platform_list,
            limit=limit
        )

        # Compatibilidad flexible: si search_all ya devuelve dict completo, lo respetamos
        if isinstance(results, dict):
            return JSONResponse(content=results)

        # Si devuelve lista simple, armamos respuesta estándar
        platform_stats = {
            "thingiverse": 0,
            "printables": 0,
            "myminifactory": 0,
            "makerworld": 0,
            "cults3d": 0,
        }

        for item in results:
            platform = str(item.get("platform", "")).lower()
            if platform in platform_stats:
                platform_stats[platform] += 1

        return JSONResponse(content={
            "query": q,
            "filter": filter,
            "total": len(results),
            "platform_stats": platform_stats,
            "results": results
        })

    except Exception as e:
        print(f"[ERROR] /api/search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


@app.post("/api/search-by-image")
async def api_search_by_image(
    image: UploadFile = File(...),
    filter: str = Query("all"),
    platforms: Optional[str] = Query(None),
    limit: int = Query(30, ge=1, le=100)
):
    temp_path = None

    try:
        if not image:
            raise HTTPException(status_code=400, detail="No image uploaded")

        suffix = os.path.splitext(image.filename or "upload.jpg")[1] or ".jpg"

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await image.read()
            tmp.write(content)
            temp_path = tmp.name

        platform_list: Optional[List[str]] = None
        if platforms:
            platform_list = [
                p.strip().lower()
                for p in platforms.split(",")
                if p.strip()
            ]

        results = await search_by_image(
            image_path=temp_path,
            filter_by=filter,
            platforms=platform_list,
            limit=limit
        )

        if isinstance(results, dict):
            return JSONResponse(content=results)

        platform_stats = {
            "thingiverse": 0,
            "printables": 0,
            "myminifactory": 0,
            "makerworld": 0,
            "cults3d": 0,
        }

        detected_query = None
        if results and isinstance(results, list):
            detected_query = results[0].get("_detected_query")

        clean_results = []
        for item in results:
            platform = str(item.get("platform", "")).lower()
            if platform in platform_stats:
                platform_stats[platform] += 1

            # limpiamos campos internos si existen
            item = dict(item)
            item.pop("_detected_query", None)
            clean_results.append(item)

        return JSONResponse(content={
            "query": detected_query or "image-search",
            "filter": filter,
            "total": len(clean_results),
            "platform_stats": platform_stats,
            "results": clean_results
        })

    except Exception as e:
        print(f"[ERROR] /api/search-by-image failed: {e}")
        raise HTTPException(status_code=500, detail=f"Image search error: {str(e)}")

    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception as cleanup_error:
                print(f"[WARN] Could not delete temp file {temp_path}: {cleanup_error}")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    print(f"[UNHANDLED ERROR] {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )
