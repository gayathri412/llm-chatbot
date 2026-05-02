import mimetypes
import re
import time
import uuid
from pathlib import Path
from typing import Any

import requests

from app.config import get_settings


MAX_CHUNK_SIZE = 5 * 1024 * 1024


class AppwriteStorageError(Exception):
    pass


def _safe_file_id() -> str:
    return uuid.uuid4().hex


def _safe_name(value: str, default: str = "upload") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip(".-")
    return cleaned[:180] or default


def _split_permissions(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    settings = get_settings()
    headers = {
        "X-Appwrite-Project": settings.appwrite_project_id or "",
        "X-Appwrite-Key": settings.appwrite_api_key or "",
        "X-Appwrite-Response-Format": "1.8.0",
    }
    headers.update(extra or {})
    return headers


def _create_file_request(
    *,
    data: bytes,
    file_id: str,
    file_name: str,
    content_type: str,
    permissions: list[str],
    content_range: str | None = None,
    appwrite_id: str | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.appwrite_project_id:
        raise AppwriteStorageError("APPWRITE_PROJECT_ID is not configured.")
    if not settings.appwrite_api_key:
        raise AppwriteStorageError("APPWRITE_API_KEY is not configured.")
    if not settings.appwrite_storage_bucket_id:
        raise AppwriteStorageError("APPWRITE_STORAGE_BUCKET_ID is not configured.")

    endpoint = settings.appwrite_endpoint.rstrip("/")
    url = f"{endpoint}/storage/buckets/{settings.appwrite_storage_bucket_id}/files"
    headers = {}
    if content_range:
        headers["Content-Range"] = content_range
    if appwrite_id:
        headers["X-Appwrite-ID"] = appwrite_id

    form_data = [("fileId", file_id)]
    for permission in permissions:
        form_data.append(("permissions[]", permission))

    response = requests.post(
        url,
        headers=_headers(headers),
        data=form_data,
        files={"file": (file_name, data, content_type)},
        timeout=60,
    )
    if response.status_code not in {200, 201}:
        raise AppwriteStorageError(
            f"Appwrite upload failed: {response.status_code} {response.text[:500]}"
        )

    try:
        return response.json()
    except ValueError as exc:
        raise AppwriteStorageError("Appwrite upload returned invalid JSON.") from exc


def upload_bytes(
    data: bytes,
    *,
    file_name: str,
    content_type: str | None = None,
    user_id: str = "anonymous",
    area: str = "general",
    metadata: dict[str, str] | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    safe_name = _safe_name(Path(file_name).name)
    guessed_type = mimetypes.guess_type(safe_name)[0]
    content_type = content_type or guessed_type or "application/octet-stream"
    file_id = _safe_file_id()
    permissions = _split_permissions(settings.appwrite_file_permissions)

    if len(data) <= MAX_CHUNK_SIZE:
        result = _create_file_request(
            data=data,
            file_id=file_id,
            file_name=safe_name,
            content_type=content_type,
            permissions=permissions,
        )
    else:
        result = {}
        appwrite_id = None
        total_size = len(data)
        for start in range(0, total_size, MAX_CHUNK_SIZE):
            end = min(start + MAX_CHUNK_SIZE, total_size) - 1
            chunk = data[start : end + 1]
            result = _create_file_request(
                data=chunk,
                file_id=file_id,
                file_name=safe_name,
                content_type=content_type,
                permissions=permissions,
                content_range=f"bytes {start}-{end}/{total_size}",
                appwrite_id=appwrite_id,
            )
            appwrite_id = result.get("$id") or result.get("id") or file_id

    file_id = result.get("$id") or result.get("id") or file_id
    endpoint = settings.appwrite_endpoint.rstrip("/")
    bucket_id = settings.appwrite_storage_bucket_id
    date_path = time.strftime("%Y/%m/%d")

    return {
        "backend": "appwrite",
        "bucket": bucket_id,
        "file_id": file_id,
        "name": safe_name,
        "uri": f"appwrite://{bucket_id}/{file_id}",
        "download_url": f"{endpoint}/storage/buckets/{bucket_id}/files/{file_id}/download",
        "view_url": f"{endpoint}/storage/buckets/{bucket_id}/files/{file_id}/view",
        "size": len(data),
        "content_type": content_type,
        "path_hint": f"uploads/{user_id}/{area}/{date_path}/{safe_name}",
        "metadata": metadata or {},
    }


def upload_streamlit_file(uploaded_file: Any, *, user_id: str, area: str) -> dict[str, Any]:
    return upload_bytes(
        uploaded_file.getvalue(),
        file_name=uploaded_file.name,
        content_type=getattr(uploaded_file, "type", None),
        user_id=user_id,
        area=area,
    )
