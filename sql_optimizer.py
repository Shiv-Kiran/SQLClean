import sqlglot
from sqlglot import exp
from google import genai
from rag_config import RAGFactory, RAGStrategy
from service.candidate_generator import generate_candidate
from service.plan_runner import PlanRunner, PlanRunnerConfig, PlanRunnerUnavailable
from service.ranker import CandidateEvaluation, rank_candidates
from service.retry import RetryPolicy, execute_with_retry
from service.safety_validator import SafetyLimits, validate_sql_safety
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


def _build_prompt(sql_input, repo_path, rag_strategy, notes):
    current_prompt = sql_input

    # --- RAG Initialization ---
    rag = RAGFactory.create_rag(rag_strategy)

    # --- RAG Indexing ---
    if repo_path:
        print(f"Indexing repository with {rag_strategy.value} RAG: {repo_path}")
        rag.index_directory(repo_path)
        relevant_docs = rag.retrieve(sql_input, top_k=3)
        if relevant_docs:
            context = "\n".join(
                [f"From {doc['source']}:\n{doc['content']}" for doc in relevant_docs]
            )
            current_prompt = f"Context from repository:\n{context}\n\nSQL to optimize:\n{sql_input}"
            notes.append(
                f"-- Note: Used repository context ({rag_strategy.value} RAG) for optimization."
            )

    # --- Input Defensive Check ---
    if not is_valid_sql(sql_input):
        print("User Input Invalid")
        notes.append("-- Note: Input did not look like standard SQL. Asking AI to interpret.")
        current_prompt = (
            "The following input might not be valid SQL. If it is text describing a query, "
            "write the SQL. If it's nonsense, say so: "
            f"{sql_input}"
        )

    return current_prompt


def _generate_candidate_with_retry(initial_prompt, temperature, max_retries):
    current_prompt = initial_prompt
    attempts = 0
    retry_notes = []
    suggested_sql = ""
    last_error = None

    while attempts <= max_retries:
        try:
            suggested_sql = execute_with_retry(
                fn=lambda: generate_candidate(
                    client=client,
                    prompt=current_prompt,
                    system_prompt=SYSTEM_PROMPT,
                    temperature=temperature,
                    model=SETTINGS.model_name,
                ),
                policy=RetryPolicy(max_attempts=2, base_delay_seconds=0.1, max_delay_seconds=0.5),
                retry_exceptions=(Exception,),
            )
        except Exception as exc:
            attempts += 1
            last_error = exc
            print(f"Attempt {attempts} failed. Error: {exc}")
            if attempts > max_retries:
                return suggested_sql, last_error, retry_notes
            continue

        try:
            sqlglot.transpile(suggested_sql)
            return suggested_sql, None, retry_notes
        except sqlglot.errors.ParseError as exc:
            attempts += 1
            last_error = exc
            print(f"Attempt {attempts} failed. Error: {exc}")
            if attempts > max_retries:
                return suggested_sql, last_error, retry_notes

            current_prompt = (
                f"Your previous SQL output had a syntax error: {str(exc)}\n"
                f"Please fix this SQL and return ONLY the corrected code:\n{suggested_sql}"
            )
            retry_notes.append(f"-- Note: AI output was corrected for syntax (Attempt {attempts}).")

    return suggested_sql, last_error, retry_notes


def _default_safety_limits():
    return SafetyLimits(
        max_sql_length=getattr(SETTINGS, "safety_max_sql_length", 50_000),
        max_joins=getattr(SETTINGS, "safety_max_joins", 12),
        max_subqueries=getattr(SETTINGS, "safety_max_subqueries", 8),
        max_ctes=getattr(SETTINGS, "safety_max_ctes", 8),
    )


def _build_plan_runner(statement_timeout_ms):
    dsn = getattr(SETTINGS, "pg_dsn", None)
    if not dsn:
        raise PlanRunnerUnavailable("SQLCLEAN_PG_DSN is not configured")
    return PlanRunner(
        PlanRunnerConfig(
            dsn=dsn,
            connect_timeout_seconds=getattr(SETTINGS, "pg_connect_timeout_seconds", 5),
            statement_timeout_ms=statement_timeout_ms,
        )
    )


def optimize_sql(
    sql_input,
    repo_path=None,
    temperature=0.1,
    max_retries=2,
    rag_strategy=RAGStrategy.HYBRID,
    candidate_count=1,
    execution_verify=False,
    explain_analyze=False,
    verify_statement_timeout_ms=None,
):
    if temperature is None:
        temperature = getattr(SETTINGS, "default_temperature", 0.1)
    if max_retries is None:
        max_retries = getattr(SETTINGS, "default_max_retries", 2)
    if verify_statement_timeout_ms is None:
        verify_statement_timeout_ms = getattr(SETTINGS, "pg_statement_timeout_ms", 2500)
    candidate_count = max(1, int(candidate_count or 1))

    user_notes = []
    current_prompt = _build_prompt(sql_input, repo_path, rag_strategy, user_notes)

    # Legacy path remains unchanged unless execution_verify is enabled.
    if not execution_verify:
        suggested_sql, parse_error, retry_notes = _generate_candidate_with_retry(
            initial_prompt=current_prompt,
            temperature=temperature,
            max_retries=max_retries,
        )
        user_notes.extend(retry_notes)

        if parse_error is not None:
            return (
                f"-- [Validation Failed after {max_retries} attempts]\n"
                f"-- Error: {parse_error}\n"
                f"{suggested_sql}"
            )

        final_output = "\n".join(user_notes) + "\n" + suggested_sql if user_notes else suggested_sql
        return final_output.strip()

    # Execution-verified path.
    candidates = []
    seen_sql = set()
    for index in range(candidate_count):
        prompt = current_prompt
        if candidate_count > 1:
            prompt = (
                f"{current_prompt}\n\n"
                f"Generate a distinct SQL rewrite variant #{index + 1}. Return only SQL."
            )

        candidate_sql, parse_error, retry_notes = _generate_candidate_with_retry(
            initial_prompt=prompt,
            temperature=min(1.0, temperature + (index * 0.05)),
            max_retries=max_retries,
        )
        user_notes.extend(retry_notes)

        if parse_error is not None and candidate_sql:
            user_notes.append(
                f"-- Note: Candidate {index + 1} had unresolved syntax issues and may be deprioritized."
            )

        if candidate_sql and candidate_sql not in seen_sql:
            seen_sql.add(candidate_sql)
            candidates.append(candidate_sql)

    if not candidates:
        return "-- [Validation Failed] No SQL candidates could be generated."

    plan_runner = None
    verification_error = None
    try:
        plan_runner = _build_plan_runner(statement_timeout_ms=verify_statement_timeout_ms)
    except PlanRunnerUnavailable as exc:
        verification_error = str(exc)
        user_notes.append(
            f"-- Note: Execution verification unavailable ({verification_error}). "
            "Falling back to safety-only ranking."
        )

    limits = _default_safety_limits()
    evaluations = []

    for sql_candidate in candidates:
        syntax_valid = True
        try:
            sqlglot.transpile(sql_candidate)
        except Exception:
            syntax_valid = False

        safety = validate_sql_safety(sql_candidate, limits=limits)
        evaluation = CandidateEvaluation(
            sql=sql_candidate,
            safe=syntax_valid and safety.safe,
            syntax_valid=syntax_valid,
            safety=safety,
            verification_status="not_attempted",
        )

        if not syntax_valid:
            evaluation.notes.append("Candidate failed SQL parsing")

        if not safety.safe:
            evaluation.notes.extend(safety.reasons)
            evaluation.verification_status = "safety_rejected"
        elif plan_runner is not None:
            try:
                plan_result = execute_with_retry(
                    fn=lambda: plan_runner.explain_sql(sql_candidate, analyze=explain_analyze),
                    policy=RetryPolicy(max_attempts=2, base_delay_seconds=0.1, max_delay_seconds=0.5),
                    retry_exceptions=(PlanRunnerUnavailable,),
                    is_retryable=lambda exc: (
                        "not configured" not in str(exc).lower()
                        and "not installed" not in str(exc).lower()
                    ),
                )
                evaluation.plan_metrics = plan_result.get("metrics", {})
                evaluation.verification_status = "verified"
            except PlanRunnerUnavailable as exc:
                evaluation.verification_status = "verification_unavailable"
                evaluation.notes.append(str(exc))
        else:
            evaluation.verification_status = "verification_unavailable"

        evaluations.append(evaluation)

    ranking = rank_candidates(evaluations)
    winner = ranking.winner

    if winner is None:
        # Last-resort fallback: first syntax-valid candidate, otherwise first candidate.
        fallback = next((item for item in evaluations if item.syntax_valid), evaluations[0])
        user_notes.append("-- Note: No fully safe candidate passed all checks; using best fallback.")
        winner_sql = fallback.sql
    else:
        winner_sql = winner.sql
        if winner.plan_metrics.get("total_cost") is not None:
            user_notes.append(
                "-- Note: Execution verification selected a candidate with "
                f"total_cost={winner.plan_metrics.get('total_cost')}."
            )

    user_notes.append(f"-- Note: Evaluated {len(evaluations)} candidate(s) in execution-verify mode.")

    final_output = "\n".join(user_notes) + "\n" + winner_sql if user_notes else winner_sql
    return final_output.strip()
