from __future__ import annotations

import requests

from ultimate_search.config import AppConfig
from ultimate_search.models import EvidenceItem, ResearchRequest, SearchPlan


def _citation(index: int, item: EvidenceItem) -> str:
    return f"[{index}] {item.title} ({item.source}) {item.url}"


def synthesize_brief(request: ResearchRequest, plan: SearchPlan, evidence: list[EvidenceItem], config: AppConfig) -> str:
    provider = choose_provider(config)
    if provider != "extractive" and evidence:
        try:
            return llm_brief(request, plan, evidence, config, provider)
        except Exception:
            return extractive_brief(request, plan, evidence, llm_failed=True)
    return extractive_brief(request, plan, evidence)


def choose_provider(config: AppConfig) -> str:
    requested = config.llm_provider.lower().strip()
    available = {
        "openai": bool(config.openai_api_key),
        "anthropic": bool(config.anthropic_api_key),
        "groq": bool(config.groq_api_key),
        "openrouter": bool(config.openrouter_api_key),
        "together": bool(config.together_api_key),
        "custom": bool(config.custom_openai_api_key and config.custom_openai_base_url and config.custom_openai_model),
        "ollama": bool(config.ollama_base_url and config.ollama_model),
        "extractive": True,
    }
    if requested != "auto":
        return requested if available.get(requested) else "extractive"
    for provider in ["openai", "anthropic", "groq", "openrouter", "together", "custom"]:
        if available[provider]:
            return provider
    return "extractive"


def llm_brief(
    request: ResearchRequest,
    plan: SearchPlan,
    evidence: list[EvidenceItem],
    config: AppConfig,
    provider: str,
) -> str:
    evidence_text = "\n\n".join(
        f"[{idx}] Title: {item.title}\nSource: {item.source}; Type: {item.source_type}; Date: {item.published}\n"
        f"URL: {item.url}\nExcerpt: {item.snippet}"
        for idx, item in enumerate(evidence, start=1)
    )
    prompt = f"""
You are a management consulting research analyst. Answer only from the evidence below.

Question: {request.question}
Country/region context: {request.country or "not specified"}
Research angles: {", ".join(plan.source_hints)}

Create a concise client-ready brief with these sections:
- Executive answer
- Key evidence
- Caveats and confidence
- Follow-up checks

Rules:
- Cite sources inline using bracket numbers like [1].
- If evidence is incomplete, say exactly what could not be verified.
- Do not invent approvals, prevalence, statistics, or regulator positions.

Evidence:
{evidence_text}
""".strip()
    content = call_provider(provider, prompt, config)
    return content + "\n\n### Sources\n" + "\n".join(_citation(i, item) for i, item in enumerate(evidence, 1))


def call_provider(provider: str, prompt: str, config: AppConfig) -> str:
    system = "You produce source-grounded consulting research briefs with careful caveats."
    if provider == "anthropic":
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": config.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": config.anthropic_model,
                "max_tokens": 1600,
                "temperature": 0.2,
                "system": system,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=120,
        )
        response.raise_for_status()
        return "\n".join(block.get("text", "") for block in response.json().get("content", []) if block.get("type") == "text")

    if provider == "ollama":
        response = requests.post(
            config.ollama_base_url.rstrip("/") + "/api/chat",
            json={
                "model": config.ollama_model,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
                "stream": False,
                "options": {"temperature": 0.2},
            },
            timeout=120,
        )
        response.raise_for_status()
        return response.json().get("message", {}).get("content", "")

    provider_config = {
        "openai": (config.openai_api_key, "https://api.openai.com/v1", config.openai_model),
        "groq": (config.groq_api_key, "https://api.groq.com/openai/v1", config.groq_model),
        "openrouter": (config.openrouter_api_key, "https://openrouter.ai/api/v1", config.openrouter_model),
        "together": (config.together_api_key, "https://api.together.xyz/v1", config.together_model),
        "custom": (config.custom_openai_api_key, config.custom_openai_base_url, config.custom_openai_model),
    }
    api_key, base_url, model = provider_config[provider]
    response = requests.post(
        base_url.rstrip("/") + "/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            "temperature": 0.2,
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"].get("content", "")


def extractive_brief(
    request: ResearchRequest,
    plan: SearchPlan,
    evidence: list[EvidenceItem],
    llm_failed: bool = False,
) -> str:
    if not evidence:
        return (
            "### Executive answer\n"
            "I could not retrieve enough evidence from the enabled sources to answer this reliably.\n\n"
            "### Suggested next step\n"
            "Enable web search via SearXNG, broaden the question, or add a more specific country, product, disease, or policy term."
        )

    top_items = evidence[: min(6, len(evidence))]
    caveat = (
        "LLM synthesis was configured but failed, so this brief uses the fallback extractive method.\n\n"
        if llm_failed
        else ""
    )
    lines = [
        "### Executive answer",
        caveat
        + "The strongest retrieved evidence is summarized below. Treat this as a first-pass research brief: verify any client-critical claims directly in the cited primary source links.",
        "",
        "### Key evidence",
    ]
    for idx, item in enumerate(top_items, start=1):
        snippet = item.snippet or "No abstract or excerpt was available from the source API."
        lines.append(f"- [{idx}] **{item.title}** ({item.source}, {item.published or 'date not listed'}): {snippet[:500]}")

    lines.extend(
        [
            "",
            "### Caveats and confidence",
            "- This fallback mode extracts and ranks evidence but does not perform deep reasoning across full-text PDFs.",
            "- Absence of evidence in the retrieved set should not be interpreted as absence of approvals, policies, or epidemiology data.",
            "- For country-specific regulatory questions, confirm against the national regulator or official gazette before client use.",
            "",
            "### Follow-up checks",
        ]
    )
    for query in plan.queries[:4]:
        lines.append(f"- {query}")
    lines.extend(["", "### Sources"])
    lines.extend(_citation(i, item) for i, item in enumerate(evidence, 1))
    return "\n".join(lines)
