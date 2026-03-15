from normalize import normalize_text

def rank_results(results, query):
    q = normalize_text(query)

    def score(item):
        title = normalize_text(item.get("title", ""))
        s = 0

        if q and q in title:
            s += 100

        if item.get("image"):
            s += 10

        if item.get("platform"):
            s += 5

        if item.get("price") in ("free", "gratis", 0, "0"):
            s += 3

        return s

    return sorted(results, key=score, reverse=True)
