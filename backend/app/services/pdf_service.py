import pdfplumber
import fitz
from PIL import Image
import pytesseract
import io
import os
import re

if os.path.exists(r'C:\Program Files\Tesseract-OCR\tesseract.exe'):
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


def extract_table_structure(pdf_path):
    result = {
        "year_headers": [],
        "rows": []
    }

    try:
        with pdfplumber.open(pdf_path) as pdf:
            all_text_lines = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    all_text_lines.extend(text.split("\n"))

            if all_text_lines:
                print(f"DEBUG: Attempting advanced parse on {len(all_text_lines)} text lines")
                result = parse_financial_statement_advanced(all_text_lines)

            if not result["rows"]:
                print("DEBUG: Advanced parse found no rows, attempting table extraction...")
                for page in pdf.pages:
                    tables = page.extract_tables()
                    if not tables:
                        continue

                    for table in tables:
                        if not table:
                            continue

                        if not result["year_headers"] and len(table) > 0:
                            header_row = table[0]
                            for cell in header_row[1:]:
                                if cell:
                                    result["year_headers"].append(str(cell).strip())

                        for row in table[1:]:
                            if not row or not row[0]:
                                continue

                            item_name = str(row[0]).strip()
                            if not item_name:
                                continue

                            indent_level = len(item_name) - len(item_name.lstrip())

                            values = []
                            for cell in row[1:]:
                                values.append(str(cell).strip() if cell else "")

                            result["rows"].append({
                                "item": item_name.strip(),
                                "values": values,
                                "indent": indent_level // 2
                            })

        if not result["rows"]:
            print("DEBUG: Table extraction found no rows, attempting OCR...")
            result = extract_table_with_ocr(pdf_path)

    except Exception as e:
        print(f"DEBUG: PDF processing error: {str(e)}")
        import traceback
        traceback.print_exc()

    return result


def extract_table_with_ocr(pdf_path):
    result = {
        "year_headers": [],
        "rows": []
    }

    try:
        doc = fitz.open(pdf_path)
        all_text_lines = []

        for page in doc:
            pix = page.get_pixmap(dpi=300)
            img_data = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_data))
            custom_config = r"--oem 3 --psm 6"
            text = pytesseract.image_to_string(image, lang="eng", config=custom_config)
            if text:
                all_text_lines.extend(text.split("\n"))

        doc.close()
        print(f"DEBUG: OCR completed, found {len(all_text_lines)} lines")
        result = parse_financial_statement_advanced(all_text_lines)

    except Exception as e:
        print(f"DEBUG: OCR error: {str(e)}")

    return result


def parse_financial_statement_advanced(lines):
    result = {
        "year_headers": [],
        "rows": []
    }

    year_pattern = re.compile(r"FY\s*(\d{2,4})", re.IGNORECASE)
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
                result["year_headers"] = [f"FY {y}" for y in years_found]
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
            ) > 1
        ]

        if numbers or is_category_header(line):
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
                    first_val_clean = numbers[0].replace(',', '').replace('(', '').replace(')', '').strip()
                    if len(first_val_clean) <= 2 and len(numbers) > 1:
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
