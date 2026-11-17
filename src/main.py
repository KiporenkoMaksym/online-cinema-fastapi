from fastapi import FastAPI

from src.api.auth import router as auth_router

app = FastAPI(
    title="Online Cinema API",
    description="REST API for Online Cinema platform",
    version="0.1.0",
)

app.include_router(auth_router)


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}