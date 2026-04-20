from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from ultimate_search.config import AppConfig
from ultimate_search.exporters import brief_to_docx, evidence_to_xlsx
from ultimate_search.models import ResearchRequest
from ultimate_search.pipeline import run_research


st.set_page_config(
    page_title="Ultimate Search",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded",
)


def init_state() -> None:
    st.session_state.setdefault("result", None)
    st.session_state.setdefault("last_question", "")


def sidebar_controls() -> tuple[ResearchRequest, AppConfig]:
    st.sidebar.title("Ultimate Search")
    st.sidebar.caption("Source-grounded research briefs for consulting questions.")

    country = st.sidebar.text_input("Country / region", placeholder="Optional, e.g. USA, UAE, South Africa")
    depth = st.sidebar.radio("Depth", ["Quick", "Standard", "Deep"], index=1)
    output_style = st.sidebar.radio("Output style", ["Executive brief", "Evidence table", "Both"], index=2)

    st.sidebar.divider()
    st.sidebar.subheader("Sources")
    use_pubmed = st.sidebar.checkbox("PubMed", value=True)
    use_europe_pmc = st.sidebar.checkbox("Europe PMC", value=True)
    use_clinical_trials = st.sidebar.checkbox("ClinicalTrials.gov", value=True)
    use_openfda = st.sidebar.checkbox("openFDA labels", value=True)
    use_web = st.sidebar.checkbox("SearXNG web search", value=False)

    st.sidebar.divider()
    st.sidebar.subheader("Behavior")
    max_sources = st.sidebar.slider("Max evidence items", 5, 40, 16, 1)
    require_country = st.sidebar.checkbox("Prioritize country-specific evidence", value=True)

    request = ResearchRequest(
        question="",
        country=country.strip(),
        depth=depth.lower(),
        output_style=output_style,
        max_sources=max_sources,
        enabled_sources={
            "pubmed": use_pubmed,
            "europe_pmc": use_europe_pmc,
            "clinical_trials": use_clinical_trials,
            "openfda": use_openfda,
            "searxng": use_web,
        },
        require_country=require_country,
    )
    return request, AppConfig.from_streamlit()


def render_result() -> None:
    result = st.session_state.get("result")
    if not result:
        return

    st.divider()
    st.subheader("Research Plan")
    for idx, query in enumerate(result.plan.queries, start=1):
        st.write(f"{idx}. {query}")

    st.subheader("Brief")
    st.markdown(result.brief)

    st.subheader("Evidence")
    rows = [item.to_row() for item in result.evidence]
    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "url": st.column_config.LinkColumn("url"),
                "score": st.column_config.ProgressColumn("score", min_value=0, max_value=100),
            },
        )

        csv = df.to_csv(index=False).encode("utf-8")
        xlsx = evidence_to_xlsx(df)
        docx = brief_to_docx(result.brief, result.evidence, result.request.question)

        c1, c2, c3 = st.columns(3)
        with c1:
            st.download_button("CSV", csv, "ultimate_search_evidence.csv", "text/csv", use_container_width=True)
        with c2:
            st.download_button(
                "Excel",
                xlsx,
                "ultimate_search_evidence.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        with c3:
            st.download_button(
                "Word brief",
                docx,
                "ultimate_search_brief.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )
    else:
        st.info("No evidence was retrieved. Try enabling more sources or broadening the question.")


def main() -> None:
    init_state()
    base_request, config = sidebar_controls()

    st.title("Ultimate Search")
    st.caption("Ask broad, peculiar, country-specific research questions and get a cited evidence brief.")

    with st.form("question_form"):
        question = st.text_area(
            "Research question",
            value=st.session_state.last_question,
            height=120,
            placeholder="Example: What are the regulatory challenges for orphan drugs in South Africa?",
        )
        submitted = st.form_submit_button("Run research", type="primary", use_container_width=True)

    if submitted:
        clean_question = question.strip()
        if not clean_question:
            st.warning("Enter a research question first.")
            return

        st.session_state.last_question = clean_question
        request = base_request.model_copy(update={"question": clean_question})
        started = datetime.now()
        with st.status("Researching sources and building a cited brief...", expanded=True) as status:
            st.write("Planning search strategy")
            try:
                result = run_research(request, config)
                elapsed = (datetime.now() - started).total_seconds()
                st.session_state.result = result
                status.update(label=f"Research complete in {elapsed:.1f}s", state="complete", expanded=False)
            except Exception as exc:
                status.update(label="Research failed", state="error", expanded=True)
                st.exception(exc)
                return

    render_result()


if __name__ == "__main__":
    main()
