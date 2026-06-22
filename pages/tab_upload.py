import streamlit as st
import json
from datetime import date
import backend.config as cfg
from backend.database import insert_product, get_all_products
from backend.extractor import extract_termsheet


def _date_input(label, default=None, key=None):
    try:
        parsed = date.fromisoformat(str(default)) if default else date.today()
    except Exception:
        parsed = date.today()
    return st.date_input(label, value=parsed, key=key)


def render():
    primary = cfg.get("primary_color") or "#003087"
    st.subheader("Load Product")

    # ── Step 1: Upload & Extract ──────────────────────────────────────────────
    st.markdown("### Step 1 — Upload Termsheet PDF")
    api_key = cfg.get("claude_api_key") or ""

    if not api_key:
        st.warning("Claude API key not configured. Go to ⚙️ Settings to add it.")

    uploaded = st.file_uploader("Upload termsheet PDF", type=["pdf"])

    if "extracted" not in st.session_state:
        st.session_state["extracted"] = None

    if uploaded is not None and api_key:
        if st.button("🤖 Extract Data with Claude", type="primary"):
            with st.spinner("Extracting fields from termsheet..."):
                try:
                    pdf_bytes = uploaded.read()
                    result = extract_termsheet(pdf_bytes, api_key)
                    st.session_state["extracted"] = result
                    st.success("Extraction complete. Review and complete the fields below.")
                except Exception as e:
                    st.error(f"Extraction failed: {e}")

    extracted = st.session_state.get("extracted") or {}

    if extracted:
        with st.expander("Raw extracted JSON", expanded=False):
            st.json(extracted)

    # ── Step 2: Complete Product Form ─────────────────────────────────────────
    st.markdown("### Step 2 — Complete Product Information")

    existing = get_all_products()
    existing_names = existing["nombre_producto"].dropna().tolist() if not existing.empty else []

    with st.form("product_form"):
        st.markdown("#### Identity")
        col1, col2, col3 = st.columns(3)
        with col1:
            nombre_producto = st.text_input(
                "Product Name *",
                value=extracted.get("nombre_producto", ""),
                help="Internal name your team uses for this product",
            )
            isin = st.text_input("ISIN", value=extracted.get("isin", ""))
        with col2:
            tipo = st.selectbox("Type", ["Note", "Option", "Swap", "Loan", "Other"],
                                index=0)
            status_options = ["VIGENTE", "POR EJECUTAR", "AUTOCALL", "VENCIDO", "EJECUTADO", "CANCELADO"]
            status = st.selectbox("Status", status_options, index=1)
        with col3:
            contraparte = st.text_input("Counterparty", value=extracted.get("contraparte", ""))
            asset_class_opts = cfg.get("asset_classes") or cfg.DEFAULTS["asset_classes"]
            asset_class = st.selectbox("Asset Class", asset_class_opts)

        st.markdown("#### Classification")
        col4, col5, col6 = st.columns(3)
        with col4:
            vehicle_opts = cfg.get("vehicles") or cfg.DEFAULTS["vehicles"]
            vehiculo = st.selectbox("Vehicle", vehicle_opts)
            segment_opts = cfg.get("segments") or cfg.DEFAULTS["segments"]
            segmento = st.selectbox("Segment", segment_opts)
        with col5:
            country_opts = cfg.get("countries") or cfg.DEFAULTS["countries"]
            pais = st.selectbox("Country", country_opts)
            entity_opts = cfg.get("entities") or cfg.DEFAULTS["entities"]
            entidad = st.selectbox("Entity", entity_opts)
        with col6:
            client_opts = cfg.get("client_types") or cfg.DEFAULTS["client_types"]
            tipo_cliente = st.selectbox("Client Type", client_opts)
            profile_opts = cfg.get("profiles") or cfg.DEFAULTS["profiles"]
            perfil = st.selectbox("Risk Profile", profile_opts)

        juris_opts = cfg.get("jurisdictions") or cfg.DEFAULTS["jurisdictions"]
        jurisdiccion = st.selectbox("Jurisdiction", juris_opts)

        st.markdown("#### Amounts (USD)")
        ca, cb, cc, cd = st.columns(4)
        with ca:
            monto_peru = st.number_input("Peru", value=float(extracted.get("monto_peru") or 0), min_value=0.0, step=1000.0)
        with cb:
            monto_chile = st.number_input("Chile", value=float(extracted.get("monto_chile") or 0), min_value=0.0, step=1000.0)
        with cc:
            monto_colombia = st.number_input("Colombia", value=float(extracted.get("monto_colombia") or 0), min_value=0.0, step=1000.0)
        with cd:
            monto_usa = st.number_input("USA", value=float(extracted.get("monto_usa") or 0), min_value=0.0, step=1000.0)

        st.markdown("**Segment breakdown (USD)**")
        s1, s2, s3, s4 = st.columns(4)
        with s1:
            monto_bp_peru = st.number_input("BP Peru", value=0.0, min_value=0.0, step=1000.0)
            monto_bp_chile = st.number_input("BP Chile", value=0.0, min_value=0.0, step=1000.0)
            monto_bp_colombia = st.number_input("BP Colombia", value=0.0, min_value=0.0, step=1000.0)
        with s2:
            monto_bp_us = st.number_input("BP US", value=0.0, min_value=0.0, step=1000.0)
            monto_ria = st.number_input("RIA", value=0.0, min_value=0.0, step=1000.0)
            monto_w9 = st.number_input("W9", value=0.0, min_value=0.0, step=1000.0)
        with s3:
            monto_enalta = st.number_input("Enalta", value=0.0, min_value=0.0, step=1000.0)
            monto_bex = st.number_input("BEX", value=0.0, min_value=0.0, step=1000.0)
            monto_consumo = st.number_input("Consumo", value=0.0, min_value=0.0, step=1000.0)
        with s4:
            monto_juridicos = st.number_input("Juridicos", value=0.0, min_value=0.0, step=1000.0)
            monto_mfo = st.number_input("MFO", value=0.0, min_value=0.0, step=1000.0)
            monto_tyba = st.number_input("TYBA", value=0.0, min_value=0.0, step=1000.0)

        moneda = st.selectbox("Currency", ["USD", "EUR", "PEN", "CLP", "COP"], index=0)

        st.markdown("#### Dates")
        d1, d2, d3, d4 = st.columns(4)
        with d1:
            fecha_ejecucion = _date_input("Execution Date", extracted.get("fecha_ejecucion"), "fe")
        with d2:
            fecha_vencimiento = _date_input("Maturity Date", extracted.get("fecha_vencimiento"), "fv")
        with d3:
            fecha_pago_ts = _date_input("TS Payment Date", extracted.get("fecha_pago_ts"), "fp_ts")
        with d4:
            dias_habiles_pago = st.number_input(
                "Business Days to Client Payment",
                value=int(extracted.get("dias_habiles_pago") or 3),
                min_value=0, max_value=30, step=1,
                help="Business days added to TS payment date to get client payment date",
            )

        st.markdown("#### Underlyings")
        u1, u2, u3, u4 = st.columns(4)
        with u1:
            underlying_1 = st.text_input("Underlying 1", value=extracted.get("underlying_1", ""))
            strike_1 = st.number_input("Strike 1 (%)", value=float(extracted.get("strike_1") or 100.0), step=0.5)
        with u2:
            underlying_2 = st.text_input("Underlying 2", value=extracted.get("underlying_2", ""))
            strike_2 = st.number_input("Strike 2 (%)", value=float(extracted.get("strike_2") or 100.0), step=0.5)
        with u3:
            underlying_3 = st.text_input("Underlying 3", value=extracted.get("underlying_3", ""))
            strike_3 = st.number_input("Strike 3 (%)", value=float(extracted.get("strike_3") or 100.0), step=0.5)
        with u4:
            underlying_4 = st.text_input("Underlying 4", value=extracted.get("underlying_4", ""))
            strike_4 = st.number_input("Strike 4 (%)", value=float(extracted.get("strike_4") or 100.0), step=0.5)

        st.markdown("#### Structure")
        p1, p2, p3, p4 = st.columns(4)
        with p1:
            tipo_estructura = st.text_input("Strategy / Structure Type",
                                             value=extracted.get("tipo_estructura", ""))
            cupon_fijo = st.number_input("Fixed Coupon (%)", value=float(extracted.get("cupon_fijo") or 0.0), step=0.1)
        with p2:
            cupon_contingente = st.number_input("Contingent Coupon (%)",
                                                  value=float(extracted.get("cupon_contingente") or 0.0), step=0.1)
            ganancia_maxima = st.number_input("Max Gain (%)",
                                               value=float(extracted.get("ganancia_maxima") or 0.0), step=0.1)
        with p3:
            trigger_autocall = st.number_input("Autocall Trigger (%)",
                                                value=float(extracted.get("trigger_autocall") or 100.0), step=0.5)
            barrera_capital = st.number_input("Capital Barrier (%)",
                                               value=float(extracted.get("barrera_capital") or 70.0), step=0.5)
        with p4:
            plazo_meses = st.number_input("Term (months)",
                                            value=int(extracted.get("plazo_meses") or 0), min_value=0, step=1)
            frecuencia_obs = st.selectbox("Observation Frequency",
                                           ["Monthly", "Quarterly", "Semi-annual", "Annual", "At maturity"])

        st.markdown("#### Autocall Schedule")
        n_autocalls = st.number_input("Number of autocall dates", min_value=0, max_value=10, value=0, step=1)
        ac_dates = []
        if n_autocalls > 0:
            ac_cols = st.columns(min(int(n_autocalls), 5))
            for i in range(int(n_autocalls)):
                col_idx = i % 5
                with ac_cols[col_idx]:
                    ext_date = extracted.get(f"fecha_autocall_{i+1}")
                    d = _date_input(f"Autocall {i+1}", ext_date, f"ac_{i}")
                    ac_dates.append(d)

        submitted = st.form_submit_button("💾 Save Product", type="primary", use_container_width=True)

    if submitted:
        if not nombre_producto.strip():
            st.error("Product Name is required.")
        elif nombre_producto.strip() in existing_names:
            st.error(f"A product named '{nombre_producto}' already exists.")
        else:
            monto_total = monto_peru + monto_chile + monto_colombia + monto_usa

            record = {
                "nombre_producto": nombre_producto.strip(),
                "isin": isin,
                "tipo": tipo,
                "status": status,
                "contraparte": contraparte,
                "asset_class": asset_class,
                "vehiculo": vehiculo,
                "segmento": segmento,
                "pais": pais,
                "entidad": entidad,
                "tipo_cliente": tipo_cliente,
                "perfil": perfil,
                "jurisdiccion": jurisdiccion,
                "monto_total": monto_total,
                "monto_peru": monto_peru,
                "monto_chile": monto_chile,
                "monto_colombia": monto_colombia,
                "monto_usa": monto_usa,
                "monto_bp_peru": monto_bp_peru,
                "monto_bp_chile": monto_bp_chile,
                "monto_bp_colombia": monto_bp_colombia,
                "monto_bp_us": monto_bp_us,
                "monto_ria": monto_ria,
                "monto_w9": monto_w9,
                "monto_enalta": monto_enalta,
                "monto_bex": monto_bex,
                "monto_consumo": monto_consumo,
                "monto_juridicos": monto_juridicos,
                "monto_mfo": monto_mfo,
                "monto_tyba": monto_tyba,
                "moneda": moneda,
                "fecha_ejecucion": fecha_ejecucion.isoformat(),
                "fecha_vencimiento": fecha_vencimiento.isoformat(),
                "fecha_pago_ts": fecha_pago_ts.isoformat(),
                "dias_habiles_pago": int(dias_habiles_pago),
                "underlying_1": underlying_1 or None,
                "underlying_2": underlying_2 or None,
                "underlying_3": underlying_3 or None,
                "underlying_4": underlying_4 or None,
                "strike_1": strike_1 / 100 if underlying_1 else None,
                "strike_2": strike_2 / 100 if underlying_2 else None,
                "strike_3": strike_3 / 100 if underlying_3 else None,
                "strike_4": strike_4 / 100 if underlying_4 else None,
                "tipo_estructura": tipo_estructura,
                "cupon_fijo": cupon_fijo / 100,
                "cupon_contingente": cupon_contingente / 100,
                "ganancia_maxima": ganancia_maxima / 100,
                "trigger_autocall": trigger_autocall / 100,
                "barrera_capital": barrera_capital / 100,
                "plazo_meses": int(plazo_meses),
                "frecuencia_obs": frecuencia_obs,
            }

            for i, d in enumerate(ac_dates):
                record[f"fecha_autocall_{i+1}"] = d.isoformat()

            try:
                insert_product(record)
                st.success(f"Product '{nombre_producto}' saved successfully!")
                st.session_state["extracted"] = None
                st.rerun()
            except Exception as e:
                st.error(f"Failed to save product: {e}")
