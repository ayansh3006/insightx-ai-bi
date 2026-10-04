from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import Dataset

from backend.app.services.analysis_service import (
    load_dataset_for_analysis,
    run_analysis,
)

from backend.app.services.dataset_service import (
    profile_dataset,
)

from backend.app.services.llm_service import (
    generate_analysis_plan,
    generate_answer,
)


router = APIRouter(
    prefix="/api/v1/analysis",
    tags=["Analysis"],
)


# ==================================================
# REQUEST MODELS
# ==================================================


class FilterCondition(BaseModel):
    column: str
    operator: str
    value: Any


class AnalysisRequest(BaseModel):
    operation: str = Field(
        description=(
            "count_rows, get_columns, summary, "
            "missing_values, sum, average, minimum, "
            "maximum, count_unique, group_by, sort, "
            "or top_n"
        )
    )

    column: str | None = None

    group_by: str | None = None

    aggregation: str | None = None

    filters: list[FilterCondition] | None = None

    sort_by: str | None = None

    sort_order: str = Field(
        default="desc",
        pattern="^(asc|desc)$",
    )

    limit: int | None = Field(
        default=None,
        ge=1,
        le=1000,
    )


class AskRequest(BaseModel):
    question: str = Field(
        min_length=1,
        max_length=1000,
    )


# ==================================================
# VALIDATE ANALYSIS REQUEST
# ==================================================


def validate_analysis_request(
    df,
    request: AnalysisRequest,
):
    """
    Validate an analysis request against the
    actual uploaded dataset.
    """

    allowed_operations = {
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
    # OPERATION
    # --------------------------------------------------

    if request.operation not in allowed_operations:
        raise ValueError(
            f"Unsupported operation: "
            f"{request.operation}"
        )

    columns = set(df.columns)

    # --------------------------------------------------
    # COLUMN
    # --------------------------------------------------

    if request.column is not None:

        if request.column not in columns:
            raise ValueError(
                f"Column '{request.column}' "
                f"does not exist."
            )

    # --------------------------------------------------
    # GROUP BY
    # --------------------------------------------------

    if request.group_by is not None:

        if request.group_by not in columns:
            raise ValueError(
                f"Group-by column "
                f"'{request.group_by}' "
                f"does not exist."
            )

    # --------------------------------------------------
    # SORT BY
    # --------------------------------------------------

    if request.sort_by is not None:

        if request.sort_by != "value":

            if request.sort_by not in columns:
                raise ValueError(
                    f"Sort column "
                    f"'{request.sort_by}' "
                    f"does not exist."
                )

    # --------------------------------------------------
    # FILTERS
    # --------------------------------------------------

    if request.filters:

        allowed_operators = {
            "eq",
            "neq",
            "gt",
            "gte",
            "lt",
            "lte",
            "contains",
            "date_eq",
            "date_before",
            "date_after",
            "date_on_or_before",
            "date_on_or_after",
        }

        for condition in request.filters:

            if condition.column not in columns:
                raise ValueError(
                    f"Filter column "
                    f"'{condition.column}' "
                    f"does not exist."
                )

            if condition.operator not in allowed_operators:
                raise ValueError(
                    f"Unsupported filter operator: "
                    f"{condition.operator}"
                )

    # --------------------------------------------------
    # AGGREGATION
    # --------------------------------------------------

    if request.aggregation:

        allowed_aggregations = {
            "sum",
            "average",
            "minimum",
            "maximum",
            "count",
        }

        if request.aggregation not in allowed_aggregations:
            raise ValueError(
                f"Unsupported aggregation: "
                f"{request.aggregation}"
            )

    # --------------------------------------------------
    # SINGLE COLUMN OPERATIONS
    # --------------------------------------------------

    if request.operation in {
        "sum",
        "average",
        "minimum",
        "maximum",
        "count_unique",
    }:

        if not request.column:
            raise ValueError(
                f"'{request.operation}' "
                f"requires a column."
            )

    # --------------------------------------------------
    # GROUP BY
    # --------------------------------------------------

    if request.operation == "group_by":

        if not request.group_by:
            raise ValueError(
                "group_by requires a group_by column."
            )

        if not request.aggregation:
            raise ValueError(
                "group_by requires an aggregation."
            )

        if request.aggregation != "count":

            if not request.column:
                raise ValueError(
                    "This aggregation requires "
                    "a column."
                )

    # --------------------------------------------------
    # SORT / TOP N
    # --------------------------------------------------

    if request.operation in {
        "sort",
        "top_n",
    }:

        if not request.sort_by:
            raise ValueError(
                f"'{request.operation}' "
                f"requires sort_by."
            )


# ==================================================
# DIRECT ANALYSIS ENDPOINT
# ==================================================


@router.post("/{dataset_id}")
def analyze_dataset(
    dataset_id: str,
    request: AnalysisRequest,
    db: Session = Depends(get_db),
):
    """
    Execute a manually supplied structured
    analysis request.
    """

    statement = select(Dataset).where(
        Dataset.dataset_id == dataset_id
    )

    dataset = db.scalar(statement)

    if dataset is None:
        raise HTTPException(
            status_code=404,
            detail="Dataset not found.",
        )

    try:

        # Load dataset
        df = load_dataset_for_analysis(
            file_path=dataset.file_path,
            file_type=dataset.file_type,
        )

        # Validate request
        validate_analysis_request(
            df,
            request,
        )

        # Convert filters
        filters = None

        if request.filters:

            filters = [
                condition.model_dump()
                for condition in request.filters
            ]

        # Execute analysis
        result = run_analysis(
            df=df,
            operation=request.operation,
            column=request.column,
            group_by=request.group_by,
            aggregation=request.aggregation,
            filters=filters,
            sort_by=request.sort_by,
            sort_order=request.sort_order,
            limit=request.limit,
        )

        return {
            "dataset_id": dataset.dataset_id,
            "dataset_name": dataset.original_filename,
            "rows_analyzed": len(df),
            "analysis_request": (
                request.model_dump()
            ),
            "analysis": result,
        }

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except FileNotFoundError as error:

        raise HTTPException(
            status_code=404,
            detail=str(error),
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {error}",
        )


# ==================================================
# NATURAL LANGUAGE ASK ENDPOINT
# ==================================================


@router.post("/{dataset_id}/ask")
def ask_about_dataset(
    dataset_id: str,
    request: AskRequest,
    db: Session = Depends(get_db),
):
    """
    Convert a natural-language question into an
    analysis plan, validate it, execute it, and
    generate a human-readable answer.
    """

    # --------------------------------------------------
    # FIND DATASET
    # --------------------------------------------------

    statement = select(Dataset).where(
        Dataset.dataset_id == dataset_id
    )

    dataset = db.scalar(statement)

    if dataset is None:
        raise HTTPException(
            status_code=404,
            detail="Dataset not found.",
        )

    try:

        # --------------------------------------------------
        # LOAD DATASET
        # --------------------------------------------------

        df = load_dataset_for_analysis(
            file_path=dataset.file_path,
            file_type=dataset.file_type,
        )

        # --------------------------------------------------
        # PROFILE DATASET
        # --------------------------------------------------

        profile = profile_dataset(
            df
        )

        # --------------------------------------------------
        # GENERATE ANALYSIS PLAN
        # --------------------------------------------------

        plan = generate_analysis_plan(
            question=request.question,
            profile=profile,
        )

        # --------------------------------------------------
        # CONVERT PLAN INTO PYDANTIC REQUEST
        # --------------------------------------------------

        analysis_request = AnalysisRequest(
            **plan
        )

        # --------------------------------------------------
        # VALIDATE AGAINST REAL DATASET
        # --------------------------------------------------

        validate_analysis_request(
            df,
            analysis_request,
        )

        # --------------------------------------------------
        # PREPARE FILTERS
        # --------------------------------------------------

        filters = None

        if analysis_request.filters:

            filters = [
                condition.model_dump()
                for condition
                in analysis_request.filters
            ]

        # --------------------------------------------------
        # EXECUTE ACTUAL ANALYSIS
        # --------------------------------------------------

        result = run_analysis(
            df=df,
            operation=analysis_request.operation,
            column=analysis_request.column,
            group_by=analysis_request.group_by,
            aggregation=analysis_request.aggregation,
            filters=filters,
            sort_by=analysis_request.sort_by,
            sort_order=analysis_request.sort_order,
            limit=analysis_request.limit,
        )

        # --------------------------------------------------
        # GENERATE HUMAN-READABLE ANSWER
        # --------------------------------------------------

        answer = generate_answer(
            question=request.question,
            profile=profile,
            analysis_plan=(
                analysis_request.model_dump()
            ),
            analysis_result=result,
        )

        # --------------------------------------------------
        # FINAL RESPONSE
        # --------------------------------------------------

        return {
            "dataset_id": dataset.dataset_id,

            "dataset_name": (
                dataset.original_filename
            ),

            "question": request.question,

            "answer": answer,

            "analysis_plan": (
                analysis_request.model_dump()
            ),

            "rows_analyzed": len(df),

            "analysis": result,
        }

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except FileNotFoundError as error:

        raise HTTPException(
            status_code=404,
            detail=str(error),
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {error}",
        )