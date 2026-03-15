import asyncio
from providers import thingiverse, printables, myminifactory, makerworld, cults3d
from services.fallback_service import search_fallback
from services.ranking_service import rank_results
from utils.dedupe import dedupe_results
from utils.normalize import build_query_variants, normalize_text

PROVIDER_MAP = {
    "thingiverse": thingiverse.search,
    "printables": printables.search,
    "myminifactory": myminifactory.search,
    "makerworld": makerworld.search,
    "cults3d": cults3d.search,
}


async def _safe_provider_call(provider_name: str, query: str) -> list[dict]:
    try:
        results = await PROVIDER_MAP[provider_name](query)
        for r in results:
            r.setdefault("platform", provider_name)
            r.setdefault("price", "unknown")
            r.setdefault("image", "")
            r.setdefault("source", "provider")
        return results
    except Exception as exc:
        print(f"[provider-error] {provider_name}: {exc}")
        return []


async def search_all(query: str, selected_platforms: list[str], price_filter: str = "all") -> dict:
    query = normalize_text(query)
    variants = build_query_variants(query)
    results = []
    platform_stats = {name: 0 for name in selected_platforms}

    for variant in variants[:2]:
        tasks = [_safe_provider_call(name, variant) for name in selected_platforms if name in PROVIDER_MAP]
        provider_groups = await asyncio.gather(*tasks)
        for provider_name, group in zip(selected_platforms, provider_groups):
            if price_filter != "all":
                group = [g for g in group if g.get("price") == price_filter]
            platform_stats[provider_name] += len(group)
            results.extend(group)
        if results:
            break

    if not results:
        fallback_results = await search_fallback(query, selected_platforms)
        results.extend(fallback_results)
        for item in fallback_results:
            platform_stats[item["platform"]] += 1

    results = dedupe_results(results)
    results = rank_results(results, query)

    return {
        "query": query,
        "filter": price_filter,
        "total": len(results),
        "platform_stats": platform_stats,
        "results": results[:30],
    }
