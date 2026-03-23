import requests
from urllib.parse import quote_plus

API_BASE = "https://www.myminifactory.com/api/v2"
API_KEY  = "d5ed1c9c-808a-466e-ba22-423f558af1e7"

HEADERS = {
    "User-Agent": "KMORRA-STLGO/1.0",
}

PLACEHOLDER = "https://via.placeholder.com/400x300?text=MyMiniFactory"


def search(query: str):
    q = quote_plus(query.strip())
    url = f"{API_BASE}/search?q={q}&key={API_KEY}&per_page=12"

    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"[myminifactory] error: {e}")
        return []

    items = data.get("items", [])
    results = []

    for item in items:
        try:
            # Imagen
            image = PLACEHOLDER
            images = item.get("images", {})
            if images.get("featured"):
                featured = images["featured"]
                if isinstance(featured, list) and featured:
                    image = featured[0].get("thumbnail", {}).get("url", PLACEHOLDER)
                elif isinstance(featured, dict):
                    image = featured.get("thumbnail", {}).get("url", PLACEHOLDER)
            elif images.get("thumbnail"):
                image = images["thumbnail"]

            # Precio
            price = "free"
            if item.get("price") and float(item.get("price", 0)) > 0:
                price = f"${item['price']}"

            results.append({
                "title": item.get("name", "Sin título"),
                "url": item.get("url", f"https://www.myminifactory.com/object/{item.get('id','')}"),
                "platform": "myminifactory",
                "image": image,
                "price": price,
            })
        except Exception as e:
            print(f"[myminifactory] item error: {e}")
            continue

    print(f"[myminifactory] '{query}' → {len(results)} resultados")
    return results
