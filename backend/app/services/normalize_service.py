from typing import List, Dict
from app.models.financial_schema import (
    FinancialSection,
    FinancialLineItem
)
from app.core.constants import (
    SECTION_KEYWORDS,
    TOTAL_KEYWORDS,
    CALCULATED_KEYWORDS
)
from app.utils.validation_utils import clean_item_name

BS_CONTEXT_MARKERS = [
    "balance sheet", "assets and liabilities", "total assets",
    "equity and liabilities", "non-current assets", "current assets",
    "non-current liabilities", "current liabilities",
    "equity share capital", "total equity"
]

PL_CONTEXT_MARKERS = [
    "revenue from operations", "profit and loss", "income statement",
    "total income", "total expenses", "profit before tax"
]


def classify_row(item_name: str, context: str = "PL") -> FinancialSection:
    item_lower = item_name.lower()

    bs_priority = [
        FinancialSection.ASSETS,
        FinancialSection.EQUITY,
        FinancialSection.LIABILITIES
    ]
    pl_priority = [
        FinancialSection.TAX,
        FinancialSection.REVENUE,
        FinancialSection.COST_OF_GOODS,
        FinancialSection.OPERATING_EXPENSES,
        FinancialSection.FINANCE_COST,
        FinancialSection.DEPRECIATION
    ]

    priority = bs_priority if context == "BS" else pl_priority

    for section in priority:
        for keyword in SECTION_KEYWORDS.get(section, []):
            if keyword in item_lower:
                return section

    remaining = [s for s in FinancialSection if s not in priority]
    for section in remaining:
        for keyword in SECTION_KEYWORDS.get(section, []):
            if keyword in item_lower:
                return section

    return FinancialSection.OTHER


def classify_rows(raw_rows: List[Dict]) -> List[FinancialLineItem]:
    classified = []
    current_context = "PL"

    for row in raw_rows:
        name = clean_item_name(row.get("item", ""))
        if not name:
            continue

        name_lower = name.lower()
        if any(m in name_lower for m in BS_CONTEXT_MARKERS):
            current_context = "BS"
        elif any(m in name_lower for m in PL_CONTEXT_MARKERS):
            current_context = "PL"

        section = classify_row(name, context=current_context)
        is_total = any(k in name_lower for k in TOTAL_KEYWORDS)
        is_calculated = any(k in name_lower for k in CALCULATED_KEYWORDS)

        # ── FIX: convert None → "" so Pydantic List[str] validation passes ──
        safe_values = [
            str(v) if v is not None else ""
            for v in row.get("values", [])
        ]

        classified.append(
            FinancialLineItem(
                item=name,
                values=safe_values,
                indent=row.get("indent", 0),
                section=section,
                is_total=is_total,
                is_calculated=is_calculated
            )
        )

    return classified


def build_hierarchy(classified_rows: List[FinancialLineItem]) -> Dict[str, List[FinancialLineItem]]:
    hierarchy: Dict[str, List[FinancialLineItem]] = {
        section.value: [] for section in FinancialSection
    }
    for item in classified_rows:
        hierarchy[item.section.value].append(item)
    return hierarchy


def sort_profit_and_loss(hierarchy: Dict) -> Dict:
    order = [
        FinancialSection.REVENUE.value,
        FinancialSection.COST_OF_GOODS.value,
        FinancialSection.OPERATING_EXPENSES.value,
        FinancialSection.FINANCE_COST.value,
        FinancialSection.DEPRECIATION.value,
        FinancialSection.PROFIT.value
    ]
    return {k: hierarchy[k] for k in order if hierarchy.get(k)}


def extract_income_statement(table_data: dict) -> dict:
    if not table_data or "rows" not in table_data:
        return {"year_headers": [], "structured_data": {}, "raw_rows": []}

    raw_rows = table_data["rows"]
    year_headers = table_data.get("year_headers", [])

    if not raw_rows:
        return {"year_headers": year_headers, "structured_data": {}, "raw_rows": []}

    classified = classify_rows(raw_rows)
    hierarchy = build_hierarchy(classified)

    return {
        "year_headers": year_headers,
        "raw_rows": raw_rows,
        "structured_data": hierarchy
    }