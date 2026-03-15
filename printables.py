import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

BASE_URL = "https://www.printables.com"


def search(query: str):
    q = quote_plus(query.strip())
    url = f"{BASE_URL}/search/models?q={q}"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
        "Referer": BASE_URL,
    }

    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
    except Exception as e:
        print(f"[WARN] printables request failed: {e}")
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    results = []
    seen = set()

    for a in soup.select('a[href*="/model/"]'):
        href = a.get("href")
        if not href or "/model/" not in href:
            continue

        full_url = href if href.startswith("http") else f"{BASE_URL}{href}"

        if full_url in seen:
            continue
        seen.add(full_url)

        title = (
            a.get("title")
            or a.get_text(" ", strip=True)
            or ""
        ).strip()

        if not title or len(title) < 3:
            slug = full_url.rstrip("/").split("/")[-1]
            title = slug.replace("-", " ").strip()

        image = None
        img = a.select_one("img")
        if img:
            image = img.get("src") or img.get("data-src")
            if image and image.startswith("//"):
                image = "https:" + image
            elif image and image.startswith("/"):
                image = f"{BASE_URL}{image}"

        results.append({
            "title": title,
            "url": full_url,
            "platform": "printables",
            "image": image,
            "price": "free",
        })

        if len(results) >= 12:
            break

    q_words = set(query.lower().split())
    filtered = []
    for item in results:
        title_lower = item["title"].lower()
        if any(w in title_lower for w in q_words):
            filtered.append(item)

    final_results = filtered if filtered else results
    final_results = sorted(
        final_results,
        key=lambda x: query.lower() in x["title"].lower(),
        reverse=True
    )

    return final_results
