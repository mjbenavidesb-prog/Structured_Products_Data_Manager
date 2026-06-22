import anthropic
import base64
import json
import re
from pathlib import Path

EXTRACTION_PROMPT = """You are an expert in structured investment products at a Latin American wealth manager.
Extract all available data from this termsheet PDF and return it as a single JSON object.

CRITICAL RULES:
- For Bloomberg tickers use the SHORT CODE only: SPX, RTY, NDX, INDU, SX5E, SX7E, AMZN, META, MSFT, GOOG, NVDA, JNJ, NFLX, XLK, XLU, XLP, XLY, etc.
- For dates use DD/MM/YYYY format (e.g. "14/08/2025").
- For percentages: store as decimal (0.80 for 80%, 1.10 for 110%). Do NOT store as 80 or 110.
- For numeric amounts: store as a plain number (4500000, not "USD 4,500,000").
- If a field is truly not present, use null. Never invent values.
- Initial levels / Strike levels are the reference index values on the Strike Date (e.g. 6340 for SPX).

Return ONLY the JSON object. No markdown, no explanation, no code fences.

Fields to extract:

{
  "tipo": "Certificate | Note | Warrant | Bond",
  "contraparte": "Issuer entity name (e.g. BNP Paribas Issuance B.V.)",
  "garante": "Guarantor bank name (e.g. BNP Paribas)",
  "isin": "ISIN code (e.g. XS3109969470)",
  "cusip": "CUSIP code if no ISIN (e.g. 09664K6J7)",
  "monto_total": numeric issue amount in the product currency (e.g. 4500000),
  "moneda": "USD | EUR | GBP | COP | PEN",
  "fecha_inicio": "Trade Date DD/MM/YYYY",
  "fecha_strike": "Strike / Fixing Date DD/MM/YYYY",
  "fecha_emision": "Issue Date DD/MM/YYYY",
  "fecha_obs_final": "Final Valuation / Observation Date DD/MM/YYYY",
  "fecha_vencimiento": "Maturity / Redemption / Settlement Date DD/MM/YYYY",
  "fecha_pago_maximo": "Maximum Payment Date DD/MM/YYYY (same as maturity if not stated separately)",
  "dias_habiles_pago": integer business days between final valuation and settlement (e.g. 3),
  "formato_subyacente": "Worst of | Individual | Basket",
  "underlying_1": "Bloomberg ticker of first underlying (e.g. SPX)",
  "underlying_2": "Bloomberg ticker of second underlying or null",
  "underlying_3": "Bloomberg ticker of third underlying or null",
  "underlying_4": "Bloomberg ticker of fourth underlying or null",
  "strike_1": numeric initial level of underlying 1 on strike date (e.g. 6340.0),
  "strike_2": numeric initial level of underlying 2 or null,
  "strike_3": numeric initial level of underlying 3 or null,
  "strike_4": numeric initial level of underlying 4 or null,
  "peso_1": weight of underlying 1 as decimal (0.25 for 25%) or null if not specified,
  "peso_2": weight of underlying 2 or null,
  "peso_3": weight of underlying 3 or null,
  "peso_4": weight of underlying 4 or null,
  "asset_class": "Renta Variable | Commodities | Renta Fija",
  "estrategia": "Opportunity | Capital Protegido",
  "tipo_estructura": "Distribucion | Participacion | Hibrido",
  "perfil": "Muy Conservador | Conservador | Moderado | Agresivo",
  "plazo_meses": integer number of months from trade date to maturity (e.g. 6),
  "cupon_fijo": annual fixed coupon as decimal (0.05 for 5% p.a.) or null,
  "cupon_contingente": annual contingent/conditional coupon as decimal or null,
  "barrera_cupon": coupon barrier as decimal (0.80 for 80%) or null,
  "barrera_capital": capital/knock-in barrier as decimal (0.70 for 70%) or null,
  "tipo_caida": "Knock In | Low Strike | Put Spread | None",
  "cap": cap level as decimal (1.126 for 112.6% cap) or null,
  "factor_participacion": participation rate as decimal (1.0 for 100%) or null,
  "ganancia_maxima": maximum gain as a formatted string (e.g. "12.6%" or "10%"),
  "trigger_autocall": autocall trigger level as decimal (1.0 for 100%) or null,
  "fecha_sin_autocall": "Non-call / no-autocall end date DD/MM/YYYY or null",
  "fecha_autocall_1": "First autocall observation date DD/MM/YYYY or null",
  "fecha_autocall_2": "Second autocall observation date DD/MM/YYYY or null",
  "fecha_autocall_3": "Third autocall observation date DD/MM/YYYY or null",
  "fecha_autocall_4": "Fourth autocall observation date DD/MM/YYYY or null",
  "fecha_autocall_5": "Fifth autocall observation date DD/MM/YYYY or null",
  "fecha_autocall_6": "Sixth autocall observation date DD/MM/YYYY or null",
  "fecha_autocall_7": "Seventh autocall observation date DD/MM/YYYY or null",
  "fecha_autocall_8": "Eighth autocall observation date DD/MM/YYYY or null",
  "fecha_autocall_9": "Ninth autocall observation date DD/MM/YYYY or null",
  "fecha_autocall_10": "Tenth autocall observation date DD/MM/YYYY or null",
  "contraparte_derivado": "Swap / derivative counterparty if different from issuer or null",
  "notional_derivado": numeric swap notional or null,
  "prima_pct": issue price as decimal if warrant/discounted note (0.0355 for 3.55%) or null,
  "formato": "Separable | No Separable",
  "nombre_producto": "A short commercial name for this product (e.g. 'Phoenix WO RTY-SPX 80% Jun26')"
}

CLASSIFICATION HINTS:
- If the product has a Knock-in barrier and conditional coupons -> tipo_caida = "Knock In", estrategia = "Opportunity"
- If capital is 100% protected regardless of performance -> estrategia = "Capital Protegido"
- If autocall trigger is present -> tipo = "Certificate" or "Note" with autocall feature
- Worst-of basket with coupon barrier = Phoenix structure
- Digital payout (binary) -> cupon_contingente = payout %, ganancia_maxima = same
- Range accrual -> cupon_contingente = max annual coupon
- For perfil: Capital Protegido -> "Conservador"; 70-75% KI -> "Moderado"; 60% or less KI -> "Agresivo"
"""


def extract_termsheet(pdf_bytes: bytes, api_key: str) -> dict:
    client = anthropic.Anthropic(api_key=api_key)
    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": EXTRACTION_PROMPT,
                    },
                ],
            }
        ],
    )

    raw = message.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


def extract_termsheet_from_path(pdf_path: str, api_key: str) -> dict:
    with open(pdf_path, "rb") as f:
        return extract_termsheet(f.read(), api_key)
