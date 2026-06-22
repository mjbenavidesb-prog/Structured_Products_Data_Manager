import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
from backend.database import get_all_products
import backend.config as cfg


def to_excel(dfs: dict) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for sheet_name, df in dfs.items():
            df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
    return output.getvalue()


def render():
    primary = cfg.get("primary_color") or "#003087"
    secondary = cfg.get("secondary_color") or "#E31837"

    st.subheader("Reports")

    df = get_all_products()
    if df.empty:
        st.warning("No products found.")
        return

    col_status, col_report = st.columns([2, 3])
    with col_status:
        status_filter = st.multiselect(
            "Status Filter",
            options=sorted(df["status"].dropna().unique()),
            default=[s for s in ["VIGENTE", "POR EJECUTAR", "AUTOCALL"] if s in df["status"].unique()],
        )

    if status_filter:
        filtered = df[df["status"].isin(status_filter)].copy()
    else:
        filtered = df.copy()

    with col_report:
        report_type = st.selectbox("Report Type", [
            "AUM by Country",
            "AUM by Vehicle",
            "AUM by Segment",
            "AUM by Strategy",
            "AUM by Asset Class",
            "AUM by Profile",
            "AUM by Counterparty",
            "Complete Portfolio",
        ])

    st.markdown("---")

    def make_aum_report(group_col, label_col, amount_cols):
        agg = {col: "sum" for col in amount_cols if col in filtered.columns}
        grp = filtered.groupby(group_col).agg({"monto_total": "sum", "nombre_producto": "count", **agg}).reset_index()
        grp.columns = [label_col, "Total AUM (USD)", "# Products"] + [
            c.replace("monto_", "AUM ").replace("_", " ").title()
            for c in amount_cols if c in filtered.columns
        ]
        grp = grp.sort_values("Total AUM (USD)", ascending=False)
        grp["% of Total"] = (grp["Total AUM (USD)"] / grp["Total AUM (USD)"].sum() * 100).round(2)
        return grp

    # --- AUM by Country ---
    if report_type == "AUM by Country":
        country_data = {
            "Peru": filtered["monto_peru"].sum(),
            "Chile": filtered["monto_chile"].sum(),
            "Colombia": filtered["monto_colombia"].sum(),
            "USA": filtered["monto_usa"].sum(),
        }
        report_df = pd.DataFrame([
            {"Country": k, "Total AUM (USD)": v,
             "% of Total": round(v / sum(country_data.values()) * 100, 2) if sum(country_data.values()) > 0 else 0}
            for k, v in country_data.items() if v > 0
        ]).sort_values("Total AUM (USD)", ascending=False)

        c1, c2 = st.columns(2)
        with c1:
            fig = px.pie(report_df, values="Total AUM (USD)", names="Country",
                         color_discrete_sequence=[primary, secondary, "#F5A623", "#28A745"])
            fig.update_layout(height=300, margin=dict(t=10, b=0))
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.dataframe(report_df.style.format({"Total AUM (USD)": "${:,.0f}", "% of Total": "{:.2f}%"}),
                         use_container_width=True, hide_index=True)
        excel_data = to_excel({"AUM by Country": report_df})

    # --- AUM by Vehicle ---
    elif report_type == "AUM by Vehicle":
        report_df = make_aum_report("vehiculo", "Vehicle", [])
        c1, c2 = st.columns(2)
        with c1:
            fig = px.bar(report_df.sort_values("Total AUM (USD)"), x="Total AUM (USD)", y="Vehicle",
                         orientation="h", color_discrete_sequence=[primary])
            fig.update_layout(height=350, margin=dict(t=10, b=0))
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.dataframe(report_df.style.format({"Total AUM (USD)": "${:,.0f}", "% of Total": "{:.2f}%"}),
                         use_container_width=True, hide_index=True)
        excel_data = to_excel({"AUM by Vehicle": report_df})

    # --- AUM by Segment ---
    elif report_type == "AUM by Segment":
        segment_cols = {
            "BP Peru": "monto_bp_peru", "BP Chile": "monto_bp_chile",
            "BP Colombia": "monto_bp_colombia", "BP US": "monto_bp_us",
            "RIA": "monto_ria", "W9": "monto_w9",
            "Enalta": "monto_enalta", "BEX": "monto_bex",
            "Consumo": "monto_consumo", "Juridicos": "monto_juridicos",
            "MFO": "monto_mfo", "TYBA": "monto_tyba",
        }
        seg_data = {k: filtered[v].sum() for k, v in segment_cols.items() if v in filtered.columns and filtered[v].sum() > 0}
        total = sum(seg_data.values())
        report_df = pd.DataFrame([
            {"Segment": k, "Total AUM (USD)": v, "% of Total": round(v / total * 100, 2) if total > 0 else 0}
            for k, v in seg_data.items()
        ]).sort_values("Total AUM (USD)", ascending=False)

        c1, c2 = st.columns(2)
        with c1:
            fig = px.bar(report_df.sort_values("Total AUM (USD)"), x="Total AUM (USD)", y="Segment",
                         orientation="h", color_discrete_sequence=[secondary])
            fig.update_layout(height=400, margin=dict(t=10, b=0))
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.dataframe(report_df.style.format({"Total AUM (USD)": "${:,.0f}", "% of Total": "{:.2f}%"}),
                         use_container_width=True, hide_index=True)
        excel_data = to_excel({"AUM by Segment": report_df})

    # --- AUM by Strategy ---
    elif report_type == "AUM by Strategy":
        report_df = make_aum_report("tipo_estructura", "Strategy", [])
        c1, c2 = st.columns(2)
        with c1:
            fig = px.pie(report_df, values="Total AUM (USD)", names="Strategy",
                         color_discrete_sequence=[primary, secondary, "#F5A623"])
            fig.update_layout(height=300, margin=dict(t=10, b=0))
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.dataframe(report_df.style.format({"Total AUM (USD)": "${:,.0f}", "% of Total": "{:.2f}%"}),
                         use_container_width=True, hide_index=True)
        excel_data = to_excel({"AUM by Strategy": report_df})

    # --- AUM by Asset Class ---
    elif report_type == "AUM by Asset Class":
        report_df = make_aum_report("asset_class", "Asset Class", [])
        c1, c2 = st.columns(2)
        with c1:
            fig = px.pie(report_df, values="Total AUM (USD)", names="Asset Class",
                         color_discrete_sequence=[primary, secondary, "#F5A623"])
            fig.update_layout(height=300, margin=dict(t=10, b=0))
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.dataframe(report_df.style.format({"Total AUM (USD)": "${:,.0f}", "% of Total": "{:.2f}%"}),
                         use_container_width=True, hide_index=True)
        excel_data = to_excel({"AUM by Asset Class": report_df})

    # --- AUM by Profile ---
    elif report_type == "AUM by Profile":
        order = ["Muy Conservador", "Conservador", "Moderado", "Agresivo"]
        report_df = make_aum_report("perfil", "Risk Profile", [])
        report_df["_order"] = report_df["Risk Profile"].map({v: i for i, v in enumerate(order)})
        report_df = report_df.sort_values("_order").drop(columns=["_order"])
        c1, c2 = st.columns(2)
        with c1:
            fig = px.bar(report_df, x="Risk Profile", y="Total AUM (USD)",
                         color_discrete_sequence=[primary])
            fig.update_layout(height=300, margin=dict(t=10, b=0))
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.dataframe(report_df.style.format({"Total AUM (USD)": "${:,.0f}", "% of Total": "{:.2f}%"}),
                         use_container_width=True, hide_index=True)
        excel_data = to_excel({"AUM by Profile": report_df})

    # --- AUM by Counterparty ---
    elif report_type == "AUM by Counterparty":
        report_df = make_aum_report("contraparte", "Counterparty", [])
        report_df = report_df[report_df["Counterparty"].notna() & (report_df["Counterparty"] != "None")]
        c1, c2 = st.columns(2)
        with c1:
            fig = px.bar(report_df.sort_values("Total AUM (USD)"), x="Total AUM (USD)", y="Counterparty",
                         orientation="h", color_discrete_sequence=[primary])
            fig.update_layout(height=350, margin=dict(t=10, b=0))
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.dataframe(report_df.style.format({"Total AUM (USD)": "${:,.0f}", "% of Total": "{:.2f}%"}),
                         use_container_width=True, hide_index=True)
        excel_data = to_excel({"AUM by Counterparty": report_df})

    # --- Complete Portfolio ---
    else:
        export_cols = [
            "nombre_producto", "tipo", "status", "vehiculo", "jurisdiccion",
            "entidad", "tipo_cliente", "monto_total", "monto_peru", "monto_chile",
            "monto_colombia", "monto_usa", "moneda", "fecha_ejecucion",
            "fecha_vencimiento", "fecha_pago_maximo", "underlying_1", "underlying_2",
            "underlying_3", "underlying_4", "strike_1", "strike_2", "strike_3", "strike_4",
            "spot_1", "spot_2", "spot_3", "spot_4", "rendimiento_total", "peor_subyacente",
            "tipo_estructura", "asset_class", "perfil", "cupon_fijo", "cupon_contingente",
            "ganancia_maxima", "trigger_autocall", "barrera_capital", "contraparte", "isin",
            "proximo_autocall", "plazo_remanente_dias",
        ]
        available = [c for c in export_cols if c in filtered.columns]
        report_df = filtered[available].copy()
        st.dataframe(report_df, use_container_width=True, height=450)
        all_sheets = {
            "Portfolio": report_df,
            "By Country": pd.DataFrame([{"Country": k, "AUM": filtered[v].sum()}
                                         for k, v in [("Peru","monto_peru"),("Chile","monto_chile"),
                                                       ("Colombia","monto_colombia"),("USA","monto_usa")]]),
            "By Vehicle": filtered.groupby("vehiculo")["monto_total"].sum().reset_index(),
        }
        excel_data = to_excel(all_sheets)

    # Download button
    st.markdown("---")
    st.download_button(
        label="⬇️ Download Excel Report",
        data=excel_data,
        file_name=f"report_{report_type.lower().replace(' ', '_')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
