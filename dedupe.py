from utils.normalize import normalize_title_for_dedupe


def dedupe_results(results: list[dict]) -> list[dict]:
    seen = set()
    clean = []
    for r in results:
        key = (
            normalize_title_for_dedupe(r.get("title", "")),
            r.get("platform", ""),
            r.get("url", ""),
        )
        if key in seen:
            continue
        seen.add(key)
        clean.append(r)
    return clean
