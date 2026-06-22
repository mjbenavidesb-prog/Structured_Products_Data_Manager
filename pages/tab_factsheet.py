import streamlit as st
from backend.database import get_all_products
import backend.config as cfg


def render():
    st.subheader("Generate Factsheet")

    df = get_all_products()
    if df.empty:
        st.warning("No products found.")
        return

    active = df[df["status"].isin(["VIGENTE", "POR EJECUTAR", "AUTOCALL", "VENCIDO", "EJECUTADO"])].copy()
    product_names = active["nombre_producto"].dropna().tolist()

    col1, col2 = st.columns(2)
    with col1:
        selected = st.selectbox("Select Product", product_names)
    with col2:
        event_type = st.selectbox("Event Type", ["Vencimiento", "Autocall", "Ejecutado"])

    if selected:
        row = active[active["nombre_producto"] == selected].iloc[0]

        st.markdown("---")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("AUM (USD)", f"${row.get('monto_total', 0):,.0f}")
        c2.metric("Maturity", str(row.get("fecha_vencimiento", "—")))
        c3.metric("Underlying 1", str(row.get("underlying_1", "—")))
        c4.metric("Counterparty", str(row.get("contraparte", "—")))

    st.markdown("---")
    st.info(
        "**Factsheet generation requires PowerPoint templates.**\n\n"
        "Please upload the PPT templates for Vencimiento, Autocall, and Ejecutado. "
        "The templates will be used to populate slides with live market data and product details.\n\n"
        "Once uploaded, this tab will generate a ready-to-send PowerPoint file."
    )

    st.markdown("#### Upload PPT Templates")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        tmpl_vcto = st.file_uploader("Vencimiento template (.pptx)", type=["pptx"], key="tmpl_vcto")
    with col_b:
        tmpl_ac = st.file_uploader("Autocall template (.pptx)", type=["pptx"], key="tmpl_ac")
    with col_c:
        tmpl_ej = st.file_uploader("Ejecutado template (.pptx)", type=["pptx"], key="tmpl_ej")

    if any([tmpl_vcto, tmpl_ac, tmpl_ej]):
        st.warning("Template uploaded. Full factsheet generation will be enabled once templates are analyzed.")
        # TODO: save templates to disk and implement backend/factsheet.py generation logic
