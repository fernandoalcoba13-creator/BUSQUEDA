import time

_CACHE = {}
_DEFAULT_TTL = 3600


def get_cached_results(query: str):
    if not query:
        return None

    item = _CACHE.get(query)
    if not item:
        return None

    if time.time() > item["expires_at"]:
        _CACHE.pop(query, None)
        return None

    return item["results"]


def set_cached_results(query: str, results, ttl: int = _DEFAULT_TTL):
    if not query:
        return

    _CACHE[query] = {
        "results": results,
        "expires_at": time.time() + ttl,
    }


def clear_cache():
    _CACHE.clear()
