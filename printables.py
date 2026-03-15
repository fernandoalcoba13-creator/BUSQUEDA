import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

BASE_URL = "https://www.printables.com"


def search(query: str):
    q = quote_plus(query.strip())
    url = f"{BASE_URL}/search/models?q={q}"

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
    except Exception as e:
        print("printables error:", e)
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

        image = None
        img = a.select_one("img")

        if img:
            image = img.get("src") or img.get("data-src")

            # ignorar base64 gigantes
            if image and image.startswith("data:image"):
                image = None

            if image and image.startswith("//"):
                image = "https:" + image

            if image and image.startswith("/"):
                image = BASE_URL + image

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
