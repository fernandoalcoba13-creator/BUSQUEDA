from normalize import build_query_variants


def fallback_search(query: str):
    variants = build_query_variants(query)

    sites = [
        ("thingiverse", "https://www.thingiverse.com/search?q={}"),
        ("printables", "https://www.printables.com/search/models?q={}"),
        ("myminifactory", "https://www.myminifactory.com/search/?query={}"),
        ("makerworld", "https://makerworld.com/en/search/models?keyword={}"),
        ("cults3d", "https://cults3d.com/en/search?q={}"),
    ]

    results = []

    for variant in variants[:3]:
        q = variant.replace(" ", "+")

        for platform, url_template in sites:
            results.append({
                "title": f"{variant} ({platform})",
                "url": url_template.format(q),
                "platform": platform,
                "image": None,
                "price": "unknown",
            })

    return results
