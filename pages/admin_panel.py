import streamlit as st
import time
from config_manager import config_manager

st.set_page_config(page_title="HouSmart Admin Panel", page_icon="⚙️", layout="centered")

st.title("⚙️ HouSmart Admin Panel")

# --- Password Protection ---
# Default password is "housmart_admin" if not set in secrets
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "housmart_admin")

if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

if not st.session_state.admin_authenticated:
    pwd_input = st.text_input("Enter Admin Password", type="password")
    if st.button("Login"):
        if pwd_input == ADMIN_PASSWORD:
            st.session_state.admin_authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop() # Stop execution if not authenticated

# --- Admin Content Below ---

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

    st.subheader("🔌 API Management")
    st.caption("Enable or disable external API calls. Disabling APIs will limit functionality.")
    
    col_api1, col_api2 = st.columns(2)
    
    with col_api1:
        enable_geoapify = st.toggle(
            "Enable Geoapify (Maps/POI)",
            value=config.get("enable_geoapify", True),
            help="Required for geocoding addresses and finding nearby places."
        )
        
        enable_rentcast = st.toggle(
            "Enable RentCast (Rentals)",
            value=config.get("enable_rentcast", True),
            help="Fetches rental estimates and comparables."
        )

    with col_api2:
        enable_census = st.toggle(
            "Enable Census API",
            value=config.get("enable_census", True),
            help="Fetches demographic data (Income, Age, etc.)."
        )
        
        enable_llm = st.toggle(
            "Enable Gemini AI (LLM)",
            value=config.get("enable_llm", True),
            help="Generates the AI score and investment analysis."
        )

    st.subheader("🛠️ Feature Flags")
    
    customized_scoring_method = st.toggle(
        "Enable Customized Scoring Method",
        value=config.get("customized_scoring_method", False),
        help="If enabled, users can adjust scoring weights in the main app."
    )

    st.subheader("🛡️ User Restrictions")
    
    enable_daily_limit = st.toggle(
        "Enable Daily Usage Limit (3 Queries/Day)",
        value=config.get("enable_daily_limit", True),
        help="If disabled, users can query unlimited times."
    )
    
    # Whitelist input
    current_whitelist = config.get("whitelist_emails", [])
    whitelist_str = "\n".join(current_whitelist)
    
    whitelist_input = st.text_area(
        "Whitelist Emails (Unlimited Access)",
        value=whitelist_str,
        help="Enter emails separated by commmas or newlines. These users will bypass the daily limit."
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
        # Process whitelist
        # Split by comma or newline, strip whitespace, remove empty
        raw_list = whitelist_input.replace(",", "\n").split("\n")
        final_whitelist = [x.strip().lower() for x in raw_list if x.strip()]
        
        new_config = {
            "model_name": selected_model,
            "temperature": temperature,
            "customized_scoring_method": customized_scoring_method,
            "cache_ttl_hours": cache_ttl,
            "enable_daily_limit": enable_daily_limit,
            "whitelist_emails": final_whitelist,
            "enable_geoapify": enable_geoapify,
            "enable_rentcast": enable_rentcast,
            "enable_census": enable_census,
            "enable_llm": enable_llm
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
