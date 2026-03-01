from fastapi import FastAPI

app = FastAPI()

from src.routes import auth
app.include_router(auth.router)
from src.routes import users
app.include_router(users.router)

@app.get("/health")
async def health_check():
    # your health check logic here
    return {"status": "healthy"}