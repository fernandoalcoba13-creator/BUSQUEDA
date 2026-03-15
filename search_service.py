import asyncio

import printables
import thingiverse
import cults3d
import makerworld
import myminifactory

from ranking_service import rank_results
from fallback_service import fallback_search
from dedupe import dedupe_results
from normalize import normalize_query
from cache import get_cached_results, set_cached_results


async def _run_provider(provider_module, query: str):
    try:
        if hasattr(provider_module, "search"):
            result = provider_module.search(query)
            if asyncio.iscoroutine(result):
                result = await result
            return result or []
        return []
    except Exception as e:
        print(f"[WARN] Provider failed: {provider_module.__name__}: {e}")
        return []


async def search_all(query: str, filter_by: str = "all", platforms=None, limit: int = 30):
    normalized_query = normalize_query(query)

    cached = get_cached_results(normalized_query)
    if cached:
        return cached[:limit]

    provider_map = {
        "thingiverse": thingiverse,
        "printables": printables,
        "myminifactory": myminifactory,
        "makerworld": makerworld,
        "cults3d": cults3d,
    }

    if platforms:
        selected = [p for p in platforms if p in provider_map]
    else:
        selected = list(provider_map.keys())

    tasks = [_run_provider(provider_map[name], normalized_query) for name in selected]
    provider_results = await asyncio.gather(*tasks)

    results = []
    for batch in provider_results:
        if batch:
            results.extend(batch)

    if not results:
        results = fallback_search(normalized_query)

    results = dedupe_results(results)
    results = rank_results(results, normalized_query)
    results = results[:limit]

    try:
        set_cached_results(normalized_query, results)
    except Exception as e:
        print(f"[WARN] Cache save failed: {e}")

    return results
