import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}


def extract_real_image(model_url):
    try:
        r = requests.get(model_url, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except Exception as e:
        print("printables model page error:", e)
        return None

    soup = BeautifulSoup(r.text, "html.parser")

    og = soup.find("meta", property="og:image")

    if og and og.get("content"):
        return og["content"]

    return None


def search_printables(query):
    url = f"https://www.printables.com/search/models?q={query}"

    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except Exception as e:
        print("printables search error:", e)
        return []

    soup = BeautifulSoup(r.text, "html.parser")

    results = []

    cards = soup.select("a[href*='/model/']")

    seen = set()

    for card in cards:

        href = card.get("href")

        if not href:
            continue

        if "/model/" not in href:
            continue

        if href in seen:
            continue

        seen.add(href)

        title = card.get_text(strip=True)

        model_url = "https://www.printables.com" + href

        image = extract_real_image(model_url)

        results.append({
            "title": title,
            "url": model_url,
            "image": image,
            "platform": "printables"
        })

        if len(results) >= 12:
            break

    return results
