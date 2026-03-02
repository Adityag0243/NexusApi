from fastapi import FastAPI

app = FastAPI(title="NexusAPI")

from src.routes import auth, users, credits, api
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(credits.router)
app.include_router(api.router)

@app.get("/")
async def root():
    return {"message": "NexusAPI is running", "status": "healthy"}

@app.get("/health")
async def health_check():
    """Health check. Returns 200 if healthy."""
    return {"status": "healthy"}
