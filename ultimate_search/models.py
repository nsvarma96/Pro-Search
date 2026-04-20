from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ResearchRequest:
    question: str
    country: str = ""
    depth: str = "standard"
    output_style: str = "Both"
    max_sources: int = 16
    enabled_sources: dict[str, bool] = field(default_factory=dict)
    require_country: bool = True

    def model_copy(self, update: dict[str, Any] | None = None) -> "ResearchRequest":
        data = self.__dict__.copy()
        data["enabled_sources"] = self.enabled_sources.copy()
        if update:
            data.update(update)
        return ResearchRequest(**data)


@dataclass
class SearchPlan:
    original_question: str
    queries: list[str]
    source_hints: list[str]


@dataclass
class EvidenceItem:
    title: str
    url: str
    source: str
    snippet: str
    published: str = ""
    source_type: str = "web"
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_row(self) -> dict[str, Any]:
        return {
            "score": round(self.score, 1),
            "source": self.source,
            "source_type": self.source_type,
            "published": self.published,
            "title": self.title,
            "snippet": self.snippet,
            "url": self.url,
        }


@dataclass
class ResearchResult:
    request: ResearchRequest
    plan: SearchPlan
    evidence: list[EvidenceItem]
    brief: str
