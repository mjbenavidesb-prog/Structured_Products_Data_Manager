from backend.database import get_config, set_config

DEFAULTS = {
    "company_name": "Credicorp Capital",
    "primary_color": "#003087",
    "secondary_color": "#E31837",
    "accent_color": "#F5A623",
    "vehicles": [
        "Fondos mutuos",
        "Patrimonio Bonos Titulizados",
        "Portafolio Segregado",
        "Subdistribucion de notas",
        "Fondo de Inversion Colectiva",
        "Patrimonio VEST",
    ],
    "segments": [
        "BP Perú", "BP Chile", "BP Colombia", "BP US",
        "Mandato RIA", "W9", "Enalta", "BEX",
        "Consumo", "Juridicos", "MFO", "Vicctus", "TYBA", "Otros",
    ],
    "countries": ["Peru", "Chile", "Colombia", "Estados Unidos", "Panama"],
    "client_types": ["Institucional", "Retail", "Mandato RIA", "W9"],
    "entities": [
        "CC SAF", "Credibolsa", "AGF", "CC Colombia",
        "ASB Bank Corp", "ASB Valores", "Credicorp Capital LLC",
    ],
    "profiles": ["Muy Conservador", "Conservador", "Moderado", "Agresivo"],
    "asset_classes": ["Renta Variable", "Commodities", "Renta Fija"],
    "jurisdictions": ["Peru", "Panama", "Colombia", "Estados Unidos", "Chile"],
    "business_days_payment": 3,
}


def get(key: str):
    val = get_config(key)
    if val is None:
        return DEFAULTS.get(key)
    return val


def save(key: str, value):
    set_config(key, value)


def get_all() -> dict:
    result = {}
    for key in DEFAULTS:
        result[key] = get(key)
    return result
