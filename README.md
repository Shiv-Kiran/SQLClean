# SQL Clean

A command-line interface (CLI) tool designed to optimize and format SQL queries using Google's Gemini generative AI. This tool automates the process of refactoring SQL for both readability and performance, eliminating the need for manual copy-pasting into LLM web interfaces.

## Features

* **Automated Refactoring**: Converts inefficient patterns (like correlated subqueries) into high-performance JOIN structures.
* **Standardized Formatting**: Enforces consistent casing and indentation for improved maintainability.
* **CLI Integration**: Designed to fit into developer workflows via Unix pipes and standard input/output.
* **Modern AI Backend**: Utilizes the Google GenAI SDK and Gemini 2.5 Flash for rapid, accurate code analysis.

## Installation

1. **Clone the Repository**:
```bash
git clone https://github.com/Shiv-Kiran/SQLClean.git
cd SQLClean

```


2. **Install Dependencies**:
```bash
pip install .

```


3. **Configure API Access**:
Store your Google AI Studio API key in your environment:
```bash
export GOOGLE_API_KEY="your_api_key_here"

```



## Usage

### Direct File Input

Process a SQL file by passing the path as an argument:

```bash
sqlclean query.sql

```

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

## Technical Architecture

* **Language**: Python 3.13+
* **CLI Framework**: Typer
* **AI SDK**: google-genai (2026 Unified Version)
* **Model**: Gemini 2.5 Flash

## Project Structure

```text
SQL_Cli/
├── sqlClean.py      # CLI tool (Typer)
├── webapp.py        # Web app (Streamlit)
├── pyproject.toml   # Add "streamlit" to dependencies
├── .env             # Store your API key here
└── README.md

```

## License

This project is licensed under the MIT License.