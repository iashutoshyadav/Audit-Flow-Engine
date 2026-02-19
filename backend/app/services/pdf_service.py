import pdfplumber
import pytesseract
import os
import re
import hashlib
import json
import time
import logging
import statistics
from typing import List, Dict, Optional, Tuple, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Tesseract - Allow override via env var, fallback to hardcoded
TESSERACT_PATH = os.getenv("TESSERACT_PATH")
if TESSERACT_PATH and os.path.exists(TESSERACT_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
else:
    for _tp in [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        '/usr/bin/tesseract',
        '/usr/local/bin/tesseract',
    ]:
        if os.path.exists(_tp):
            pytesseract.pytesseract.tesseract_cmd = _tp
            break

# Poppler - Allow override via env var, fallback to hardcoded
POPPLER_PATH = os.getenv("POPPLER_PATH")
if not POPPLER_PATH or not os.path.exists(POPPLER_PATH):
    for _pp in [
        r"C:\Users\ashutosh yadav\Downloads\Release-25.12.0-0\poppler-25.12.0\Library\bin",
        r"C:\Program Files\poppler\Library\bin",
        '/usr/bin',
        '/usr/local/bin',
    ]:
        if os.path.exists(_pp) and any(
            f.startswith('pdftoppm') for f in (os.listdir(_pp) if os.path.isdir(_pp) else [])
        ):
            POPPLER_PATH = _pp
            break

if POPPLER_PATH:
    logger.info(f"Poppler: {POPPLER_PATH}")

CACHE_DIR = os.getenv("CACHE_DIR", "C:/tmp/pdf_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

OCR_DPI = 250
MAX_PAGES = 8

_MONTH_RE = re.compile(
    r'^(?:January|February|March|April|May|June|July|August|September|'
    r'October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)$',
    re.IGNORECASE
)
_QUARTER_RE = re.compile(r'^Q[1-4]$', re.IGNORECASE)
_YEAR_RE = re.compile(r'^20\d{2}$')
_FY_RE = re.compile(r'^(?:FY|F\.Y\.?)\s*(?:20)?\d{2}(?:[-/]\d{2,4})?$', re.IGNORECASE)
_FY_SLASH_RE = re.compile(r'^20\d{2}[-/]\d{2,4}$')
_DAY_RE = re.compile(r'^(?:3[01]|[12]\d|0?[1-9]),?$')
_NOTE_RE = re.compile(r'^\d+\.\d+$')

_HDR_UNIT_RE = re.compile(r'\s*[\(\[].*?(?:cr|crore|lakh|million|usd|inr|₹|■|n)\w*.*?[\)\]].*$', re.IGNORECASE)

_DATE_RE = re.compile(
    r'(?:January|February|March|April|May|June|July|August|September|October'
    r'|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec'
    r'|Q[1-4]\s*(?:FY)?\s*\d{2,4}|H[12]\s*(?:FY)?\s*\d{2,4}|FY\s*\d{2,4}'
    r'|20\d{2}[-/]\d{2}|20\d{2})',
    re.IGNORECASE
)

_UNIT_PATTERNS = [
    (re.compile(r'₹\s*in\s*crore', re.IGNORECASE), "₹ in Crores"),
    (re.compile(r'rs\.?\s*in\s*crore', re.IGNORECASE), "₹ in Crores"),
    (re.compile(r'rupees?\s*in\s*crore', re.IGNORECASE), "₹ in Crores"),
    (re.compile(r'\bcrore', re.IGNORECASE), "₹ in Crores"),
    (re.compile(r'₹\s*in\s*lakh', re.IGNORECASE), "₹ in Lakhs"),
    (re.compile(r'\blakhs?\b', re.IGNORECASE), "₹ in Lakhs"),
    (re.compile(r'usd\s*(?:in\s*)?million', re.IGNORECASE), "USD in Millions"),
    (re.compile(r'\$\s*million', re.IGNORECASE), "USD in Millions"),
    (re.compile(r'gbp\s*(?:in\s*)?million', re.IGNORECASE), "GBP in Millions"),
    (re.compile(r'eur\s*(?:in\s*)?million', re.IGNORECASE), "EUR in Millions"),
    (re.compile(r'₹',), "₹ in Crores"),
]

_SECTION_KW = [
    'revenue from operations', 'other income', 'total income', 'total revenue',
    'expenses', 'cost of material', 'employee benefit', 'finance cost',
    'depreciation', 'other expenses', 'tax expense', 'other comprehensive',
    'profit and loss', 'balance sheet', 'assets', 'liabilities', 'equity',
    'cash flow', 'shareholders', 'discontinued', 'capital and reserves',
    'earnings per share', 'net premium', 'gross premium', 'claims', 'underwriting',
    'operating activities', 'investing activities', 'financing activities',
    'non-current assets', 'current assets', 'non-current liabilities',
    'current liabilities',
]

_TOTAL_KW = [
    'total', 'gross profit', 'ebitda', 'profit before', 'profit after',
    'profit for', 'net profit', 'earnings after', 'pat', 'pbt',
    'profit/(loss)', 'loss for', 'total comprehensive', 'net income',
    'total income', 'total revenue', 'total expenses', 'net claims',
    'net premium earned', 'surplus', 'deficit',
]

_NOISE_PATTERNS = [
    r'^\d+\)\s',
    r'^note\s*\d',
    r'as per the actuarial',
    r'scheme of arrangement',
    r'pursuant to the nclt',
    r'the excess of consideration',
    r'has been accounted',
    r'discontinued operation.*separately',
    r'difference of.*securities premium',
    r'ordinary shares.*yet to be transferred',
    r'working capital.*current assets.*excluding',
    r'trade and other receivables includes',
    r'raw material consumed includes',
    r'\(ii\) equity = equity attributable',
    r'net worth as defined',
    r'^\s*(?:page|pg)[\s\.\:]\s*\d+',
    r'^\s*cin\s*[\:\-]',
    r'^\s*(?:www\.|http)',
    r'^\s*regd\.\s*office',
    r'^\s*telephone',
    r'^\s*email',
    r'^\s*[\|\!\[\]_]{2,}',
    r'\|\s*[a-zA-Z]\s*\|',
    r'^\|\s*[a-zA-Z]\s*\|',
    r'^[ivxlVIXL\s\|_]{3,}$',
    r'regd\.?\s*office',
    r'bombay\s*house',
    r'homi\s*mody',
    r'cin\s*[lL]\d',
    r'not\s+annualised',
    r'refer\s+note\s+\d',
    r'^\s*\*\s*re-?presented',
    r'face\s+value\s+of\s+₹',
    r'audited\s*\[refer',
    r'unaudited',
    r'^on\s+november\s+\d',
    r'^the\s+(?:board|parties|company|statutory|nclt)',
    r'^further,\s+the',
    r'^\d{3},\d{3}\s+new\s+ordinary',
    r'shareholders\.',
    r'pension\s+fund',
    r'epfo',
    r'hon\'ble\s+supreme\s+court',
    r'^\[equity\s+share\s+capital',
    r'^\[current\s+(?:assets|liabilities)',
    r'accrued\s+on\s+borrowings',
    r'tive\s+debts\s+to\s+total',
    r'turnover\s+\(number\s+of\s+times\)',
    r'inventories.*gains.*loss',
    r'incentives\)\)',
    r'^\[profit\s+for',
    r'assets\s+under\s+development',
    r'acquisition.*demerger',
    r'normal\s+pension\s+valuation',
    r'members.*data.*epfo',
    r'overrides\s+the\s+requirement',
    r'comparative\s+consolidated\s+results',
    r'segment\s+(?:assets|liabilities|results|revenue)',
    r'net\s+segment',
    r'unallocable\s+(?:assets|liabilities)',
    r'commercial\s+vehicle',
    r'jaguar\s+and\s+land\s+rover',
    r'intra\s+segment',
    r'inter\s+segment',
    r'debt\s+equity\s+ratio',
    r'vehicle\s+financing',
    r'corporate/unallocable',
]
_NOISE_RE = [re.compile(p, re.IGNORECASE) for p in _NOISE_PATTERNS]

_SKIP_COL_HEADERS = {
    'note no', 'note no.', 'note', 'notes', 'sr no', 'sr. no', 'sl no',
    'sl. no', 'no.', 's.no', 'ref', 'reference', 'particulars', 'description'
}

_HDR_NOISE = {
    'particulars', 'sl', 'sr', 'no', 'no.', 'sr.', 'sl.',
    's.no', 'description', 'items', 'note no.', 'note no', 'note'
}

def _hash(pdf_path: str) -> Optional[str]:
    h = hashlib.md5()
    try:
        with open(pdf_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        logger.error(f"Hash error: {e}")
        return None

def _load_cache(fhash: Optional[str]) -> Optional[dict]:
    if not fhash:
        return None
    p = os.path.join(CACHE_DIR, f"{fhash}.json")
    if os.path.exists(p):
        try:
            with open(p) as f:
                logger.info("Cache hit")
                return json.load(f)
        except Exception:
            pass
    return None

def _write_cache(fhash: Optional[str], data: dict) -> None:
    if not fhash:
        return
    p = os.path.join(CACHE_DIR, f"{fhash}.json")
    try:
        with open(p, "w") as f:
            json.dump(data, f)
    except Exception as e:
        logger.error(f"Cache write: {e}")

def _is_num(text: str) -> bool:
    s = str(text).replace(',', '').replace(' ', '').strip()
    if s.startswith('(') and s.endswith(')'):
        s = s[1:-1]
    if not s:
        return False
    try:
        v = float(s)
        if _NOTE_RE.match(s) and abs(v) < 20:
            return False
        return True
    except ValueError:
        return False

def _to_num(text: str) -> Optional[float]:
    s = str(text).replace(',', '').strip()
    if s.startswith('(') and s.endswith(')'):
        try:
            return -abs(float(s[1:-1]))
        except ValueError:
            return None
    try:
        v = float(s)
        if _NOTE_RE.match(s) and abs(v) < 20:
            return None
        return v
    except ValueError:
        return None


def _is_noise_line(label: str) -> bool:
    if not label or len(label) < 3:
        return True
    lower = label.lower().strip()
    if re.match(r'^[\d\s\.\-\(\)\|,₹\*]+$', lower):
        return True
    if len(label) > 280:
        return True
    pipe_count = label.count('|') + label.count('_')
    if pipe_count > 1:
        return True
    for rx in _NOISE_RE:
        if rx.search(lower):
            return True
    return False


def _is_section(text: str) -> bool:
    lower = text.lower()
    return any(k in lower for k in _SECTION_KW)


def _section_type(text: str) -> str:
    lower = text.lower()
    if any(k in lower for k in ['revenue', 'income', 'sales', 'premium earned']):
        return 'REVENUE'
    if any(k in lower for k in ['expense', 'cost', 'depreciation', 'finance cost', 'claims']):
        return 'EXPENSE'
    if any(k in lower for k in ['profit', 'loss', 'ebitda', 'pat', 'pbt', 'earnings', 'surplus']):
        return 'PROFIT'
    if 'tax' in lower:
        return 'TAX'
    if any(k in lower for k in ['asset', 'liabilit', 'equity', 'balance', 'capital']):
        return 'BALANCE'
    if 'cash' in lower or 'activit' in lower:
        return 'CASHFLOW'
    return 'OTHER'


def _detect_indent(label: str) -> int:
    raw = str(label)
    sp = len(raw) - len(raw.lstrip())
    if sp > 10:
        return 2
    if sp > 3:
        return 1
    stripped = raw.strip()
    if stripped and stripped[0].islower():
        return 1
    return 0


def _detect_unit_from_text(text: str) -> Optional[str]:
    for pat, label in _UNIT_PATTERNS:
        if pat.search(text):
            return label
    return None


def _clean_cell(val) -> str:
    if val is None:
        return ""
    s = re.sub(r'\s+', ' ', str(val).replace('\n', ' ')).strip()
    return "" if s in {'-', '–', '—', '_', '...', 'NA', 'N.A.'} else s


def _to_float_str(raw: str) -> str:
    s = _clean_cell(raw).replace(',', '').strip()
    s = re.sub(r'^[₹$£€\s]+', '', s).strip()
    if s.startswith('(') and s.endswith(')'):
        s = '-' + s[1:-1]
    if _NOTE_RE.match(s):
        try:
            if abs(float(s)) < 20:
                return ""
        except ValueError:
            pass
    try:
        return str(float(s))
    except ValueError:
        return ""


def _clean_header(raw: str) -> str:
    h = _clean_cell(raw)
    if not h:
        return ""
    h = _HDR_UNIT_RE.sub('', h).strip()
    h = re.sub(r'[■\*†‡]', '', h).strip()
    h = re.sub(r'\s+', ' ', h).strip()
    return h


def _is_note_col(header: str) -> bool:
    return _clean_cell(header).lower().strip() in _SKIP_COL_HEADERS


def _parse_text_headers(raw_row: List, skip_note_cols: bool = True) -> Tuple[List[str], List[int]]:
    hdrs = []
    valid_indices = []
    for i, cell in enumerate(raw_row[1:], start=1):
        text = _clean_cell(cell)
        if not text:
            continue
        lower = text.lower().strip()
        if lower in _HDR_NOISE:
            continue
        if skip_note_cols and _is_note_col(text):
            continue
        cleaned = _clean_header(text)
        if cleaned:
            hdrs.append(cleaned)
            valid_indices.append(i)
    return hdrs, valid_indices


def _extract_words_as_table(page) -> List[List[Optional[str]]]:
    try:
        words = page.extract_words()
        if not words:
            return []
        from collections import defaultdict
        y_groups: Dict[int, List] = defaultdict(list)
        for w in words:
            y_band = round(w['top'] / 5) * 5
            y_groups[y_band].append(w)
        rows = []
        for y in sorted(y_groups):
            words_in_row = sorted(y_groups[y], key=lambda w: w['x0'])
            row = [' '.join(w['text'] for w in words_in_row)]
            rows.append(row)
        return rows
    except Exception:
        return []


def _text_extract(pdf_path: str) -> dict:
    result: dict = {"year_headers": [], "rows": [], "unit_label": ""}
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total = len(pdf.pages)
            pages = min(total, MAX_PAGES)
            logger.info(f"Text extraction: {pages}/{total} pages")

            found_hdrs: List[str] = []
            valid_cols: List[int] = []
            all_rows: List[dict] = []
            current_section = "OTHER"
            unit_label = ""

            full_text = ""
            for pg_num in range(pages):
                full_text += (pdf.pages[pg_num].extract_text() or "") + "\n"
            detected_unit = _detect_unit_from_text(full_text)
            if detected_unit:
                unit_label = detected_unit
                logger.info(f"Unit detected: {unit_label}")

            extraction_settings = [
                {"vertical_strategy": "lines", "horizontal_strategy": "lines"},
                {"vertical_strategy": "text", "horizontal_strategy": "text"},
            ]

            for pg_num in range(pages):
                page = pdf.pages[pg_num]
                tables = None

                for settings in extraction_settings:
                    try:
                        tables = page.extract_tables(settings)
                        if tables and any(len(t) > 3 for t in tables):
                            break
                    except Exception:
                        continue

                if not tables:
                    text_rows = _extract_words_as_table(page)
                    if text_rows:
                        tables = [text_rows]

                if not tables:
                    continue

                for tbl in tables:
                    if not tbl or len(tbl) < 2:
                        continue

                    hdr_ti = -1
                    for ti, trow in enumerate(tbl[:8]):
                        if not trow:
                            continue
                        row_text = ' '.join(str(c) for c in trow if c)
                        if _DATE_RE.search(row_text) or 'Particulars' in row_text:
                            hdr_ti = ti
                            break

                    if hdr_ti == -1:
                        for ti, trow in enumerate(tbl[:5]):
                            non_empty = [c for c in trow if c and str(c).strip()]
                            if len(non_empty) >= 3:
                                hdr_ti = ti
                                break

                    if hdr_ti == -1:
                        continue

                    new_hdrs, new_valid = _parse_text_headers(tbl[hdr_ti])
                    if new_hdrs and len(new_hdrs) > len(found_hdrs):
                        found_hdrs = new_hdrs
                        valid_cols = new_valid

                    if not valid_cols:
                        valid_cols = list(range(1, len(tbl[hdr_ti])))

                    num_h = len(found_hdrs) if found_hdrs else 5

                    for trow in tbl[hdr_ti + 1:]:
                        if not trow or len(trow) < 2:
                            continue
                        item = _clean_cell(trow[0])
                        if not item or len(item) < 2:
                            continue
                        if item.lower() in _HDR_NOISE:
                            continue
                        if _is_noise_line(item):
                            continue

                        if _is_section(item):
                            current_section = _section_type(item)

                        vals = []
                        for ci in valid_cols:
                            if len(vals) >= num_h:
                                break
                            cell_val = trow[ci] if ci < len(trow) else None
                            vals.append(_to_float_str(_clean_cell(str(cell_val) if cell_val else "")))
                        while len(vals) < num_h:
                            vals.append("")

                        has_values = any(v for v in vals)
                        all_rows.append({
                            "item": item,
                            "values": vals[:num_h],
                            "indent": _detect_indent(item),
                            "section": current_section,
                            "is_section_header": not has_values and _is_section(item),
                        })

            result["year_headers"] = found_hdrs[:8]
            result["rows"] = all_rows
            result["unit_label"] = unit_label
            logger.info(f"Text extracted {len(all_rows)} rows, headers={found_hdrs}, unit={unit_label}")

    except Exception as e:
        logger.error(f"Text extract failed: {e}")
        import traceback; traceback.print_exc()

    return result


def _get_anchor_type(words_df) -> str:
    texts = words_df['text'].str.strip()
    if texts.str.match(_MONTH_RE.pattern, case=False, na=False).sum() >= 2:
        return 'month'
    if texts.str.match(_QUARTER_RE.pattern, na=False).sum() >= 2:
        return 'quarter'
    fy_count = texts.str.match(_FY_RE.pattern, case=False, na=False).sum()
    fy_slash = texts.str.match(_FY_SLASH_RE.pattern, na=False).sum()
    if fy_count + fy_slash >= 2:
        return 'fy'
    if (texts.str.match(_YEAR_RE.pattern, na=False) & (words_df['cx'] > words_df['cx'].max() * 0.35)).sum() >= 2:
        return 'year'
    return 'generic'


def _detect_col_centers(words_df, img_width: int) -> List[int]:
    anchor_type = _get_anchor_type(words_df)
    logger.info(f"OCR anchor type: {anchor_type}")
    texts = words_df['text'].str.strip()

    if anchor_type == 'month':
        mask = texts.str.match(_MONTH_RE.pattern, case=False, na=False)
    elif anchor_type == 'quarter':
        mask = texts.str.match(_QUARTER_RE.pattern, na=False)
    elif anchor_type == 'fy':
        mask = texts.str.match(_FY_RE.pattern, case=False, na=False) | texts.str.match(_FY_SLASH_RE.pattern, na=False)
    elif anchor_type == 'year':
        mask = texts.str.match(_YEAR_RE.pattern, na=False) & (words_df['cx'] > img_width * 0.35)
    else:
        mask = texts.apply(_is_num) & (words_df['cx'] > img_width * 0.30)

    anchor_words = words_df[mask].copy()
    if anchor_words.empty:
        mask = texts.apply(_is_num) & (words_df['cx'] > img_width * 0.30)
        anchor_words = words_df[mask].copy()
    if anchor_words.empty:
        return []

    if anchor_type in ('month', 'quarter', 'fy', 'year'):
        anchor_words['row_band'] = (anchor_words['top'] // 30) * 30
        row_counts = anchor_words.groupby('row_band').size()
        best_band = row_counts.idxmax()
        anchors_for_clustering = anchor_words[
            (anchor_words['top'] >= best_band - 20) &
            (anchor_words['top'] <= best_band + 60)
        ]
    else:
        anchors_for_clustering = anchor_words

    cx_vals = sorted(anchors_for_clustering['cx'].tolist())
    if len(cx_vals) < 2:
        return [cx_vals[0]] if cx_vals and cx_vals[0] > img_width * 0.3 else []

    gaps = [cx_vals[i+1] - cx_vals[i] for i in range(len(cx_vals) - 1)]
    median_gap = statistics.median(gaps)
    cluster_gap = max(int(median_gap * 0.6), 55) if anchor_type != 'generic' else max(int(median_gap * 0.4), 40)

    clusters: List[List[int]] = []
    current: List[int] = [cx_vals[0]]
    for cx in cx_vals[1:]:
        if cx - current[-1] > cluster_gap:
            clusters.append(current)
            current = [cx]
        else:
            current.append(cx)
    clusters.append(current)

    centres = [int(sum(c) / len(c)) for c in clusters]
    cols = sorted([c for c in centres if c > img_width * 0.28])
    logger.info(f"OCR col centers: {cols}")
    return cols[:8]


def _build_ocr_headers(words_df, col_centers: List[int], plain_lines: List[str], img_width: int) -> List[str]:
    if not col_centers:
        return []
    anchor_type = _get_anchor_type(words_df)
    texts = words_df['text'].str.strip()

    if anchor_type == 'month':
        mask = texts.str.match(_MONTH_RE.pattern, case=False, na=False)
    elif anchor_type == 'quarter':
        mask = texts.str.match(_QUARTER_RE.pattern, na=False)
    elif anchor_type == 'fy':
        mask = texts.str.match(_FY_RE.pattern, case=False, na=False) | texts.str.match(_FY_SLASH_RE.pattern, na=False)
    elif anchor_type == 'year':
        mask = texts.str.match(_YEAR_RE.pattern, na=False) & (words_df['cx'] > img_width * 0.35)
    else:
        mask = texts.apply(_is_num) & (words_df['cx'] > img_width * 0.30)

    anchor_found = words_df[mask]
    month_row_top = int(anchor_found['top'].median()) if not anchor_found.empty else int(words_df['top'].max() * 0.08)

    band_top = max(0, month_row_top - 50)
    band_bottom = month_row_top + 160
    header_band = words_df[(words_df['top'] >= band_top) & (words_df['top'] <= band_bottom)]
    wide_band = words_df[(words_df['top'] >= max(0, month_row_top - 200)) & (words_df['top'] <= band_bottom)]

    if len(col_centers) > 1:
        inter_col = statistics.median([col_centers[i+1] - col_centers[i] for i in range(len(col_centers) - 1)])
        col_tol = max(int(inter_col * 0.55), 60)
    else:
        col_tol = 160

    headers = []
    for ci, cx in enumerate(col_centers):
        near = header_band[abs(header_band['cx'] - cx) <= col_tol].sort_values('top')
        near_wide = wide_band[abs(wide_band['cx'] - cx) <= col_tol].sort_values('top')
        month = day = year = quarter = fy_label = None

        for _, w in near.iterrows():
            t = str(w['text']).strip()
            if _MONTH_RE.match(t): month = t[:3].capitalize()
            elif _DAY_RE.match(t): day = re.sub(r',', '', t).zfill(2)
            elif _YEAR_RE.match(t): year = t
            elif _QUARTER_RE.match(t): quarter = t.upper()
            elif _FY_RE.match(t) or _FY_SLASH_RE.match(t): fy_label = t

        if year is None:
            for _, w in near_wide.iterrows():
                t = str(w['text']).strip()
                if _YEAR_RE.match(t):
                    year = t; break

        if fy_label: headers.append(fy_label)
        elif quarter and year: headers.append(f"{quarter} {year}")
        elif quarter: headers.append(quarter)
        elif month and year: headers.append(f"{month} {day+', ' if day else ''}{year}")
        elif month: headers.append(f"{month} {day+', ' if day else ''}".rstrip())
        elif year: headers.append(year)
        else: headers.append(f"Col {ci + 1}")

    if anchor_type in ('month', 'quarter') and any(not re.search(r'20\d{2}', h) for h in headers):
        headers = _infer_years_sebi(headers, words_df, col_centers, plain_lines, img_width)

    logger.info(f"OCR headers: {headers}")
    return headers


def _infer_years_sebi(headers, words_df, col_centers, plain_lines, img_width) -> List[str]:
    reporting_year: Optional[int] = None
    year_words = words_df[words_df['text'].str.match(_YEAR_RE.pattern, na=False) & (words_df['cx'] > img_width * 0.35)]
    if not year_words.empty:
        reporting_year = int(year_words.iloc[0]['text'])
    if reporting_year is None:
        for line in plain_lines[:20]:
            m = re.search(r'20\d{2}', line)
            if m: reporting_year = int(m.group()); break
    if reporting_year is None:
        for h in headers:
            m = re.search(r'20\d{2}', h)
            if m: reporting_year = int(m.group()); break
    if reporting_year is None:
        return headers

    n = len(col_centers)
    quarterly_count = {2: 1, 3: 2, 4: 2, 5: 3, 6: 3, 7: 4, 8: 4}.get(n, max(1, n // 2))
    annual_start_idx = quarterly_count
    month_occ: Dict[str, int] = {}
    ann_month_occ: Dict[str, int] = {}

    for i, h in enumerate(headers):
        if re.search(r'20\d{2}', h):
            continue
        m3 = h[:3].lower()
        is_annual = i >= annual_start_idx
        if is_annual:
            ann_month_occ.setdefault(m3, 0)
            occ = ann_month_occ[m3]; ann_month_occ[m3] += 1
            yr = reporting_year if occ == 0 else reporting_year - 1
        else:
            month_occ.setdefault(m3, 0)
            occ = month_occ[m3]; month_occ[m3] += 1
            yr = reporting_year - 1 if m3 == 'dec' else (reporting_year if occ == 0 else reporting_year - 1)
        headers[i] = f"{h.strip()} {yr}".strip()
    return headers


def _extract_page(img, plain_lines: List[str]) -> Tuple[List[str], List[dict]]:
    raw = pytesseract.image_to_data(img, output_type=pytesseract.Output.DATAFRAME)
    df = raw[raw['conf'] > 20].dropna(subset=['text']).copy()
    df = df[df['text'].str.strip() != ''].copy()
    df['cx'] = df['left'] + df['width'] // 2

    img_width = img.width
    col_centers = _detect_col_centers(df, img_width)
    if len(col_centers) < 1:
        logger.warning("No columns detected, skipping page")
        return [], []

    if len(col_centers) > 1:
        spacings = [col_centers[i+1] - col_centers[i] for i in range(len(col_centers) - 1)]
        col_tol = max(int(statistics.median(spacings) * 0.42), 50)
    else:
        col_tol = 120

    logger.info(f"col_centers={col_centers}, col_tol={col_tol}")

    def assign_col(cx: int) -> int:
        dists = [abs(cx - c) for c in col_centers]
        mn = min(dists)
        return dists.index(mn) if mn <= col_tol else -1

    year_headers = _build_ocr_headers(df, col_centers, plain_lines, img_width)
    N = len(col_centers)

    df_sorted = df.sort_values('top')
    row_groups: List[List] = []
    cur_top = None
    cur_grp: List = []

    for _, w in df_sorted.iterrows():
        if cur_top is None or abs(w['top'] - cur_top) > 22:
            if cur_grp:
                row_groups.append(cur_grp)
            cur_grp = [w]
            cur_top = w['top']
        else:
            cur_grp.append(w)
    if cur_grp:
        row_groups.append(cur_grp)

    rows: List[dict] = []
    current_section = "OTHER"
    header_found = False

    for grp in row_groups:
        label_parts: List[Tuple[int, str]] = []
        cols: Dict[int, List[float]] = {i: [] for i in range(N)}

        for w in grp:
            txt = str(w['text']).strip()
            col = assign_col(int(w['cx']))
            if col == -1:
                if int(w['cx']) < col_centers[0] - col_tol:
                    label_parts.append((int(w['left']), txt))
            elif _is_num(txt):
                v = _to_num(txt)
                if v is not None:
                    cols[col].append(v)

        label_parts.sort(key=lambda x: x[0])
        label = re.sub(r'\s+', ' ', ' '.join(t for _, t in label_parts)).strip()

        if not header_found:
            if _DATE_RE.search(label) or 'Particulars' in label or 'Description' in label:
                header_found = True
            elif any(_MONTH_RE.match(w2) for w2 in label.split()):
                header_found = True
            continue

        if not label or len(label) < 2:
            continue
        if _is_noise_line(label):
            continue
        if re.match(r'^[\d\s\.\-\(\)\|,₹]+$', label):
            continue

        has_values = any(bool(cols[i]) for i in range(N))
        if _is_section(label):
            current_section = _section_type(label)

        str_values = [str(cols[i][-1]) if cols[i] else "" for i in range(N)]
        is_sec_hdr = not has_values and _is_section(label)

        if has_values or is_sec_hdr:
            rows.append({
                "item": label,
                "values": str_values,
                "indent": _detect_indent(label),
                "section": current_section,
                "is_section_header": is_sec_hdr,
            })

    return year_headers, rows


def _ocr_extract(pdf_path: str) -> dict:
    result: dict = {"year_headers": [], "rows": [], "unit_label": ""}
    try:
        import pdf2image

        try:
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
        except Exception:
            total_pages = MAX_PAGES

        pages_to_do = min(total_pages, MAX_PAGES)
        images = pdf2image.convert_from_path(
            pdf_path, dpi=OCR_DPI, first_page=1, last_page=pages_to_do,
            poppler_path=POPPLER_PATH,
        )

        plain_lines: List[str] = []
        full_text = ""
        for img in images:
            t = pytesseract.image_to_string(img)
            plain_lines.extend(t.split('\n'))
            full_text += t + "\n"

        unit_label = _detect_unit_from_text(full_text) or ""

        found_headers: List[str] = []
        all_rows: List[dict] = []

        for pg_i, img in enumerate(images):
            logger.info(f"OCR page {pg_i + 1}/{len(images)}")
            try:
                pg_hdrs, pg_rows = _extract_page(img, plain_lines)
                if len(pg_hdrs) > len(found_headers):
                    found_headers = pg_hdrs
                all_rows.extend(pg_rows)
            except Exception as e:
                logger.error(f"Page {pg_i+1} error: {e}")
                import traceback; traceback.print_exc()

        result["year_headers"] = found_headers
        result["rows"] = all_rows
        result["unit_label"] = unit_label

    except Exception as e:
        logger.error(f"OCR failed: {e}")
        import traceback; traceback.print_exc()

    return result


def extract_table_structure(pdf_path: str) -> dict:
    t0 = time.time()
    fhash = _hash(pdf_path)
    cached = _load_cache(fhash)
    if cached:
        return cached

    has_text = False
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for pg in pdf.pages[:3]:
                txt = pg.extract_text() or ""
                if len(txt.strip()) > 150:
                    has_text = True
                    break
    except Exception:
        pass

    if has_text:
        logger.info("Text-layer PDF → pdfplumber")
        result = _text_extract(pdf_path)
        if len(result.get("rows", [])) < 5:
            logger.warning("Text weak → OCR fallback")
            result = _ocr_extract(pdf_path)
    else:
        logger.info("Image PDF → OCR")
        result = _ocr_extract(pdf_path)

    if not result.get("year_headers"):
        result["year_headers"] = ["Period 1", "Period 2", "Period 3", "Period 4", "Period 5"]

    seen: set = set()
    clean: List[dict] = []
    for row in result.get("rows", []):
        key = row["item"].strip().lower()
        if key not in seen and key:
            seen.add(key)
            clean.append(row)
    result["rows"] = clean

    elapsed = time.time() - t0
    if result["rows"]:
        _write_cache(fhash, result)
        logger.info(f"✅ {len(result['rows'])} rows in {elapsed:.1f}s")
    else:
        result["error"] = "Could not extract financial data from this PDF"
        logger.error("❌ No data extracted")

    return result


def extract_lines(pdf_path: str) -> List[str]:
    data = extract_table_structure(pdf_path)
    return [f"{r['item']} {' '.join(str(v) for v in r['values'])}" for r in data.get("rows", [])]


def extract_lines_gen(pdf_path: str):
    data = extract_table_structure(pdf_path)
    for r in data.get("rows", []):
        yield f"{r['item']} {' '.join(str(v) for v in r['values'])}"