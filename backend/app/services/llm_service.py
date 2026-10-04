import json
import os

from dotenv import load_dotenv
from openai import OpenAI


# --------------------------------------------------
# ENVIRONMENT
# --------------------------------------------------

load_dotenv("backend/.env")


OPENROUTER_API_KEY = os.getenv(
    "OPENROUTER_API_KEY"
)

if not OPENROUTER_API_KEY:
    raise RuntimeError(
        "OPENROUTER_API_KEY is not configured."
    )


# --------------------------------------------------
# OPENROUTER CLIENT
# --------------------------------------------------

client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
    timeout=30.0,
    max_retries=1,
)


MODEL_NAME = "qwen/qwen3.8-27b:free"


# --------------------------------------------------
# ALLOWED ANALYSIS OPERATIONS
# --------------------------------------------------

ALLOWED_OPERATIONS = {
    "count_rows",
    "get_columns",
    "summary",
    "missing_values",
    "sum",
    "average",
    "minimum",
    "maximum",
    "count_unique",
    "group_by",
    "sort",
    "top_n",
}


# --------------------------------------------------
# BUILD ANALYSIS PROMPT
# --------------------------------------------------

def build_analysis_prompt(
    question: str,
    profile: dict,
) -> str:
    """
    Build a prompt that converts a natural-language
    question into a structured analysis request.
    """

    return f"""
You are the analysis-planning engine for InsightX.

InsightX is a dataset-agnostic AI analytics platform.

The user can upload ANY structured CSV or XLSX dataset.
The dataset may contain sales, finance, HR, banking,
healthcare, education, marketing, IoT, weather,
government, survey, or other tabular data.

You MUST use only the columns available in the
provided dataset profile.

USER QUESTION:

{question}


DATASET PROFILE:

{json.dumps(
    profile,
    indent=2,
    default=str
)}


YOUR TASK:

Convert the user's question into ONE structured
analysis plan.

Do NOT calculate the answer.

The backend will execute the plan using Pandas.


AVAILABLE OPERATIONS:

1. count_rows
   Count the number of rows.

2. get_columns
   Return information about the dataset columns.

3. summary
   Give a general summary of the dataset.

4. missing_values
   Check missing values in the dataset.

5. sum
   Calculate the sum of a numeric column.

6. average
   Calculate the average of a numeric column.

7. minimum
   Find the minimum value of a column.

8. maximum
   Find the maximum value of a column.

9. count_unique
   Count unique values in a column.

10. group_by
    Group data by a column and calculate
    sum, average, minimum, maximum, or count.

11. sort
    Sort dataset rows using a column.

12. top_n
    Return the top N rows according to a column.


IMPORTANT RULES:

- "What columns are in the dataset?"
  → get_columns

- "Give me a summary of the dataset."
  → summary

- "Are there missing values?"
  → missing_values

- "How many rows are there?"
  → count_rows

- Use only columns that actually exist.

- Never invent column names.

- Do not calculate the answer yourself.

- The backend will execute the plan.
- Never invent column names.
- Use exact column names from the dataset profile.
- If the user asks for an average/sum/etc. by a category,
  use group_by.
- Example:
  "What is the average salary by department?"

  should become:

  operation = group_by
  group_by = Department
  column = Salary
  aggregation = average

- If the user asks "how many rows", use count_rows.
- If the user asks "how many unique X", use count_unique.
- Use filters when the user specifies a condition.
- Use date filters when the user specifies dates.
- Use sort_by="value" when sorting grouped results
  by their calculated value.
- Use sort_order="desc" unless the user explicitly asks
  for ascending order.
- Keep limit reasonable.
- Do not add unnecessary filters.
- Do not answer the question.
- Return ONLY valid JSON.
- Do not use Markdown.
- Do not wrap the JSON in ```.

VALID FILTER OPERATORS:

eq
neq
gt
gte
lt
lte
contains
date_eq
date_before
date_after
date_on_or_before
date_on_or_after


RETURN EXACTLY THIS JSON STRUCTURE:

{{
    "operation": "...",
    "column": null,
    "group_by": null,
    "aggregation": null,
    "filters": [],
    "sort_by": null,
    "sort_order": "desc",
    "limit": null
}}
"""


# --------------------------------------------------
# GENERATE ANALYSIS PLAN
# --------------------------------------------------

def generate_analysis_plan(
    question: str,
    profile: dict,
) -> dict:
    """
    Ask the LLM to convert a natural-language question
    into a structured and executable analysis plan.
    """

    prompt = build_analysis_prompt(
        question=question,
        profile=profile,
    )

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
    )

    content = response.choices[0].message.content

    if not content:
        raise ValueError(
            "OpenRouter returned an empty response."
        )

    content = content.strip()

    # --------------------------------------------------
    # REMOVE MARKDOWN JSON FENCES IF PRESENT
    # --------------------------------------------------

    if content.startswith("```json"):

        content = content[
            len("```json"):
        ]

        if content.endswith("```"):
            content = content[:-3]

        content = content.strip()

    elif content.startswith("```"):

        content = content[
            len("```"):
        ]

        if content.endswith("```"):
            content = content[:-3]

        content = content.strip()

    # --------------------------------------------------
    # PARSE JSON
    # --------------------------------------------------

    try:

        plan = json.loads(content)

    except json.JSONDecodeError as error:

        raise ValueError(
            "OpenRouter returned invalid JSON."
        ) from error

    # --------------------------------------------------
    # BASIC STRUCTURE VALIDATION
    # --------------------------------------------------

    if not isinstance(plan, dict):

        raise ValueError(
            "Analysis plan must be a JSON object."
        )

    operation = plan.get("operation")

    if operation not in ALLOWED_OPERATIONS:

        raise ValueError(
            f"Unsupported analysis operation: "
            f"{operation}"
        )

    # --------------------------------------------------
    # NORMALIZE OPTIONAL FIELDS
    # --------------------------------------------------

    plan.setdefault(
        "column",
        None,
    )

    plan.setdefault(
        "group_by",
        None,
    )

    plan.setdefault(
        "aggregation",
        None,
    )

    plan.setdefault(
        "filters",
        [],
    )

    plan.setdefault(
        "sort_by",
        None,
    )

    plan.setdefault(
        "sort_order",
        "desc",
    )

    plan.setdefault(
        "limit",
        None,
    )

    # --------------------------------------------------
    # OPERATION-SPECIFIC VALIDATION
    # --------------------------------------------------

    if operation == "group_by":

        if not plan.get("group_by"):

            raise ValueError(
                "group_by operation requires "
                "a group_by column."
            )

        if not plan.get("aggregation"):

            raise ValueError(
                "group_by operation requires "
                "an aggregation."
            )

    if operation in {
        "sum",
        "average",
        "minimum",
        "maximum",
        "count_unique",
    }:

        if not plan.get("column"):

            raise ValueError(
                f"{operation} operation requires "
                "a column."
            )

    if operation in {
        "sort",
        "top_n",
    }:

        if not plan.get("sort_by"):

            raise ValueError(
                f"{operation} operation requires "
                "sort_by."
            )

    # --------------------------------------------------
    # RETURN PLAN
    # --------------------------------------------------

    return plan


# --------------------------------------------------
# GENERATE FINAL ANSWER
# --------------------------------------------------

def generate_answer(
    question: str,
    profile: dict,
    analysis_plan: dict,
    analysis_result: dict,
) -> str:
    """
    Generate a human-readable answer from an already
    calculated analysis result.

    The LLM explains the result but does NOT perform
    the actual calculation.
    """

    prompt = f"""
You are the answer-generation assistant for InsightX.

InsightX is an AI-powered data analytics platform.

The user asked:

{question}


DATASET PROFILE:

{json.dumps(
    profile,
    indent=2,
    default=str
)}


VALIDATED ANALYSIS PLAN:

{json.dumps(
    analysis_plan,
    indent=2,
    default=str
)}


THE BACKEND HAS ALREADY EXECUTED THE ANALYSIS.

ACTUAL CALCULATED RESULT:

{json.dumps(
    analysis_result,
    indent=2,
    default=str
)}


IMPORTANT RULES:

1. Use ONLY the supplied analysis result.

2. Do NOT invent any numbers.

3. Do NOT perform new calculations.

4. Do NOT contradict the backend result.

5. Answer the user's question directly.

6. Keep the answer concise and easy to understand.

7. Mention important values from the result.

8. If the result contains grouped categories,
   explain the important comparison when appropriate.

9. If the result is empty, clearly state that
   no matching data was found.

10. Do not mention prompts, APIs, OpenRouter,
    models, or internal implementation details.

11. Do not return JSON.

12. Do not include Markdown code blocks.

13. Return ONLY the natural-language answer.


Generate the final answer now.
"""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
    )

    content = response.choices[0].message.content

    if not content:

        raise ValueError(
            "OpenRouter returned an empty answer."
        )

    return content.strip()