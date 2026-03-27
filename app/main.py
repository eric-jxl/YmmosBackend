from fastapi import FastAPI

app = FastAPI(title="YmmosBackend", version="0.1.0")


@app.get("/")
async def root():
    return {"message": "YmmosBackend is running"}


@app.get("/health")
async def health():
    return {"status": "ok"}
