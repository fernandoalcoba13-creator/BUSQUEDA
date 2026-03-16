import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

BASE_URL = "https://www.printables.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9"
}

def extract_real_image(model_url):
    try:
        r = requests.get(model_url, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except:
        return None

    soup = BeautifulSoup(r.text, "html.parser")

    # 1 OG IMAGE (la correcta casi siempre)
    og = soup.find("meta", property="og:image")
    if og and og.get("content"):
        img = og["content"]
        if "printables" in img:
            return img

    # 2 buscar imagen del modelo
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if "media.printables.com/media/prints" in src:
            return src

    # 3 fallback placeholder
    return "https://kmorra.com/assets/img/no-preview.png"

    # 3️⃣ fallback usando ID del modelo
    try:
        model_id = model_url.split("/model/")[1].split("-")[0]
        return f"https://media.printables.com/media/prints/{model_id}/images/1_preview.jpg"
    except:
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

    for a in soup.find_all("a", href=True):
        href = a["href"]

        if "/model/" not in href:
            continue

        full_url = href if href.startswith("http") else BASE_URL + href

        if full_url in seen:
            continue
        seen.add(full_url)

        title = a.get_text(strip=True)
        if not title:
            slug = full_url.rstrip("/").split("/")[-1]
            title = slug.replace("-", " ").strip()

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
