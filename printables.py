import requests
from urllib.parse import quote_plus

API_URL = "https://api.printables.com/v1/search/?q={}&type=prints"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json"
}


def search(query: str):

    q = quote_plus(query.strip())
    url = API_URL.format(q)

    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except Exception as e:
        print("printables api error:", e)
        return []

    data = r.json()

    results = []

    for item in data.get("prints", [])[:12]:

        title = item.get("name")
        model_id = item.get("id")

        image = None
        images = item.get("images")

        if images:
            image = images[0].get("url")

        results.append({
            "title": title,
            "url": f"https://www.printables.com/model/{model_id}",
            "platform": "printables",
            "image": image,
            "price": "free"
        })

    return results
