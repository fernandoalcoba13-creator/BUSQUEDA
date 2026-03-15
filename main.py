from fastapi import FastAPI, Query, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import asyncio
import httpx
import os
import base64
import json
import re
from openai import AsyncOpenAI

app = FastAPI(title="KMORRA STL Search API v2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html, */*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

def make_client():
    return httpx.AsyncClient(follow_redirects=True, verify=False, timeout=12, headers=HEADERS)

# ── THINGIVERSE ──
async def search_thingiverse(client, query: str, filter: str) -> list:
    try:
        token = "9b9cf5f3a14d33543e8a78b15e3e3d13"
        url = f"https://api.thingiverse.com/search/{query}?type=things&sort=relevant&per_page=12&access_token={token}"
        r = await client.get(url, timeout=10)
        if r.status_code != 200:
            return []
        data = r.json()
        hits = data.get("hits", []) or data.get("results", [])
        results = []
        for item in hits[:12]:
            price = item.get("price", 0) or 0
            is_free = float(str(price) or 0) == 0
            if filter == "free" and not is_free: continue
            if filter == "paid" and is_free: continue
            thumb = item.get("thumbnail","") or item.get("default_image",{}).get("url","") or ""
            results.append({
                "platform": "Thingiverse", "platform_id": "thingiverse",
                "title": item.get("name",""), "description": item.get("description","") or "",
                "thumbnail": thumb,
                "url": item.get("public_url","") or f"https://www.thingiverse.com/thing:{item.get('id','')}",
                "price": "Gratis" if is_free else f"${price}", "is_free": is_free,
                "downloads": item.get("download_count",0) or 0, "likes": item.get("like_count",0) or 0,
            })
        return results
    except Exception as e:
        print(f"Thingiverse error: {e}"); return []

# ── PRINTABLES ──
async def search_printables(client, query: str, filter: str) -> list:
    try:
        url = "https://api.printables.com/graphql/"
        hdrs = {**HEADERS, "Content-Type": "application/json", "Origin": "https://www.printables.com", "Referer": "https://www.printables.com/"}
        items = []

        # Query 1: moreDownloadedModels2 (acepta query + limit + cursor)
        p1 = {"query": "query($query:String!,$limit:Int!){moreDownloadedModels2(query:$query,limit:$limit,cursor:\"\"){items{id name slug price likesCount downloadCount summary images{filePath}}}}", "variables": {"query": query, "limit": 12}}
        r1 = await client.post(url, json=p1, headers=hdrs, timeout=12)
        if r1.status_code == 200:
            items = (((r1.json().get("data") or {}).get("moreDownloadedModels2") or {}).get("items") or [])

        # Fallback: moreLikedPrints2
        if not items:
            p2 = {"query": "query($query:String!,$limit:Int!){moreLikedPrints2(query:$query,limit:$limit,cursor:\"\"){items{id name slug price likesCount downloadCount summary images{filePath}}}}", "variables": {"query": query, "limit": 12}}
            r2 = await client.post(url, json=p2, headers=hdrs, timeout=12)
            if r2.status_code == 200:
                items = (((r2.json().get("data") or {}).get("moreLikedPrints2") or {}).get("items") or [])

        results = []
        for item in items[:12]:
            price = item.get("price") or 0
            is_free = float(str(price) or 0) == 0
            if filter == "free" and not is_free: continue
            if filter == "paid" and is_free: continue
            images = item.get("images", [])
            fp = images[0].get("filePath","") if images else ""
            thumb = f"https://media.printables.com/{fp}" if fp else ""
            pid, slug = item.get("id",""), item.get("slug","")
            results.append({
                "platform": "Printables", "platform_id": "printables",
                "title": item.get("name",""), "description": item.get("summary","") or "",
                "thumbnail": thumb, "url": f"https://www.printables.com/model/{pid}-{slug}",
                "price": "Gratis" if is_free else f"${price}", "is_free": is_free,
                "downloads": item.get("downloadCount",0) or 0, "likes": item.get("likesCount",0) or 0,
            })
        return results
    except Exception as e:
        print(f"Printables error: {e}"); return []

# ── MYMINIFACTORY ──
async def search_myminifactory(client, query: str, filter: str) -> list:
    try:
        params = {"q": query, "per_page": 12}
        if filter == "free": params["free_download"] = 1
        r = await client.get("https://www.myminifactory.com/api/v2/search", params=params, headers={**HEADERS,"Referer":"https://www.myminifactory.com/"}, timeout=10)
        if r.status_code != 200: return []
        items = r.json().get("items", [])
        results = []
        for item in items[:12]:
            price = item.get("price", 0) or 0
            is_free = item.get("free_download", False) or float(str(price) or 0) == 0
            if filter == "free" and not is_free: continue
            if filter == "paid" and is_free: continue
            images = item.get("images", {})
            thumb = ""
            if isinstance(images, dict): thumb = images.get("thumbnail", {}).get("url","") or ""
            elif isinstance(images, list) and images: thumb = images[0].get("url","") or ""
            results.append({
                "platform": "MyMiniFactory", "platform_id": "myminifactory",
                "title": item.get("name",""), "description": item.get("description","") or "",
                "thumbnail": thumb, "url": item.get("url","") or "",
                "price": "Gratis" if is_free else f"${price}", "is_free": is_free,
                "downloads": item.get("download_count",0) or 0, "likes": item.get("likes",0) or 0,
            })
        return results
    except Exception as e:
        print(f"MMF error: {e}"); return []

# ── MAKERWORLD ──
async def search_makerworld(client, query: str, filter: str) -> list:
    try:
        params = {"keyword": query, "limit": 12, "offset": 0, "sortBy": "hot"}
        if filter == "free": params["priceMax"] = 0
        elif filter == "paid": params["priceMin"] = 1
        endpoints = [
            "https://makerworld.com/api/v1/design-service/search",
            "https://makerworld.com/api/v2/designs",
        ]
        data = None
        for ep in endpoints:
            try:
                r = await client.get(ep, params=params, headers={**HEADERS,"Referer":"https://makerworld.com/","Origin":"https://makerworld.com"}, timeout=12)
                if r.status_code == 200:
                    data = r.json()
                    break
            except: continue
        if not data: return []
        items = data.get("hits") or data.get("list") or data.get("data") or data.get("items") or []
        results = []
        for item in items[:12]:
            price = item.get("price", 0) or 0
            is_free = float(str(price) or 0) == 0
            if filter == "free" and not is_free: continue
            if filter == "paid" and is_free: continue
            thumb = item.get("cover","") or item.get("thumbnail","") or item.get("previewImg","") or ""
            mid = item.get("id","") or item.get("designId","") or item.get("design_id","")
            results.append({
                "platform": "MakerWorld", "platform_id": "makerworld",
                "title": item.get("title","") or item.get("name","") or "",
                "description": item.get("description","") or item.get("summary","") or "",
                "thumbnail": thumb,
                "url": f"https://makerworld.com/en/models/{mid}" if mid else "https://makerworld.com",
                "price": "Gratis" if is_free else f"${price}", "is_free": is_free,
                "downloads": item.get("downloadCount",0) or item.get("download_count",0) or 0,
                "likes": item.get("likeCount",0) or item.get("like_count",0) or 0,
            })
        return results
    except Exception as e:
        print(f"MakerWorld error: {e}"); return []

# ── CULTS3D ──
async def search_cults3d(client, query: str, filter: str) -> list:
    try:
        params = {"q": query, "sort": "hot"}
        if filter == "free": params["price"] = "free"
        elif filter == "paid": params["price"] = "paid"
        r = await client.get("https://cults3d.com/en/search", params=params, headers={
            **HEADERS,"Accept":"application/json,*/*","X-Requested-With":"XMLHttpRequest","Referer":"https://cults3d.com/"
        }, timeout=12)
        if r.status_code == 200:
            try:
                data = r.json()
                items = data.get("creations",[]) or data.get("results",[]) or []
                if items:
                    results = []
                    for item in items[:12]:
                        price = item.get("price_cents",0) or 0
                        is_free = price == 0
                        if filter == "free" and not is_free: continue
                        if filter == "paid" and is_free: continue
                        slug = item.get("slug","")
                        results.append({
                            "platform": "Cults3D", "platform_id": "cults3d",
                            "title": item.get("name",""), "description": item.get("description","") or "",
                            "thumbnail": item.get("illustration_url","") or "",
                            "url": f"https://cults3d.com/en/3d-model/{slug}" if slug else "https://cults3d.com",
                            "price": "Gratis" if is_free else f"${price/100:.2f}", "is_free": is_free,
                            "downloads": item.get("downloads_count",0) or 0, "likes": item.get("likes_count",0) or 0,
                        })
                    return results
            except: pass
        # Fallback HTML
        r2 = await client.get("https://cults3d.com/en/search", params=params, headers={**HEADERS,"Accept":"text/html","Referer":"https://cults3d.com/"}, timeout=12)
        if r2.status_code == 200:
            html = r2.text
            m = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', html, re.DOTALL)
            if m:
                try:
                    state = json.loads(m.group(1))
                    creations = state.get("creations",[]) or []
                    results = []
                    for item in creations[:12]:
                        price = item.get("price_cents",0) or 0
                        is_free = price == 0
                        if filter == "free" and not is_free: continue
                        if filter == "paid" and is_free: continue
                        results.append({
                            "platform": "Cults3D", "platform_id": "cults3d",
                            "title": item.get("name",""), "description": "",
                            "thumbnail": item.get("illustration_url","") or "",
                            "url": f"https://cults3d.com/en/3d-model/{item.get('slug','')}",
                            "price": "Gratis" if is_free else f"${price/100:.2f}", "is_free": is_free,
                            "downloads": item.get("downloads_count",0) or 0, "likes": item.get("likes_count",0) or 0,
                        })
                    return results
                except: pass
        return []
    except Exception as e:
        print(f"Cults3D error: {e}"); return []

# ── GPT-4 VISION ──
async def analyze_image(image_bytes: bytes, mime_type: str) -> dict:
    api_key = os.environ.get("OPENAI_API_KEY","")
    if not api_key: raise HTTPException(status_code=500, detail="OPENAI_API_KEY no configurada")
    client = AsyncOpenAI(api_key=api_key)
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    prompt = 'Analyze this image and describe the 3D object. Respond ONLY with JSON: {"keywords":["k1","k2","k3"],"description":"short description","search_query":"2-5 keywords for STL search"}'
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role":"user","content":[{"type":"image_url","image_url":{"url":f"data:{mime_type};base64,{b64}","detail":"low"}},{"type":"text","text":prompt}]}],
        max_tokens=200, temperature=0.3,
    )
    raw = response.choices[0].message.content.strip()
    try: return json.loads(raw.replace("```json","").replace("```","").strip())
    except: return {"keywords":raw.split()[:5],"description":raw[:100],"search_query":raw[:50]}

async def run_search(q: str, filter: str, platforms: list) -> dict:
    async with make_client() as client:
        tasks, names = [], []
        if "thingiverse" in platforms: tasks.append(search_thingiverse(client,q,filter)); names.append("thingiverse")
        if "printables" in platforms: tasks.append(search_printables(client,q,filter)); names.append("printables")
        if "myminifactory" in platforms: tasks.append(search_myminifactory(client,q,filter)); names.append("myminifactory")
        if "makerworld" in platforms: tasks.append(search_makerworld(client,q,filter)); names.append("makerworld")
        if "cults3d" in platforms: tasks.append(search_cults3d(client,q,filter)); names.append("cults3d")
        results = await asyncio.gather(*tasks, return_exceptions=True)
    merged, stats = [], {}
    for name, result in zip(names, results):
        if isinstance(result, list): merged.extend(result); stats[name] = len(result)
        else: print(f"Error {name}: {result}"); stats[name] = 0
    return {"filter": filter, "total": len(merged), "platform_stats": stats, "results": merged}

@app.get("/api/search")
async def search(q: str = Query(..., min_length=1), filter: str = Query("all"), platforms: str = Query("thingiverse,printables,myminifactory,makerworld,cults3d")):
    data = await run_search(q, filter, [p.strip() for p in platforms.split(",")])
    return {"query": q, **data}

@app.post("/api/search-by-image")
async def search_by_image(file: UploadFile = File(...), filter: str = Form("all"), platforms: str = Form("thingiverse,printables,myminifactory,makerworld,cults3d")):
    content_type = file.content_type or "image/jpeg"
    if content_type not in ["image/jpeg","image/png","image/webp"]:
        raise HTTPException(status_code=400, detail="Formato no soportado.")
    image_bytes = await file.read()
    if len(image_bytes) > 10*1024*1024: raise HTTPException(status_code=400, detail="Imagen muy grande.")
    try: analysis = await analyze_image(image_bytes, content_type)
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error IA: {str(e)}")
    q = analysis.get("search_query","") or " ".join(analysis.get("keywords",[]))
    if not q: raise HTTPException(status_code=500, detail="No se pudo extraer keywords")
    data = await run_search(q, filter, [p.strip() for p in platforms.split(",")])
    return {"query": q, "analysis": analysis, **data}

@app.get("/api/health")
async def health(): return {"status": "ok", "version": "2.0.0"}

frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
