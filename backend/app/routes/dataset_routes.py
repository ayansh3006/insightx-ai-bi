from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import Dataset
from backend.app.services.dataset_service import (
    load_dataset,
    profile_dataset,
    save_uploaded_dataset,
)


router = APIRouter(
    prefix="/api/v1/datasets",
    tags=["Datasets"],
)


@router.post("/upload")
async def upload_dataset(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload a CSV/XLSX dataset, profile it,
    and store its metadata in PostgreSQL.
    """

    try:
        file_bytes = await file.read()

        if not file_bytes:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty.",
            )

        dataset_info = save_uploaded_dataset(
            file_bytes=file_bytes,
            original_filename=file.filename or "dataset",
        )

        df = load_dataset(
            file_path=dataset_info["file_path"],
            file_type=dataset_info["file_type"],
        )

        profile = profile_dataset(df)

        dataset = Dataset(
            dataset_id=dataset_info["dataset_id"],
            original_filename=dataset_info["original_filename"],
            file_path=dataset_info["file_path"],
            file_type=dataset_info["file_type"],
            row_count=profile["row_count"],
            column_count=profile["column_count"],
        )

        db.add(dataset)
        db.commit()
        db.refresh(dataset)

        return {
            "message": "Dataset uploaded successfully.",
            "dataset": dataset_info,
            "profile": profile,
            "database": {
                "id": dataset.id,
                "created_at": dataset.created_at,
            },
        }

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except HTTPException:
        raise

    except Exception as error:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to process dataset: {error}",
        )


@router.get("/")
def get_datasets(db: Session = Depends(get_db)):
    """
    Return all uploaded datasets.
    """

    statement = select(Dataset).order_by(Dataset.created_at.desc())

    datasets = db.scalars(statement).all()

    return {
        "count": len(datasets),
        "datasets": [
            {
                "id": dataset.id,
                "dataset_id": dataset.dataset_id,
                "original_filename": dataset.original_filename,
                "file_type": dataset.file_type,
                "row_count": dataset.row_count,
                "column_count": dataset.column_count,
                "created_at": dataset.created_at,
            }
            for dataset in datasets
        ],
    }


@router.get("/{dataset_id}")
def get_dataset(
    dataset_id: str,
    db: Session = Depends(get_db),
):
    """
    Return metadata for one dataset.
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

    return {
        "id": dataset.id,
        "dataset_id": dataset.dataset_id,
        "original_filename": dataset.original_filename,
        "file_path": dataset.file_path,
        "file_type": dataset.file_type,
        "row_count": dataset.row_count,
        "column_count": dataset.column_count,
        "created_at": dataset.created_at,
    }