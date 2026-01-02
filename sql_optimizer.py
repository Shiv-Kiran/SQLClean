import os
import sqlglot
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

SYSTEM_PROMPT = """
You are a Senior Database Administrator and SQL Optimization expert.
Your goal is to:
1. Prettify the SQL (proper indentation, capitalization of keywords).
2. Performance Optimize the SQL (suggest JOINs over subqueries, avoid SELECT *, etc.).
3. Return ONLY the optimized SQL code. Do not include explanations.
"""

def optimize_sql(sql_input, temperature=0.1, max_retries=2):
    current_input = sql_input
    attempts = 0

    while attempts <= max_retries:
        # 1. Get response from Gemini
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=current_input,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=temperature,
            )
        )
        
        suggested_sql = response.text.strip()
        
        # Clean up Markdown backticks if the LLM included them
        if suggested_sql.startswith("```sql"):
            suggested_sql = suggested_sql.split("```sql")[1].split("```")[0].strip()
        elif suggested_sql.startswith("```"):
            suggested_sql = suggested_sql.split("```")[1].split("```")[0].strip()

        # suggested_sql = "SELECT ( FROM users" # Defensive check test
        # 2. Validate Syntax with sqlglot
        try:
            sqlglot.transpile(suggested_sql)
            print("Defensive Check Passed")
            # If it passes, return the clean SQL
            return suggested_sql
            
        except sqlglot.errors.ParseError as e:
            print("Defensive Check Failed : ", e)
            attempts += 1
            if attempts > max_retries:
                # If we've exhausted retries, return the last known version 
                # or raise an error for the user
                return f"-- [Validation Failed after {max_retries} retries]\n{suggested_sql}"
            
            # 3. SELF-HEAL: Prepare a "Correction" prompt
            error_details = str(e)
            current_input = (
                f"Your previous SQL output had a syntax error:\n{error_details}\n\n"
                f"Please fix the syntax error in this SQL and return ONLY the code:\n{suggested_sql}"
            )
            print(f"Retry {attempts}: Syntax error detected. Asking Gemini to self-heal...")

    return None