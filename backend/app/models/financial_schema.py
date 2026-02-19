from pydantic import BaseModel
from typing import List, Dict, Optional
from enum import Enum


class FinancialSection(str, Enum):
    REVENUE = "Revenue"
    COST_OF_GOODS = "Cost of Goods"
    OPERATING_EXPENSES = "Operating Expenses"
    FINANCE_COST = "Finance Cost"
    DEPRECIATION = "Depreciation"
    TAX = "Tax"
    PROFIT = "Profit"
    ASSETS = "Assets"
    EQUITY = "Equity"
    LIABILITIES = "Liabilities"
    OTHER = "Other"


class FinancialLineItem(BaseModel):
    item: str
    values: List[str]
    indent: int = 0
    section: FinancialSection = FinancialSection.OTHER
    is_total: bool = False
    is_calculated: bool = False


class FinancialStatement(BaseModel):
    year_headers: List[str]
    structured_data: Dict[str, List[FinancialLineItem]]
    raw_rows: List[Dict]