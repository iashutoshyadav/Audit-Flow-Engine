from app.services import structure_service

def extract_income_statement(table_data):
    if not table_data or "rows" not in table_data:
        return {
            "year_headers": [],
            "structured_data": {},
            "raw_rows": []
        }

    raw_rows = table_data["rows"]
    year_headers = table_data.get("year_headers", [])

    classified = structure_service.classify_rows(raw_rows)
    hierarchy = structure_service.build_hierarchy(classified)

    return {
        "year_headers": year_headers,
        "structured_data": hierarchy,
        "raw_rows": raw_rows
    }
