from sql_optimizer import optimize_sql
import os
import tempfile
from rag_config import RAGStrategy

# --- CORE LOGIC ---
# Using the same logic as your CLI

def get_optimized_sql(sql_input, repo_path=None, uploaded_files=None, rag_strategy=RAGStrategy.HYBRID):
    if uploaded_files:
        # Create temporary directory and save uploaded files
        with tempfile.TemporaryDirectory() as temp_dir:
            for uploaded_file in uploaded_files:
                file_path = os.path.join(temp_dir, uploaded_file.name)
                with open(file_path, 'wb') as f:
                    f.write(uploaded_file.getbuffer())
            return optimize_sql(sql_input, repo_path=temp_dir, rag_strategy=rag_strategy)
    else:
        return optimize_sql(sql_input, repo_path=repo_path, rag_strategy=rag_strategy)

# --- UI DESIGN ---
# Only import streamlit when running as main script
if __name__ == "__main__":
    import streamlit as st
    
    # --- PAGE CONFIG ---
    st.set_page_config(page_title="SQL Clean", page_icon="🪄")
    
    st.title("🪄 SQL Clean")
    st.markdown("Transform messy queries into high-performance SQL with optional repository context.")
    
    # RAG Strategy Selection
    st.sidebar.markdown("### RAG Configuration")
    rag_strategy_name = st.sidebar.radio(
        "Choose RAG Strategy:",
        ["Simple (TF-IDF)", "Hybrid (TF-IDF + Chroma + FAISS)"],
        help="Simple: Fast, lightweight. Hybrid: Better semantic understanding"
    )
    rag_strategy = RAGStrategy.SIMPLE if "Simple" in rag_strategy_name else RAGStrategy.HYBRID
    
    if rag_strategy == RAGStrategy.HYBRID:
        st.sidebar.info("🔀 Hybrid RAG combines TF-IDF, Chroma embeddings, and FAISS for best results")
    else:
        st.sidebar.info("⚡ Simple RAG uses TF-IDF for fast keyword-based retrieval")
    
    # Input area
    raw_sql = st.text_area("Paste your SQL here:", height=200, placeholder="SELECT * FROM users...")
    
    # Repository selection method
    repo_method = st.radio(
        "Repository Source:",
        ["Server Path", "Upload Files"],
        help="Choose how to provide repository context for RAG"
    )
    
    repo_path = None
    uploaded_files = None
    
    if repo_method == "Server Path":
        repo_path = st.text_input("Repository Path (on server):", 
                                 placeholder="e.g., sqlSchema/education or /path/to/your/repo",
                                 help="Specify a directory path accessible to the server containing .md and .sql files")
    else:  # Upload Files
        uploaded_files = st.file_uploader(
            "Upload repository files (.md and .sql):",
            accept_multiple_files=True,
            type=['md', 'sql'],
            help="Upload .md and .sql files from your local machine to use as repository context"
        )
        if uploaded_files:
            st.info(f"📁 {len(uploaded_files)} files uploaded for context")
    
    if st.button("Optimize SQL"):
        if raw_sql.strip():
            context_msg = ""
            if repo_method == "Server Path" and repo_path and repo_path.strip():
                context_msg = f" with repository context from `{repo_path}`..."
            elif repo_method == "Upload Files" and uploaded_files:
                context_msg = f" with {len(uploaded_files)} uploaded files..."
            else:
                context_msg = "..."
                
            with st.spinner("Optimizing" + context_msg):
                try:
                    optimized = get_optimized_sql(raw_sql, repo_path, uploaded_files, rag_strategy)
                    
                    # Show results in columns
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader("Original")
                        st.code(raw_sql, language="sql")
                    with col2:
                        st.subheader("Optimized")
                        st.code(optimized, language="sql")
                        
                    if (repo_method == "Server Path" and repo_path and repo_path.strip()) or \
                       (repo_method == "Upload Files" and uploaded_files):
                        st.info("✅ Used repository context for optimization")
                    st.success("Refactoring complete!")
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.warning("Please enter some SQL first.")