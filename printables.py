import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0"
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

    tw = soup.find("meta", property="twitter:image")
    if tw and tw.get("content"):
        return tw["content"]

    return None


def search(query):

    url = f"https://www.printables.com/search/models?q={query}"

    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except Exception as e:
        print("printables search error:", e)
        return []

    soup = BeautifulSoup(r.text, "html.parser")

    results = []
    seen = set()

    links = soup.find_all("a", href=True)

    for link in links:

        href = link["href"]

        if "/model/" not in href:
            continue

        if href in seen:
            continue

        seen.add(href)

        title = link.get_text(strip=True)

        if not title:
            continue

        model_url = "https://www.printables.com" + href

        image = extract_real_image(model_url)

        results.append({
            "title": title,
            "url": model_url,
            "image": image,
            "platform": "printables",
            "price": "free"
        })

        if len(results) >= 12:
            break

    return results
