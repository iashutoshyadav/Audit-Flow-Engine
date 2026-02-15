from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes.extract import router
import os

app = FastAPI(title="Financial Extractor API")

frontend_url = os.getenv("FRONTEND_URL")

origins = [
    frontend_url,
    "http://localhost:5173",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def health_check():
    return {"status": "ok", "message": "API is online"}

app.include_router(router, prefix="/api")
