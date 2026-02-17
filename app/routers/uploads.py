"""Uploads endpoints: upload, list, metadata, download, delete."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db
from app.limiter import limiter
from app.middleware.auth import get_current_user_id
from app.repositories.files_repository import FilesRepository
from app.schemas.uploads import (
    UploadListItem,
    UploadListResponse,
    UploadMetadataResponse,
    UploadSuccessResponse,
)
from app.services.uploads_service import UploadsService

router = APIRouter()


@router.post(
    "/",
    response_model=UploadSuccessResponse,
    summary="Upload a file",
    description="Upload one file (multipart). Validates type, size, and user quota (max 5). Scans in prod. Returns file_id.",
)
@limiter.limit("30/minute")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    """Accept multipart file, validate, store, scan, and return file_id."""
    files_repo = FilesRepository(db)
    service = UploadsService(files_repo)
    file_id, _ = await service.upload_file(user_id, file)
    return UploadSuccessResponse(ok=True, file_id=file_id)


@router.get(
    "/",
    response_model=UploadListResponse,
    summary="List uploads",
    description="List files for the current user (CLEAN and PENDING_SCAN).",
)
async def list_uploads(
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Return list of user's files."""
    files_repo = FilesRepository(db)
    service = UploadsService(files_repo)
    files = await service.list_files(user_id)
    items = [
        UploadListItem(
            file_id=f.file_id,
            name=f.filename,
            size=f.size_bytes,
            uploaded_at=f.created_at,
            status=f.status,
        )
        for f in files
    ]
    return UploadListResponse(items=items)


@router.get(
    "/{file_id}",
    response_model=UploadMetadataResponse,
    summary="Get file metadata",
    description="Return metadata for one file (no download).",
)
async def get_upload_metadata(
    file_id: uuid.UUID,
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Return metadata only."""
    files_repo = FilesRepository(db)
    service = UploadsService(files_repo)
    file_record = await service.get_file_metadata(file_id, user_id)
    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found.",
        )
    return UploadMetadataResponse(
        file_id=file_record.file_id,
        name=file_record.filename,
        size=file_record.size_bytes,
        content_type=file_record.content_type,
        status=file_record.status,
        uploaded_at=file_record.created_at,
    )


@router.get(
    "/{file_id}/download",
    summary="Download file",
    description="Stream file content. Only allowed for CLEAN files owned by user.",
)
async def download_upload(
    file_id: uuid.UUID,
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Stream file; 404 if not found or not CLEAN."""
    from app.infrastructure.storage import get_storage

    files_repo = FilesRepository(db)
    service = UploadsService(files_repo)
    file_record = await service.get_file_for_download(file_id, user_id)
    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found or not available for download.",
        )
    storage = get_storage()
    try:
        stream = storage.open(file_record.stored_path)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found.",
        )

    def iterfile():
        try:
            yield from stream
        finally:
            stream.close()

    return StreamingResponse(
        iterfile(),
        media_type=file_record.content_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{file_record.filename}"'
        },
    )


@router.delete(
    "/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete file",
    description="Delete file from storage and DB. Only owner.",
)
async def delete_upload(
    file_id: uuid.UUID,
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete file if owned by user."""
    files_repo = FilesRepository(db)
    service = UploadsService(files_repo)
    deleted = await service.delete_file(file_id, user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found.",
        )
