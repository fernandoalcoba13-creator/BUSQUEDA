import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

BASE_URL = "https://makerworld.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9"
}

PLACEHOLDER = "https://via.placeholder.com/400x300?text=MakerWorld"


def search(query: str):
    q = quote_plus(query.strip())
    url = f"{BASE_URL}/en/search/models?keyword={q}"

    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        print(f"[makerworld] status={r.status_code} url={url}")
        r.raise_for_status()
    except Exception as e:
        print(f"[makerworld] request error: {e}")
        return []

    html = r.text
    print(f"[makerworld] html preview: {html[:500]}")

    soup = BeautifulSoup(html, "html.parser")

    results = []
    seen = set()

    links = soup.find_all("a", href=True)
    print(f"[makerworld] total <a> encontrados: {len(links)}")

    for a in links:
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

        img_tag = a.find("img")
        image = None
        if img_tag:
            image = img_tag.get("src") or img_tag.get("data-src")

        if not image:
            image = PLACEHOLDER

        results.append({
            "title": title,
            "url": full_url,
            "platform": "makerworld",
            "image": image,
            "price": "free"
        })

        if len(results) >= 12:
            break

    print(f"[makerworld] '{query}' -> {len(results)} resultados")
    return results
