from pathlib import Path

import pandas as pd


UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".csv", ".xlsx"}


def save_uploaded_dataset(
    file_bytes: bytes,
    original_filename: str,
) -> dict:
    """
    Save an uploaded CSV/XLSX dataset using a generated filename.
    """

    extension = Path(original_filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError(
            "Only CSV and XLSX files are supported."
        )

    from uuid import uuid4

    dataset_id = str(uuid4())

    saved_filename = f"{dataset_id}{extension}"

    file_path = UPLOAD_DIR / saved_filename

    file_path.write_bytes(file_bytes)

    return {
        "dataset_id": dataset_id,
        "original_filename": original_filename,
        "file_path": str(file_path),
        "file_type": extension.replace(".", ""),
    }


def load_dataset(
    file_path: str,
    file_type: str,
) -> pd.DataFrame:
    """
    Load a CSV/XLSX dataset into Pandas.
    """

    if file_type == "csv":
        return pd.read_csv(file_path)

    if file_type == "xlsx":
        return pd.read_excel(file_path)

    raise ValueError(
        "Unsupported dataset type."
    )


def detect_column_type(
    series: pd.Series,
) -> str:
    """
    Detect a useful semantic type for a dataset column.
    """

    dtype = series.dtype

    if pd.api.types.is_bool_dtype(dtype):
        return "boolean"

    if pd.api.types.is_numeric_dtype(dtype):
        return "numeric"

    if pd.api.types.is_datetime64_any_dtype(dtype):
        return "date"

    # Try detecting dates in object/string columns.
    if series.dtype == "object":
        non_null = series.dropna()

        if len(non_null) > 0:
            converted = pd.to_datetime(
                non_null,
                errors="coerce",
            )

            success_rate = converted.notna().mean()

            if success_rate >= 0.8:
                return "date"

    return "text"


def detect_role(
    series: pd.Series,
    column_type: str,
) -> str:
    """
    Estimate the analytical role of a column.
    """

    column_name = str(series.name).lower()

    # Common ID naming patterns.
    id_keywords = (
        "id",
        "uuid",
        "code",
        "identifier",
    )

    if any(
        keyword in column_name
        for keyword in id_keywords
    ):
        return "identifier"

    if column_type == "date":
        return "date"

    if column_type == "numeric":
        return "measure"

    if column_type == "boolean":
        return "boolean"

    return "dimension"


def get_numeric_statistics(
    series: pd.Series,
) -> dict:
    """
    Return basic statistics for numeric columns.
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


def profile_dataset(
    df: pd.DataFrame,
) -> dict:
    """
    Generate a dataset-aware profile.
    """

    columns = []

    for column in df.columns:

        series = df[column]

        column_type = detect_column_type(
            series
        )

        role = detect_role(
            series,
            column_type,
        )

        column_info = {
            "name": str(column),
            "data_type": str(series.dtype),
            "semantic_type": column_type,
            "role": role,
            "missing_values": int(
                series.isna().sum()
            ),
            "missing_percentage": round(
                float(series.isna().mean() * 100),
                2,
            ),
            "unique_values": int(
                series.nunique(
                    dropna=True
                )
            ),
            "sample_values": (
                series
                .dropna()
                .head(5)
                .tolist()
            ),
        }

        if column_type == "numeric":
            column_info["statistics"] = (
                get_numeric_statistics(series)
            )

        columns.append(column_info)

    return {
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "columns": columns,
        "sample": (
            df.head(5)
            .fillna("")
            .to_dict(orient="records")
        ),
    }