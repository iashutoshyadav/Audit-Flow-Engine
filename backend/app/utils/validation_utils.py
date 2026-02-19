import re
from typing import Optional


def parse_number(value) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = str(value).strip()
    if not cleaned:
        return None

    cleaned = cleaned.replace('(', '-').replace(')', '')
    cleaned = cleaned.replace(',', '')
    cleaned = cleaned.replace('—', '-').replace('–', '-')
    cleaned = re.sub(r'[₹$€£¥]', '', cleaned)
    cleaned = re.sub(r'^[a-zA-Z\s]+', '', cleaned).strip()
    cleaned = re.sub(r'[a-zA-Z\s]+$', '', cleaned).strip()

    if not cleaned:
        return None
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None

def clean_item_name(item_name) -> str:
    if not item_name:
        return ""
    if not isinstance(item_name, str):
        item_name = str(item_name)
    cleaned = ' '.join(item_name.split()).strip('- ')
    cleaned = re.sub(r'[\|\>\<\$\[\]\{\}]+$', '', cleaned).strip()
    return cleaned