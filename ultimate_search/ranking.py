from __future__ import annotations

import re
from datetime import datetime

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from ultimate_search.models import EvidenceItem, ResearchRequest


SOURCE_WEIGHT = {
    "regulatory label": 18,
    "trial registry": 15,
    "peer-reviewed / biomedical": 14,
    "web": 6,
}


def parse_year(text: str) -> int:
    match = re.search(r"(19|20)\d{2}", text or "")
    return int(match.group(0)) if match else 0


def recency_score(published: str) -> float:
    year = parse_year(published)
    if not year:
        return 4
    age = max(0, datetime.now().year - year)
    return max(0, 12 - age)


def rank_evidence(items: list[EvidenceItem], request: ResearchRequest) -> list[EvidenceItem]:
    if not items:
        return []

    docs = [f"{item.title} {item.snippet}" for item in items]
    try:
        matrix = TfidfVectorizer(stop_words="english", max_features=6000).fit_transform([request.question, *docs])
        similarities = cosine_similarity(matrix[0:1], matrix[1:]).flatten()
    except Exception:
        similarities = [0.0 for _ in items]

    country = request.country.lower().strip()
    for item, similarity in zip(items, similarities):
        country_bonus = 0
        if country and (country in item.title.lower() or country in item.snippet.lower()):
            country_bonus = 12 if request.require_country else 6
        item.score = min(
            100,
            (float(similarity) * 55)
            + SOURCE_WEIGHT.get(item.source_type, 8)
            + recency_score(item.published)
            + country_bonus,
        )

    return sorted(items, key=lambda item: item.score, reverse=True)[: request.max_sources]
