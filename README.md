# SQL Clean

A minimalist tool designed to optimize and format SQL queries using Google's Gemini generative AI. This project provides both a high-performance CLI for local development and a web interface for quick refactors.

## Features

* **Automated Refactoring**: Converts inefficient patterns (like correlated subqueries) into high-performance JOIN structures.
* **Standardized Formatting**: Enforces consistent casing and indentation for improved maintainability.
* **CLI Integration**: Designed to fit into developer workflows via Unix pipes and standard input/output.
* **Modern AI Backend**: Powered by the Gemini 2.5 Flash model for rapid, accurate code analysis.
* **SQL Defensive Check**: Incorporates `sqlglot` to validate and parse SQL queries before optimization.
* **Local RAG Support**: Index local repositories with .md and .sql files to provide context-aware optimizations.

## Installation

1. **Clone the Repository**:
```bash
git clone https://github.com/Shiv-Kiran/SQLClean.git
cd SQLClean

```


2. **Install the Package**:
```bash
pip install .

```


3. **Configure API Access**:
Store your Google AI Studio API key in your environment variables:
```bash
export GOOGLE_API_KEY="your_api_key_here"

```



## Usage

### Direct File Input

Process a SQL file by passing the path as an argument:

```bash
sqlclean query.sql

```

### With Repository Context (RAG)

Index a local repository for context-aware optimization. The repository can contain multiple subfolders for different domains:

```bash
# Use education schema context
sqlclean education_query.sql --repo sqlSchema/education

# Use e-commerce schema context  
sqlclean ecommerce_query.sql --repo sqlSchema/ecommerce
```

The tool indexes all `.md` and `.sql` files in the specified repository, providing schema-aware optimizations.

### Piped Input

Integrate with other terminal commands using standard pipes:

```bash
cat messy_query.sql | sqlclean

```

### Saving Output

Redirect the optimized output to a new file:

```bash
sqlclean input.sql > optimized.sql

```

## Web Interface

For users who prefer a graphical interface, a live version of the tool is available at:
**[sqlclean.streamlit.app](https://sqlclean-unrcjopcjq3kawbb4qks3b.streamlit.app/)**

The web interface supports the same Classic Sparse RAG (TF-IDF + cosine) functionality as the CLI - you can either specify a server-side repository path or upload .md and .sql files directly from your local machine for context-aware optimizations.

Sparse Lexical RAG : Good for smaller datasets and quick setups. Fails for synonyms, semantic intent and query optimization. 

Added Chroma bge-large based Semantic RAG which is better at understanding intent of SQL queries

FAISS vector search for faster and more accurate retrieval.

TODO: Optmizing the sql refactoring with SQL specific optimizations

* Embedding-based RAG
* Hybrid RAG (Lexical + Semantic)
* Structure aware RAG (Using SQL ASTs for better retrieval)
* Schema-first RAG 
* Query-Pattern RAG (For specific optimization patterns)



To run locally:
```bash
streamlit run webapp.py
```

## Technical Architecture

* **Language**: Python 3.13+
* **CLI Framework**: Typer
* **Web Framework**: Streamlit
* **AI SDK**: `google-genai`
* **Model**: Gemini 2.5 Flash

## Project Structure

```text
SQL_Cli/
├── sqlClean.py      # CLI tool (Typer)
├── sql_optimizer.py # Core optimization logic with RAG
├── rag_utils.py     # RAG indexing and retrieval utilities
├── webapp.py        # Web app (Streamlit)
├── pyproject.toml   # Project metadata and dependencies
├── .env.example     # Environment variable template
└── README.md        # Project documentation

```

## License

This project is licensed under the MIT License.
