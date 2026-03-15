from search_service import search_all


async def search_by_image(image_path: str, filter_by: str = "all", platforms=None, limit: int = 30):
    results = await search_all(
        query="3d printable model",
        filter_by=filter_by,
        platforms=platforms,
        limit=limit
    )

    clean_results = []
    for item in results:
        row = dict(item)
        row["_detected_query"] = "3d printable model"
        clean_results.append(row)

    return clean_results
