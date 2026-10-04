from pathlib import Path

import pandas as pd


# ==================================================
# DATASET LOADING
# ==================================================

def load_dataset_for_analysis(
    file_path: str,
    file_type: str,
) -> pd.DataFrame:
    """
    Load an uploaded CSV/XLSX dataset.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            "Dataset file not found."
        )

    if file_type == "csv":
        return pd.read_csv(path)

    if file_type == "xlsx":
        return pd.read_excel(path)

    raise ValueError(
        "Unsupported dataset type."
    )


# ==================================================
# COLUMN VALIDATION
# ==================================================

def validate_column(
    df: pd.DataFrame,
    column: str,
) -> None:
    """
    Check whether a requested column exists.
    """

    if column not in df.columns:
        raise ValueError(
            f"Column '{column}' does not exist in the dataset."
        )


# ==================================================
# FILTERS
# ==================================================

def apply_filters(
    df: pd.DataFrame,
    filters: list[dict] | None,
) -> pd.DataFrame:
    """
    Apply normal filters to the dataset.
    """

    if not filters:
        return df

    filtered_df = df.copy()

    allowed_operators = {
        "eq",
        "neq",
        "gt",
        "gte",
        "lt",
        "lte",
        "contains",
    }

    for condition in filters:

        column = condition.get("column")
        operator = condition.get("operator")
        value = condition.get("value")

        if not column:
            raise ValueError(
                "Filter column is required."
            )

        # Date operators are handled separately.
        if operator in {
            "date_eq",
            "date_before",
            "date_after",
            "date_on_or_before",
            "date_on_or_after",
        }:
            continue

        if operator not in allowed_operators:
            raise ValueError(
                f"Unsupported filter operator: {operator}"
            )

        validate_column(
            filtered_df,
            column,
        )

        series = filtered_df[column]

        if operator == "eq":
            mask = series == value

        elif operator == "neq":
            mask = series != value

        elif operator == "gt":
            mask = series > value

        elif operator == "gte":
            mask = series >= value

        elif operator == "lt":
            mask = series < value

        elif operator == "lte":
            mask = series <= value

        elif operator == "contains":
            mask = series.astype(str).str.contains(
                str(value),
                case=False,
                na=False,
            )

        filtered_df = filtered_df[mask]

    return filtered_df


# ==================================================
# DATE FILTERS
# ==================================================

def parse_date_value(value):
    """
    Convert an incoming value into a Pandas timestamp.
    """

    try:
        return pd.to_datetime(value)

    except Exception:
        raise ValueError(
            f"Invalid date value: {value}"
        )


def apply_date_filters(
    df: pd.DataFrame,
    filters: list[dict] | None,
) -> pd.DataFrame:
    """
    Apply date-specific filters.
    """

    if not filters:
        return df

    filtered_df = df.copy()

    date_operators = {
        "date_eq",
        "date_before",
        "date_after",
        "date_on_or_before",
        "date_on_or_after",
    }

    for condition in filters:

        column = condition.get("column")
        operator = condition.get("operator")
        value = condition.get("value")

        if operator not in date_operators:
            continue

        if not column:
            raise ValueError(
                "Filter column is required."
            )

        validate_column(
            filtered_df,
            column,
        )

        filtered_df[column] = pd.to_datetime(
            filtered_df[column],
            errors="coerce",
        )

        date_value = parse_date_value(
            value
        )

        if operator == "date_eq":
            mask = (
                filtered_df[column]
                == date_value
            )

        elif operator == "date_before":
            mask = (
                filtered_df[column]
                < date_value
            )

        elif operator == "date_after":
            mask = (
                filtered_df[column]
                > date_value
            )

        elif operator == "date_on_or_before":
            mask = (
                filtered_df[column]
                <= date_value
            )

        elif operator == "date_on_or_after":
            mask = (
                filtered_df[column]
                >= date_value
            )

        filtered_df = filtered_df[mask]

    return filtered_df


# ==================================================
# NUMERIC STATISTICS
# ==================================================

def get_numeric_statistics(
    series: pd.Series,
) -> dict:
    """
    Return basic statistics for a numeric column.
    """

    numeric_series = pd.to_numeric(
        series,
        errors="coerce",
    ).dropna()

    if numeric_series.empty:
        return {}

    return {
        "min": float(numeric_series.min()),
        "max": float(numeric_series.max()),
        "mean": float(numeric_series.mean()),
        "median": float(numeric_series.median()),
    }


# ==================================================
# MAIN ANALYSIS ENGINE
# ==================================================

def run_analysis(
    df: pd.DataFrame,
    operation: str,
    column: str | None = None,
    group_by: str | None = None,
    aggregation: str | None = None,
    filters: list[dict] | None = None,
    sort_by: str | None = None,
    sort_order: str = "desc",
    limit: int | None = None,
) -> dict:
    """
    Execute a structured analysis request.
    """

    # --------------------------------------------------
    # APPLY FILTERS
    # --------------------------------------------------

    working_df = apply_filters(
        df,
        filters,
    )

    working_df = apply_date_filters(
        working_df,
        filters,
    )

    # --------------------------------------------------
    # GET COLUMNS
    # --------------------------------------------------

    if operation == "get_columns":

        columns = []

        for name in df.columns:

            series = df[name]

            columns.append({
                "name": str(name),
                "data_type": str(
                    series.dtype
                ),
                "non_null_values": int(
                    series.notna().sum()
                ),
                "unique_values": int(
                    series.nunique(
                        dropna=True
                    )
                ),
            })

        return {
            "operation": operation,
            "result": columns,
        }

    # --------------------------------------------------
    # SUMMARY
    # --------------------------------------------------

    if operation == "summary":

        numeric_columns = []

        text_columns = []

        date_columns = []

        for name in df.columns:

            series = df[name]

            if pd.api.types.is_numeric_dtype(
                series
            ):
                numeric_columns.append(
                    str(name)
                )

            elif pd.api.types.is_datetime64_any_dtype(
                series
            ):
                date_columns.append(
                    str(name)
                )

            else:
                text_columns.append(
                    str(name)
                )

        missing_by_column = {
            str(name): int(
                df[name].isna().sum()
            )
            for name in df.columns
            if df[name].isna().sum() > 0
        }

        return {
            "operation": operation,
            "result": {
                "row_count": int(
                    len(df)
                ),
                "column_count": int(
                    len(df.columns)
                ),
                "columns": [
                    str(name)
                    for name in df.columns
                ],
                "numeric_columns": numeric_columns,
                "text_columns": text_columns,
                "date_columns": date_columns,
                "total_missing_values": int(
                    df.isna().sum().sum()
                ),
                "missing_by_column": (
                    missing_by_column
                ),
            },
        }

    # --------------------------------------------------
    # MISSING VALUES
    # --------------------------------------------------

    if operation == "missing_values":

        missing = []

        for name in df.columns:

            count = int(
                df[name].isna().sum()
            )

            percentage = round(
                float(
                    df[name].isna().mean()
                    * 100
                ),
                2,
            )

            missing.append({
                "column": str(name),
                "missing_values": count,
                "missing_percentage": percentage,
            })

        return {
            "operation": operation,
            "result": missing,
        }

    # --------------------------------------------------
    # COUNT ROWS
    # --------------------------------------------------

    if operation == "count_rows":

        return {
            "operation": operation,
            "result": int(
                len(working_df)
            ),
        }

    # --------------------------------------------------
    # SINGLE COLUMN AGGREGATIONS
    # --------------------------------------------------

    if operation in {
        "sum",
        "average",
        "minimum",
        "maximum",
        "count_unique",
    }:

        if not column:
            raise ValueError(
                f"Column is required for "
                f"'{operation}'."
            )

        validate_column(
            working_df,
            column,
        )

        series = working_df[column]

        if operation == "sum":
            result = series.sum()

        elif operation == "average":
            result = series.mean()

        elif operation == "minimum":
            result = series.min()

        elif operation == "maximum":
            result = series.max()

        else:
            result = series.nunique()

        if pd.isna(result):
            result = None

        elif hasattr(result, "item"):
            result = result.item()

        return {
            "operation": operation,
            "column": column,
            "result": result,
        }

    # --------------------------------------------------
    # GROUP BY
    # --------------------------------------------------

    if operation == "group_by":

        if not group_by:
            raise ValueError(
                "group_by column is required."
            )

        if not aggregation:
            raise ValueError(
                "aggregation is required for group_by."
            )

        validate_column(
            working_df,
            group_by,
        )

        allowed_aggregations = {
            "sum",
            "average",
            "minimum",
            "maximum",
            "count",
        }

        if aggregation not in allowed_aggregations:
            raise ValueError(
                f"Unsupported aggregation: "
                f"{aggregation}"
            )

        if aggregation == "count":

            grouped = (
                working_df
                .groupby(
                    group_by,
                    dropna=False,
                )
                .size()
                .reset_index(
                    name="value"
                )
            )

        else:

            if not column:
                raise ValueError(
                    "column is required for "
                    "this aggregation."
                )

            validate_column(
                working_df,
                column,
            )

            aggregation_map = {
                "sum": "sum",
                "average": "mean",
                "minimum": "min",
                "maximum": "max",
            }

            grouped = (
                working_df
                .groupby(
                    group_by,
                    dropna=False,
                )[column]
                .agg(
                    aggregation_map[
                        aggregation
                    ]
                )
                .reset_index(
                    name="value"
                )
            )

        if sort_by == "value":

            grouped = grouped.sort_values(
                "value",
                ascending=(
                    sort_order == "asc"
                ),
            )

        if limit is not None:

            grouped = grouped.head(
                limit
            )

        records = grouped.to_dict(
            orient="records"
        )

        return {
            "operation": operation,
            "group_by": group_by,
            "column": column,
            "aggregation": aggregation,
            "result": records,
        }

    # --------------------------------------------------
    # SORT / TOP N
    # --------------------------------------------------

    if operation in {
        "sort",
        "top_n",
    }:

        if not sort_by:
            raise ValueError(
                "sort_by column is required."
            )

        validate_column(
            working_df,
            sort_by,
        )

        ascending = (
            sort_order == "asc"
        )

        sorted_df = (
            working_df.sort_values(
                by=sort_by,
                ascending=ascending,
            )
        )

        if limit is not None:
            sorted_df = (
                sorted_df.head(limit)
            )

        records = sorted_df.to_dict(
            orient="records"
        )

        return {
            "operation": operation,
            "sort_by": sort_by,
            "sort_order": sort_order,
            "limit": limit,
            "result": records,
        }

    # --------------------------------------------------
    # UNKNOWN OPERATION
    # --------------------------------------------------

    raise ValueError(
        f"Unsupported analysis operation: "
        f"{operation}"
    )