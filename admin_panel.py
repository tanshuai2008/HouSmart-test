import streamlit as st
import time
from config_manager import config_manager

st.set_page_config(page_title="HouSmart Admin Panel", page_icon="⚙️", layout="centered")

st.title("⚙️ HouSmart Admin Panel")

# Load current config
config = config_manager.get_config()

with st.form("settings_form"):
    st.subheader("🤖 Model Settings")
    
    model_options = [
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite", 
        "gemini-2.0-flash", 
        "gemini-1.5-pro",
        "gemini-1.5-flash"
    ]
    
    # Handle case where current config model is not in options
    current_model = config.get("model_name", "gemini-2.5-flash")
    if current_model not in model_options:
         model_options.append(current_model)
    
    selected_model = st.selectbox(
        "Select Model",
        options=model_options,
        index=model_options.index(current_model)
    )

    temperature = st.slider(
        "Temperature",
        min_value=0.0,
        max_value=1.0,
        value=float(config.get("temperature", 0.7)),
        step=0.1,
        help="Higher values mean more creative/random responses."
    )

    st.subheader("🛠️ Feature Flags")
    
    customized_scoring_method = st.toggle(
        "Enable Customized Scoring Method",
        value=config.get("customized_scoring_method", False),
        help="If enabled, users can adjust scoring weights in the main app."
    )

    st.subheader("💾 Cache Settings")
    
    cache_ttl = st.number_input(
        "Cache TTL (Hours)",
        min_value=1,
        max_value=1000,
        value=int(config.get("cache_ttl_hours", 240)),
        step=1,
        help="How long to keep analysis results in cache."
    )

    submitted = st.form_submit_button("Save Changes", type="primary")

    if submitted:
        new_config = {
            "model_name": selected_model,
            "temperature": temperature,
            "customized_scoring_method": customized_scoring_method,
            "cache_ttl_hours": cache_ttl
        }
        
        if config_manager.save_config(new_config):
            st.success("Configuration saved successfully!")
            st.json(new_config)
            time.sleep(1) 
            st.rerun()
        else:
            st.error("Failed to save configuration.")

st.markdown("---")
st.caption("Changes take effect immediately in the main application.")
