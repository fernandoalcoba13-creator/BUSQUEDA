from normalize import normalize_title_for_dedupe


def dedupe_results(results):
    seen = set()
    deduped = []

    for item in results:
        title = item.get("title", "")
        url = item.get("url", "")

        key = (
            normalize_title_for_dedupe(title),
            url.strip().lower()
        )

        if key in seen:
            continue

        seen.add(key)
        deduped.append(item)

    return deduped
