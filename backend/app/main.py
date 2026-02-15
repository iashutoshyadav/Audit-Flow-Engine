from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes.extract import router

app = FastAPI(title="Financial Extractor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

@app.get("/")
async def health_check():
    return {"status": "ok", "message": "API is online"}

app.include_router(router, prefix="/api")
