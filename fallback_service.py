from utils.normalize import build_query_variants

PLATFORMS = {
    "thingiverse": "thingiverse.com",
    "printables": "printables.com",
    "myminifactory": "myminifactory.com",
    "makerworld": "makerworld.com",
    "cults3d": "cults3d.com",
}


async def search_fallback(query: str, selected_platforms: list[str]) -> list[dict]:
    # Fallback simple y seguro: generar links de búsqueda directa por dominio.
    # No depende de scraping. Muestra al usuario dónde seguir buscando.
    results = []
    for variant in build_query_variants(query)[:2]:
        for platform in selected_platforms:
            domain = PLATFORMS.get(platform)
            if not domain:
                continue
            results.append(
                {
                    "title": f"Buscar '{variant}' en {platform}",
                    "url": f"https://www.google.com/search?q=site:{domain}+{variant.replace(' ', '+')}",
                    "image": "",
                    "platform": platform,
                    "price": "unknown",
                    "score": 10,
                    "source": "fallback",
                }
            )
    return results
