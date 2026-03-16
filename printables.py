import requests

def search(query):

    url = f"https://api.printables.com/search/models?q={query}"

    try:
        r = requests.get(url, timeout=15)
        data = r.json()
    except:
        return []

    results = []

    for item in data.get("models", [])[:12]:

        results.append({
            "title": item.get("name"),
            "url": f"https://www.printables.com/model/{item.get('id')}",
            "image": item.get("preview_image"),
            "platform": "printables",
            "price": "free"
        })

    return results
