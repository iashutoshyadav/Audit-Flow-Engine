from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes.extract import router
import os

app = FastAPI(title="Financial Extractor API")

# Hardcoded known origins + env var support
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://audit-flow-engine-gamma.vercel.app",
]

# Add any extra origins from env (comma-separated)
extra = os.getenv("ALLOWED_ORIGINS", "")
if extra:
    origins.extend([o.strip() for o in extra.split(",") if o.strip()])

# Deduplicate
origins = list(set(origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,
)

@app.get("/")
async def health_check():
    return {"status": "ok", "message": "API is online"}

@app.api_route("/health", methods=["GET", "HEAD"])
async def health():
    return {"status": "healthy"}

app.include_router(router, prefix="/api")