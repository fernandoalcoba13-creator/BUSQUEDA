import requests
from urllib.parse import quote_plus

API_BASE = "https://api.thingiverse.com"
CLIENT_ID = "33002fec30356885d1ec"

HEADERS = {
    "Authorization": f"Bearer {CLIENT_ID}",
    "User-Agent": "KMORRA-STLGO/1.0",
}

PLACEHOLDER = "https://via.placeholder.com/400x300?text=Thingiverse"


def search(query: str):
    q = quote_plus(query.strip())
    url = f"{API_BASE}/search/{q}?type=things&per_page=12&sort=relevant"

    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"[thingiverse] error: {e}")
        return []

    results = []
    for item in data:
        try:
            # Imagen
            image = PLACEHOLDER
            if item.get("thumbnail"):
                image = item["thumbnail"]
            elif item.get("default_image") and item["default_image"].get("url"):
                image = item["default_image"]["url"]

            # Precio
            price = "free"
            if item.get("is_purchased"):
                price = "paid"

            results.append({
                "title": item.get("name", "Sin título"),
                "url": f"https://www.thingiverse.com/thing:{item.get('id', '')}",
                "platform": "thingiverse",
                "image": image,
                "price": price,
            })
        except Exception as e:
            print(f"[thingiverse] item error: {e}")
            continue

    print(f"[thingiverse] '{query}' → {len(results)} resultados")
    return results
