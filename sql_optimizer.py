import os
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
3. Return ONLY the optimized SQL code. Do not include explanations unless asked.
4. If the SQL is already perfect, return it as is.
"""

def optimize_sql(sql_input, temperature=0.1):
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=sql_input,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=temperature,
        )
    )
    return response.text