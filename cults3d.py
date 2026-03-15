from utils.normalize import encode_q


async def search(query: str) -> list[dict]:
    # TODO: reemplazar por scraper/API real
    _ = encode_q(query)
    return []
