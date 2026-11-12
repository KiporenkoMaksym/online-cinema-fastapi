from fastapi import FastAPI

app = FastAPI(
    title="Online Cinema API",
    description="REST API for Online Cinema",
    version="0.1.0",
)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}
