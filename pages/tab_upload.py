import streamlit as st
from datetime import date, datetime
import backend.config as cfg
from backend.database import insert_product, get_all_products
from backend.extractor import extract_termsheet


def _to_date(val) -> date:
    """Parse various date string formats gracefully."""
    if not val:
        return date.today()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%b-%y", "%d-%b-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(str(val), fmt).date()
        except ValueError:
            continue
    return date.today()


def _date_field(label: str, default=None, key: str = None):
    return st.date_input(label, value=_to_date(default), key=key)


def render():
    st.subheader("Load Product")

    # ── Step 1: Upload & Extract ──────────────────────────────────────────────
    st.markdown("### Step 1 — Upload Termsheet PDF")
    api_key = cfg.get("claude_api_key") or ""

    if not api_key:
        st.warning("Claude API key not set. Go to ⚙️ Settings to add it first.")

    uploaded = st.file_uploader("Upload termsheet PDF", type=["pdf"])

    if "extracted" not in st.session_state:
        st.session_state["extracted"] = None

    if uploaded is not None and api_key:
        if st.button("Extract Data with Claude", type="primary"):
            with st.spinner("Reading termsheet with Claude AI..."):
                try:
                    result = extract_termsheet(uploaded.read(), api_key)
                    st.session_state["extracted"] = result
                    st.success("Extraction complete. Review the fields below.")
                except Exception as e:
                    st.error(f"Extraction failed: {e}")

    extracted = st.session_state.get("extracted") or {}

    if extracted:
        with st.expander("Raw extracted JSON", expanded=False):
            st.json(extracted)

    # ── Step 2: Product Form ──────────────────────────────────────────────────
    st.markdown("### Step 2 — Complete Product Information")
    existing = get_all_products()
    existing_names = existing["nombre_producto"].dropna().tolist() if not existing.empty else []

    # Use guarantor as primary counterparty (e.g. "BNP Paribas" not the SPV)
    default_cpty = extracted.get("garante") or extracted.get("contraparte") or ""
    default_issuer = extracted.get("contraparte") or ""

    with st.form("product_form"):
        st.markdown("#### Identity")
        col1, col2, col3 = st.columns(3)
        with col1:
            nombre_producto = st.text_input(
                "Product Name *",
                value=extracted.get("nombre_producto", ""),
                help="Internal commercial name (e.g. 'Phoenix WO RTY-SPX 80% Jun26')",
            )
            isin = st.text_input("ISIN", value=extracted.get("isin", "") or extracted.get("cusip", ""))
        with col2:
            tipo_opts = ["Note", "Certificate", "Warrant", "Bond", "Option", "Swap", "Other"]
            extracted_tipo = extracted.get("tipo", "Note")
            tipo_idx = tipo_opts.index(extracted_tipo) if extracted_tipo in tipo_opts else 0
            tipo = st.selectbox("Instrument Type", tipo_opts, index=tipo_idx)
            status_options = ["VIGENTE", "POR EJECUTAR", "AUTOCALL", "VENCIDO", "EJECUTADO", "CANCELADO"]
            status = st.selectbox("Status", status_options, index=1)
        with col3:
            contraparte = st.text_input(
                "Counterparty (Guarantor)",
                value=default_cpty,
                help="Main bank guaranteeing the product (e.g. BNP Paribas, BBVA)",
            )
            contraparte_derivado = st.text_input(
                "Issuer Entity",
                value=default_issuer,
                help="Legal issuer / SPV name (e.g. BNP Paribas Issuance B.V.)",
            )

        st.markdown("#### Classification")
        col4, col5, col6 = st.columns(3)
        with col4:
            asset_class_opts = cfg.get("asset_classes") or cfg.DEFAULTS["asset_classes"]
            ac_default = extracted.get("asset_class", asset_class_opts[0])
            ac_idx = asset_class_opts.index(ac_default) if ac_default in asset_class_opts else 0
            asset_class = st.selectbox("Asset Class", asset_class_opts, index=ac_idx)
            profile_opts = cfg.get("profiles") or cfg.DEFAULTS["profiles"]
            p_default = extracted.get("perfil", profile_opts[0])
            p_idx = profile_opts.index(p_default) if p_default in profile_opts else 0
            perfil = st.selectbox("Risk Profile", profile_opts, index=p_idx)
        with col5:
            vehicle_opts = cfg.get("vehicles") or cfg.DEFAULTS["vehicles"]
            vehiculo = st.selectbox("Vehicle", vehicle_opts)
            entity_opts = cfg.get("entities") or cfg.DEFAULTS["entities"]
            entidad = st.selectbox("Entity", entity_opts)
        with col6:
            juris_opts = cfg.get("jurisdictions") or cfg.DEFAULTS["jurisdictions"]
            jurisdiccion = st.selectbox("Jurisdiction", juris_opts)
            client_opts = cfg.get("client_types") or cfg.DEFAULTS["client_types"]
            tipo_cliente = st.selectbox("Client Type", client_opts)

        st.markdown("#### Amounts")
        total_issue = float(extracted.get("monto_total") or 0)
        moneda = st.selectbox(
            "Currency",
            ["USD", "EUR", "GBP", "PEN", "CLP", "COP"],
            index=0 if not extracted.get("moneda") else
            (["USD", "EUR", "GBP", "PEN", "CLP", "COP"].index(extracted["moneda"])
             if extracted.get("moneda") in ["USD", "EUR", "GBP", "PEN", "CLP", "COP"] else 0),
        )
        ca, cb, cc, cd = st.columns(4)
        with ca:
            monto_peru = st.number_input("Peru", value=0.0, min_value=0.0, step=10000.0)
        with cb:
            monto_chile = st.number_input("Chile", value=0.0, min_value=0.0, step=10000.0)
        with cc:
            monto_colombia = st.number_input("Colombia", value=0.0, min_value=0.0, step=10000.0)
        with cd:
            monto_usa = st.number_input("USA", value=0.0, min_value=0.0, step=10000.0)

        if total_issue > 0:
            st.caption(f"Issue amount from termsheet: **{moneda} {total_issue:,.0f}**")

        st.markdown("**Segment breakdown**")
        s1, s2, s3, s4 = st.columns(4)
        with s1:
            monto_bp_peru = st.number_input("BP Peru", value=0.0, min_value=0.0, step=10000.0)
            monto_bp_chile = st.number_input("BP Chile", value=0.0, min_value=0.0, step=10000.0)
        with s2:
            monto_bp_colombia = st.number_input("BP Colombia", value=0.0, min_value=0.0, step=10000.0)
            monto_bp_us = st.number_input("BP US", value=0.0, min_value=0.0, step=10000.0)
        with s3:
            monto_ria = st.number_input("RIA", value=0.0, min_value=0.0, step=10000.0)
            monto_w9 = st.number_input("W9", value=0.0, min_value=0.0, step=10000.0)
            monto_enalta = st.number_input("Enalta", value=0.0, min_value=0.0, step=10000.0)
        with s4:
            monto_bex = st.number_input("BEX", value=0.0, min_value=0.0, step=10000.0)
            monto_mfo = st.number_input("MFO", value=0.0, min_value=0.0, step=10000.0)
            monto_tyba = st.number_input("TYBA", value=0.0, min_value=0.0, step=10000.0)

        st.markdown("#### Dates")
        d1, d2, d3, d4 = st.columns(4)
        with d1:
            fecha_inicio = _date_field("Trade / Strike Date", extracted.get("fecha_inicio") or extracted.get("fecha_strike"), "fd_ini")
        with d2:
            fecha_emision = _date_field("Issue Date", extracted.get("fecha_emision"), "fd_em")
        with d3:
            fecha_obs_final = _date_field("Final Obs. Date", extracted.get("fecha_obs_final"), "fd_obs")
        with d4:
            fecha_vencimiento = _date_field("Maturity / Settlement", extracted.get("fecha_vencimiento"), "fd_vcto")

        d5, d6 = st.columns([1, 3])
        with d5:
            dias_habiles_pago = st.number_input(
                "Business Days to Client Payment",
                value=int(extracted.get("dias_habiles_pago") or cfg.get("business_days_payment") or 3),
                min_value=0, max_value=30, step=1,
                help="Added to settlement date to determine client payment date",
            )

        st.markdown("#### Underlyings")
        st.caption("Enter Bloomberg ticker codes (e.g. SPX, RTY, AMZN, META). Initial Level = index/stock value on strike date.")
        u1, u2, u3, u4 = st.columns(4)
        with u1:
            underlying_1 = st.text_input("Underlying 1 (Bloomberg)", value=extracted.get("underlying_1", ""))
            strike_1 = st.number_input(
                "Initial Level 1",
                value=float(extracted.get("strike_1") or 0.0),
                min_value=0.0, step=1.0,
                help="Actual index/stock level on strike date (not percentage)",
            )
        with u2:
            underlying_2 = st.text_input("Underlying 2", value=extracted.get("underlying_2", "") or "")
            strike_2 = st.number_input("Initial Level 2", value=float(extracted.get("strike_2") or 0.0), min_value=0.0, step=1.0)
        with u3:
            underlying_3 = st.text_input("Underlying 3", value=extracted.get("underlying_3", "") or "")
            strike_3 = st.number_input("Initial Level 3", value=float(extracted.get("strike_3") or 0.0), min_value=0.0, step=1.0)
        with u4:
            underlying_4 = st.text_input("Underlying 4", value=extracted.get("underlying_4", "") or "")
            strike_4 = st.number_input("Initial Level 4", value=float(extracted.get("strike_4") or 0.0), min_value=0.0, step=1.0)

        fmt_sub = extracted.get("formato_subyacente", "Worst of")
        fmt_opts = ["Worst of", "Individual", "Basket"]
        fmt_idx = fmt_opts.index(fmt_sub) if fmt_sub in fmt_opts else 0
        formato_subyacente = st.selectbox("Underlying Structure", fmt_opts, index=fmt_idx)

        st.markdown("#### Structure Parameters")
        p1, p2, p3, p4 = st.columns(4)
        with p1:
            cupon_fijo_pct = float((extracted.get("cupon_fijo") or 0.0))
            if cupon_fijo_pct > 1:
                cupon_fijo_pct /= 100
            cupon_fijo = st.number_input(
                "Fixed Coupon (annual %)",
                value=round(cupon_fijo_pct * 100, 4),
                min_value=0.0, max_value=100.0, step=0.01,
            )
            cc_pct = float((extracted.get("cupon_contingente") or 0.0))
            if cc_pct > 1:
                cc_pct /= 100
            cupon_contingente = st.number_input(
                "Contingent Coupon (annual %)",
                value=round(cc_pct * 100, 4),
                min_value=0.0, max_value=100.0, step=0.01,
            )
        with p2:
            bc_pct = float((extracted.get("barrera_cupon") or 0.0))
            if bc_pct > 1:
                bc_pct /= 100
            barrera_cupon = st.number_input(
                "Coupon Barrier (%)",
                value=round(bc_pct * 100, 2) or 80.0,
                min_value=0.0, max_value=150.0, step=1.0,
            )
            bk_pct = float((extracted.get("barrera_capital") or 0.0))
            if bk_pct > 1:
                bk_pct /= 100
            barrera_capital = st.number_input(
                "Capital Barrier / KI (%)",
                value=round(bk_pct * 100, 2) or 70.0,
                min_value=0.0, max_value=150.0, step=1.0,
            )
        with p3:
            tac_pct = float((extracted.get("trigger_autocall") or 1.0))
            if tac_pct > 1:
                tac_pct /= 100
            trigger_autocall = st.number_input(
                "Autocall Trigger (%)",
                value=round(tac_pct * 100, 2) or 100.0,
                min_value=0.0, max_value=200.0, step=1.0,
            )
            cap_pct = float((extracted.get("cap") or 0.0))
            if cap_pct > 1:
                cap_pct /= 100
            cap = st.number_input(
                "Cap (%)",
                value=round(cap_pct * 100, 2),
                min_value=0.0, max_value=500.0, step=0.5,
            )
        with p4:
            plazo_meses = st.number_input("Term (months)", value=int(extracted.get("plazo_meses") or 0), min_value=0, step=1)
            ganancia_maxima = st.text_input("Max Gain", value=extracted.get("ganancia_maxima") or "")

        tipo_caida_opts = ["Knock In", "Low Strike", "Put Spread", "None"]
        tc_default = extracted.get("tipo_caida", "Knock In")
        tc_idx = tipo_caida_opts.index(tc_default) if tc_default in tipo_caida_opts else 0
        tipo_caida = st.selectbox("Downside Type", tipo_caida_opts, index=tc_idx)

        st.markdown("#### Autocall Schedule")
        n_autocalls = st.number_input(
            "Number of autocall observation dates",
            min_value=0, max_value=10, value=0, step=1,
        )
        ac_dates = []
        if n_autocalls > 0:
            ac_cols_ui = st.columns(min(int(n_autocalls), 5))
            for i in range(int(n_autocalls)):
                with ac_cols_ui[i % 5]:
                    ext_date = extracted.get(f"fecha_autocall_{i+1}")
                    d = _date_field(f"Autocall {i+1}", ext_date, f"ac_{i}")
                    ac_dates.append(d)

        submitted = st.form_submit_button("Save Product", type="primary", use_container_width=True)

    if submitted:
        if not nombre_producto.strip():
            st.error("Product Name is required.")
        elif nombre_producto.strip() in existing_names:
            st.error(f"A product named '{nombre_producto}' already exists.")
        else:
            monto_total = monto_peru + monto_chile + monto_colombia + monto_usa

            record = {
                "nombre_producto": nombre_producto.strip(),
                "isin": isin or None,
                "tipo": tipo,
                "status": status,
                "contraparte": contraparte or None,
                "contraparte_derivado": contraparte_derivado or None,
                "asset_class": asset_class,
                "vehiculo": vehiculo,
                "entidad": entidad,
                "tipo_cliente": tipo_cliente,
                "perfil": perfil,
                "jurisdiccion": jurisdiccion,
                "moneda": moneda,
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
                "monto_mfo": monto_mfo,
                "monto_tyba": monto_tyba,
                "fecha_inicio": fecha_inicio.isoformat(),
                "fecha_emision": fecha_emision.isoformat(),
                "fecha_strike": fecha_inicio.isoformat(),
                "fecha_obs_final": fecha_obs_final.isoformat(),
                "fecha_vencimiento": fecha_vencimiento.isoformat(),
                "fecha_pago_maximo": fecha_vencimiento.isoformat(),
                "dias_habiles_pago": int(dias_habiles_pago),
                "underlying_1": underlying_1 or None,
                "underlying_2": underlying_2 or None,
                "underlying_3": underlying_3 or None,
                "underlying_4": underlying_4 or None,
                "strike_1": strike_1 if underlying_1 and strike_1 > 0 else None,
                "strike_2": strike_2 if underlying_2 and strike_2 > 0 else None,
                "strike_3": strike_3 if underlying_3 and strike_3 > 0 else None,
                "strike_4": strike_4 if underlying_4 and strike_4 > 0 else None,
                "formato_subyacente": formato_subyacente,
                "cupon_fijo": cupon_fijo / 100,
                "cupon_contingente": cupon_contingente / 100,
                "barrera_cupon": barrera_cupon / 100,
                "barrera_capital": barrera_capital / 100,
                "trigger_autocall": trigger_autocall / 100,
                "cap": cap / 100 if cap > 0 else None,
                "plazo_meses": int(plazo_meses),
                "ganancia_maxima": ganancia_maxima or None,
                "tipo_caida": tipo_caida,
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
