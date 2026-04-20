from __future__ import annotations

import re

from ultimate_search.models import ResearchRequest, SearchPlan


QUESTION_HINTS = {
    "epidemiology": ["prevalence", "incidence", "disease burden", "patient population", "registry"],
    "healthcare_regulatory": ["drug", "pharma", "orphan", "medicine", "therapeutic", "vaccine", "biologic"],
    "clinical": ["trial", "efficacy", "safety", "clinical", "standard of care", "treatment"],
    "market": [
        "market",
        "size",
        "share",
        "forecast",
        "revenue",
        "sales",
        "key players",
        "competitors",
        "landscape",
        "distributors",
        "manufacturers",
    ],
    "policy": ["regulatory", "regulation", "authority", "approval", "approved", "licensing", "compliance"],
    "definition": ["what is", "define", "meaning of", "overview"],
    "mechanism": ["mechanism of action", "drug class", "antibody", "pathway", "receptor", "enzyme"],
}


def infer_hints(question: str) -> list[str]:
    lowered = question.lower()
    hints = [name for name, terms in QUESTION_HINTS.items() if any(term.lower() in lowered for term in terms)]
    if "market" in hints and "definition" in hints:
        hints.remove("definition")
    if any(term in lowered for term in ["drug", "pharma", "medicine", "disease", "syndrome", "cancer", "therapy", "antibody"]):
        if "healthcare_regulatory" not in hints:
            hints.append("healthcare_regulatory")
    return hints or ["general"]


def compact_query(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip(" ?")


def focus_terms(question: str) -> str:
    focus = question.lower()
    replacements = [
        "what is",
        "what are",
        "the size of",
        "size of",
        "and who are the key players",
        "who are the key players",
        "key players",
        "market size",
    ]
    for phrase in replacements:
        focus = focus.replace(phrase, " ")
    focus = re.sub(r"\b(in|for|of|the|a|an|and|are|is)\b", " ", focus)
    return compact_query(focus)


def build_plan(request: ResearchRequest) -> SearchPlan:
    question = compact_query(request.question)
    country = compact_query(request.country)
    hints = infer_hints(question)
    focus = focus_terms(question)
    queries: list[str] = [question]

    if country and country.lower() not in question.lower():
        queries.append(f"{question} {country}")

    if "epidemiology" in hints:
        queries.extend([
            f"{question} prevalence incidence epidemiology",
            f"{question} systematic review registry population",
        ])
    if "market" in hints:
        market_focus = compact_query(f"{focus} {country}") if country and country.lower() not in focus.lower() else focus
        queries.extend([
            f"{market_focus} market size revenue forecast",
            f"{market_focus} key players companies distributors",
            f"{market_focus} importers suppliers manufacturers",
            f"{market_focus} industry report",
        ])
    if "policy" in hints:
        queries.extend([
            f"{question} regulation standards compliance authority",
            f"{question} licensing approval requirements",
        ])
    if "clinical" in hints:
        queries.extend([
            f"{question} clinical trial evidence",
            f"{question} treatment guideline safety efficacy",
        ])
    if "mechanism" in hints:
        queries.extend([
            f"{question} mechanism of action review",
            f"{question} approved products label",
        ])
    if "definition" in hints and "mechanism" not in hints:
        queries.extend([
            f"{question} overview explanation",
            f"{question} industry background",
        ])

    if request.depth == "quick":
        query_limit = 3
    elif request.depth == "deep":
        query_limit = 10
    else:
        query_limit = 6

    deduped = list(dict.fromkeys(compact_query(query) for query in queries if compact_query(query)))
    return SearchPlan(original_question=question, queries=deduped[:query_limit], source_hints=hints)
