import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, timedelta
from backend.database import get_all_products
import backend.config as cfg


def render():
    primary = cfg.get("primary_color") or "#003087"
    secondary = cfg.get("secondary_color") or "#E31837"

    st.subheader("Upcoming Maturities & Autocalls")

    df = get_all_products()
    if df.empty:
        st.warning("No products found.")
        return

    active = df[df["status"].isin(["VIGENTE", "POR EJECUTAR", "AUTOCALL"])].copy()

    today = pd.Timestamp.now().normalize()

    def parse_date(col):
        return pd.to_datetime(active[col], dayfirst=True, errors="coerce")

    active["_fecha_vcto"] = parse_date("fecha_vencimiento")
    active["_proximo_ac"] = parse_date("proximo_autocall")

    # Horizon filter
    col1, col2 = st.columns([2, 2])
    with col1:
        horizon = st.selectbox(
            "Horizon",
            options=[30, 60, 90, 180, 365, 9999],
            format_func=lambda x: "All" if x == 9999 else f"Next {x} days",
            index=2,
        )
    with col2:
        event_type = st.radio("Event Type", ["Both", "Maturities", "Autocalls"], horizontal=True)

    cutoff = today + timedelta(days=horizon)

    # --- MATURITIES ---
    maturities = active[
        (active["_fecha_vcto"] >= today) & (active["_fecha_vcto"] <= cutoff)
    ].copy()
    maturities["days_to_maturity"] = (maturities["_fecha_vcto"] - today).dt.days
    maturities = maturities.sort_values("days_to_maturity")

    # --- AUTOCALLS ---
    ac_cols = [f"fecha_autocall_{i}" for i in range(1, 11)]
    ac_rows = []
    for _, row in active.iterrows():
        for col in ac_cols:
            dt = pd.to_datetime(row.get(col), dayfirst=True, errors="coerce")
            if pd.notna(dt) and today <= dt <= cutoff:
                ac_rows.append({
                    "nombre_producto": row["nombre_producto"],
                    "status": row["status"],
                    "vehiculo": row["vehiculo"],
                    "monto_total": row["monto_total"],
                    "underlying_1": row.get("underlying_1"),
                    "underlying_2": row.get("underlying_2"),
                    "trigger_autocall": row.get("trigger_autocall"),
                    "autocall_date": dt,
                    "days_to_autocall": (dt - today).days,
                    "contraparte": row.get("contraparte"),
                })
                break  # only show next upcoming autocall per product

    autocalls = pd.DataFrame(ac_rows).sort_values("days_to_autocall") if ac_rows else pd.DataFrame()

    # KPIs
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Maturities in horizon", len(maturities))
    k2.metric("Autocall obs. in horizon", len(autocalls))
    aum_vcto = maturities["monto_total"].sum() if not maturities.empty else 0
    aum_ac = autocalls["monto_total"].sum() if not autocalls.empty else 0
    k3.metric("AUM at maturity", f"${aum_vcto/1e6:.1f}M" if aum_vcto >= 1e6 else f"${aum_vcto:,.0f}")
    k4.metric("AUM at autocall obs.", f"${aum_ac/1e6:.1f}M" if aum_ac >= 1e6 else f"${aum_ac:,.0f}")

    st.markdown("---")

    # Timeline chart
    timeline_rows = []
    if event_type in ("Both", "Maturities") and not maturities.empty:
        for _, r in maturities.iterrows():
            timeline_rows.append({
                "Product": r["nombre_producto"][:35],
                "Date": r["_fecha_vcto"],
                "Type": "Maturity",
                "AUM": r["monto_total"],
            })
    if event_type in ("Both", "Autocalls") and not autocalls.empty:
        for _, r in autocalls.iterrows():
            timeline_rows.append({
                "Product": r["nombre_producto"][:35],
                "Date": r["autocall_date"],
                "Type": "Autocall Obs.",
                "AUM": r["monto_total"],
            })

    if timeline_rows:
        tl_df = pd.DataFrame(timeline_rows).sort_values("Date")
        tl_df["Month"] = tl_df["Date"].dt.to_period("M").astype(str)
        monthly = tl_df.groupby(["Month", "Type"])["AUM"].sum().reset_index()

        fig = px.bar(
            monthly, x="Month", y="AUM", color="Type",
            color_discrete_map={"Maturity": primary, "Autocall Obs.": secondary},
            barmode="group",
            title="AUM by Event and Month",
        )
        fig.update_layout(height=300, margin=dict(t=30, b=0), xaxis_title="", yaxis_title="AUM (USD)")
        st.plotly_chart(fig, use_container_width=True)

    # Tables
    if event_type in ("Both", "Maturities") and not maturities.empty:
        st.markdown(f"### Maturities ({len(maturities)})")
        vcto_display = maturities[[
            "nombre_producto", "status", "vehiculo", "monto_total",
            "_fecha_vcto", "days_to_maturity", "underlying_1", "underlying_2",
            "rendimiento_total", "contraparte",
        ]].rename(columns={
            "nombre_producto": "Product",
            "status": "Status",
            "vehiculo": "Vehicle",
            "monto_total": "AUM (USD)",
            "_fecha_vcto": "Maturity Date",
            "days_to_maturity": "Days Left",
            "underlying_1": "U1",
            "underlying_2": "U2",
            "rendimiento_total": "Total Return",
            "contraparte": "Counterparty",
        })
        vcto_display["AUM (USD)"] = vcto_display["AUM (USD)"].apply(lambda x: f"${x:,.0f}" if pd.notna(x) else "")
        vcto_display["Total Return"] = vcto_display["Total Return"].apply(
            lambda x: f"{x*100:.2f}%" if pd.notna(x) and x != 0 else ""
        )
        st.dataframe(vcto_display, use_container_width=True, hide_index=True)

    if event_type in ("Both", "Autocalls") and not autocalls.empty:
        st.markdown(f"### Upcoming Autocall Observations ({len(autocalls)})")
        ac_display = autocalls[[
            "nombre_producto", "status", "vehiculo", "monto_total",
            "autocall_date", "days_to_autocall",
            "underlying_1", "underlying_2", "trigger_autocall", "contraparte",
        ]].rename(columns={
            "nombre_producto": "Product",
            "status": "Status",
            "vehiculo": "Vehicle",
            "monto_total": "AUM (USD)",
            "autocall_date": "Autocall Date",
            "days_to_autocall": "Days Left",
            "underlying_1": "U1",
            "underlying_2": "U2",
            "trigger_autocall": "Trigger",
            "contraparte": "Counterparty",
        })
        ac_display["AUM (USD)"] = ac_display["AUM (USD)"].apply(lambda x: f"${x:,.0f}" if pd.notna(x) else "")
        ac_display["Trigger"] = ac_display["Trigger"].apply(
            lambda x: f"{x*100:.0f}%" if pd.notna(x) and x != 0 else ""
        )
        st.dataframe(ac_display, use_container_width=True, hide_index=True)
