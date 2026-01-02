import os
import sqlglot
from sqlglot import exp
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

SYSTEM_PROMPT = """
You are a Senior DBA. Optimize the provided SQL for performance and readability.
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

def optimize_sql(sql_input, temperature=0.1, max_retries=2):
    current_prompt = sql_input
    user_notes = []
    
    # --- PHASE 1: Input Defensive Check ---
    if not is_valid_sql(sql_input):
        print("User Input Invalid")
        user_notes.append("-- Note: Input did not look like standard SQL. Asking AI to interpret.")
        current_prompt = f"The following input might not be valid SQL. If it is text describing a query, write the SQL. If it's nonsense, say so: {sql_input}"

    attempts = 0
    while attempts <= max_retries:
        # --- PHASE 2: Gemini Call ---
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=current_prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=temperature,
            )
        )
        
        suggested_sql = response.text.strip()
        
        # Clean Markdown backticks
        if "```" in suggested_sql:
            suggested_sql = suggested_sql.split("```")[1].replace("sql", "").strip()

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