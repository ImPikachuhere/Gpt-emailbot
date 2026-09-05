import asyncio
import io
from collections import Counter

from telegram import Bot

from config import Config
from parser import URLParser
from tester import URLHealthTester


class QueueManager:

    def __init__(self, bot: Bot, chat_id: int):
        self.bot = bot
        self.chat_id = chat_id

        self.queue = asyncio.Queue()
        self.tester = URLHealthTester()

        self.results = []
        self.processed = 0
        self.total = 0

        self.cancel_event = asyncio.Event()

    async def worker(self):
        while True:
            entry = await self.queue.get()

            try:
                if self.cancel_event.is_set():
                    continue

                result = await self.tester.test(entry)

                self.results.append(result)
                self.processed += 1

                if self.processed % 50 == 0:
                    await self.send_progress()

            finally:
                self.queue.task_done()

    async def send_progress(self):
        await self.bot.send_message(
            self.chat_id,
            (
                "🔄 Health check running\n\n"
                f"Completed: {self.processed}/{self.total}\n"
                f"Remaining: {self.total - self.processed}"
            )
        )

    async def cancel(self):
        self.cancel_event.set()

        while not self.queue.empty():
            try:
                self.queue.get_nowait()
                self.queue.task_done()
            except asyncio.QueueEmpty:
                break

    async def process(self, content: str):
        entries, stats = URLParser.parse_file(content)

        ready = [
            entry
            for entry in entries
            if entry["status"] == "READY"
        ]

        self.total = len(ready)

        await self.bot.send_message(
            self.chat_id,
            (
                "📄 File processed\n\n"
                f"Lines: {stats['total_lines']}\n"
                f"URLs ready: {stats['ready']}\n"
                f"Malformed: {stats['malformed']}\n"
                f"Unauthorized domains: {stats['unauthorized']}\n"
                f"Duplicates: {stats['duplicates']}\n\n"
                f"Starting health checks for {self.total} URLs..."
            )
        )

        workers = [
            asyncio.create_task(self.worker())
            for _ in range(Config.MAX_WORKERS)
        ]

        for entry in ready:
            await self.queue.put(entry)

        await self.queue.join()

        for worker in workers:
            worker.cancel()

        await asyncio.gather(
            *workers,
            return_exceptions=True
        )

        await self.send_results()

    async def send_results(self):
        counts = Counter(
            result["status"]
            for result in self.results
        )

        output = io.StringIO()

        output.write(
            "URL | RESULT | HTTP_STATUS | RESPONSE_MS | FINAL_URL | ERROR\n"
        )

        for result in self.results:
            output.write(
                f"{result['url']} | "
                f"{result['status']} | "
                f"{result['http_status']} | "
                f"{result['response_ms']} | "
                f"{result['final_url']} | "
                f"{result['error']}\n"
            )

        data = io.BytesIO(
            output.getvalue().encode("utf-8")
        )

        data.name = "url_health_results.txt"

        await self.bot.send_document(
            self.chat_id,
            document=data
        )

        summary = (
            "✅ Health check completed\n\n"
            f"Total checked: {len(self.results)}\n"
            f"Reachable: {counts.get('REACHABLE', 0)}\n"
            f"Timeout: {counts.get('TIMEOUT', 0)}\n"
            f"TLS errors: {counts.get('TLS_ERROR', 0)}\n"
            f"Connection errors: {counts.get('CONNECTION_ERROR', 0)}\n"
            f"HTTP/client errors: {counts.get('HTTP_ERROR', 0)}\n"
            f"Other errors: {counts.get('ERROR', 0)}"
        )

        await self.bot.send_message(
            self.chat_id,
            summary
      )
