from utils.matching import score_opportunity

def test_matching_returns_bounded_score_and_reason():
    score, reasons = score_opportunity(
        title="Python software engineering internship",
        snippet="Internship for engineering students in India. Apply before deadline.",
        degree="B.Tech / Engineering",
        year="2nd year",
        skills="Python, problem solving",
        interests="software development, AI",
        location="India",
    )
    assert 0 <= score <= 100
    assert reasons
