import re

STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "your", "are",
    "you", "our", "into", "not", "all", "job", "role", "work", "india"
}

def words(text):
    return {w for w in re.findall(r"[a-zA-Z0-9+#.]+", (text or "").lower())
            if len(w) > 2 and w not in STOPWORDS}

def score_opportunity(title, snippet, degree, year, skills, interests, location):
    """Explainable heuristic relevance score, not an eligibility determination."""
    source_words = words(f"{title} {snippet}")
    profile_terms = words(f"{skills}, {interests}")
    overlap = source_words & profile_terms
    reasons = []
    score = 35
    if overlap:
        score += min(35, 12 + 6 * len(overlap))
        reasons.append("overlapping terms: " + ", ".join(sorted(overlap)[:5]))
    degree_terms = words(degree)
    if source_words & degree_terms:
        score += 10
        reasons.append("mentions a related degree/background")
    year_terms = words(year)
    if source_words & year_terms:
        score += 10
        reasons.append("mentions a related study year")
    loc_terms = words(location)
    if source_words & loc_terms:
        score += 5
        reasons.append("mentions your preferred location")
    if any(x in (title + " " + snippet).lower() for x in ["eligibility", "apply", "deadline", "internship", "scholarship", "hackathon"]):
        score += 5
        reasons.append("contains opportunity-related signals")
    score = max(0, min(100, score))
    if not reasons:
        reasons.append("general relevance; inspect the source details")
    return score, reasons
