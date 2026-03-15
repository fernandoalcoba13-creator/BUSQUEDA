from utils.normalize import normalize_text


def score_result(result: dict, query: str) -> int:
    score = 0
    q = normalize_text(query)
    title = normalize_text(result.get("title", ""))
    if q and q in title:
        score += 50
    if result.get("image"):
        score += 15
    if result.get("price") == "free":
        score += 10
    if result.get("source") == "provider":
        score += 20
    return score


def rank_results(results: list[dict], query: str) -> list[dict]:
    for result in results:
        result["score"] = score_result(result, query)
    return sorted(results, key=lambda x: x.get("score", 0), reverse=True)
