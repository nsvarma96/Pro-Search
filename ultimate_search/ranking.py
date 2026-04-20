from __future__ import annotations

import re
from collections import Counter
from datetime import datetime

from ultimate_search.models import EvidenceItem, ResearchRequest


SOURCE_WEIGHT = {
    "regulatory label": 18,
    "trial registry": 15,
    "peer-reviewed / biomedical": 14,
    "web": 6,
}

STOP_WORDS = {
    "about",
    "after",
    "also",
    "and",
    "are",
    "for",
    "from",
    "has",
    "have",
    "how",
    "into",
    "is",
    "of",
    "on",
    "or",
    "the",
    "to",
    "what",
    "which",
    "with",
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


def tokenize(text: str) -> list[str]:
    return [
        token.lower()
        for token in re.findall(r"[A-Za-z0-9-]{3,}", text or "")
        if token.lower() not in STOP_WORDS
    ]


def lexical_similarity(question: str, document: str) -> float:
    query_terms = Counter(tokenize(question))
    doc_terms = Counter(tokenize(document))
    if not query_terms or not doc_terms:
        return 0
    overlap = sum(min(count, doc_terms.get(term, 0)) for term, count in query_terms.items())
    coverage = overlap / max(1, sum(query_terms.values()))
    rare_bonus = sum(1 for term in query_terms if doc_terms.get(term, 0)) / max(1, len(query_terms))
    return min(1.0, (coverage * 0.75) + (rare_bonus * 0.25))


def ascii_ratio(text: str) -> float:
    if not text:
        return 1.0
    ascii_chars = sum(1 for char in text if ord(char) < 128)
    return ascii_chars / len(text)


def passes_web_quality(item: EvidenceItem, request: ResearchRequest) -> bool:
    text = f"{item.title} {item.snippet}".lower()
    if ascii_ratio(text) < 0.75:
        return False
    country = request.country.lower().strip()
    if country and request.require_country and country not in text:
        return False
    important_terms = [term for term in tokenize(request.question) if len(term) > 4]
    matched = sum(1 for term in set(important_terms) if term in text)
    return matched >= min(3, max(1, len(set(important_terms)) // 3))


def rank_evidence(items: list[EvidenceItem], request: ResearchRequest) -> list[EvidenceItem]:
    if not items:
        return []

    country = request.country.lower().strip()
    for item in items:
        similarity = lexical_similarity(request.question, f"{item.title} {item.snippet}")
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

    ranked = sorted(items, key=lambda item: item.score, reverse=True)
    filtered = [
        item
        for item in ranked
        if item.source_type != "web" or (item.score >= 20 and passes_web_quality(item, request))
    ]
    return filtered[: request.max_sources]
