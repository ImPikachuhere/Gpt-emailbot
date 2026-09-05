from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def root():
    return {
        "service": "telegram-url-health-bot",
        "status": "ok"
    }


@app.get("/health")
async def health():
    return {
        "status": "ok"
    }
