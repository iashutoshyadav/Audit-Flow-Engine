import pdfplumber
import fitz  # PyMuPDF
from PIL import Image, ImageEnhance
import pytesseract
import io
import os
import re
import hashlib
import json
import time
import logging
from concurrent.futures import ThreadPoolExecutor

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if os.path.exists(r'C:\Program Files\Tesseract-OCR\tesseract.exe'):
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Configuration
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "temp", "cache")
os.makedirs(CACHE_DIR, exist_ok=True)
MAX_PAGES_TO_PROCESS = 10
OCR_DPI = 200  # Reduced to save memory on Free Tier

def get_file_hash(pdf_path):
    """Calculates MD5 hash of file for caching."""
    hash_md5 = hashlib.md5()
    try:
        with open(pdf_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
    except Exception as e:
        logger.error(f"Hashing error: {e}")
        return None
    return hash_md5.hexdigest()

def get_cached_result(file_hash):
    if not file_hash: return None
    cache_path = os.path.join(CACHE_DIR, f"{file_hash}.json")
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r") as f:
                logger.info(f"Cache hit: {file_hash}")
                return json.load(f)
        except Exception as e:
            logger.error(f"Cache read error: {e}")
    return None

def save_to_cache(file_hash, data):
    if not file_hash: return
    cache_path = os.path.join(CACHE_DIR, f"{file_hash}.json")
    try:
        with open(cache_path, "w") as f:
            json.dump(data, f)
            logger.info(f"Saved to cache: {file_hash}")
    except Exception as e:
        logger.error(f"Cache save error: {e}")

def preprocess_image(image):
    """Optimizes image for OCR: Grayscale + Contrast."""
    try:
        image = image.convert('L') # Grayscale
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0) # Increased contrast for sharper text
        return image
    except Exception as e:
        logger.warning(f"Image preprocessing failed: {e}")
        return image

def ocr_page(page_index, pdf_path):
    """Worker function for parallel OCR."""
    try:
        doc = fitz.open(pdf_path)
        page = doc[page_index]
        pix = page.get_pixmap(dpi=OCR_DPI)
        img_data = pix.tobytes("png")
        image = Image.open(io.BytesIO(img_data))
        image = preprocess_image(image)
        
        custom_config = r"--oem 3 --psm 6"
        text = pytesseract.image_to_string(image, lang="eng", config=custom_config)
        doc.close()
        return text
    except Exception as e:
        logger.error(f"OCR error on page {page_index}: {e}")
        return ""

def extract_table_structure(pdf_path):
    start_time = time.time()
    
    # Check File Size Limit (10MB)
    file_size = os.path.getsize(pdf_path)
    if file_size > 10 * 1024 * 1024:
        logger.error(f"File too large: {file_size / (1024*1024):.2f}MB")
        return {"rows": [], "error": "File exceeds 10MB limit"}

    # 1. Caching
    file_hash = get_file_hash(pdf_path)
    cached = get_cached_result(file_hash)
    if cached:
        return cached

    result = {
        "year_headers": [],
        "rows": []
    }

    try:
        all_text_lines = []
        pages_to_process_indices = []

        # 2. Smart Page Detection & Text Extraction
        logger.info("Starting Text Extraction...")
        
        is_scanned = False
        total_pages = 0
        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            # Check first page text to determine if scanned (FAST)
            text_check = ""
            for i in range(min(1, total_pages)):
                text_check += doc[i].get_text()
            
            if not text_check.strip():
                is_scanned = True
                logger.info("PyMuPDF detected scanned document. Switching to OCR mode.")
            doc.close()
        except Exception as e:
            logger.error(f"PyMuPDF check failed: {e}")
            # If PyMuPDF fails, we might proceed to pdfplumber or just error out, 
            # but usually it's reliable. We'll set scanned=False to try pdfplumber.
            is_scanned = False

        if is_scanned:
            # For scanned PDFs, take first 6 pages max
            pages_to_process_indices = list(range(min(total_pages, 6)))
        else:
            # Native PDF: Use PyMuPDF for fast text extraction (avoid pdfplumber hangs)
            try:
                doc = fitz.open(pdf_path)
                keywords = ["Balance Sheet", "Profit and Loss", "Cash Flow", "Assets", "Liabilities", "Income"]
                
                for i in range(len(doc)):
                    page = doc[i]
                    text = page.get_text() or ""
                    
                    if any(k.lower() in text.lower() for k in keywords):
                        pages_to_process_indices.append(i)
                        all_text_lines.extend(text.split("\n"))
                
                # Context: Add next 1 page for each hit to catch overflow tables
                additional_indices = []
                for idx in pages_to_process_indices:
                    if idx + 1 < len(doc) and (idx + 1) not in pages_to_process_indices:
                        additional_indices.append(idx + 1)
                
                # Fetch text for context pages
                for idx in additional_indices:
                    # Only if we aren't over limit
                    if len(pages_to_process_indices) + len(additional_indices) <= MAX_PAGES_TO_PROCESS:
                         text = doc[idx].get_text()
                         if text: all_text_lines.extend(text.split("\n"))
                
                doc.close()
            except Exception as e:
                logger.error(f"PyMuPDF native extraction failed: {e}")
                # Fallback to empty, will trigger OCR if result is empty


        # deduplicate and limit indices
        pages_to_process_indices = sorted(list(set(pages_to_process_indices)))[:MAX_PAGES_TO_PROCESS]
        
        # 3. Parallel OCR (Only if needed)
        if is_scanned or not all_text_lines:
            logger.info(f"Running Parallel OCR on {len(pages_to_process_indices)} pages...")
            # Reduced workers to prevent OOM on Free Tier
            with ThreadPoolExecutor(max_workers=2) as executor: 
                futures = [executor.submit(ocr_page, idx, pdf_path) for idx in pages_to_process_indices]
                for future in futures:
                    text_content = future.result()
                    if text_content:
                        all_text_lines.extend(text_content.split("\n"))

        # 4. Parse Results
        logger.info(f"Parsing {len(all_text_lines)} lines...")
        result = parse_financial_statement_advanced(all_text_lines)
        
        # 5. Fallback Table Extraction (Native only)
        if not result["rows"] and not is_scanned:
             logger.info("Parsing failed, trying native table extraction...")
             with pdfplumber.open(pdf_path) as pdf:
                 for i in pages_to_process_indices:
                     page = pdf.pages[i]
                     tables = page.extract_tables()
                     for table in tables:
                         if not table: continue
                         # ... (reuse table parsing logic if needed, simplified here)
                         # Simple converter for table to rows for consistency
                         for row in table:
                             if row and len(row) > 1 and row[0]: # Basic validation
                                 result["rows"].append({
                                     "item": str(row[0]).strip(),
                                     "values": [str(c).strip() for c in row[1:] if c],
                                     "indent": 0
                                 })

        # Save to cache if successful
        if result["rows"]:
            save_to_cache(file_hash, result)
            
        logger.info(f"Extraction completed in {time.time() - start_time:.2f}s")

    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        import traceback
        traceback.print_exc()

    return result

# ... (Keep existing parse_financial_statement_advanced and helper functions below)



def parse_financial_statement_advanced(lines):
    result = {
        "year_headers": [],
        "rows": []
    }

    # Enhanced year pattern to catch "March 2024", "31-03-2024", "FY25", etc.
    year_pattern = re.compile(r"FY\s*(\d{2,4})|(\d{1,2})[-/](?:\d{1,2}|Start|End|Dec|Mar|Jun|Sep)[-/](\d{2,4})|(?:March|December|September|June)\s+(\d{4})", re.IGNORECASE)
    number_pattern = r"[-—–]?\(?\s*\d+(?:,\d+)*(?:\.\d+)?\s*\)?"

    year_header_found = False
    i = 0

    while i < len(lines):
        line = lines[i]

        if not line.strip():
            i += 1
            continue

        if not year_header_found:
            if "year ended" in line.lower():
                print(f"DEBUG: 'Year ended' block detected: '{line.strip()}'")
            
            years_found = year_pattern.findall(line)
            if years_found:
                # Correctly handle regex groups (findall returns tuples)
                flat_years = []
                for y_match in years_found:
                    if isinstance(y_match, tuple):
                        # Find the first non-empty group in the tuple
                        yr = next((item for item in y_match if item), "")
                        if yr: flat_years.append(yr)
                    else:
                        flat_years.append(y_match)
                
                if flat_years:
                     result["year_headers"] = [f"FY {y}" for y in flat_years]
                     year_header_found = True
                     i += 1
                     continue

        numbers = re.findall(number_pattern, line)

        numbers = [
            n for n in numbers
            if len(
                n.replace(",", "")
                .replace(".", "")
                .replace("(", "")
                .replace(")", "")
                .replace("-", "")
                .replace("—", "")
                .replace("–", "")
            ) > 0 # Changed from > 1 to allow single digits if they are valid values, handled later
        ]

        if numbers or is_category_header(line):
            # Extract preliminary item_name for safety checks
            # Find where numbers start to get the item name
            preliminary_item_name = line
            if numbers:
                first_num_match = re.search(re.escape(numbers[0]), line)
                if first_num_match:
                    preliminary_item_name = line[:first_num_match.start()].strip()
            
            first_num_pos = len(line)
            if numbers:
                potential_pos = line.find(numbers[0])
                date_context = line[max(0, potential_pos-10):potential_pos+10].lower()
                if "march" in date_context or "september" in date_context or "december" in date_context:
                    if len(numbers) > 1:
                        first_num_pos = line.find(numbers[1])
                    else:
                        first_num_pos = len(line)
                else:
                    # Logic to identify if the first number is a Note Index
                    first_val_clean = numbers[0].replace(',', '').replace('(', '').replace(')', '').strip()
                    first_val_float = 0.0
                    try: first_val_float = float(first_val_clean)
                    except: pass
                    
                    is_note_index = False
                    
                    # 1. If we have more numbers than headers, and first is small (< 100)
                    if len(result["year_headers"]) > 0 and len(numbers) > len(result["year_headers"]):
                        if first_val_float < 100:
                            is_note_index = True
                    
                    # 2. Heuristic: If first number is small (< 100) and it's NOT a Ratio/EPS row
                    # This handles cases like "2.1" where count check might fail or headers aren't perfect
                    # USE PRELIMINARY ITEM NAME for safety check
                    if not is_note_index and first_val_float < 100:
                         is_safe_to_drop = True
                         # Safety: Don't drop small numbers for EPS, Ratios, or specific fields
                         if any(x in preliminary_item_name.lower() for x in ["earnings", "share", "eps", "ratio", "parity", "yield"]):
                             is_safe_to_drop = False
                         
                         if is_safe_to_drop and len(numbers) > 1: 
                             is_note_index = True
                    
                    if is_note_index:
                         print(f"DEBUG: Dropping note index: '{numbers[0]}'")
                         first_num_pos = line.find(numbers[1])
                         numbers = numbers[1:]
                    else:
                         first_num_pos = potential_pos
            
            item_name = line[:first_num_pos].strip()

            STOP_SECTIONS = [
                "cash flow", "segment", "ratio", "earnings per share", 
                "descriptive", "exceptional items", "kpi",
                "significant accounting", "notes to financial"
            ]
            if not numbers and any(re.search(rf"\b{re.escape(s)}\b", line.lower()) for s in STOP_SECTIONS):
                print(f"DEBUG: Stop section detected: '{line.strip()}'. Breaking extraction.")
                break
            if re.match(r'^[IVX]+\.', line.strip()):
                print(f"DEBUG: Identified structural header: '{line.strip()}'")
                result["rows"].append({
                    "item": line.strip(),
                    "values": [],
                    "indent": 0
                })
                i += 1
                continue

            if len(item_name) < 2 or item_name.lower() in ["note no.", "note", "particulars"]:
                if result["rows"] and not any(r.get('values') for r in [result["rows"][-1]]):
                    result["rows"][-1]["values"] = clean_numbers(numbers, result.get("year_headers"))
                    print(f"DEBUG: Merged numbers into previous label: '{result['rows'][-1]['item']}'")
                    i += 1
                    continue
                
                i += 1
                continue

            if len(numbers) > len(result["year_headers"]) and len(result["year_headers"]) > 0:
                try:
                    first_val_clean = numbers[0].replace(',', '').replace('(', '').replace(')', '').strip()
                    if first_val_clean.isdigit() and int(first_val_clean) < 100:
                        print(f"DEBUG: Dropping perceived note index column: '{numbers[0]}'")
                        numbers = numbers[1:]
                except:
                    pass

            cleaned_numbers = clean_numbers(numbers, result["year_headers"])
            
            if len(cleaned_numbers) > 1:
                try:
                    first_val = float(cleaned_numbers[0])
                    next_val = float(cleaned_numbers[1])
                    is_note_like = (abs(first_val) < 100 and abs(next_val) > 500) or ('.' in cleaned_numbers[0] and abs(first_val) < 50)
                    
                    if is_note_like:
                        print(f"DEBUG: Identified potential note '{cleaned_numbers[0]}' in line: '{line.strip()}' - Skipping it.")
                        cleaned_numbers = cleaned_numbers[1:]
                except:
                    pass

            indent_level = detect_indentation(line, first_num_pos)

            result["rows"].append({
                "item": item_name,
                "values": cleaned_numbers,
                "indent": indent_level
            })

        i += 1

    if not result["year_headers"] and result["rows"]:
        max_values = max(len(row["values"]) for row in result["rows"])
        result["year_headers"] = [f"Year {i+1}" for i in range(max_values)]

    return result


def is_category_header(line):
    keywords = [
        "Revenue", "Expenses", "Cost of Material",
        "Employee Benefit", "Finance Cost",
        "Other Expense", "EBITDA", "Profit",
        "Tax", "Purchases of Stock",
        "Gross Profit", "Gross Margin"
    ]
    return any(keyword.lower() in line.lower() for keyword in keywords)


def detect_indentation(line, first_num_pos):
    original_line = line[:first_num_pos]
    leading_spaces = len(original_line) - len(original_line.lstrip())

    if leading_spaces == 0:
        return 0
    if leading_spaces <= 2:
        return 1
    if leading_spaces <= 4:
        return 2
    return 3


def clean_numbers(numbers, year_headers=None):
    cleaned = []
    year_strings = []
    if year_headers:
        for yh in year_headers:
            match = re.search(r'(\d{2,4})', yh)
            if match:
                year_strings.append(match.group(1))

    for num in numbers:
        num = num.strip()

        if "(" in num and ")" in num:
            inner = num.replace("(", "").replace(")", "").strip()
            num = "-" + inner

        num = num.replace("—", "-").replace("–", "-")
        num = num.replace(",", "").strip()

        cleaned.append(num)
    return cleaned


def extract_lines(pdf_path):
    table_data = extract_table_structure(pdf_path)
    lines = []
    for row in table_data["rows"]:
        lines.append(f"{row['item']} {' '.join(row['values'])}")
    return lines


def extract_lines_gen(pdf_path):
    yield 10, None
    yield 30, None
    yield 50, None
    table_data = extract_table_structure(pdf_path)
    yield 80, table_data
