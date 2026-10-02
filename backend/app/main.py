from fastapi import FastAPI

app = FastAPI(
    title="InsightX API",
    description="AI-powered dataset analysis platform",
    version="0.1.0"
)


@app.get("/")
def root():
    return {
        "message": "Welcome to InsightX API",
        "status": "running"
    }