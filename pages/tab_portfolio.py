import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from backend.database import get_all_products, update_spots, save_aum_snapshot, get_aum_history
from backend.market_data import refresh_product_spots
import backend.config as cfg


def fmt_usd(val):
    if pd.isna(val) or val == 0:
        return "$0"
    if abs(val) >= 1_000_000:
        return f"${val/1_000_000:.1f}M"
    if abs(val) >= 1_000:
        return f"${val/1_000:.0f}K"
    return f"${val:,.0f}"


def render():
    primary = cfg.get("primary_color") or "#003087"
    secondary = cfg.get("secondary_color") or "#E31837"

    st.subheader("Portfolio Overview")

    # Load data
    df = get_all_products()
    if df.empty:
        st.warning("No products found. Load products first.")
        return

    # Status filter
    all_statuses = sorted(df["status"].dropna().unique().tolist())
    col_f1, col_f2, col_f3 = st.columns([2, 2, 1])
    with col_f1:
        selected_statuses = st.multiselect(
            "Filter by Status",
            options=all_statuses,
            default=[s for s in ["VIGENTE", "POR EJECUTAR", "AUTOCALL"] if s in all_statuses],
        )
    with col_f2:
        selected_vehicle = st.multiselect(
            "Filter by Vehicle",
            options=sorted(df["vehiculo"].dropna().unique().tolist()),
        )
    with col_f3:
        if st.button("🔄 Refresh Prices", use_container_width=True):
            with st.spinner("Fetching live prices..."):
                updates = refresh_product_spots(df)
                update_spots(updates)
                save_aum_snapshot()
                st.success(f"Updated {len(updates)} products")
                st.rerun()

    # Apply filters
    filtered = df.copy()
    if selected_statuses:
        filtered = filtered[filtered["status"].isin(selected_statuses)]
    if selected_vehicle:
        filtered = filtered[filtered["vehiculo"].isin(selected_vehicle)]

    active = filtered[filtered["status"].isin(["VIGENTE", "POR EJECUTAR", "AUTOCALL"])]

    # KPI cards
    st.markdown("---")
    k1, k2, k3, k4, k5 = st.columns(5)
    total_aum = active["monto_total"].sum()
    k1.metric("Total AUM", fmt_usd(total_aum))
    k2.metric("Active Products", len(active))
    k3.metric("Pending Execution", len(active[active["status"] == "POR EJECUTAR"]))
    k4.metric("Pending Autocall", len(active[active["status"] == "AUTOCALL"]))
    k5.metric("Maturing Soon (≤30d)", len(
        active[pd.to_datetime(active["fecha_vencimiento"], dayfirst=True, errors="coerce") <=
               pd.Timestamp.now() + pd.Timedelta(days=30)]
    ))

    st.markdown("---")

    # Charts row 1
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("**AUM by Country**")
        country_data = {
            "Peru": active["monto_peru"].sum(),
            "Chile": active["monto_chile"].sum(),
            "Colombia": active["monto_colombia"].sum(),
            "USA": active["monto_usa"].sum(),
        }
        country_df = pd.DataFrame(list(country_data.items()), columns=["Country", "AUM"])
        country_df = country_df[country_df["AUM"] > 0]
        if not country_df.empty:
            fig = px.pie(country_df, values="AUM", names="Country",
                         color_discrete_sequence=[primary, secondary, "#F5A623", "#28A745"])
            fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=280)
            st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown("**AUM by Vehicle**")
        veh_df = active.groupby("vehiculo")["monto_total"].sum().reset_index()
        veh_df.columns = ["Vehicle", "AUM"]
        veh_df = veh_df[veh_df["AUM"] > 0].sort_values("AUM", ascending=True)
        if not veh_df.empty:
            fig = px.bar(veh_df, x="AUM", y="Vehicle", orientation="h",
                         color_discrete_sequence=[primary])
            fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=280,
                               xaxis_title="AUM (USD)", yaxis_title="")
            st.plotly_chart(fig, use_container_width=True)

    # Charts row 2
    c3, c4 = st.columns(2)

    with c3:
        st.markdown("**AUM by Asset Class**")
        ac_df = active.groupby("asset_class")["monto_total"].sum().reset_index()
        ac_df.columns = ["Asset Class", "AUM"]
        ac_df = ac_df[ac_df["AUM"] > 0]
        if not ac_df.empty:
            fig = px.pie(ac_df, values="AUM", names="Asset Class",
                         color_discrete_sequence=[primary, secondary, "#F5A623"])
            fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=260)
            st.plotly_chart(fig, use_container_width=True)

    with c4:
        st.markdown("**AUM by Segment**")
        segment_cols = {
            "BP Peru": "monto_bp_peru", "BP Chile": "monto_bp_chile",
            "BP Colombia": "monto_bp_colombia", "BP US": "monto_bp_us",
            "RIA": "monto_ria", "W9": "monto_w9",
            "Enalta": "monto_enalta", "BEX": "monto_bex",
            "Consumo": "monto_consumo", "Juridicos": "monto_juridicos",
            "MFO": "monto_mfo", "TYBA": "monto_tyba",
        }
        seg_data = {k: active[v].sum() for k, v in segment_cols.items() if v in active.columns}
        seg_df = pd.DataFrame(list(seg_data.items()), columns=["Segment", "AUM"])
        seg_df = seg_df[seg_df["AUM"] > 0].sort_values("AUM", ascending=True)
        if not seg_df.empty:
            fig = px.bar(seg_df, x="AUM", y="Segment", orientation="h",
                         color_discrete_sequence=[secondary])
            fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=260,
                               xaxis_title="AUM (USD)", yaxis_title="")
            st.plotly_chart(fig, use_container_width=True)

    # AUM history chart
    history = get_aum_history()
    if not history.empty and len(history) > 1:
        st.markdown("**AUM Historical Evolution**")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=history["fecha"], y=history["monto_total"],
            mode="lines+markers", name="Total AUM",
            line=dict(color=primary, width=2),
        ))
        fig.update_layout(height=220, margin=dict(t=10, b=10, l=0, r=0),
                           xaxis_title="Date", yaxis_title="AUM (USD)")
        st.plotly_chart(fig, use_container_width=True)

    # Products table
    st.markdown("---")
    st.markdown("**Product List**")

    display_cols = {
        "nombre_producto": "Product Name",
        "tipo": "Type",
        "status": "Status",
        "vehiculo": "Vehicle",
        "monto_total": "Total AUM",
        "moneda": "Currency",
        "underlying_1": "U1",
        "underlying_2": "U2",
        "spot_1": "Spot 1",
        "spot_2": "Spot 2",
        "rendimiento_total": "Return",
        "fecha_vencimiento": "Maturity",
        "proximo_autocall": "Next Autocall",
        "plazo_remanente_dias": "Days Left",
        "contraparte": "Counterparty",
        "perfil": "Profile",
    }

    available = {k: v for k, v in display_cols.items() if k in filtered.columns}
    tbl = filtered[list(available.keys())].rename(columns=available).copy()
    tbl["Total AUM"] = tbl["Total AUM"].apply(lambda x: fmt_usd(x) if pd.notna(x) else "")
    if "Return" in tbl.columns:
        tbl["Return"] = tbl["Return"].apply(
            lambda x: f"{x*100:.2f}%" if pd.notna(x) and x != 0 else ""
        )

    st.dataframe(tbl, use_container_width=True, height=400)
