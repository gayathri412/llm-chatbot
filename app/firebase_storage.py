import mimetypes
import os
import re
import time
import uuid
from pathlib import Path
from typing import Any

try:
    from google.cloud import storage
except ImportError:  # pragma: no cover - handled at runtime in Streamlit UI
    storage = None

try:
    import streamlit as st
except ImportError:  # pragma: no cover - this module can still be imported by non-UI tools
    st = None


class FirebaseStorageError(Exception):
    pass


def _secret_value(section: str, key: str) -> str | None:
    if st is None:
        return None

    try:
        values = st.secrets.get(section, {})
        if hasattr(values, "get"):
            return values.get(key) or None
    except Exception:
        return None

    return None


def firebase_storage_bucket_name() -> str | None:
    bucket_names = _firebase_storage_bucket_candidates()
    return bucket_names[0] if bucket_names else None


def _configured_bucket_name() -> str | None:
    return (
        os.getenv("FIREBASE_STORAGE_BUCKET")
        or _secret_value("firebase", "storage_bucket")
    )


def _firebase_project_id() -> str | None:
    return (
        os.getenv("FIREBASE_PROJECT_ID")
        or os.getenv("GCP_PROJECT_ID")
        or os.getenv("GOOGLE_CLOUD_PROJECT")
        or _secret_value("firebase", "project_id")
    )


def _firebase_storage_bucket_candidates() -> list[str]:
    configured = _configured_bucket_name()
    if configured:
        return [configured]

    project_id = _firebase_project_id()
    if not project_id:
        return []

    return [
        f"{project_id}.appspot.com",
        f"{project_id}.firebasestorage.app",
    ]


def _is_not_found_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return getattr(exc, "code", None) == 404 or ("404" in message and "not found" in message)


def _storage_project_id() -> str | None:
    project_id = (
        os.getenv("GCP_PROJECT_ID")
        or os.getenv("FIREBASE_PROJECT_ID")
        or os.getenv("GOOGLE_CLOUD_PROJECT")
    )
    return project_id or None


def _safe_path_part(value: str, default: str = "unknown") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip(".-")
    return cleaned[:120] or default


def upload_bytes(
    data: bytes,
    *,
    file_name: str,
    content_type: str | None = None,
    user_id: str = "anonymous",
    area: str = "general",
    metadata: dict[str, str] | None = None,
) -> dict[str, Any]:
    if storage is None:
        raise FirebaseStorageError("google-cloud-storage is not installed.")

    bucket_names = _firebase_storage_bucket_candidates()
    if not bucket_names:
        raise FirebaseStorageError("FIREBASE_STORAGE_BUCKET or FIREBASE_PROJECT_ID is not configured.")

    safe_user = _safe_path_part(user_id, "anonymous")
    safe_area = _safe_path_part(area, "general")
    safe_name = _safe_path_part(Path(file_name).name, "upload")
    date_path = time.strftime("%Y/%m/%d")
    object_name = f"uploads/{safe_user}/{safe_area}/{date_path}/{uuid.uuid4().hex}-{safe_name}"
    guessed_type = mimetypes.guess_type(safe_name)[0]

    client = storage.Client(project=_storage_project_id())
    upload_error = None

    for bucket_name in bucket_names:
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(object_name)
        blob.metadata = {
            "original_name": file_name,
            "user_id": user_id,
            "area": area,
            **(metadata or {}),
        }

        try:
            blob.upload_from_string(data, content_type=content_type or guessed_type or "application/octet-stream")
            break
        except Exception as exc:
            upload_error = exc
            if len(bucket_names) > 1 and _is_not_found_error(exc):
                continue
            raise
    else:
        raise FirebaseStorageError(f"Firebase Storage bucket was not found: {upload_error}")

    return {
        "bucket": bucket_name,
        "name": object_name,
        "uri": f"gs://{bucket_name}/{object_name}",
        "size": len(data),
        "content_type": content_type or guessed_type or "application/octet-stream",
    }


def upload_streamlit_file(uploaded_file: Any, *, user_id: str, area: str) -> dict[str, Any]:
    data = uploaded_file.getvalue()
    return upload_bytes(
        data,
        file_name=uploaded_file.name,
        content_type=getattr(uploaded_file, "type", None),
        user_id=user_id,
        area=area,
    )
