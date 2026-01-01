import sys
import typer
from sql_optimizer import optimize_sql

app = typer.Typer() 

# Define the Senior DBA Persona
SYSTEM_PROMPT = """
You are a Senior Database Administrator and SQL Optimization expert.
Your goal is to:
1. Prettify the SQL (proper indentation, capitalization of keywords).
2. Performance Optimize the SQL (suggest JOINs over subqueries, avoid SELECT *, etc.).
3. Return ONLY the optimized SQL code. Do not include explanations unless asked.
4. If the SQL is already perfect, return it as is.
"""

@app.command()
def clean(file: str = typer.Argument(None, help="Path to the SQL file. If omitted, reads from pipe (stdin).")):
    """
    Clean and optimize SQL from a file or piped input.
    Example: cat query.sql | python sqlclean.py
    """
    # 2. Get the SQL content
    if file:
        try:
            with open(file, "r") as f:
                sql_input = f.read()
        except FileNotFoundError:
            typer.echo(f"Error: File '{file}' not found.", err=True)
            raise typer.Exit(1)
    else:
        # Check if there is actually data being piped in
        if sys.stdin.isatty():
            typer.echo("Error: No SQL provided. Pipe a file or provide a filename.")
            raise typer.Exit(1)
        sql_input = sys.stdin.read()

    if not sql_input.strip():
        typer.echo("Error: SQL input is empty.")
        raise typer.Exit(1)

    # 3. Call the LLM with System Instructions
    try:
        optimized = optimize_sql(sql_input)
        
        # 4. Output to user
        typer.echo(optimized)
    except Exception as e:
        typer.echo(f"API Error: {e}", err=True)
        raise typer.Exit(1)

if __name__ == "__main__":
    app()