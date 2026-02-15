import re
from typing import Optional

def parse_number(value: str) -> Optional[float]:
    if not value:
        return None
    cleaned = value.strip()
    cleaned = cleaned.replace('(', '-').replace(')', '')
    cleaned = cleaned.replace(',', '')
    cleaned = cleaned.replace('—', '-').replace('–', '-')
    try:
        return float(cleaned)
    except:
        return None

def clean_item_name(item_name: str) -> str:
    return ' '.join(item_name.split()).strip('- ')
