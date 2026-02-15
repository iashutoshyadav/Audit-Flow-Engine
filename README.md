# Financial Modeling Pipeline

A professional financial data extraction and modeling system that transforms PDF financial statements into structured Excel models with dynamic formulas.

## 🎯 What It Does

Converts PDF financial statements into professional Excel models with:
- ✅ **Hierarchical structure** (Revenue → Expenses → Profit)
- ✅ **Dynamic Excel formulas** (not static numbers)
- ✅ **Calculated metrics** (EBITDA, PBT, PAT, margins)
- ✅ **Professional formatting** (bold headers, indents, borders)

## 🚀 5-Step Pipeline

```
PDF → Extract → Classify → Build Model → Calculate → Fill Template → Excel
```

### Step 1: Extract
- Reads PDF using pdfplumber + OCR
- Extracts tables, line items, and values
- **Service**: `pdf_service.py`

### Step 2: Classify
- Categorizes rows into Revenue/Expenses/Profit
- Uses keyword matching for automatic classification
- **Service**: `structure_service.py`

### Step 3: Build Financial Model
- Groups rows by section
- Creates hierarchical structure
- **Service**: `structure_service.py`

### Step 4: Calculate Totals
- Computes EBITDA, PBT, PAT
- Generates Excel formulas
- Calculates margins
- **Service**: `calculation_service.py`

### Step 5: Fill Structured Template
- Creates professional Excel file
- Applies formatting (bold, indents, borders)
- Injects formulas into cells
- **Service**: `excel_service.py`

## 📁 Project Structure

```
backend/
├── app/
│   ├── api/
│   │   └── routes/
│   │       └── extract.py          # API endpoints
│   ├── core/
│   │   ├── config.py               # Configuration
│   │   └── constants.py            # Constants
│   ├── models/
│   │   └── financial_schema.py     # Data models & classification rules
│   ├── services/
│   │   ├── pdf_service.py          # PDF extraction (Step 1)
│   │   ├── structure_service.py    # Classification & hierarchy (Steps 2-3)
│   │   ├── calculation_service.py  # Calculations & formulas (Step 4)
│   │   ├── excel_service.py        # Excel generation (Step 5)
│   │   └── normalize_service.py    # Pipeline orchestrator
│   └── utils/
│       ├── validation_utils.py     # Data validation
│       ├── number_utils.py         # Number parsing
│       └── file_utils.py           # File operations
├── requirements.txt
└── main.py

frontend/
├── src/
│   ├── components/
│   │   ├── Upload.jsx              # Upload component with progress
│   │   └── ResultsTable.jsx        # Results display
│   ├── App.jsx                     # Main app
│   └── index.css                   # Styles
└── package.json
```

## 🔧 Installation

### Backend
```bash
cd backend
pip install -r requirements.txt
```

### Frontend
```bash
cd frontend
npm install
```

## ▶️ Running the Application

### Start Backend
```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

### Start Frontend
```bash
cd frontend
npm run dev
```

Open `http://localhost:3001` in your browser.

## 📊 Example Output

### Input (PDF):
```
Revenue from operations: 204,813
Other income: 1,212
Cost of materials: 82,937
```

### Output (Excel):
```
STATEMENT OF PROFIT AND LOSS

REVENUE
  Revenue from operations       204,813    189,456
  Other income                    1,212      1,089
  ──────────────────────────────────────────────
  Total Revenue                 =SUM(B4:B5)  ← Formula!

EXPENSES
  Cost of materials              82,937     76,234
  ──────────────────────────────────────────────
  Total Expenses                =SUM(B8:B8)  ← Formula!

EBITDA                          =B6-B10     ← Formula!
```

## 🎨 Key Features

### 1. Intelligent Classification
Automatically categorizes rows using keyword matching:
- "Revenue from operations" → REVENUE
- "Cost of materials" → EXPENSES
- "Profit before tax" → PROFIT (calculated)

### 2. Dynamic Formulas
Generates Excel formulas instead of copying static numbers:
```excel
Total Revenue: =SUM(B4:B5)
EBITDA: =B6-B12
PBT: =B14-B15-B16
PAT: =B17-B18
```

### 3. Professional Formatting
- Bold section headers
- Indented sub-items
- Right-aligned numbers with thousand separators
- Top borders for totals
- Percentage formatting for margins

### 4. Two-Sheet Output
- **Financial Statement**: Clean, formatted, with formulas
- **Raw Data**: Original extracted data for debugging

## 🧮 Calculations

The system computes standard financial metrics:

| Metric | Formula |
|--------|---------|
| **Total Revenue** | Sum of all revenue items |
| **Total Expenses** | Sum of all expense items |
| **Gross Profit** | Revenue - Cost of Goods |
| **EBITDA** | Revenue - Operating Expenses |
| **PBT** | EBITDA - Finance Cost - Depreciation |
| **PAT** | PBT - Tax Expense |
| **Gross Margin** | Gross Profit / Revenue |
| **Net Margin** | PAT / Revenue |

## 📝 Code Documentation

All core files include comprehensive comments:

- **financial_schema.py**: Data models and classification rules
- **normalize_service.py**: Pipeline orchestrator with detailed flow diagram
- **structure_service.py**: Row classification and hierarchy building
- **calculation_service.py**: Financial calculations and formula generation
- **excel_service.py**: Excel generation with formatting

## 🔍 Validation

The system validates:
- ✅ Data quality (non-numeric values, missing data)
- ✅ Calculation accuracy (extracted vs calculated totals)
- ✅ Formula correctness (proper cell references)

## 🛠️ Technologies Used

### Backend
- **FastAPI**: Web framework
- **pdfplumber**: PDF extraction
- **PyMuPDF (fitz)**: PDF processing
- **pytesseract**: OCR
- **openpyxl**: Excel generation
- **Pydantic**: Data validation

### Frontend
- **React**: UI framework
- **Vite**: Build tool
- **CSS**: Styling with animations

## 📄 License

This project is for financial data extraction and modeling purposes.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

For issues or questions, please open an issue in the repository.

---

**Built with ❤️ for professional financial modeling**
