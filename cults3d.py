import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import re

BASE_URL = "https://cults3d.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://cults3d.com/",
}

PLACEHOLDER = "https://via.placeholder.com/400x300?text=Cults3D"


def normalize_url(url: str) -> str:
    if not url:
        return None
    url = url.strip()
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return BASE_URL + url
    return url


def extract_image(tag) -> str:
    if not tag:
        return PLACEHOLDER
    img = tag.find("img")
    if img:
        for attr in ["src", "data-src", "data-lazy-src", "data-original"]:
            val = normalize_url(img.get(attr))
            if val and val.startswith("http") and "placeholder" not in val:
                return val
        srcset = img.get("srcset", "")
        if srcset:
            parts = [p.strip() for p in srcset.split(",") if p.strip()]
            for part in parts:
                url = normalize_url(part.split(" ")[0])
                if url and url.startswith("http"):
                    return url
    return PLACEHOLDER


def search(query: str):
    q = quote_plus(query.strip())
    url = f"{BASE_URL}/en/search?q={q}"

    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except Exception as e:
        print(f"[cults3d] error: {e}")
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    results = []
    seen = set()

    # Cults3D usa /en/3d-model/ en sus URLs
    for a in soup.find_all("a", href=re.compile(r"/en/3d-model/")):
        href = a.get("href", "")
        full_url = href if href.startswith("http") else BASE_URL + href

        if full_url in seen:
            continue
        seen.add(full_url)

        title = a.get_text(strip=True)
        if not title:
            title = full_url.rstrip("/").split("/")[-1].replace("-", " ").strip()

        image = extract_image(a) or extract_image(a.find_parent())

        # Precio — Cults3D tiene modelos gratis y pagos
        price = "free"
        price_tag = a.find(class_=re.compile(r"price|cost|amount", re.I))
        if price_tag:
            price_text = price_tag.get_text(strip=True)
            if price_text and price_text != "0" and "free" not in price_text.lower():
                price = price_text

        results.append({
            "title": title,
            "url": full_url,
            "platform": "cults3d",
            "image": image,
            "price": price,
        })

        if len(results) >= 12:
            break

    print(f"[cults3d] '{query}' → {len(results)} resultados")
    return results
