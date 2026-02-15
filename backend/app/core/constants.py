from app.models.financial_schema import FinancialSection

SECTION_KEYWORDS = {
    FinancialSection.REVENUE: [
        "revenue", "sales", "income from operations", "other income", "revenue from operations",
        "turnover", "income from sales", "operating income"
    ],
    FinancialSection.COST_OF_GOODS: [
        "cost of material", "cost of goods", "purchases", "inventory", "stock in trade",
        "change in inventory", "material consumed", "direct cost", "cost of services", "technical services"
    ],
    FinancialSection.OPERATING_EXPENSES: [
        "employee", "salary", "welfare", "power", "rent", "legal", "advertisement",
        "freight", "other expense", "consumption", "travel", "insurance", 
        "communication", "marketing", "promotion", "rates and taxes", "repair",
        "postage", "utility", "professional fee", "audit fee", "printing"
    ],
    FinancialSection.FINANCE_COST: [
        "finance cost", "interest expense", "bank charges", "borrowing cost"
    ],
    FinancialSection.DEPRECIATION: [
        "depreciation", "amortization", "depletion"
    ],
    FinancialSection.TAX: [
        "tax expense", "current tax", "deferred tax", "taxation", "provision for tax"
    ],
    FinancialSection.PROFIT: [
        "gross profit", "ebitda", "profit before tax", "profit after tax", "net profit",
        "margin", "operating profit", "pbt", "pat"
    ],
    FinancialSection.ASSETS: [
        "assets", "inventory", "receivables", "cash", "property", "plant", "equipment",
        "intangible", "investments", "loans", "advances", "bank balance", "receivable",
        "non-current assets", "current assets", "goodwill", "capital work-in-progress"
    ],
    FinancialSection.EQUITY: [
        "equity", "share capital", "reserves", "surplus", "retained earnings",
        "shareholders' funds", "capital"
    ],
    FinancialSection.LIABILITIES: [
        "liabilities", "borrowing", "payables", "provisions", "debt",
        "non-current liabilities", "current liabilities", "trade payables"
    ]
}

TOTAL_KEYWORDS = [
    "total",
    "sum",
    "aggregate"
]

CALCULATED_KEYWORDS = [
    "gross profit",
    "gross margin",
    "ebitda",
    "profit before tax",
    "profit after tax",
    "net profit",
    "margin"
]
