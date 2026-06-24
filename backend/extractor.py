import anthropic
import base64
import json
import re
from pathlib import Path

EXTRACTION_PROMPT = """You are a senior derivatives structurer at a Latin American wealth manager with deep expertise in structured investment products and financial engineering.

Read this termsheet in full and extract all available fields. Return a single JSON object.

CRITICAL RULES:
- Bloomberg tickers: SHORT form only. For ETFs like "XLK UP Equity" use "XLK". For indices: SPX, RTY, NDX, INDU, SX5E, NKY, STOXX50E, etc.
- Dates: DD/MM/YYYY (e.g. "04/06/2026").
- Percentages as decimals: 75% → 0.75, 11% → 0.11. Never store as 75 or 11.
- Leverage as decimal: 1.33, not 133%.
- Numeric amounts: plain number (925000, not "USD 925,000").
- null if a field is truly absent. Never invent values.

FIELDS TO EXTRACT:
{
  "nombre_producto": "Short commercial name max 60 chars (e.g. 'Range Accrual XLK-XLU-XLP-XLY 75% Jun29')",
  "tipo": "Certificate | Note | Warrant | Bond",
  "isin": "ISIN code or null",
  "cusip": "CUSIP if present and no ISIN, else null",
  "moneda": "USD | EUR | GBP | PEN | CLP | COP",
  "contraparte": "Guarantor bank short name (e.g. 'Nomura Holdings')",
  "garante": "Guarantor full legal name or null",
  "emisor": "Issuer entity full name (e.g. 'Nomura International Funding Pte. Ltd.')",

  "fecha_inicio": "Trade Date DD/MM/YYYY",
  "fecha_emision": "Issue Date DD/MM/YYYY",
  "fecha_strike": "Strike/Fixing Date DD/MM/YYYY (same as trade date if not separate)",
  "fecha_obs_final": "Final Valuation/Observation Date DD/MM/YYYY",
  "fecha_vencimiento": "Maturity/Redemption/Settlement Date DD/MM/YYYY",
  "plazo_meses": integer months from trade date to maturity (e.g. 36),

  "formato_subyacente": "Worst of | Individual | Basket",
  "underlying_1": "Bloomberg ticker of first underlying",
  "underlying_2": "Bloomberg ticker of second underlying or null",
  "underlying_3": "Bloomberg ticker of third underlying or null",
  "underlying_4": "Bloomberg ticker of fourth underlying or null",
  "strike_1": numeric initial/strike level of U1 or null,
  "strike_2": numeric initial/strike level of U2 or null,
  "strike_3": numeric initial/strike level of U3 or null,
  "strike_4": numeric initial/strike level of U4 or null,
  "peso_1": weight of U1 as decimal or null if equal-weighted/not stated,
  "peso_2": weight of U2 or null,
  "peso_3": weight of U3 or null,
  "peso_4": weight of U4 or null,

  "asset_class": "Renta Variable | Commodities | Renta Fija",
  "estrategia": "Opportunity | Capital Protegido",
  "tipo_estructura": "Distribucion | Participacion | Hibrido",
  "perfil": "Muy Conservador | Conservador | Moderado | Agresivo",

  "cupon_fijo": annual fixed coupon as decimal or null,
  "cupon_contingente": annual contingent/range accrual coupon as decimal (0.11 for 11% p.a.) or null,
  "barrera_cupon": coupon observation barrier as decimal (0.75 for 75%) or null,
  "barrera_capital": capital protection / knock-in barrier as decimal or null,
  "tipo_caida": "Knock In | Low Strike | Put Spread | None",
  "cap": cap level as decimal or null,
  "factor_participacion": participation rate as decimal or null,
  "trigger_autocall": autocall/knock-out trigger as decimal (1.0 for 100%) or null,
  "fecha_sin_autocall": "Non-call / lock-out end date DD/MM/YYYY or null",
  "ganancia_maxima": "Maximum gain as a string — read it directly from the termsheet. Examples: '33%', '16.25%', 'Ilimitada', 'Unlimited'. For coupon products multiply annual coupon rate by years ONLY if no cap or explicit max is stated. For capped products use the cap. For unlimited participation products use 'Ilimitada'.",

  "fecha_autocall_1": "First knock-out/autocall observation date DD/MM/YYYY or null",
  "fecha_autocall_2": "Second or null",
  "fecha_autocall_3": "Third or null",
  "fecha_autocall_4": "Fourth or null",
  "fecha_autocall_5": "Fifth or null",
  "fecha_autocall_6": "Sixth or null",
  "fecha_autocall_7": "Seventh or null",
  "fecha_autocall_8": "Eighth or null",
  "fecha_autocall_9": "Ninth or null",
  "fecha_autocall_10": "Tenth or null",

  "contraparte_derivado": "Swap counterparty if different from issuer or null",
  "prima_pct": issue price as decimal if discounted/warrant (e.g. 0.9645) or null,
  "formato": "Separable | No Separable",

  "elemento_1_tipo": "Primary element type — see ENGINEERING GUIDE",
  "elemento_1_leverage": numeric leverage of element 1 (e.g. 1.00),
  "elemento_1_posicion": "Long | Short",
  "elemento_2_tipo": "Secondary element type — see ENGINEERING GUIDE, or null",
  "elemento_2_leverage": numeric leverage of element 2 or null,
  "elemento_2_posicion": "Long | Short or null",
  "elemento_3_tipo": "Third element type if present or null",
  "elemento_3_leverage": numeric leverage or null,
  "elemento_3_posicion": "Long | Short or null"
}

CLASSIFICATION HINTS:
- Knock-in barrier + conditional coupons → tipo_caida = "Knock In", estrategia = "Opportunity"
- Capital 100% protected regardless of performance → estrategia = "Capital Protegido", tipo_caida = "None"
- perfil: Capital Protegido → "Conservador"; barrier 70-80% → "Moderado"; barrier ≤ 65% → "Agresivo"
- For autocall dates: extract the Knock-Out Determination Days (observation dates), NOT the coupon payment dates
- For Range Accrual: barrera_cupon = coupon barrier; barrera_capital = knock-in/capital barrier (may be same value)

ENGINEERING GUIDE — Decompose the product into its derivative building blocks:

ELEMENT 1 (return generator — investor is LONG):
- "Daily Range Accrual": coupon paid proportional to fraction of trading days where each underlying closes >= coupon barrier. Key signal: "Relevant Accrual Fraction" or daily observation of basket.
- "Phoenix Autocall": conditional coupon at periodic observation dates if worst-of >= coupon barrier; autocalls if >= trigger.
- "Phoenix with Memory": Phoenix where missed coupons accumulate and are all paid when barrier is next observed.
- "Athena Autocall": always pays coupon on autocall dates (no separate coupon barrier).
- "Fixed Coupon": fixed rate regardless of performance.
- "Digital Coupon": binary — full coupon if above barrier, zero otherwise. Typically one large payment.
- "Capital Protected Participation": 100% capital floor + participation in upside.
- "Dual Directional": investor participates 1:1 in upside AND benefits from moderate downside (absolute value of return) within a buffer zone; full loss below barrier. Key signals: "twin win", "dual directional", "buffer", absolute return participation.

ELEMENT 2 (secondary derivative block — may be Long or Short):
- "Low Strike Put": put struck BELOW 100% of initial price. Investor bears loss when worst-of < strike at maturity. Leverage = 1/strike_pct (e.g. strike=75% → 1/0.75 = 1.333). European observation (final valuation date only). Redemption = Denomination × Final_worst/Strike_worst. Position: Short.
- "KI Put (European)": put activated only if worst-of <= KI price on the FINAL valuation date. Usually struck at 100%. Leverage = 1.00. Position: Short.
- "KI Put (American)": put activated if worst-of <= KI price on ANY trading day. Higher risk than European. Position: Short.
- "KO Put (ATM)": ATM put that KNOCKS OUT if worst-of <= barrier on final valuation date. Provides upside from downside within buffer zone. Used in Dual Directional / Twin Win structures. Position: Long.
- "Vanilla Put (100%)": standard put struck at 100%, no knock-in, observed at maturity. Position: Short.
- "Low Strike Call": investor is LONG a call with strike below 100%; provides leveraged upside. Leverage = 1/strike. Position: Long.
- null: fully capital protected — no secondary element.

ELEMENT 3 (third derivative block if needed — used in complex structures):
- "Low Strike Put": same as element 2 definition. Typically Short in element 3.
- "KO Put (ATM)": same as element 2 definition.
- "Vanilla Put (100%)": Short put at 100% that offsets part of element 2 cost. Used in Dual Directional structures.
- "Short Call (OTM)": investor sells upside beyond a cap level. Provides a maximum gain cap. Position: Short.
- null: no third element.

LEVERAGE CALCULATION GUIDE:
- Range Accrual / Phoenix coupon component: 1.00
- Low Strike Put: leverage = 1.0 / strike_as_decimal (e.g. 75% strike → 1.333)
- KI Put at 100% strike: 1.00
- Participation / upside element: the stated participation rate (e.g. 1.33 for 133%)
- If leverage for an element is not explicitly stated and cannot be calculated, use 1.00

EXAMPLE 1 — Nomura 36M Callable Daily Range Accrual (Strike=75%, KI=75%, European final obs):
{
  "elemento_1_tipo": "Daily Range Accrual",
  "elemento_1_leverage": 1.00,
  "elemento_1_posicion": "Long",
  "elemento_2_tipo": "Low Strike Put",
  "elemento_2_leverage": 1.333,
  "elemento_2_posicion": "Short",
  "elemento_3_tipo": null,
  "elemento_3_leverage": null,
  "elemento_3_posicion": null,
  "ganancia_maxima": "33.0%"
}
Reasoning: leverage = 1/0.75 = 1.333; KI observed only at final valuation → European → Low Strike Put. Max gain = 11% × 3 years = 33%.

EXAMPLE 2 — BNP Paribas Twin Win / Dual Directional (buffer 16.25%, barrier 83.75%, participation 1.00x, no cap):
{
  "elemento_1_tipo": "Dual Directional",
  "elemento_1_leverage": 1.00,
  "elemento_1_posicion": "Long",
  "elemento_2_tipo": "KO Put (ATM)",
  "elemento_2_leverage": 2.00,
  "elemento_2_posicion": "Long",
  "elemento_3_tipo": "Vanilla Put (100%)",
  "elemento_3_leverage": 1.00,
  "elemento_3_posicion": "Short",
  "ganancia_maxima": "Ilimitada"
}
Reasoning: Long Call ATM (1x) + Long KO Put ATM (2x, KO at 83.75%) + Short Put 100% (1x) = investor gains above AND below initial level within the 16.25% buffer. No upside cap → ganancia_maxima = "Ilimitada".

Return ONLY the JSON object. No markdown, no explanation, no code fences.
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
