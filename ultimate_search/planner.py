from __future__ import annotations

import re

from ultimate_search.models import ResearchRequest, SearchPlan


QUESTION_HINTS = {
    "epidemiology": ["prevalence", "incidence", "burden", "rate", "population", "registry"],
    "regulatory": ["regulatory", "approval", "approved", "authority", "orphan", "designation", "guideline"],
    "clinical": ["trial", "efficacy", "safety", "clinical", "standard of care", "treatment"],
    "market": ["market", "pricing", "reimbursement", "access", "HTA", "payer"],
    "mechanism": ["mechanism", "what is", "define", "drug class", "antibody", "pathway"],
}


def infer_hints(question: str) -> list[str]:
    lowered = question.lower()
    hints = [name for name, terms in QUESTION_HINTS.items() if any(term.lower() in lowered for term in terms)]
    return hints or ["general"]


def compact_query(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip(" ?")


def build_plan(request: ResearchRequest) -> SearchPlan:
    question = compact_query(request.question)
    country = compact_query(request.country)
    hints = infer_hints(question)
    queries: list[str] = [question]

    if country and country.lower() not in question.lower():
        queries.append(f"{question} {country}")

    if "epidemiology" in hints:
        queries.extend([
            f"{question} prevalence incidence epidemiology",
            f"{question} systematic review registry population",
        ])
    if "regulatory" in hints:
        queries.extend([
            f"{question} regulatory authority guidance approval",
            f"{question} orphan drug policy market authorization",
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
    if "market" in hints:
        queries.extend([
            f"{question} reimbursement HTA pricing access",
            f"{question} payer policy assessment",
        ])

    if request.depth == "quick":
        query_limit = 3
    elif request.depth == "deep":
        query_limit = 10
    else:
        query_limit = 6

    deduped = list(dict.fromkeys(compact_query(query) for query in queries if compact_query(query)))
    return SearchPlan(original_question=question, queries=deduped[:query_limit], source_hints=hints)
