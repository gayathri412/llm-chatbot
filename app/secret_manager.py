from app.config import get_settings

try:
    from google.cloud import secretmanager
except ImportError:
    secretmanager = None


def get_secret_value(env_name: str, secret_env_name: str | None = None) -> str | None:
    """Read a secret from env first, then Google Secret Manager when configured."""
    settings = get_settings()
    env_value = getattr(settings, env_name.lower(), None)
    if env_value:
        return env_value

    if not settings.secret_manager_enabled:
        return None

    if secretmanager is None:
        return None

    project_id = settings.gcp_project_id
    if not project_id:
        return None

    secret_attr = (secret_env_name or f"{env_name}_SECRET").lower()
    secret_id = getattr(settings, secret_attr, None)
    if not secret_id:
        return None

    if secret_id.startswith("projects/"):
        secret_path = secret_id
    else:
        secret_path = f"projects/{project_id}/secrets/{secret_id}/versions/latest"

    try:
        client = secretmanager.SecretManagerServiceClient()
        response = client.access_secret_version(request={"name": secret_path})
        return response.payload.data.decode("utf-8")
    except Exception:
        return None
