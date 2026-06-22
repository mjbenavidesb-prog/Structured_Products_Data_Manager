import streamlit as st
import backend.config as cfg


def render():
    st.subheader("Settings")
    st.markdown("Configure your company branding and product classification lists.")

    tab_company, tab_lists = st.tabs(["Company", "Classification Lists"])

    with tab_company:
        st.markdown("#### Branding")
        col1, col2 = st.columns(2)
        with col1:
            company_name = st.text_input("Company Name", value=cfg.get("company_name") or "Credicorp Capital")
            primary_color = st.color_picker("Primary Color", value=cfg.get("primary_color") or "#003087")
            secondary_color = st.color_picker("Secondary Color", value=cfg.get("secondary_color") or "#E31837")
            accent_color = st.color_picker("Accent Color", value=cfg.get("accent_color") or "#F5A623")

        with col2:
            st.markdown("**Color Preview**")
            st.markdown(f"""
            <div style='display:flex; gap:12px; margin-top:8px;'>
                <div style='width:80px;height:80px;background:{primary_color};border-radius:8px;
                            display:flex;align-items:center;justify-content:center;color:white;
                            font-size:11px;font-weight:bold;'>Primary</div>
                <div style='width:80px;height:80px;background:{secondary_color};border-radius:8px;
                            display:flex;align-items:center;justify-content:center;color:white;
                            font-size:11px;font-weight:bold;'>Secondary</div>
                <div style='width:80px;height:80px;background:{accent_color};border-radius:8px;
                            display:flex;align-items:center;justify-content:center;color:white;
                            font-size:11px;font-weight:bold;'>Accent</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("#### API Configuration")
        current_key = cfg.get("claude_api_key") or ""
        api_key_display = current_key[:8] + "..." if len(current_key) > 8 else ""
        new_api_key = st.text_input(
            "Claude API Key",
            value="",
            type="password",
            placeholder=api_key_display or "sk-ant-...",
            help="Required for termsheet extraction. Stored locally only.",
        )

        if st.button("Save Company Settings", type="primary"):
            cfg.save("company_name", company_name)
            cfg.save("primary_color", primary_color)
            cfg.save("secondary_color", secondary_color)
            cfg.save("accent_color", accent_color)
            if new_api_key.strip():
                cfg.save("claude_api_key", new_api_key.strip())
            st.success("Company settings saved. Reload the app to apply colors.")

    with tab_lists:
        st.markdown("Edit the dropdown options available throughout the app. Enter one item per line.")

        def list_editor(label, config_key, default_values):
            current = cfg.get(config_key) or default_values
            if isinstance(current, list):
                current_text = "\n".join(current)
            else:
                current_text = str(current)
            edited = st.text_area(label, value=current_text, height=160, key=f"list_{config_key}")
            return [v.strip() for v in edited.splitlines() if v.strip()]

        col_a, col_b = st.columns(2)
        with col_a:
            vehicles = list_editor("Vehicles", "vehicles",
                cfg.DEFAULTS["vehicles"])
            segments = list_editor("Segments", "segments",
                cfg.DEFAULTS["segments"])
            asset_classes = list_editor("Asset Classes", "asset_classes",
                cfg.DEFAULTS["asset_classes"])

        with col_b:
            countries = list_editor("Countries", "countries",
                cfg.DEFAULTS["countries"])
            client_types = list_editor("Client Types", "client_types",
                cfg.DEFAULTS["client_types"])
            profiles = list_editor("Risk Profiles", "profiles",
                cfg.DEFAULTS["profiles"])

        col_c, col_d = st.columns(2)
        with col_c:
            entities = list_editor("Entities", "entities",
                cfg.DEFAULTS["entities"])
        with col_d:
            jurisdictions = list_editor("Jurisdictions", "jurisdictions",
                cfg.DEFAULTS["jurisdictions"])

        if st.button("Save Lists", type="primary"):
            cfg.save("vehicles", vehicles)
            cfg.save("segments", segments)
            cfg.save("asset_classes", asset_classes)
            cfg.save("countries", countries)
            cfg.save("client_types", client_types)
            cfg.save("profiles", profiles)
            cfg.save("entities", entities)
            cfg.save("jurisdictions", jurisdictions)
            st.success("Lists saved successfully.")
