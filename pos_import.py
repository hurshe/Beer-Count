"""
pos_import.py — Parse IzzyRest XLSX export and return aggregated POS sales.
"""
import pandas as pd
from datetime import datetime

# Maps product name from IzzyRest → (beer_name_in_app, size_label)
PRODUCT_MAP = {
    "ŻYWIEC SMALL":          ("ŻYWIEC",    "0.3L"),
    "ŻYWIEC LARGE":          ("ŻYWIEC",    "0.5L"),
    "ŻYWIEC JUG":            ("ŻYWIEC",    "1.5L"),
    "ŻYWIEC IPA":            ("IPA",       "0.4L"),
    "ŻYWIEC BIAŁE SMALL":    ("BIAŁE",     "0.3L"),
    "ŻYWIEC BIAŁE LARGE":    ("BIAŁE",     "0.5L"),
    "ŻYWIEC BIAŁE 0% SMALL": ("BIAŁE 0%",  "0.3L"),
    "ŻYWIEC BIAŁE 0% LARGE": ("BIAŁE 0%",  "0.5L"),
    "MURPHYS SMALL":         ("MURPHYS",   "0.3L"),
    "MURPHYS LARGE":         ("MURPHYS",   "0.5L"),
    "HEINEKEN SMALL":        ("HEINEKEN",  "0.3L"),
    "HEINEKEN LARGE":        ("HEINEKEN",  "0.5L"),
}


def parse_pos_file(filepath: str) -> dict:
    """
    Parse IzzyRest XLSX file.
    Returns: {
        "2026-06-14": {
            "ŻYWIEC":   {"0.3L": 12, "0.5L": 84, "1.5L": 3},
            "HEINEKEN": {"0.3L": 5,  "0.5L": 22},
            "IPA":      {"0.4L": 30},
            ...
        },
        ...
    }
    Raises: ValueError if file cannot be parsed.
    """
    try:
        df = pd.read_excel(filepath, header=None)
    except Exception as e:
        raise ValueError(f"Nie można otworzyć pliku: {e}")

    results = {}
    current_product = None

    for idx, row in df.iterrows():
        cell2 = str(row[2]) if pd.notna(row[2]) else ""

        # Detect product header: col[2] contains "Produkt : NAME"
        if "Produkt :" in cell2:
            product_name = cell2.replace("Produkt :", "").strip()
            current_product = PRODUCT_MAP.get(product_name)
            continue

        if current_product is None:
            continue

        # Parse datetime from col[2]
        date_val = row[2]
        if not pd.notna(date_val):
            continue
        try:
            if isinstance(date_val, datetime):
                dt = date_val
            else:
                dt = pd.to_datetime(str(date_val))
            date_str = dt.strftime("%Y-%m-%d")
        except Exception:
            continue

        # Quantity from col[6]
        qty = row[6]
        if not pd.notna(qty):
            continue
        try:
            qty = int(float(qty))
        except (ValueError, TypeError):
            continue
        if qty <= 0:
            continue

        beer, size = current_product
        if date_str not in results:
            results[date_str] = {}
        if beer not in results[date_str]:
            results[date_str][beer] = {}
        results[date_str][beer][size] = \
            results[date_str][beer].get(size, 0) + qty

    if not results:
        raise ValueError(
            "Nie znaleziono danych sprzedażowych w pliku.\n"
            "Sprawdź czy plik pochodzi z IzzyRest (format BEERS).")

    return results


def get_available_dates(filepath: str) -> list:
    """Return sorted list of dates available in the file."""
    data = parse_pos_file(filepath)
    return sorted(data.keys())


def get_sales_for_date(filepath: str, date_str: str) -> dict:
    """Return sales dict for a specific date, or empty dict."""
    data = parse_pos_file(filepath)
    return data.get(date_str, {})
