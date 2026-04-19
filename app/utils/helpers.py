"""
Helpers de uso general.
"""
import re
import uuid
from datetime import datetime, timezone


def generate_invoice_number(prefix: str = "FAC") -> str:
    """Genera un número de factura único: FAC-20250416-A3B9F2"""
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    suffix = uuid.uuid4().hex[:6].upper()
    return f"{prefix}-{today}-{suffix}"


def clean_phone(phone: str) -> str:
    """Limpia y normaliza un número de teléfono (solo dígitos)."""
    return re.sub(r"\D", "", phone)


def format_currency(amount: float, currency: str = "BOB") -> str:
    """Formatea un monto con símbolo de moneda."""
    symbols = {"BOB": "Bs.", "USD": "$", "EUR": "€"}
    symbol = symbols.get(currency, currency)
    return f"{symbol} {amount:,.2f}"
