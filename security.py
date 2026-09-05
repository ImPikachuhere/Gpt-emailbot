from urllib.parse import urlparse
from config import Config


def is_admin(user_id: int) -> bool:
    return user_id in Config.ADMIN_USER_IDS


def get_hostname(url: str) -> str:
    try:
        parsed = urlparse(url)
        return (parsed.hostname or "").lower()
    except Exception:
        return ""


def validate_domain(url: str) -> bool:
    hostname = get_hostname(url)

    if not hostname:
        return False

    for allowed in Config.ALLOWED_DOMAINS:
        allowed = allowed.lower().lstrip(".")

        if hostname == allowed:
            return True

        if hostname.endswith("." + allowed):
            return True

    return False
