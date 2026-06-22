import anthropic
import base64
import json
import re
from pathlib import Path

EXTRACTION_PROMPT = """You are an expert in structured investment products. Extract all relevant information from this termsheet PDF and return it as a JSON object.

Extract the following fields (use null if not found):

{
  "underlying_1": "ticker or name of first underlying asset",
  "underlying_2": "ticker or name of second underlying asset (or null)",
  "underlying_3": "ticker or name of third underlying asset (or null)",
  "underlying_4": "ticker or name of fourth underlying asset (or null)",
  "formato_subyacente": "Worst of / Individual / Canasta",
  "strike_1": numeric initial level of underlying 1,
  "strike_2": numeric initial level of underlying 2 (or null),
  "strike_3": numeric initial level of underlying 3 (or null),
  "strike_4": numeric initial level of underlying 4 (or null),
  "peso_1": weight of underlying 1 as decimal (e.g. 0.25 for 25%),
  "peso_2": weight of underlying 2 as decimal (or null),
  "peso_3": weight of underlying 3 as decimal (or null),
  "peso_4": weight of underlying 4 as decimal (or null),
  "fecha_inicio": "DD-Mon-YY start/trade date",
  "fecha_strike": "DD-Mon-YY strike/fixing date",
  "fecha_emision": "DD-Mon-YY issue date",
  "fecha_vencimiento": "DD-Mon-YY maturity/expiry date",
  "fecha_obs_final": "DD-Mon-YY final observation date",
  "fecha_pago_maximo": "DD-Mon-YY maximum payment date",
  "moneda": "USD / EUR / COP / PEN",
  "contraparte": "issuer bank name",
  "isin": "ISIN code if present",
  "formato": "Separable / No Separable",
  "tipo_estructura": "Distribucion / Participacion / Hibrido",
  "estrategia": "Opportunity / Capital Protegido",
  "asset_class": "Renta Variable / Commodities / Renta Fija",
  "perfil": "Conservador / Moderado / Agresivo / Muy Conservador",
  "plazo_meses": integer number of months,
  "cupon_fijo": annual fixed coupon as decimal (or null),
  "cupon_contingente": annual contingent coupon as decimal (or null),
  "ganancia_maxima": "maximum gain as string e.g. '25%'",
  "factor_participacion": participation factor as decimal (or null),
  "trigger_autocall": autocall trigger level as decimal e.g. 1.0 for 100% (or null),
  "barrera_cupon": coupon barrier as decimal (or null),
  "barrera_capital": capital barrier as decimal (or null),
  "tipo_caida": "Knock In / Low Strike Apalancada / Low Strike Sin Apalancar / Put Spread",
  "fecha_sin_autocall": "date from which autocall is possible (or null)",
  "fecha_autocall_1": "first autocall observation date (or null)",
  "fecha_autocall_2": "second autocall observation date (or null)",
  "fecha_autocall_3": "third autocall observation date (or null)",
  "fecha_autocall_4": "fourth autocall observation date (or null)",
  "fecha_autocall_5": "fifth autocall observation date (or null)",
  "fecha_autocall_6": "sixth autocall observation date (or null)",
  "fecha_autocall_7": "seventh autocall observation date (or null)",
  "fecha_autocall_8": "eighth autocall observation date (or null)",
  "fecha_autocall_9": "ninth autocall observation date (or null)",
  "fecha_autocall_10": "tenth autocall observation date (or null)",
  "contraparte_derivado": "derivative counterparty bank name",
  "notional_derivado": numeric notional amount of the derivative,
  "prima_pct": premium percentage as decimal (or null)
}

Return ONLY the JSON object, no explanation or markdown.
"""


def extract_termsheet(pdf_bytes: bytes, api_key: str) -> dict:
    client = anthropic.Anthropic(api_key=api_key)
    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
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
    # Strip markdown code fences if present
    raw = re.sub(r"^```(?:json)?\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    return json.loads(raw)


def extract_termsheet_from_path(pdf_path: str, api_key: str) -> dict:
    with open(pdf_path, "rb") as f:
        return extract_termsheet(f.read(), api_key)
