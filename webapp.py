import os
import tempfile

from api.client import optimize_sql_via_api
from rag_config import RAGStrategy
from service.settings import load_settings
from sql_optimizer import optimize_sql

# --- CORE LOGIC ---
# Uses the same optimization path as CLI by default.
SETTINGS = load_settings()


def get_optimized_sql(
    sql_input,
    repo_path=None,
    uploaded_files=None,
    rag_strategy=RAGStrategy.HYBRID,
    use_api_mode=False,
    api_base_url=None,
):
    if use_api_mode and not uploaded_files:
        response = optimize_sql_via_api(
            base_url=api_base_url or SETTINGS.api_base_url,
            payload={
                "sql_input": sql_input,
                "repo_path": repo_path,
                "rag_strategy": rag_strategy.value if hasattr(rag_strategy, "value") else rag_strategy,
                "candidate_count": SETTINGS.default_candidate_count,
                "execution_verify": SETTINGS.default_execution_verify,
                "explain_analyze": SETTINGS.default_explain_analyze,
            },
        )
        return response.get("optimized_sql", "")

    if uploaded_files:
        with tempfile.TemporaryDirectory() as temp_dir:
            for uploaded_file in uploaded_files:
                file_path = os.path.join(temp_dir, uploaded_file.name)
                with open(file_path, "wb") as handle:
                    handle.write(uploaded_file.getbuffer())
            return optimize_sql(sql_input, repo_path=temp_dir, rag_strategy=rag_strategy)

    return optimize_sql(sql_input, repo_path=repo_path, rag_strategy=rag_strategy)


# --- UI DESIGN ---
if __name__ == "__main__":
    import streamlit as st

    st.set_page_config(page_title="SQL Clean", page_icon="SQL")
    st.title("SQL Clean")
    st.markdown("Transform messy queries into high-performance SQL with optional repository context.")

    api_mode = st.sidebar.toggle(
        "Use API Mode",
        value=SETTINGS.api_mode,
        help="If enabled, calls backend API for optimization.",
    )
    api_base_url = st.sidebar.text_input(
        "API Base URL",
        value=SETTINGS.api_base_url,
        disabled=not api_mode,
    )

    st.sidebar.markdown("### RAG Configuration")
    rag_strategy_name = st.sidebar.radio(
        "Choose RAG Strategy:",
        ["Simple (TF-IDF)", "Hybrid (TF-IDF + Chroma + FAISS)"],
        help="Simple: Fast, lightweight. Hybrid: Better semantic understanding",
    )
    rag_strategy = RAGStrategy.SIMPLE if "Simple" in rag_strategy_name else RAGStrategy.HYBRID

    raw_sql = st.text_area("Paste your SQL here:", height=200, placeholder="SELECT * FROM users...")

    repo_method = st.radio(
        "Repository Source:",
        ["Server Path", "Upload Files"],
        help="Choose how to provide repository context for RAG",
    )

    repo_path = None
    uploaded_files = None

    if repo_method == "Server Path":
        repo_path = st.text_input(
            "Repository Path (on server):",
            placeholder="e.g., sqlSchema/education or /path/to/your/repo",
            help="Path containing .md and .sql files.",
        )
    else:
        uploaded_files = st.file_uploader(
            "Upload repository files (.md and .sql):",
            accept_multiple_files=True,
            type=["md", "sql"],
            help="Upload context files from your machine.",
        )
        if uploaded_files:
            st.info(f"{len(uploaded_files)} files uploaded for context")

    if st.button("Optimize SQL"):
        if not raw_sql.strip():
            st.warning("Please enter some SQL first.")
        else:
            context_msg = ""
            if repo_method == "Server Path" and repo_path and repo_path.strip():
                context_msg = f" with repository context from `{repo_path}`..."
            elif repo_method == "Upload Files" and uploaded_files:
                context_msg = f" with {len(uploaded_files)} uploaded files..."
            else:
                context_msg = "..."

            with st.spinner("Optimizing" + context_msg):
                try:
                    optimized = get_optimized_sql(
                        raw_sql,
                        repo_path=repo_path,
                        uploaded_files=uploaded_files,
                        rag_strategy=rag_strategy,
                        use_api_mode=api_mode,
                        api_base_url=api_base_url,
                    )

                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader("Original")
                        st.code(raw_sql, language="sql")
                    with col2:
                        st.subheader("Optimized")
                        st.code(optimized, language="sql")

                    if (repo_method == "Server Path" and repo_path and repo_path.strip()) or (
                        repo_method == "Upload Files" and uploaded_files
                    ):
                        st.info("Used repository context for optimization")
                    st.success("Refactoring complete")
                except Exception as exc:
                    st.error(f"Error: {exc}")

