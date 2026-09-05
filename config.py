import os
from dotenv import load_dotenv

load_dotenv()


def csv_env(name: str) -> list[str]:
    value = os.getenv(name, "")
    return [x.strip().lower() for x in value.split(",") if x.strip()]


class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")

    ADMIN_USER_IDS = {
        int(x)
        for x in csv_env("ADMIN_USER_IDS")
        if x.isdigit()
    }

    ALLOWED_DOMAINS = csv_env("ALLOWED_DOMAINS")

    MAX_WORKERS = max(1, int(os.getenv("MAX_WORKERS", "5")))
    REQUEST_TIMEOUT = max(1, int(os.getenv("REQUEST_TIMEOUT", "15")))
    MAX_FILE_SIZE_MB = max(1, int(os.getenv("MAX_FILE_SIZE_MB", "20")))
    MAX_LINES_PER_JOB = max(1, int(os.getenv("MAX_LINES_PER_JOB", "10000")))

    # Delay between requests to the same hostname.
    PER_DOMAIN_DELAY = max(
        0.0,
        float(os.getenv("PER_DOMAIN_DELAY", "1"))
    )
