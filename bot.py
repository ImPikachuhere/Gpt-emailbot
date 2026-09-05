import asyncio

from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import Config
from security import is_admin
from queue_manager import QueueManager
from health import app as fastapi_app


job_lock = asyncio.Lock()
current_job = None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin access required.")
        return

    await update.message.reply_text(
        "Send a TXT file containing authorized URLs.\n\n"
        "Example:\n"
        "https://example.com/health\n"
        "https://example.com/api/status"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin access required.")
        return

    if current_job is None:
        await update.message.reply_text("✅ No job running.")
        return

    await update.message.reply_text(
        f"🔄 Job running\n"
        f"Completed: {current_job.processed}/{current_job.total}"
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin access required.")
        return

    if current_job is None:
        await update.message.reply_text("No active job.")
        return

    await current_job.cancel()

    await update.message.reply_text(
        "🛑 Cancellation requested."
    )


async def handle_document(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    global current_job

    if not is_admin(update.effective_user.id):
        await update.message.reply_text(
            "⛔ Admin access required."
        )
        return

    async with job_lock:

        if current_job is not None:
            await update.message.reply_text(
                "⚠️ A job is already running."
            )
            return

        document = update.message.document

        if document.file_size is None:
            await update.message.reply_text(
                "Unable to determine file size."
            )
            return

        max_bytes = (
            Config.MAX_FILE_SIZE_MB * 1024 * 1024
        )

        if document.file_size > max_bytes:
            await update.message.reply_text(
                f"File too large. Maximum: "
                f"{Config.MAX_FILE_SIZE_MB} MB."
            )
            return

        telegram_file = await context.bot.get_file(
            document.file_id
        )

        data = await telegram_file.download_as_bytearray()

        try:
            content = bytes(data).decode("utf-8")
        except UnicodeDecodeError:
            await update.message.reply_text(
                "❌ File must be UTF-8 encoded TXT."
            )
            return

        if len(content.splitlines()) > Config.MAX_LINES_PER_JOB:
            await update.message.reply_text(
                f"Too many lines. Maximum: "
                f"{Config.MAX_LINES_PER_JOB}."
            )
            return

        current_job = QueueManager(
            context.bot,
            update.effective_chat.id
        )

        try:
            await current_job.process(content)
        finally:
            current_job = None


async def post_init(application: Application):
    await application.bot.set_my_commands([
        ("start", "Start the bot"),
        ("status", "Show current job status"),
        ("cancel", "Cancel current job"),
    ])


def create_bot():
    application = (
        ApplicationBuilder()
        .token(Config.BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CommandHandler("status", status)
    )

    application.add_handler(
        CommandHandler("cancel", cancel)
    )

    application.add_handler(
        MessageHandler(
            filters.Document.TEXT,
            handle_document
        )
    )

    return application


# Used by the Render process.
bot_application = create_bot()
