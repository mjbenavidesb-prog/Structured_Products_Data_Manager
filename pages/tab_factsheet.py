import streamlit as st
import pandas as pd
from backend.database import get_all_products
from backend.factsheet import generate_factsheet_pdf
import backend.config as cfg

_STATUS_LABEL = {
    "AUTOCALL":     ("Autocall",    "product was called early"),
    "VENCIDO":      ("Vencimiento", "product reached scheduled maturity"),
    "VIGENTE":      ("Ejecutado",   "active product — current marketing sheet"),
    "POR EJECUTAR": (None,          "no termsheet yet — factsheet cannot be generated"),
}
_BADGE_COLOR = {
    "AUTOCALL":     "#2563EB",
    "VENCIDO":      "#DC2626",
    "VIGENTE":      "#16A34A",
    "POR EJECUTAR": "#9CA3AF",
}


def _status_badge(status: str) -> str:
    color = _BADGE_COLOR.get(status, "#6B7280")
    return (
        f"<span style='background:{color};color:white;padding:2px 10px;"
        f"border-radius:12px;font-size:0.78rem;font-weight:600'>{status}</span>"
    )


def render():
    st.subheader("Generate Factsheet")

    df = get_all_products()
    if df.empty:
        st.warning("No products found. Load products first.")
        return

    # ── Product selector ───────────────────────────────────────────────────────
    col1, col2 = st.columns([4, 1])

    with col1:
        product_names = df["nombre_producto"].dropna().tolist()
        selected = st.selectbox("Select Product", product_names)

    with col2:
        st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
        generate = st.button("Generate PDF", type="primary", use_container_width=True)

    if not selected:
        return

    row     = df[df["nombre_producto"] == selected].iloc[0]
    product = row.to_dict()
    status  = str(product.get("status") or "VIGENTE").upper()

    ftype_label, ftype_desc = _STATUS_LABEL.get(status, ("Ejecutado", ""))
    badge_html = _status_badge(status)

    st.markdown(
        f"{badge_html} &nbsp; → &nbsp; "
        f"<span style='font-size:0.9rem'><b>{ftype_label or 'N/A'}</b> factsheet — {ftype_desc}</span>",
        unsafe_allow_html=True,
    )

    if ftype_label is None:
        st.warning(
            "**POR EJECUTAR** products have not been terminated yet and have no termsheet data. "
            "No factsheet can be generated at this stage."
        )
        return

    # ── Product KPIs ───────────────────────────────────────────────────────────
    st.markdown("---")
    k1, k2, k3, k4, k5 = st.columns(5)

    aum = product.get("monto_total") or 0
    k1.metric("AUM", f"${float(aum):,.0f}" if aum else "—")
    k2.metric("Maturity", str(product.get("fecha_vencimiento") or "—"))

    underlyings = [
        str(product.get(f"underlying_{i}")).strip()
        for i in range(1, 5)
        if product.get(f"underlying_{i}") and
           str(product.get(f"underlying_{i}")).strip() not in ("", "nan", "None")
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

    # ── Data expander ──────────────────────────────────────────────────────────
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
            "fecha_autocall_1", "fecha_autocall_2", "fecha_autocall_3",
            "fecha_autocall_4", "fecha_autocall_5",
            "fecha_autocall_6", "fecha_autocall_7", "fecha_autocall_8",
            "fecha_autocall_9", "fecha_autocall_10",
        ]
        available = {k: product.get(k) for k in display_fields
                     if product.get(k) is not None}
        st.json(available)

    # ── Generation ────────────────────────────────────────────────────────────
    if generate:
        company_name = cfg.get("company_name") or "My Company"
        primary      = cfg.get("primary_color") or "#CC2200"

        with st.spinner(f"Generating {ftype_label} factsheet — fetching market data..."):
            try:
                pdf_bytes = generate_factsheet_pdf(
                    product=product,
                    company_name=company_name,
                    primary=primary,
                )
                st.success(f"Factsheet **{ftype_label}** generado correctamente.")

                file_name = (
                    f"Factsheet_{ftype_label}_{selected[:40].replace(' ', '_')}.pdf"
                )
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
        "**Factsheet type is derived from product status:**  "
        "AUTOCALL → called early before maturity  |  "
        "VENCIDO → reached scheduled maturity (autocallable or fixed-term)  |  "
        "VIGENTE → active product.  "
        "Colors follow your company branding configured in ⚙️ Settings."
    )
