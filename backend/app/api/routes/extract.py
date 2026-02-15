from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
import os
import json
from app.utils.file_utils import save_temp_file, cleanup_file
from app.services.pdf_service import extract_table_structure
from app.services.normalize_service import extract_income_statement
from app.services.excel_service import create_excel
from app.core.config import TEMP_DIR

router = APIRouter()

@router.post("/upload")
async def extract_financials(file: UploadFile = File(...)):
    async def event_generator():
        pdf_path = save_temp_file(file)
        try:
            yield json.dumps({"progress": 5, "message": "PDF uploaded successfully..."}) + "\n"
            
            yield json.dumps({"progress": 10, "message": "Initializing AI extraction..."}) + "\n"
            
            yield json.dumps({"progress": 15, "message": "Reading PDF document..."}) + "\n"
            
            yield json.dumps({"progress": 20, "message": "Extracting text from PDF..."}) + "\n"
            
            table_data = extract_table_structure(pdf_path)
            
            if table_data.get("error"):
                 yield json.dumps({"status": "error", "message": table_data["error"]}) + "\n"
                 return
            
            yield json.dumps({"progress": 35, "message": "Text extraction complete..."}) + "\n"
            
            yield json.dumps({"progress": 40, "message": "Analyzing financial statements..."}) + "\n"
            
            yield json.dumps({"progress": 50, "message": "Classifying line items..."}) + "\n"
            
            processed = extract_income_statement(table_data)
            
            yield json.dumps({"progress": 60, "message": "Building financial model..."}) + "\n"
            
            yield json.dumps({"progress": 70, "message": "Calculating totals and formulas..."}) + "\n"
            
            yield json.dumps({"progress": 80, "message": "Generating Excel structure..."}) + "\n"
            
            excel_stream = create_excel(processed)
            
            yield json.dumps({"progress": 90, "message": "Finalizing Excel report..."}) + "\n"
            
            filename = f"financials_{file.filename}.xlsx"
            file_path = os.path.join(TEMP_DIR, filename)
            
            with open(file_path, "wb") as f:
                f.write(excel_stream.getvalue())
            
            yield json.dumps({"progress": 95, "message": "Saving file..."}) + "\n"
            
            row_count = 0
            for section_items in processed.get('structured_data', {}).values():
                row_count += len(section_items)

            yield json.dumps({
                "status": "complete",
                "progress": 100,
                "message": "Extraction complete!",
                "data": {
                    "filename": filename,
                    "extracted_data": {
                        "year_headers": processed.get('year_headers', []),
                        "row_count": row_count
                    }
                }
            }) + "\n"
            
        except Exception as e:
            print(f"Extraction error: {str(e)}")
            yield json.dumps({"status": "error", "message": str(e)}) + "\n"
        finally:
            cleanup_file(pdf_path)
            
    return StreamingResponse(event_generator(), media_type="application/x-ndjson")

@router.get("/download/{filename}")
async def download_file(filename: str):
    path = os.path.join(TEMP_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404)
    return FileResponse(path)
