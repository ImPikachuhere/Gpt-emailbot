from urllib.parse import urlparse
from security import validate_domain


class URLParser:

    @staticmethod
    def parse_line(line: str) -> dict:
        raw = line.strip()

        if not raw:
            return {
                "status": "EMPTY",
                "raw": raw,
                "url": None
            }

        # Only the first field is considered.
        # Credential material is never used.
        url = raw.split(" : ", 1)[0].strip()

        if not url.startswith(("http://", "https://")):
            return {
                "status": "MALFORMED",
                "raw": raw,
                "url": url
            }

        try:
            parsed = urlparse(url)

            if not parsed.hostname:
                raise ValueError()

            if parsed.username or parsed.password:
                raise ValueError()

        except Exception:
            return {
                "status": "MALFORMED",
                "raw": raw,
                "url": url
            }

        if not validate_domain(url):
            return {
                "status": "UNAUTHORIZED_DOMAIN",
                "raw": raw,
                "url": url
            }

        return {
            "status": "READY",
            "raw": raw,
            "url": url
        }

    @staticmethod
    def parse_file(content: str):
        results = []

        stats = {
            "total_lines": 0,
            "ready": 0,
            "malformed": 0,
            "unauthorized": 0,
            "duplicates": 0,
        }

        seen = set()

        for line in content.splitlines():
            if not line.strip():
                continue

            stats["total_lines"] += 1

            entry = URLParser.parse_line(line)

            if entry["status"] == "READY":
                normalized = entry["url"].rstrip("/").lower()

                if normalized in seen:
                    entry["status"] = "DUPLICATE"
                    stats["duplicates"] += 1
                else:
                    seen.add(normalized)
                    stats["ready"] += 1

            elif entry["status"] == "MALFORMED":
                stats["malformed"] += 1

            elif entry["status"] == "UNAUTHORIZED_DOMAIN":
                stats["unauthorized"] += 1

            results.append(entry)

        return results, stats
