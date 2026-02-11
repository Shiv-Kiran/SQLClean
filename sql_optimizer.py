import sqlglot
from sqlglot import exp
from google import genai
from rag_config import RAGFactory, RAGStrategy
from service.candidate_generator import generate_candidate
from service.settings import load_settings

SETTINGS = load_settings()
client = genai.Client(api_key=SETTINGS.google_api_key)

SYSTEM_PROMPT = """
You are a Senior DBA. Optimize the provided SQL for performance and readability.
Use any provided context from the repository to inform your optimizations, such as best practices, schema information, or common patterns.
- Return ONLY the optimized SQL. 
- If the input is not SQL, politely explain what it is and offer to convert it if relevant.
- Ensure standard keyword capitalization (SELECT, FROM, JOIN).
"""

def is_valid_sql(text):
    """Checks if the input text resembles a SQL statement."""
    try:
        # We use parse_one; if it's just 'hello', it parses as an Identifier.
        # Real SQL usually parses as a Statement/Select/Command.
        parsed = sqlglot.parse_one(text)
        return not isinstance(parsed, (exp.Identifier, exp.Literal))
    except:
        return False

def optimize_sql(
    sql_input,
    repo_path=None,
    temperature=0.1,
    max_retries=2,
    rag_strategy=RAGStrategy.HYBRID,
):
    if temperature is None:
        temperature = SETTINGS.default_temperature
    if max_retries is None:
        max_retries = SETTINGS.default_max_retries

    current_prompt = sql_input
    user_notes = []
    
    # --- RAG Initialization ---
    rag = RAGFactory.create_rag(rag_strategy)
    
    # --- RAG Indexing ---
    if repo_path:
        print(f"Indexing repository with {rag_strategy.value} RAG: {repo_path}")
        rag.index_directory(repo_path)
        # Retrieve relevant docs
        relevant_docs = rag.retrieve(sql_input, top_k=3)
        if relevant_docs:
            context = "\n".join([f"From {doc['source']}:\n{doc['content']}" for doc in relevant_docs])
            current_prompt = f"Context from repository:\n{context}\n\nSQL to optimize:\n{sql_input}"
            user_notes.append(f"-- Note: Used repository context ({rag_strategy.value} RAG) for optimization.")
    
    # --- PHASE 1: Input Defensive Check ---
    if not is_valid_sql(sql_input):
        print("User Input Invalid")
        user_notes.append("-- Note: Input did not look like standard SQL. Asking AI to interpret.")
        current_prompt = f"The following input might not be valid SQL. If it is text describing a query, write the SQL. If it's nonsense, say so: {sql_input}"

    attempts = 0
    while attempts <= max_retries:
        # --- PHASE 2: Candidate Generation ---
        suggested_sql = generate_candidate(
            client=client,
            prompt=current_prompt,
            system_prompt=SYSTEM_PROMPT,
            temperature=temperature,
            model=SETTINGS.model_name,
        )

        # --- PHASE 3: Output Defensive Check ---
        try:
            sqlglot.transpile(suggested_sql)
            
            # Combine notes and final SQL for the user
            final_output = "\n".join(user_notes) + "\n" + suggested_sql if user_notes else suggested_sql
            return final_output.strip()
            
        except sqlglot.errors.ParseError as e:
            attempts += 1
            print(f"Attempt {attempts} failed. Error: {e}")
            
            if attempts > max_retries:
                return f"-- [Validation Failed after {max_retries} attempts]\n-- Error: {e}\n{suggested_sql}"
            
            # --- PHASE 4: Self-Correction Loop ---
            current_prompt = (
                f"Your previous SQL output had a syntax error: {str(e)}\n"
                f"Please fix this SQL and return ONLY the corrected code:\n{suggested_sql}"
            )
            user_notes.append(f"-- Note: AI output was corrected for syntax (Attempt {attempts}).")

    return None
