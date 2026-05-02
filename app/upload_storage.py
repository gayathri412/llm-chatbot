from typing import Any

from app.appwrite_storage import AppwriteStorageError
from app.config import get_settings
from app.firebase_storage import FirebaseStorageError


class UploadStorageError(Exception):
    pass


def storage_backend() -> str:
    return (get_settings().app_storage_backend or "firebase").strip().lower()


def upload_streamlit_file(uploaded_file: Any, *, user_id: str, area: str) -> dict[str, Any]:
    backend = storage_backend()

    try:
        if backend == "appwrite":
            from app.appwrite_storage import upload_streamlit_file as upload_appwrite_file

            return upload_appwrite_file(uploaded_file, user_id=user_id, area=area)

        if backend in {"firebase", "gcs"}:
            from app.firebase_storage import upload_streamlit_file as upload_firebase_file

            result = upload_firebase_file(uploaded_file, user_id=user_id, area=area)
            result.setdefault("backend", "firebase")
            return result

        if backend in {"none", "disabled", "local"}:
            raise UploadStorageError("Upload storage is disabled.")

        raise UploadStorageError(f"Unknown APP_STORAGE_BACKEND: {backend}")
    except (AppwriteStorageError, FirebaseStorageError):
        raise
    except Exception as exc:
        raise UploadStorageError(str(exc)) from exc
