from __future__ import annotations

import html
from html.parser import HTMLParser
import re
import xml.etree.ElementTree as ET
from urllib.parse import quote_plus, unquote, urlparse, parse_qs

import requests

from ultimate_search.config import AppConfig
from ultimate_search.models import EvidenceItem, SearchPlan


def _get_json(url: str, timeout: int) -> dict:
    response = requests.get(url, timeout=timeout, headers={"User-Agent": "UltimateSearch/0.1"})
    response.raise_for_status()
    return response.json()


def _get_text(url: str, timeout: int) -> str:
    response = requests.get(
        url,
        timeout=timeout,
        headers={
            "User-Agent": "Mozilla/5.0 UltimateSearch/0.1",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    response.raise_for_status()
    return response.text


def _clean(text: str) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    return re.sub(r"\s+", " ", text).strip()


def search_pubmed(query: str, config: AppConfig, limit: int = 5) -> list[EvidenceItem]:
    encoded = quote_plus(query)
    search_url = (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        f"?db=pubmed&retmode=json&retmax={limit}&sort=relevance&term={encoded}"
    )
    ids = _get_json(search_url, config.request_timeout).get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []
    summary_url = (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        f"?db=pubmed&retmode=json&id={','.join(ids)}"
    )
    data = _get_json(summary_url, config.request_timeout).get("result", {})
    items: list[EvidenceItem] = []
    for pmid in ids:
        record = data.get(pmid, {})
        title = _clean(record.get("title", "PubMed record"))
        authors = record.get("authors", [])
        author_text = ", ".join(author.get("name", "") for author in authors[:3])
        snippet = _clean(f"{record.get('fulljournalname', '')}. {author_text}. {record.get('pubdate', '')}")
        items.append(
            EvidenceItem(
                title=title,
                url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                source="PubMed",
                source_type="peer-reviewed / biomedical",
                snippet=snippet,
                published=record.get("pubdate", ""),
                metadata={"pmid": pmid},
            )
        )
    return items


def search_europe_pmc(query: str, config: AppConfig, limit: int = 5) -> list[EvidenceItem]:
    url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={quote_plus(query)}&format=json&pageSize={limit}"
    data = _get_json(url, config.request_timeout)
    items: list[EvidenceItem] = []
    for record in data.get("resultList", {}).get("result", []):
        pmid = record.get("pmid") or record.get("id", "")
        link = record.get("doi")
        url = f"https://doi.org/{link}" if link else f"https://europepmc.org/article/MED/{pmid}"
        snippet = _clean(record.get("abstractText") or record.get("journalTitle") or "")
        items.append(
            EvidenceItem(
                title=_clean(record.get("title", "Europe PMC record")),
                url=url,
                source="Europe PMC",
                source_type="peer-reviewed / biomedical",
                snippet=snippet[:900],
                published=record.get("firstPublicationDate") or record.get("pubYear", ""),
                metadata={"pmid": pmid, "doi": record.get("doi", "")},
            )
        )
    return items


def search_clinical_trials(query: str, config: AppConfig, limit: int = 5) -> list[EvidenceItem]:
    url = (
        "https://clinicaltrials.gov/api/v2/studies"
        f"?query.term={quote_plus(query)}&pageSize={limit}&format=json"
    )
    data = _get_json(url, config.request_timeout)
    items: list[EvidenceItem] = []
    for study in data.get("studies", []):
        protocol = study.get("protocolSection", {})
        identification = protocol.get("identificationModule", {})
        status = protocol.get("statusModule", {})
        design = protocol.get("designModule", {})
        nct_id = identification.get("nctId", "")
        title = identification.get("briefTitle") or identification.get("officialTitle") or "ClinicalTrials.gov study"
        phase = ", ".join(design.get("phases", []))
        snippet = _clean(
            f"{status.get('overallStatus', '')}. {phase}. Start: {status.get('startDateStruct', {}).get('date', '')}. "
            f"Completion: {status.get('completionDateStruct', {}).get('date', '')}."
        )
        items.append(
            EvidenceItem(
                title=_clean(title),
                url=f"https://clinicaltrials.gov/study/{nct_id}" if nct_id else "https://clinicaltrials.gov/",
                source="ClinicalTrials.gov",
                source_type="trial registry",
                snippet=snippet,
                published=status.get("studyFirstSubmitDate", ""),
                metadata={"nct_id": nct_id},
            )
        )
    return items


def search_openfda(query: str, config: AppConfig, limit: int = 5) -> list[EvidenceItem]:
    words = [word for word in re.findall(r"[A-Za-z0-9-]{4,}", query) if word.lower() not in {"what", "which", "approved", "regulatory"}]
    if not words:
        return []
    search_terms = " OR ".join(f'openfda.brand_name:"{word}" openfda.generic_name:"{word}" indications_and_usage:"{word}"' for word in words[:5])
    url = f"https://api.fda.gov/drug/label.json?search={quote_plus(search_terms)}&limit={limit}"
    try:
        data = _get_json(url, config.request_timeout)
    except requests.HTTPError:
        return []
    items: list[EvidenceItem] = []
    for record in data.get("results", []):
        brand = ", ".join(record.get("openfda", {}).get("brand_name", [])[:2])
        generic = ", ".join(record.get("openfda", {}).get("generic_name", [])[:2])
        title = _clean(" / ".join(part for part in [brand, generic] if part) or "FDA drug label")
        indications = " ".join(record.get("indications_and_usage", [])[:1])
        warnings = " ".join(record.get("warnings", [])[:1])
        snippet = _clean(indications or warnings)[:900]
        set_id = record.get("set_id", "")
        items.append(
            EvidenceItem(
                title=title,
                url=f"https://dailymed.nlm.nih.gov/dailymed/search.cfm?query={quote_plus(title)}",
                source="openFDA",
                source_type="regulatory label",
                snippet=snippet,
                published=record.get("effective_time", ""),
                metadata={"set_id": set_id},
            )
        )
    return items


def search_searxng(query: str, config: AppConfig, limit: int = 5) -> list[EvidenceItem]:
    if not config.searxng_url:
        return []
    params = f"?q={quote_plus(query)}&format=json&language=en"
    data = _get_json(config.searxng_url.rstrip("/") + params, config.request_timeout)
    items: list[EvidenceItem] = []
    for result in data.get("results", [])[:limit]:
        items.append(
            EvidenceItem(
                title=_clean(result.get("title", "Web result")),
                url=result.get("url", ""),
                source="SearXNG",
                source_type="web",
                snippet=_clean(result.get("content", ""))[:900],
                published=result.get("publishedDate", ""),
            )
        )
    return items


class DuckDuckGoParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[dict[str, str]] = []
        self._current: dict[str, str] | None = None
        self._field = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {key: value or "" for key, value in attrs}
        classes = attr.get("class", "")
        if tag == "a" and "result__a" in classes:
            self._current = {"title": "", "url": self._normalize_url(attr.get("href", "")), "snippet": ""}
            self._field = "title"
        elif self._current is not None and tag in {"a", "div"} and "result__snippet" in classes:
            self._field = "snippet"

    def handle_data(self, data: str) -> None:
        if self._current is not None and self._field:
            self._current[self._field] += data

    def handle_endtag(self, tag: str) -> None:
        if self._current is not None and tag == "a" and self._field == "title":
            if self._current["title"].strip() and self._current["url"].strip():
                self.results.append(self._current)
            self._current = None
            self._field = ""
        elif self._field == "snippet" and tag in {"a", "div"}:
            self._field = ""

    @staticmethod
    def _normalize_url(url: str) -> str:
        parsed = urlparse(html.unescape(url))
        if parsed.path == "/l/":
            uddg = parse_qs(parsed.query).get("uddg", [""])[0]
            return unquote(uddg)
        return html.unescape(url)


def search_duckduckgo(query: str, config: AppConfig, limit: int = 5) -> list[EvidenceItem]:
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    parser = DuckDuckGoParser()
    parser.feed(_get_text(url, config.request_timeout))
    items: list[EvidenceItem] = []
    for result in parser.results[:limit]:
        items.append(
            EvidenceItem(
                title=_clean(result.get("title", "Web result")),
                url=result.get("url", ""),
                source="DuckDuckGo",
                source_type="web",
                snippet=_clean(result.get("snippet", ""))[:900],
            )
        )
    return items


def search_bing(query: str, config: AppConfig, limit: int = 5) -> list[EvidenceItem]:
    url = f"https://www.bing.com/search?format=rss&q={quote_plus(query)}"
    xml_text = _get_text(url, config.request_timeout)
    root = ET.fromstring(xml_text)
    items: list[EvidenceItem] = []
    for channel_item in root.findall("./channel/item")[:limit]:
        items.append(
            EvidenceItem(
                title=_clean(channel_item.findtext("title", "Web result")),
                url=channel_item.findtext("link", ""),
                source="Bing Web",
                source_type="web",
                snippet=_clean(channel_item.findtext("description", ""))[:900],
                published=channel_item.findtext("pubDate", ""),
            )
        )
    return items


def search_brave(query: str, config: AppConfig, limit: int = 5) -> list[EvidenceItem]:
    if not config.brave_api_key:
        return []
    response = requests.get(
        "https://api.search.brave.com/res/v1/web/search",
        params={"q": query, "count": limit, "search_lang": "en"},
        headers={"X-Subscription-Token": config.brave_api_key, "Accept": "application/json"},
        timeout=config.request_timeout,
    )
    response.raise_for_status()
    items: list[EvidenceItem] = []
    for result in response.json().get("web", {}).get("results", [])[:limit]:
        items.append(
            EvidenceItem(
                title=_clean(result.get("title", "Web result")),
                url=result.get("url", ""),
                source="Brave Search",
                source_type="web",
                snippet=_clean(result.get("description", ""))[:900],
                published=result.get("age", ""),
            )
        )
    return items


def search_tavily(query: str, config: AppConfig, limit: int = 5) -> list[EvidenceItem]:
    if not config.tavily_api_key:
        return []
    response = requests.post(
        "https://api.tavily.com/search",
        json={"api_key": config.tavily_api_key, "query": query, "max_results": limit, "search_depth": "basic"},
        timeout=config.request_timeout,
    )
    response.raise_for_status()
    items: list[EvidenceItem] = []
    for result in response.json().get("results", [])[:limit]:
        items.append(
            EvidenceItem(
                title=_clean(result.get("title", "Web result")),
                url=result.get("url", ""),
                source="Tavily",
                source_type="web",
                snippet=_clean(result.get("content", ""))[:900],
                published=result.get("published_date", ""),
            )
        )
    return items


def search_serpapi(query: str, config: AppConfig, limit: int = 5) -> list[EvidenceItem]:
    if not config.serpapi_api_key:
        return []
    response = requests.get(
        "https://serpapi.com/search.json",
        params={"engine": "google", "q": query, "api_key": config.serpapi_api_key, "num": limit},
        timeout=config.request_timeout,
    )
    response.raise_for_status()
    items: list[EvidenceItem] = []
    for result in response.json().get("organic_results", [])[:limit]:
        items.append(
            EvidenceItem(
                title=_clean(result.get("title", "Web result")),
                url=result.get("link", ""),
                source="SerpAPI",
                source_type="web",
                snippet=_clean(result.get("snippet", ""))[:900],
                published=result.get("date", ""),
            )
        )
    return items


def collect_sources(plan: SearchPlan, enabled_sources: dict[str, bool], config: AppConfig) -> list[EvidenceItem]:
    per_query = 3 if len(plan.queries) > 4 else 5
    results: list[EvidenceItem] = []
    healthcare = bool({"epidemiology", "healthcare_regulatory", "clinical", "mechanism"} & set(plan.source_hints))
    source_functions = [
        ("brave", search_brave),
        ("tavily", search_tavily),
        ("serpapi", search_serpapi),
        ("bing", search_bing),
        ("duckduckgo", search_duckduckgo),
        ("searxng", search_searxng),
        ("pubmed", search_pubmed),
        ("europe_pmc", search_europe_pmc),
        ("clinical_trials", search_clinical_trials),
        ("openfda", search_openfda),
    ]
    for query in plan.queries:
        for source_name, func in source_functions:
            if not enabled_sources.get(source_name, False):
                continue
            if source_name in {"pubmed", "europe_pmc", "clinical_trials", "openfda"} and not healthcare:
                continue
            try:
                results.extend(func(query, config, limit=per_query))
            except Exception:
                continue
    return dedupe(results)


def dedupe(items: list[EvidenceItem]) -> list[EvidenceItem]:
    seen: set[str] = set()
    deduped: list[EvidenceItem] = []
    for item in items:
        key = (item.url or item.title).lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped
