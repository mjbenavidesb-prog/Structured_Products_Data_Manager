import streamlit as st
import pandas as pd
from datetime import date, timedelta
from backend.database import get_all_products
from backend.factsheet import generate_factsheet_pdf
from backend.market_data import resolve_ticker
import backend.config as cfg

try:
    import yfinance as yf
    _YF = True
except ImportError:
    _YF = False

_BADGE = {
    "AUTOCALL":     "#2563EB",
    "VENCIDO":      "#DC2626",
    "VIGENTE":      "#16A34A",
    "POR EJECUTAR": "#9CA3AF",
}


def _badge(status: str) -> str:
    color = _BADGE.get(status, "#6B7280")
    return (
        f"<span style='background:{color};color:white;padding:2px 10px;"
        f"border-radius:12px;font-size:0.78rem;font-weight:600'>{status}</span>"
    )


def _parse_date(val) -> date | None:
    if val is None:
        return None
    try:
        d = pd.to_datetime(str(val), dayfirst=True, errors="coerce")
        return d.date() if pd.notna(d) else None
    except Exception:
        return None


def _safe_float(v):
    try:
        f = float(v)
        return None if f != f else f
    except (TypeError, ValueError):
        return None


def _has_termsheet(p: dict) -> bool:
    has_underlying = any(
        p.get(f"underlying_{i}") and
        str(p.get(f"underlying_{i}")).strip() not in ("", "nan", "None")
        for i in range(1, 5)
    )
    has_start = bool(p.get("fecha_inicio") or p.get("fecha_strike"))
    return has_underlying and has_start


# ── Pre-validation (fast, no API calls) ───────────────────────────────────────

def _validate(ftype: str, p: dict) -> tuple[bool, str]:
    """
    Returns (is_valid, reason).
    Only fast checks — no price fetching.
    For Autocall, just checks that past dates and trigger data exist.
    The actual price verification happens at generate time.
    """
    today = date.today()

    if ftype == "Autocall":
        past_obs = [
            d for i in range(1, 11)
            if (d := _parse_date(p.get(f"fecha_autocall_{i}"))) and d <= today
        ]
        if not past_obs:
            return False, (
                "No hay fechas de observación de autocall en el pasado. "
                "Para que el producto haya autocalleado necesita al menos una "
                "fecha de observación ya transcurrida."
            )
        unds = [
            str(p.get(f"underlying_{i}")).strip()
            for i in range(1, 5)
            if p.get(f"underlying_{i}") and
               str(p.get(f"underlying_{i}")).strip() not in ("", "nan", "None")
        ]
        strikes = [_safe_float(p.get(f"strike_{i}")) for i in range(1, len(unds) + 1)]
        trigger = _safe_float(p.get("trigger_autocall"))
        if not unds or not any(s for s in strikes if s):
            return False, (
                "Faltan subyacentes o niveles de strike para verificar si autocalleó. "
                "Carga el termsheet primero."
            )
        if trigger is None:
            return False, (
                "Falta el nivel de trigger de autocall en el termsheet."
            )
        # Looks OK for a fast check — price verification happens at generate time
        return True, ""

    if ftype == "Vencimiento":
        obs_final = _parse_date(p.get("fecha_obs_final"))
        vcto      = _parse_date(p.get("fecha_vencimiento"))
        if obs_final and obs_final <= today:
            return True, ""
        if vcto and vcto <= today:
            return True, ""
        ref     = obs_final or vcto
        ref_str = ref.strftime("%d/%m/%Y") if ref else "desconocida"
        return False, (
            f"La fecha de observación final / vencimiento ({ref_str}) aún no ha llegado. "
            "Solo se puede generar el factsheet Vencimiento cuando el producto ya venció."
        )

    if ftype == "Ejecutado":
        if not _has_termsheet(p):
            return False, (
                "El producto no tiene datos de termsheet (subyacentes ni fecha de inicio). "
                "Carga primero el termsheet desde el tab **Load Product**."
            )
        return True, ""

    return False, "Tipo de factsheet desconocido."


# ── Deep price verification (runs at generate time) ───────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def _verify_autocall_prices(
    tickers: tuple, strikes: tuple, trigger: float, obs_dates: tuple
) -> tuple[bool, str | None, str]:
    """
    Fetches close prices from yfinance on each past observation date and checks
    whether the worst-of underlying closed >= strike * trigger on any date.

    Returns:
        (did_autocall: bool, autocall_date_str: str | None, message: str)
    """
    if not _YF:
        return True, None, "yfinance not available — skipping price check."

    yf_syms = [resolve_ticker(t) for t in tickers if resolve_ticker(t)]
    if not yf_syms:
        return True, None, "No yfinance tickers resolved — skipping price check."

    trigger_dec = trigger if trigger <= 1.5 else trigger / 100

    for obs_date in sorted(obs_dates):
        # Fetch a 5-day window around the observation date to handle holidays
        start = str(obs_date - timedelta(days=4))
        end   = str(obs_date + timedelta(days=1))
        try:
            if len(yf_syms) == 1:
                raw = yf.download(yf_syms[0], start=start, end=end,
                                  auto_adjust=True, progress=False)
                closes = raw[["Close"]]
                closes.columns = yf_syms
            else:
                raw = yf.download(yf_syms, start=start, end=end,
                                  auto_adjust=True, progress=False)
                closes = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw

            if closes.empty:
                continue

            # Use the last available close on or before obs_date
            closes.index = pd.to_datetime(closes.index).tz_localize(None)
            closes = closes[closes.index.date <= obs_date]
            if closes.empty:
                continue

            row = closes.iloc[-1]

            # Check worst-of: each underlying must be >= strike * trigger
            autocalled = True
            for sym, strike in zip(yf_syms, strikes):
                if sym not in row.index or strike is None or strike == 0:
                    autocalled = False
                    break
                price = float(row[sym])
                if price < strike * trigger_dec:
                    autocalled = False
                    break

            if autocalled:
                return True, str(obs_date), ""

        except Exception:
            continue  # network error on one date → keep checking others

    # None of the past observation dates triggered autocall
    dates_str = ", ".join(str(d) for d in obs_dates)
    return False, None, (
        f"El producto **no ha autocalleado**. Se verificaron los precios de cierre "
        f"en las fechas de observación pasadas ({dates_str}) y en ninguna el "
        f"peor subyacente superó el nivel de autocall ({trigger_dec*100:.0f}% del strike inicial)."
    )


# ── Tab render ────────────────────────────────────────────────────────────────

def render():
    st.subheader("Generate Factsheet")

    df = get_all_products()
    if df.empty:
        st.warning("No products found. Load products first.")
        return

    col1, col2, col3 = st.columns([3, 2, 1])

    with col1:
        selected = st.selectbox("Select Product", df["nombre_producto"].dropna().tolist())

    with col2:
        ftype = st.selectbox(
            "Factsheet Type",
            ["Autocall", "Vencimiento", "Ejecutado"],
            help=(
                "Autocall — producto fue llamado anticipadamente  |  "
                "Vencimiento — producto llegó a plazo  |  "
                "Ejecutado — producto activo (marketing sheet)"
            ),
        )

    with col3:
        st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
        generate = st.button("Generate PDF", type="primary", use_container_width=True)

    if not selected:
        return

    row     = df[df["nombre_producto"] == selected].iloc[0]
    product = row.to_dict()
    status  = str(product.get("status") or "").upper()

    st.markdown(_badge(status), unsafe_allow_html=True)

    # Fast pre-validation (no API)
    valid, reason = _validate(ftype, product)
    if not valid:
        st.error(f"**No se puede generar factsheet {ftype}:** {reason}")

    # ── KPIs ──────────────────────────────────────────────────────────────────
    st.markdown("---")
    k1, k2, k3, k4, k5 = st.columns(5)

    aum = product.get("monto_total") or 0
    k1.metric("AUM", f"${float(aum):,.0f}" if aum else "—")
    k2.metric("Maturity", str(product.get("fecha_vencimiento") or "—"))

    underlyings = [
        str(product.get(f"underlying_{i}")).strip()
        for i in range(1, 5)
        if product.get(f"underlying_{i}")
        and str(product.get(f"underlying_{i}")).strip() not in ("", "nan", "None")
    ]
    k3.metric("Underlyings", " / ".join(underlyings) if underlyings else "—")
    k4.metric("Counterparty", str(product.get("contraparte") or "—"))

    rt = product.get("rendimiento_total")
    if rt is not None:
        rt_f   = float(rt)
        rt_pct = rt_f * 100 if abs(rt_f) <= 1 else rt_f
        k5.metric("Total Return", f"{rt_pct:.2f}%")
    else:
        k5.metric("Total Return", "—")

    # ── Data expander ─────────────────────────────────────────────────────────
    with st.expander("Product data used for factsheet", expanded=False):
        display_fields = [
            "isin", "moneda", "contraparte", "perfil", "asset_class", "tipo",
            "plazo_meses", "cupon_contingente", "cupon_fijo", "barrera_capital",
            "trigger_autocall", "ganancia_maxima", "cap", "factor_participacion",
            "fecha_inicio", "fecha_strike", "fecha_emision", "fecha_obs_final",
            "fecha_vencimiento", "rendimiento_total",
            "underlying_1", "strike_1", "spot_1",
            "underlying_2", "strike_2", "spot_2",
            "underlying_3", "strike_3", "spot_3",
            "underlying_4", "strike_4", "spot_4",
            *(f"fecha_autocall_{i}" for i in range(1, 11)),
        ]
        available = {k: product.get(k) for k in display_fields if product.get(k) is not None}
        st.json(available)

    # ── Generation ────────────────────────────────────────────────────────────
    if generate:
        if not valid:
            st.warning("Corrige la selección antes de generar.")
            return

        company_name = cfg.get("company_name") or "My Company"
        primary      = cfg.get("primary_color") or "#CC2200"

        # For Autocall: verify prices on observation dates before generating
        if ftype == "Autocall":
            unds_list = [
                str(product.get(f"underlying_{i}")).strip()
                for i in range(1, 5)
                if product.get(f"underlying_{i}")
                and str(product.get(f"underlying_{i}")).strip() not in ("", "nan", "None")
            ]
            strikes_list = [
                _safe_float(product.get(f"strike_{i}"))
                for i in range(1, len(unds_list) + 1)
            ]
            trigger = _safe_float(product.get("trigger_autocall")) or 1.0
            today   = date.today()
            past_obs = tuple(
                d for i in range(1, 11)
                if (d := _parse_date(product.get(f"fecha_autocall_{i}"))) and d <= today
            )

            with st.spinner("Verificando precios en fechas de observación..."):
                did_ac, ac_date_str, msg = _verify_autocall_prices(
                    tuple(unds_list), tuple(strikes_list), trigger, past_obs
                )

            if not did_ac:
                st.error(msg)
                return

            if ac_date_str:
                st.info(f"Autocall verificado en fecha de observación: **{ac_date_str}**")

        with st.spinner(f"Generating {ftype} factsheet — fetching market data..."):
            try:
                pdf_bytes = generate_factsheet_pdf(
                    product=product,
                    event_type=ftype,
                    company_name=company_name,
                    primary=primary,
                )
                st.success(f"Factsheet **{ftype}** generado correctamente.")

                file_name = f"Factsheet_{ftype}_{selected[:40].replace(' ', '_')}.pdf"
                st.download_button(
                    label=f"Download PDF — {file_name}",
                    data=pdf_bytes,
                    file_name=file_name,
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True,
                )

            except Exception as e:
                st.error(f"Factsheet generation failed: {e}")
                st.exception(e)

    # ── Legend ────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.caption(
        "**Validación de tipos:**  "
        "Autocall — verifica precios reales en fechas de observación vs. trigger  |  "
        "Vencimiento — fecha obs. final o vencimiento ya pasó  |  "
        "Ejecutado — termsheet cargado"
    )
