import asyncio
import time
import aiohttp

from config import Config
from security import get_hostname


class URLHealthTester:

    def __init__(self):
        self.semaphore = asyncio.Semaphore(Config.MAX_WORKERS)
        self.domain_locks = {}
        self.last_request = {}

    def _get_domain_lock(self, hostname):
        if hostname not in self.domain_locks:
            self.domain_locks[hostname] = asyncio.Lock()

        return self.domain_locks[hostname]

    async def _respect_domain_delay(self, hostname):
        lock = self._get_domain_lock(hostname)

        async with lock:
            now = time.monotonic()
            previous = self.last_request.get(hostname, 0)

            wait = Config.PER_DOMAIN_DELAY - (now - previous)

            if wait > 0:
                await asyncio.sleep(wait)

            self.last_request[hostname] = time.monotonic()

    async def test(self, entry: dict) -> dict:
        url = entry["url"]

        hostname = get_hostname(url)

        async with self.semaphore:
            await self._respect_domain_delay(hostname)

            timeout = aiohttp.ClientTimeout(
                total=Config.REQUEST_TIMEOUT
            )

            try:
                async with aiohttp.ClientSession(
                    timeout=timeout,
                    headers={
                        "User-Agent": "Authorized-URL-Health-Checker/1.0"
                    }
                ) as session:

                    start = time.monotonic()

                    async with session.get(
                        url,
                        allow_redirects=True
                    ) as response:

                        elapsed = round(
                            (time.monotonic() - start) * 1000,
                            2
                        )

                        return {
                            "url": url,
                            "status": "REACHABLE",
                            "http_status": response.status,
                            "final_url": str(response.url),
                            "response_ms": elapsed,
                            "error": ""
                        }

            except asyncio.TimeoutError:
                return {
                    "url": url,
                    "status": "TIMEOUT",
                    "http_status": "",
                    "final_url": "",
                    "response_ms": "",
                    "error": "Request timed out"
                }

            except aiohttp.ClientConnectorCertificateError:
                return {
                    "url": url,
                    "status": "TLS_ERROR",
                    "http_status": "",
                    "final_url": "",
                    "response_ms": "",
                    "error": "TLS certificate error"
                }

            except aiohttp.ClientConnectorError as exc:
                return {
                    "url": url,
                    "status": "CONNECTION_ERROR",
                    "http_status": "",
                    "final_url": "",
                    "response_ms": "",
                    "error": str(exc)
                }

            except aiohttp.ClientError as exc:
                return {
                    "url": url,
                    "status": "HTTP_ERROR",
                    "http_status": "",
                    "final_url": "",
                    "response_ms": "",
                    "error": str(exc)
                }

            except Exception as exc:
                return {
                    "url": url,
                    "status": "ERROR",
                    "http_status": "",
                    "final_url": "",
                    "response_ms": "",
                    "error": str(exc)
                  }
