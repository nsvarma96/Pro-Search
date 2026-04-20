from __future__ import annotations

from ultimate_search.config import AppConfig
from ultimate_search.models import ResearchRequest, ResearchResult
from ultimate_search.planner import build_plan
from ultimate_search.ranking import rank_evidence
from ultimate_search.sources import collect_sources
from ultimate_search.synthesizer import synthesize_brief


def run_research(request: ResearchRequest, config: AppConfig) -> ResearchResult:
    plan = build_plan(request)
    raw_evidence = collect_sources(plan, request.enabled_sources, config)
    ranked_evidence = rank_evidence(raw_evidence, request)
    brief = synthesize_brief(request, plan, ranked_evidence, config)
    return ResearchResult(request=request, plan=plan, evidence=ranked_evidence, brief=brief)
