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


def classify_row(item_name: str, context: str = "PL") -> FinancialSection:
    item_lower = item_name.lower()
    
    bs_priority = [FinancialSection.ASSETS, FinancialSection.EQUITY, FinancialSection.LIABILITIES]
    pl_priority = [FinancialSection.TAX, FinancialSection.REVENUE, FinancialSection.COST_OF_GOODS, 
                   FinancialSection.OPERATING_EXPENSES, FinancialSection.FINANCE_COST, 
                   FinancialSection.DEPRECIATION]

    priority = bs_priority if context == "BS" else pl_priority
    
    for section in priority:
        keywords = SECTION_KEYWORDS.get(section, [])
        for keyword in keywords:
            if keyword in item_lower:
                return section
                
    remaining = [s for s in FinancialSection if s not in priority]
    for section in remaining:
        keywords = SECTION_KEYWORDS.get(section, [])
        for keyword in keywords:
            if keyword in item_lower:
                return section
                
    return FinancialSection.OTHER


def classify_rows(raw_rows: List[Dict]) -> List[FinancialLineItem]:
    classified = []

    for row in raw_rows:
        name = clean_item_name(row.get("item", ""))
        if not name:
            continue

        section = classify_row(name)
        is_total = any(k in name.lower() for k in TOTAL_KEYWORDS)
        is_calculated = any(k in name.lower() for k in CALCULATED_KEYWORDS)

        classified.append(
            FinancialLineItem(
                item=name,
                values=row.get("values", []),
                indent=row.get("indent", 0),
                section=section,
                is_total=is_total,
                is_calculated=is_calculated
            )
        )

    return classified


def build_hierarchy(classified_rows: List[FinancialLineItem]) -> Dict[FinancialSection, List[FinancialLineItem]]:
    hierarchy = {section: [] for section in FinancialSection}

    for item in classified_rows:
        hierarchy[item.section].append(item)

    return hierarchy


def sort_profit_and_loss(hierarchy: Dict[FinancialSection, List[FinancialLineItem]]):
    ordered = {}

    order = [
        FinancialSection.REVENUE,
        FinancialSection.COST_OF_GOODS,
        FinancialSection.OPERATING_EXPENSES,
        FinancialSection.FINANCE_COST,
        FinancialSection.DEPRECIATION,
        FinancialSection.PROFIT
    ]

    for section in order:
        if hierarchy.get(section):
            ordered[section] = hierarchy[section]

    return ordered
