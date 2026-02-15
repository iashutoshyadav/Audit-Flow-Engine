import openpyxl
import re
from io import BytesIO
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from app.utils.validation_utils import parse_number, clean_item_name
from app.models.financial_schema import FinancialSection, FinancialLineItem

def create_excel(processed_data):
    wb = openpyxl.Workbook()
    
    if 'Sheet' in wb.sheetnames:
        wb.remove(wb['Sheet'])
    
    year_headers = processed_data.get("year_headers", [])
    structured = processed_data.get("structured_data", {})
    raw_rows = processed_data.get("raw_rows", [])
    
    HEADER_FILL = PatternFill(start_color="1B3E5F", end_color="1B3E5F", fill_type="solid") # Navy Blue
    TITLE_FONT = Font(bold=True, size=14, color="1B3E5F")
    HEADER_FONT = Font(bold=True, size=11, color="FFFFFF")
    
    create_financial_statements_sheet(wb, structured, year_headers, TITLE_FONT, HEADER_FONT, HEADER_FILL, raw_rows)
    
    create_raw_data_sheet(wb, raw_rows, year_headers)
    
    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)
    return stream

def create_financial_statements_sheet(wb, structured, year_headers, title_font, header_font, header_fill, raw_rows):
    ws = wb.create_sheet("Financial Statements")
    curr_row = 1
    
    pl_start_idx = -1
    pl_end_idx = -1
    bs_start_idx = -1
    bs_end_idx = len(raw_rows)

    pl_start_markers = ["statement of profit and loss", "income statement", "statement of comprehensive income", "profit & loss"]
    bs_start_markers = ["balance sheet", "statement of financial position", "consolidated balance sheet"]
    bs_end_markers = ["validation", "note on", "forming part of", "significant accounting policies"]

    for idx, row in enumerate(raw_rows):
        item_text = clean_item_name(row.get('item', ''))
        item_lower = item_text.lower()
        
        if any(marker in item_lower for marker in pl_start_markers) and pl_start_idx == -1:
            pl_start_idx = idx
            print(f"DEBUG: Found P&L start at index {idx}: '{item_text}'")

        if any(marker in item_lower for marker in bs_start_markers):
            if pl_end_idx == -1 and pl_start_idx != -1: 
                pl_end_idx = idx
                print(f"DEBUG: Found P&L end (BS start) at index {idx}")
            if bs_start_idx == -1: 
                bs_start_idx = idx
                print(f"DEBUG: Found BS start at index {idx}: '{item_text}'")

        if any(marker in item_lower for marker in bs_end_markers) and bs_start_idx != -1:
            if idx > bs_start_idx:
                bs_end_idx = idx
                print(f"DEBUG: Found BS end at index {idx}: '{item_text}'")
                break

    if pl_start_idx == -1 and bs_start_idx == -1:
        print("DEBUG: No markers found, using 50/50 fallback")
        pl_start_idx = 0
        pl_end_idx = len(raw_rows) // 2
        bs_start_idx = pl_end_idx
        bs_end_idx = len(raw_rows)
    elif pl_start_idx != -1 and bs_start_idx == -1:
        print("DEBUG: Only P&L marker found, checking for remaining data")
        if pl_end_idx == -1: pl_end_idx = len(raw_rows)
    elif pl_start_idx == -1 and bs_start_idx != -1:
        print("DEBUG: Only BS marker found, assuming preceding data is P&L")
        pl_start_idx = 0
        pl_end_idx = bs_start_idx

    if pl_end_idx == -1: pl_end_idx = len(raw_rows)
    if bs_end_idx == -1: bs_end_idx = len(raw_rows)

    pl_items_in_block = set()
    for i in range(max(0, pl_start_idx), min(len(raw_rows), pl_end_idx)):
        pl_items_in_block.add(clean_item_name(raw_rows[i].get('item', '')).lower())

    bs_items_in_block = set()
    for i in range(max(0, bs_start_idx), min(len(raw_rows), bs_end_idx)):
        bs_items_in_block.add(clean_item_name(raw_rows[i].get('item', '')).lower())

    ws.cell(row=curr_row, column=1, value="STATEMENT OF PROFIT AND LOSS").font = title_font
    curr_row += 2
    
    headers = ["Particulars"] + year_headers
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=curr_row, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')
    curr_row += 1
    
    rev_start = curr_row
    revenue_items = [i for i in structured.get(FinancialSection.REVENUE, []) if i.item.lower() in pl_items_in_block]
    curr_row = render_items(ws, revenue_items, curr_row, year_headers, "PL")
    rev_end = curr_row - 1
    
    existing_rev_total = None
    for item in revenue_items:
        if any(k in item.item.lower() for k in ["total", "sum", "subtotal", "net"]) and any(v.strip() for v in item.values if v):
            existing_rev_total = item
    
    if not existing_rev_total:
        total_rev_row = curr_row
        ws.cell(row=total_rev_row, column=1, value="Total Income").font = Font(bold=True)
        for i in range(len(year_headers)):
            col = get_column_letter(i+2)
            val = f"=SUM({col}{rev_start}:{col}{rev_end})" if rev_end >= rev_start else "0"
            ws.cell(row=total_rev_row, column=i+2, value=val).font = Font(bold=True, color="1B3E5F")
            ws.cell(row=total_rev_row, column=i+2).number_format = '#,##0'
        curr_row += 2
    else:
        curr_row += 1 # Space after existing total
    
    ws.cell(row=curr_row, column=1, value="EXPENSES").font = Font(bold=True)
    curr_row += 1
    exp_start = curr_row
    
    expense_cats = [FinancialSection.COST_OF_GOODS, FinancialSection.OPERATING_EXPENSES, 
                    FinancialSection.FINANCE_COST, FinancialSection.DEPRECIATION]
    expense_items = []
    for cat in expense_cats:
        cat_items = structured.get(cat, [])
        for item in cat_items:
            item_lower = item.item.lower()
            if item_lower in pl_items_in_block and "tax" not in item_lower:
                expense_items.append(item)
        
    curr_row = render_items(ws, expense_items, curr_row, year_headers, "PL")
    exp_end = curr_row - 1
    
    existing_exp_total = None
    for item in expense_items:
        if any(k in item.item.lower() for k in ["total", "sum", "subtotal", "net"]) and any(v.strip() for v in item.values if v):
            existing_exp_total = item

    if not existing_exp_total:
        total_exp_row = curr_row
        ws.cell(row=total_exp_row, column=1, value="Total Expenses").font = Font(bold=True)
        for i in range(len(year_headers)):
            col = get_column_letter(i+2)
            val = f"=SUM({col}{exp_start}:{col}{exp_end})" if exp_end >= exp_start else "0"
            ws.cell(row=total_exp_row, column=i+2, value=val).font = Font(bold=True, color="1B3E5F")
            ws.cell(row=total_exp_row, column=i+2).number_format = '#,##0'
        curr_row += 2
    else:
        curr_row += 1 # Space after existing total
    
    from app.services.structure_service import classify_row
    pbt_items = [i for i in raw_rows[max(0, pl_start_idx):pl_end_idx] if "profit" in i.get('item','').lower() and "before" in i.get('item','').lower()]
    existing_pbt = None
    if pbt_items:
        existing_pbt = pbt_items[0]

    if existing_pbt:
        pbt_vals = (existing_pbt.get('values', [])[:len(year_headers)] + [''] * len(year_headers))[:len(year_headers)]
        ws.cell(row=curr_row, column=1, value=existing_pbt.get('item')).font = Font(bold=True)
        for i, v in enumerate(pbt_vals):
            ws.cell(row=curr_row, column=i+2, value=parse_number(v)).font = Font(bold=True, color="1B3E5F")
            ws.cell(row=curr_row, column=i+2).number_format = '#,##0'
        pbt_row = curr_row
        curr_row += 2
    else:
        pbt_row = curr_row
        ws.cell(row=pbt_row, column=1, value="Profit Before Tax").font = Font(bold=True)
        for i in range(len(year_headers)):
            col = get_column_letter(i+2)
            rev_ref = total_rev_row if not existing_rev_total else (rev_end + 1) # This is getting complex
            ws.cell(row=pbt_row, column=i+2, value=f"={col}{total_rev_row}-{col}{total_exp_row}").font = Font(bold=True, color="1B3E5F")
            ws.cell(row=pbt_row, column=i+2).number_format = '#,##0'
        curr_row += 2
    
    ws.cell(row=curr_row, column=1, value="TAX").font = Font(bold=True)
    curr_row += 1
    
    tax_start = curr_row
    tax_items = []
    for i in structured.get(FinancialSection.TAX, []):
        clean_i = clean_item_name(i.item).lower()
        if clean_i in pl_items_in_block:
            tax_items.append(i)
            
    curr_row = render_items(ws, tax_items, curr_row, year_headers, "PL")
    tax_end = curr_row - 1
    
    profit_items = structured.get(FinancialSection.PROFIT, [])
    pl_profit_item = None
    for item in profit_items:
        clean_p = clean_item_name(item.item).lower()
        if clean_p in pl_items_in_block and any(k in clean_p for k in ["period", "year", "after tax"]):
            pl_profit_item = item
            break
            
    if pl_profit_item:
        curr_row = render_items(ws, [pl_profit_item], curr_row, year_headers, "PL", force=True)
    else:
        ws.cell(row=curr_row, column=1, value="Profit for the Period").font = Font(bold=True)
        for i in range(len(year_headers)):
            col = get_column_letter(i+2)
            tax_sum = f"SUM({col}{tax_start}:{col}{tax_end})" if tax_end >= tax_start else "0"
            ws.cell(row=curr_row, column=i+2, value=f"={col}{pbt_row}-({tax_sum})").font = Font(bold=True, color="1B3E5F")
            ws.cell(row=curr_row, column=i+2).number_format = '#,##0'
        curr_row += 1
    
    curr_row += 4
    
    from app.services.structure_service import classify_row

    ws.cell(row=curr_row, column=1, value="BALANCE SHEET").font = title_font
    curr_row += 2
    
    split_idx = -1
    eq_liab_markers = ["equity and liabilities", "sources of funds", "liabilities and equity"]
    
    if bs_start_idx != -1:
        for idx in range(bs_start_idx, bs_end_idx):
            item_text = clean_item_name(raw_rows[idx].get('item', '')).lower()
            if any(marker in item_text for marker in eq_liab_markers):
                split_idx = idx
                print(f"DEBUG: Found BS split (Equity/Liabilities header) at index {idx}: '{item_text}'")
                break
    
    assets_items = []
    eq_liab_items = []
    
    if split_idx != -1:
        for idx in range(bs_start_idx + 1, split_idx):
            row = raw_rows[idx]
            item_name = clean_item_name(row.get('item', ''))
            if not is_bs_excluded(item_name) and item_name.lower() not in ["assets", "balance sheet"]:
                assets_items.append(FinancialLineItem(item=item_name, values=row.get('values', []), indent=row.get('indent', 0)))
        
        for idx in range(split_idx + 1, bs_end_idx):
            row = raw_rows[idx]
            item_name = clean_item_name(row.get('item', ''))
            if not is_bs_excluded(item_name):
                eq_liab_items.append(FinancialLineItem(item=item_name, values=row.get('values', []), indent=row.get('indent', 0)))

    ws.cell(row=curr_row, column=1, value="ASSETS").font = Font(bold=True)
    curr_row += 1
    assets_start = curr_row
    curr_row = render_items(ws, assets_items, curr_row, year_headers, "BS")
    assets_end = curr_row - 1
    
    existing_assets_total = None
    for item in assets_items:
        if any(kw in item.item.lower() for kw in ["total assets", "total asset", "sum of assets"]):
            existing_assets_total = item

    if not existing_assets_total:
        total_assets_row = curr_row
        ws.cell(row=total_assets_row, column=1, value="Total Assets").font = Font(bold=True)
        for i in range(len(year_headers)):
            col = get_column_letter(i+2)
            val = f"=SUM({col}{assets_start}:{col}{assets_end})" if assets_end >= assets_start else "0"
            ws.cell(row=total_assets_row, column=i+2, value=val).font = Font(bold=True)
            ws.cell(row=total_assets_row, column=i+2).number_format = '#,##0'
        curr_row += 2
    else:
        total_assets_row = assets_start
        for i, item in enumerate(assets_items):
            if item == existing_assets_total:
                total_assets_row = assets_start + i
                break
        curr_row += 1
    
    ws.cell(row=curr_row, column=1, value="EQUITY AND LIABILITIES").font = Font(bold=True)
    curr_row += 1
    eq_start = curr_row
    curr_row = render_items(ws, eq_liab_items, curr_row, year_headers, "BS")
    eq_end = curr_row - 1
    
    existing_eq_total = None
    for item in eq_liab_items:
        item_lower = item.item.lower()
        if any(kw in item_lower for kw in ["total equity and liabilities", "total equity", "total liabilit", "sum of funds"]):
             existing_eq_total = item
             break

    if not existing_eq_total:
        total_eq_liab_row = curr_row
        ws.cell(row=total_eq_liab_row, column=1, value="Total Equity and Liabilities").font = Font(bold=True)
        for i in range(len(year_headers)):
            col = get_column_letter(i+2)
            val = f"=SUM({col}{eq_start}:{col}{eq_end})" if eq_end >= eq_start else "0"
            ws.cell(row=total_eq_liab_row, column=i+2, value=val).font = Font(bold=True)
            ws.cell(row=total_eq_liab_row, column=i+2).number_format = '#,##0'
        curr_row += 2
    else:
        total_eq_liab_row = eq_start
        for i, item in enumerate(eq_liab_items):
            if item == existing_eq_total:
                total_eq_liab_row = eq_start + i
                break
        curr_row += 1
    
    ws.cell(row=curr_row, column=1, value="Validation (Assets = Equity + Liab)").font = Font(bold=True, italic=True)
    for i in range(len(year_headers)):
        col = get_column_letter(i+2)
        ws.cell(row=curr_row, column=i+2, value=f"=IF(AND({col}{total_assets_row}>0, ABS({col}{total_assets_row}-{col}{total_eq_liab_row})<1), \"OK\", \"ERROR\")")
    
    ws.column_dimensions['A'].width = 50
    for i in range(len(year_headers)):
        ws.column_dimensions[get_column_letter(i+2)].width = 15

def is_pl_excluded(item_name: str) -> bool:
    item_lower = item_name.lower()
    pl_exclude = [
        "borrowings", "repayment", "proceeds", "net change", "distribution", 
        "vehicle financing", "non-controlling", "segment", "ratio", "number of times", "%", "coverage", 
        "cash flow", "exceptional", "refer", "forming part as",
        "profit before tax", "profit after tax", "total revenue", "total expenses", "total income"
    ]
    for k in pl_exclude:
        if k in ["%", "note", "ratio"]:
            if f" {k} " in f" {item_lower} " or item_lower == k:
                return True
        elif k in item_lower:
            return True
            
    if item_lower.startswith("note") or item_lower == "note":
        return True
    return False

def is_bs_excluded(item_name: str) -> bool:
    """
    CRITICAL FIX: Enhanced to properly exclude ALL Cash Flow items
    """
    item_lower = item_name.lower()
    
    cash_flow_keywords = [
        "cash flow", "net cash", "cash and cash equivalents",
        "opening balance", "closing balance", "opening balanc", "closing balanc",
        "proceeds from", "repayment of", "payment for", "payments for",
        "operating activities", "investing activities", "financing activities",
        "increase in cash", "decrease in cash", "net increase", "net decrease",
        "liability towards property", "liability towards", 
        "acquisition of", "disposal of", "sale of",
        "dividend paid", "dividend received", "interest paid", "interest received",
        "effect of foreign exchange", "effect of exchange",
        "realisation of", "realization of",
        "loan given", "loan taken", "investment in",
        "expenses paid on cancellation", "proceeds received",
        "payment towards", "distribution to"
    ]
    
    other_exclude = [
        "ratio", "number of times", "%", "coverage",
        "segment",
        "exceptional",
        "refer", "forming part of", "schedule", "annexure",
        "particulars", "year headed", "at 31 march", "at 31st march"
    ]
    
    if any(k in item_lower for k in cash_flow_keywords):
        return True
    
    if any(k in item_lower for k in other_exclude):
        return True
    
    if item_lower.startswith("note") or item_lower == "note":
        return True
    
    if re.match(r'^\d+\.', item_name):
        return True
        
    return False

def render_items(ws, items, curr_row, year_headers, mode="PL", force=False):
    rendered_count = 0
    for item in items:
        item_lower = item.item.lower()
            
        if not any(v.strip() for v in item.values if v):
            continue
            
        excluded = is_pl_excluded(item.item) if mode == "PL" else is_bs_excluded(item.item)
        if excluded:
            continue
            
        ws.cell(row=curr_row, column=1, value=("    " * item.indent) + item.item)
        row_values = (item.values[:len(year_headers)] + [''] * len(year_headers))[:len(year_headers)]
        
        item_lower = item.item.lower()
        for i, val in enumerate(row_values):
            num = parse_number(val)
            
            if num is not None and "deferred" in item_lower and "tax" in item_lower:
                raw_val = str(val)
                if "(" in raw_val and num > 0:
                    num = -num
                    print(f"DEBUG: Safety sign flip for '{item.item}': {raw_val} -> {num}")
            
            cell = ws.cell(row=curr_row, column=i+2, value=num if num is not None else val)
            if num is not None:
                cell.number_format = '#,##0'
        curr_row += 1
        rendered_count += 1
    return curr_row

def create_raw_data_sheet(wb, raw_rows, year_headers):
    ws = wb.create_sheet("Raw Data")
    
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(year_headers) + 3)
    title_cell = ws.cell(row=1, column=1, value="RAW DATA EXTRACTION LOG (Verification Only)")
    title_cell.font = Font(bold=True, size=12, color="800000")
    
    headers = ["Item"] + year_headers + ["Section", "Indent"]
    ws.append([]) # Spacer row
    ws.append(headers)
    
    header_row_idx = 3
    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=header_row_idx, column=col_idx)
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
    
    for r in raw_rows:
        vals = r.get('values', [])
        display_vals = (vals[:len(year_headers)] + [''] * len(year_headers))[:len(year_headers)]
        row_data = [r.get('item')] + display_vals + [str(r.get('section', '')), r.get('indent')]
        ws.append(row_data)
        
    ws.column_dimensions['A'].width = 60
    for i in range(len(year_headers)):
        ws.column_dimensions[get_column_letter(i+2)].width = 18
    
    ws.column_dimensions[get_column_letter(len(year_headers)+2)].width = 25 # Section
    ws.column_dimensions[get_column_letter(len(year_headers)+3)].width = 10 # Indent
