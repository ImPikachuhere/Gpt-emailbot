import os
import asyncio
import uvicorn

from bot import bot_application
from health import app as health_app


async def run_bot():
    await bot_application.initialize()
    await bot_application.start()
    await bot_application.updater.start_polling()

    try:
        await asyncio.Event().wait()
    finally:
        await bot_application.updater.stop()
        await bot_application.stop()
        await bot_application.shutdown()


async def main():
    port = int(os.getenv("PORT", "10000"))

    server_config = uvicorn.Config(
        health_app,
        host="0.0.0.0",
        port=port,
        log_level="info",
    )

    server = uvicorn.Server(server_config)

    await asyncio.gather(
        run_bot(),
        server.serve(),
    )


if __name__ == "__main__":
    asyncio.run(main())
