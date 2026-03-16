import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

BASE_URL = "https://www.printables.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9"
}


def extract_real_image(model_url: str):
    try:
        r = requests.get(model_url, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except Exception as e:
        print("printables model page error:", e)
        return None

    soup = BeautifulSoup(r.text, "html.parser")

    # 1) Open Graph image
    og = soup.find("meta", property="og:image")
    if og and og.get("content"):
        return og["content"]

    # 2) Twitter image
    tw = soup.find("meta", attrs={"name": "twitter:image"})
    if tw and tw.get("content"):
        return tw["content"]

    # 3) fallback img
    img = soup.find("img")
    if img:
        src = img.get("src") or img.get("data-src")
        if src:
            if src.startswith("//"):
                return "https:" + src
            if src.startswith("/"):
                return BASE_URL + src
            if src.startswith("http"):
                return src

    return None


def search(query: str):
    q = quote_plus(query.strip())
    url = f"{BASE_URL}/search/models?q={q}"

    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except Exception as e:
        print("printables search error:", e)
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    results = []
    seen = set()

    for a in soup.select('a[href*="/model/"]'):
        href = a.get("href")
        if not href:
            continue

        full_url = href if href.startswith("http") else BASE_URL + href

        if full_url in seen:
            continue
        seen.add(full_url)

        title = a.get_text(strip=True)
        if not title:
            slug = full_url.split("/")[-1]
            title = slug.replace("-", " ")

        image = extract_real_image(full_url)

        results.append({
            "title": title,
            "url": full_url,
            "platform": "printables",
            "image": image,
            "price": "free"
        })

        if len(results) >= 12:
            break

    return results
