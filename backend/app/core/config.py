import os
from dotenv import load_dotenv

load_dotenv()

TEMP_DIR = os.getenv("TEMP_DIR", "app/temp")
os.makedirs(TEMP_DIR, exist_ok=True)
