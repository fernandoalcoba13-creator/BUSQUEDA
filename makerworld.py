import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

BASE_URL = "https://makerworld.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9",
}

PLACEHOLDER = "https://via.placeholder.com/400x300?text=MakerWorld"


def normalize_url(url: str):
    if not url:
        return None
    url = url.strip()
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return BASE_URL + url
    return url


def extract_image(tag):
    if not tag:
        return PLACEHOLDER

    img = tag.find("img")
    if not img:
        return PLACEHOLDER

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
    url = f"{BASE_URL}/en/search/models?keyword={q}"

    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        print(f"[makerworld] status={r.status_code} url={url}")
        r.raise_for_status()
    except Exception as e:
        print(f"[makerworld] error: {e}")
        return []

    soup = BeautifulSoup(r.text, "html.parser")

    results = []
    seen = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]

        if "/en/models/" not in href:
            continue

        full_url = href if href.startswith("http") else BASE_URL + href

        if full_url in seen:
            continue
        seen.add(full_url)

        title = a.get_text(strip=True)
        if not title:
            title = full_url.rstrip("/").split("/")[-1].replace("-", " ")

        image = extract_image(a)
        if image == PLACEHOLDER:
            parent = a.find_parent()
            if parent:
                image = extract_image(parent)

        results.append({
            "title": title,
            "url": full_url,
            "platform": "makerworld",
            "image": image,
            "price": "free",
        })

        if len(results) >= 12:
            break

    print(f"[makerworld] '{query}' -> {len(results)} resultados")
    return results
