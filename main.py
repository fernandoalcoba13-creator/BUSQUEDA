from fastapi import FastAPI, Query, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import asyncio
import base64
import html
import json
import os
import re
from urllib.parse import quote, urlparse

import httpx
from openai import AsyncOpenAI

app = FastAPI(title="KMORRA STL Search API v3")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/html, */*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

PLATFORM_LABELS = {
    "thingiverse": "Thingiverse",
    "printables": "Printables",
    "myminifactory": "MyMiniFactory",
    "makerworld": "MakerWorld",
    "cults3d": "Cults3D",
}

PLATFORM_DOMAINS = {
    "thingiverse": "thingiverse.com",
    "printables": "printables.com",
    "myminifactory": "myminifactory.com",
    "makerworld": "makerworld.com",
    "cults3d": "cults3d.com",
}


def make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        follow_redirects=True,
        verify=False,
        timeout=20,
        headers=HEADERS,
    )


def clean_query(query: str) -> str:
    q = (query or "").strip()
    q = re.sub(r"\s+", " ", q)
    return q


def simplify_query_for_stl(query: str) -> str:
    q = clean_query(query).lower()
    q = re.sub(r"\b(stl|archivo|model|modelo|3d|gratis|free|download|descarga)\b", " ", q)
    q = re.sub(r"\s+", " ", q).strip()
    return q or clean_query(query)


def dedupe_results(items: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for item in items:
        key = (item.get("platform_id", ""), item.get("url", ""))
        if key in seen or not item.get("url"):
            continue
        seen.add(key)
        out.append(item)
    return out


def normalize_result(platform_id: str, title: str, url: str, **extra) -> dict:
    return {
        "platform": PLATFORM_LABELS[platform_id],
        "platform_id": platform_id,
        "title": (title or "").strip(),
        "description": extra.get("description", "") or "",
        "thumbnail": extra.get("thumbnail", "") or "",
        "url": url,
        "price": extra.get("price", "Gratis"),
        "is_free": extra.get("is_free", True),
        "downloads": int(extra.get("downloads", 0) or 0),
        "likes": int(extra.get("likes", 0) or 0),
    }


# ---------- direct provider integrations ----------
async def search_thingiverse_direct(client: httpx.AsyncClient, query: str, price_filter: str) -> list:
    """Thingiverse still has an API, but tokens can fail. This is best-effort only."""
    token = os.environ.get("THINGIVERSE_TOKEN", "9b9cf5f3a14d33543e8a78b15e3e3d13")
    url = (
        f"https://api.thingiverse.com/search/{quote(query)}"
        f"?type=things&sort=relevant&per_page=12&access_token={token}"
    )
    try:
        r = await client.get(url, timeout=12)
        if r.status_code != 200:
            print(f"Thingiverse direct status: {r.status_code}")
            return []
        data = r.json()
        hits = data.get("hits", []) or data.get("results", []) or []
        results = []
        for item in hits[:12]:
            price = item.get("price", 0) or 0
            is_free = float(str(price) or 0) == 0
            if price_filter == "free" and not is_free:
                continue
            if price_filter == "paid" and is_free:
                continue
            thumb = item.get("thumbnail", "") or item.get("default_image", {}).get("url", "") or ""
            results.append(
                normalize_result(
                    "thingiverse",
                    item.get("name", ""),
                    item.get("public_url", "") or f"https://www.thingiverse.com/thing:{item.get('id','')}",
                    description=item.get("description", "") or "",
                    thumbnail=thumb,
                    price="Gratis" if is_free else f"${price}",
                    is_free=is_free,
                    downloads=item.get("download_count", 0) or 0,
                    likes=item.get("like_count", 0) or 0,
                )
            )
        return results
    except Exception as e:
        print(f"Thingiverse direct error: {e}")
        return []


async def search_printables_direct(client: httpx.AsyncClient, query: str, price_filter: str) -> list:
    url = "https://api.printables.com/graphql/"
    payloads = [
        {
            "query": "query SearchPrints($q:String!,$limit:Int!){morePrints(filters:{q:$q,limit:$limit}){items{id name slug price likesCount downloadCount summary images{filePath}}}}",
            "variables": {"q": query, "limit": 12},
        },
        {
            "query": 'query($q:String!){searchPrints(q:$q,limit:12,ordering:"-download_count"){items{id name slug price likesCount downloadCount summary images{filePath}}}}',
            "variables": {"q": query},
        },
    ]
    items = []
    for payload in payloads:
        try:
            r = await client.post(
                url,
                json=payload,
                headers={
                    **HEADERS,
                    "Content-Type": "application/json",
                    "Origin": "https://www.printables.com",
                    "Referer": "https://www.printables.com/",
                },
                timeout=12,
            )
            if r.status_code == 200:
                data = r.json().get("data") or {}
                items = (
                    data.get("morePrints", {}).get("items", [])
                    or data.get("searchPrints", {}).get("items", [])
                )
                if items:
                    break
            else:
                print(f"Printables direct status: {r.status_code}")
        except Exception as e:
            print(f"Printables direct attempt error: {e}")
    results = []
    for item in items[:12]:
        price = item.get("price") or 0
        is_free = float(str(price) or 0) == 0
        if price_filter == "free" and not is_free:
            continue
        if price_filter == "paid" and is_free:
            continue
        images = item.get("images", []) or []
        fp = images[0].get("filePath", "") if images else ""
        thumb = f"https://media.printables.com/{fp}" if fp else ""
        pid, slug = item.get("id", ""), item.get("slug", "")
        results.append(
            normalize_result(
                "printables",
                item.get("name", ""),
                f"https://www.printables.com/model/{pid}-{slug}" if pid else f"https://www.printables.com/search?q={quote(query)}",
                description=item.get("summary", "") or "",
                thumbnail=thumb,
                price="Gratis" if is_free else f"${price}",
                is_free=is_free,
                downloads=item.get("downloadCount", 0) or 0,
                likes=item.get("likesCount", 0) or 0,
            )
        )
    return results


async def search_myminifactory_direct(client: httpx.AsyncClient, query: str, price_filter: str) -> list:
    try:
        params = {"q": query, "per_page": 12}
        if price_filter == "free":
            params["free_download"] = 1
        r = await client.get(
            "https://www.myminifactory.com/api/v2/search",
            params=params,
            headers={**HEADERS, "Referer": "https://www.myminifactory.com/"},
            timeout=12,
        )
        if r.status_code != 200:
            print(f"MMF direct status: {r.status_code}")
            return []
        items = r.json().get("items", []) or []
        results = []
        for item in items[:12]:
            price = item.get("price", 0) or 0
            is_free = item.get("free_download", False) or float(str(price) or 0) == 0
            if price_filter == "free" and not is_free:
                continue
            if price_filter == "paid" and is_free:
                continue
            images = item.get("images", {})
            thumb = ""
            if isinstance(images, dict):
                thumb = images.get("thumbnail", {}).get("url", "") or ""
            elif isinstance(images, list) and images:
                thumb = images[0].get("url", "") or ""
            results.append(
                normalize_result(
                    "myminifactory",
                    item.get("name", ""),
                    item.get("url", "") or f"https://www.myminifactory.com/search/?query={quote(query)}",
                    description=item.get("description", "") or "",
                    thumbnail=thumb,
                    price="Gratis" if is_free else f"${price}",
                    is_free=is_free,
                    downloads=item.get("download_count", 0) or 0,
                    likes=item.get("likes", 0) or 0,
                )
            )
        return results
    except Exception as e:
        print(f"MMF direct error: {e}")
        return []


async def search_makerworld_direct(client: httpx.AsyncClient, query: str, price_filter: str) -> list:
    params = {"keyword": query, "limit": 12, "offset": 0, "sortBy": "hot"}
    if price_filter == "free":
        params["priceMax"] = 0
    elif price_filter == "paid":
        params["priceMin"] = 1
    endpoints = [
        "https://makerworld.com/api/v1/design-service/search",
        "https://makerworld.com/api/v2/designs",
    ]
    data = None
    for ep in endpoints:
        try:
            r = await client.get(
                ep,
                params=params,
                headers={**HEADERS, "Referer": "https://makerworld.com/", "Origin": "https://makerworld.com"},
                timeout=12,
            )
            if r.status_code == 200:
                data = r.json()
                break
            print(f"MakerWorld direct status {ep}: {r.status_code}")
        except Exception as e:
            print(f"MakerWorld direct error {ep}: {e}")
    if not data:
        return []
    items = data.get("hits") or data.get("list") or data.get("data") or data.get("items") or []
    results = []
    for item in items[:12]:
        price = item.get("price", 0) or 0
        is_free = float(str(price) or 0) == 0
        if price_filter == "free" and not is_free:
            continue
        if price_filter == "paid" and is_free:
            continue
        thumb = item.get("cover", "") or item.get("thumbnail", "") or item.get("previewImg", "") or ""
        mid = item.get("id", "") or item.get("designId", "") or item.get("design_id", "")
        title = item.get("title", "") or item.get("name", "") or ""
        results.append(
            normalize_result(
                "makerworld",
                title,
                f"https://makerworld.com/en/models/{mid}" if mid else f"https://makerworld.com/en/search/models?keyword={quote(query)}",
                description=item.get("description", "") or item.get("summary", "") or "",
                thumbnail=thumb,
                price="Gratis" if is_free else f"${price}",
                is_free=is_free,
                downloads=item.get("downloadCount", 0) or item.get("download_count", 0) or 0,
                likes=item.get("likeCount", 0) or item.get("like_count", 0) or 0,
            )
        )
    return results


async def search_cults3d_direct(client: httpx.AsyncClient, query: str, price_filter: str) -> list:
    try:
        params = {"q": query, "sort": "hot"}
        if price_filter == "free":
            params["price"] = "free"
        elif price_filter == "paid":
            params["price"] = "paid"
        r = await client.get(
            "https://cults3d.com/en/search",
            params=params,
            headers={
                **HEADERS,
                "Accept": "application/json,*/*",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": "https://cults3d.com/",
            },
            timeout=12,
        )
        if r.status_code == 200:
            try:
                data = r.json()
                items = data.get("creations", []) or data.get("results", []) or []
                results = []
                for item in items[:12]:
                    price = item.get("price_cents", 0) or 0
                    is_free = price == 0
                    if price_filter == "free" and not is_free:
                        continue
                    if price_filter == "paid" and is_free:
                        continue
                    slug = item.get("slug", "")
                    results.append(
                        normalize_result(
                            "cults3d",
                            item.get("name", ""),
                            f"https://cults3d.com/en/3d-model/{slug}" if slug else f"https://cults3d.com/en/search?q={quote(query)}",
                            description=item.get("description", "") or "",
                            thumbnail=item.get("illustration_url", "") or "",
                            price="Gratis" if is_free else f"${price / 100:.2f}",
                            is_free=is_free,
                            downloads=item.get("downloads_count", 0) or 0,
                            likes=item.get("likes_count", 0) or 0,
                        )
                    )
                if results:
                    return results
            except Exception as e:
                print(f"Cults3D direct JSON parse error: {e}")
    except Exception as e:
        print(f"Cults3D direct error: {e}")
    return []


# ---------- generic web fallback ----------
async def search_duckduckgo_site(client: httpx.AsyncClient, query: str, platform_id: str) -> list:
    domain = PLATFORM_DOMAINS[platform_id]
    search_q = f'site:{domain} ("{query}" OR "{simplify_query_for_stl(query)}") (stl OR 3d OR model)'
    url = "https://html.duckduckgo.com/html/"
    try:
        r = await client.get(url, params={"q": search_q}, headers={**HEADERS, "Referer": "https://duckduckgo.com/"}, timeout=15)
        if r.status_code != 200:
            print(f"DDG fallback status {platform_id}: {r.status_code}")
            return []
        return parse_duckduckgo_results(r.text, platform_id)
    except Exception as e:
        print(f"DDG fallback error {platform_id}: {e}")
        return []


def parse_duckduckgo_results(html_text: str, platform_id: str) -> list:
    blocks = re.findall(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html_text, re.I | re.S)
    results = []
    domain = PLATFORM_DOMAINS[platform_id]
    for href, raw_title in blocks[:20]:
        title = re.sub(r"<.*?>", "", raw_title)
        title = html.unescape(title).strip()
        url = html.unescape(href)
        parsed = urlparse(url)
        if domain not in parsed.netloc and domain not in url:
            continue
        if platform_id == "thingiverse" and "/thing:" not in url:
            continue
        if platform_id == "printables" and "/model/" not in url:
            continue
        if platform_id == "myminifactory" and "/object/3d-print/" not in url and "/prints/" not in url:
            continue
        if platform_id == "makerworld" and "/models/" not in url:
            continue
        if platform_id == "cults3d" and "/3d-model/" not in url:
            continue
        results.append(
            normalize_result(
                platform_id,
                title,
                url,
                description="Resultado recuperado por búsqueda web de respaldo.",
                thumbnail="",
                price="Ver sitio",
                is_free=True,
                downloads=0,
                likes=0,
            )
        )
    return dedupe_results(results)[:12]


async def search_provider(client: httpx.AsyncClient, platform_id: str, query: str, price_filter: str) -> list:
    direct_map = {
        "thingiverse": search_thingiverse_direct,
        "printables": search_printables_direct,
        "myminifactory": search_myminifactory_direct,
        "makerworld": search_makerworld_direct,
        "cults3d": search_cults3d_direct,
    }
    direct_results = await direct_map[platform_id](client, query, price_filter)
    if direct_results:
        return dedupe_results(direct_results)[:12]
    print(f"{platform_id}: direct returned 0, using DDG fallback")
    fallback = await search_duckduckgo_site(client, query, platform_id)
    if price_filter == "paid":
        # fallback cannot reliably infer price, so return the URLs anyway instead of hiding everything
        for item in fallback:
            item["price"] = "Ver sitio"
            item["is_free"] = False
    return dedupe_results(fallback)[:12]


# ---------- image analysis ----------
async def analyze_image(image_bytes: bytes, mime_type: str) -> dict:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY no configurada")

    client = AsyncOpenAI(api_key=api_key)
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    prompt = (
        "Analyze this image for an STL/model search engine. "
        "Respond ONLY with valid JSON like: "
        '{"keywords":["keyword 1","keyword 2","keyword 3"],' \
        '"description":"short description",' \
        '"search_query":"2 to 5 keyword STL search query"}'
    )

    response = await client.chat.completions.create(
        model=os.environ.get("OPENAI_VISION_MODEL", "gpt-4o-mini"),
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64}", "detail": "low"}},
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        max_tokens=220,
        temperature=0.2,
    )
    raw = (response.choices[0].message.content or "").strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("JSON root is not object")
        return data
    except Exception:
        words = [w for w in re.split(r"[^a-zA-Z0-9áéíóúñÁÉÍÓÚÑ_-]+", raw) if w]
        return {
            "keywords": words[:5],
            "description": raw[:140],
            "search_query": " ".join(words[:4]) if words else "3d model",
        }


# ---------- orchestration ----------
async def run_search(q: str, price_filter: str, platforms: list[str]) -> dict:
    q = clean_query(q)
    if not q:
        return {"filter": price_filter, "total": 0, "platform_stats": {}, "results": []}

    async with make_client() as client:
        tasks = [search_provider(client, pid, q, price_filter) for pid in platforms if pid in PLATFORM_DOMAINS]
        names = [pid for pid in platforms if pid in PLATFORM_DOMAINS]
        gathered = await asyncio.gather(*tasks, return_exceptions=True)

    merged = []
    stats = {}
    for name, result in zip(names, gathered):
        if isinstance(result, Exception):
            print(f"Error {name}: {result}")
            stats[name] = 0
            continue
        stats[name] = len(result)
        merged.extend(result)

    merged = dedupe_results(merged)
    merged.sort(key=lambda x: (0 if x.get("downloads", 0) else 1, -x.get("downloads", 0), -x.get("likes", 0), x.get("title", "")))
    return {
        "filter": price_filter,
        "total": len(merged),
        "platform_stats": stats,
        "results": merged[:60],
    }


@app.get("/api/search")
async def search(
    q: str = Query(..., min_length=1),
    filter: str = Query("all"),
    platforms: str = Query("thingiverse,printables,myminifactory,makerworld,cults3d"),
):
    chosen = [p.strip() for p in platforms.split(",") if p.strip()]
    data = await run_search(q, filter, chosen)
    return {"query": q, **data}


@app.post("/api/search-by-image")
async def search_by_image(
    file: UploadFile = File(...),
    filter: str = Form("all"),
    platforms: str = Form("thingiverse,printables,myminifactory,makerworld,cults3d"),
):
    content_type = file.content_type or "image/jpeg"
    if content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(status_code=400, detail="Formato no soportado.")
    image_bytes = await file.read()
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Imagen muy grande.")

    try:
        analysis = await analyze_image(image_bytes, content_type)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error IA: {str(e)}")

    q = clean_query(analysis.get("search_query", "") or " ".join(analysis.get("keywords", [])))
    if not q:
        raise HTTPException(status_code=500, detail="No se pudieron extraer keywords")

    chosen = [p.strip() for p in platforms.split(",") if p.strip()]
    data = await run_search(q, filter, chosen)
    return {"query": q, "analysis": analysis, **data}


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "3.0.0"}


frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
