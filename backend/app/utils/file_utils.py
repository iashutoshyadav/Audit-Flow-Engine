import uuid
import os
from app.core.config import TEMP_DIR

def save_temp_file(upload_file):
    filename = f"{uuid.uuid4()}_{upload_file.filename}"
    path = os.path.join(TEMP_DIR, filename)
    with open(path, "wb") as f:
        f.write(upload_file.file.read())
    return path

def cleanup_file(path):
    if os.path.exists(path):
        os.remove(path)
