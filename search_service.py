import asyncio

import printables
import thingiverse
import cults
import makerworld
import myminifactory


async def run_search(loop, func, query):
    return await loop.run_in_executor(None, func, query)


async def search_all_async(query):

    loop = asyncio.get_event_loop()

    tasks = [
        run_search(loop, printables.search, query),
        run_search(loop, thingiverse.search, query),
        run_search(loop, cults.search, query),
        run_search(loop, makerworld.search, query),
        run_search(loop, myminifactory.search, query),
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    combined = []

    for r in results:
        if isinstance(r, list):
            combined.extend(r)

    return combined


def search_all(query):
    return asyncio.run(search_all_async(query))
