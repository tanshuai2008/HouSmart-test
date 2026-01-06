import streamlit as st
import os
import csv
import datetime
from datetime import timedelta
from dotenv import load_dotenv
import pandas as pd
import altair as alt
from streamlit_folium import st_folium
import gspread
from google.oauth2.service_account import Credentials

import data
import llm
import map
import components
import state_data

# Load environment variables
load_dotenv()

st.set_page_config(page_title="HouSmart: AI Location Intelligence", layout="wide", page_icon="🏠")

# Initialize Session State
if "analyzed" not in st.session_state:
    st.session_state.analyzed = False
if "analysis" not in st.session_state:
    st.session_state.analysis = {}
if "census" not in st.session_state:
    st.session_state.census = {}
if "pois" not in st.session_state:
    st.session_state.pois = []
if "rent_data" not in st.session_state:
    st.session_state.rent_data = {}
if "lat" not in st.session_state:
    st.session_state.lat = 0.0
if "lon" not in st.session_state:
    st.session_state.lon = 0.0
if "target_address" not in st.session_state:
    st.session_state.target_address = ""
if "log_status" not in st.session_state:
    st.session_state.log_status = []
if "processing" not in st.session_state:
    st.session_state.processing = False

# Inject CSS
st.markdown(components.get_base_css(), unsafe_allow_html=True)

# Render Header
components.render_header()

# --- Helper Functions ---
def connect_to_gsheet():
    try:
        if "gcp_service_account" not in st.secrets:
            return None
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        sheet_name = st.secrets.get("GSHEET_NAME", "HouSmart_Logs")
        sheet = client.open(sheet_name).sheet1
        return sheet
    except Exception as e:
        print(f"GSheet Connect Error: {e}")
        return None

def get_daily_usage(email):
    count = 0
    now = datetime.datetime.now()
    cutoff = now - timedelta(hours=24)
    email_clean = email.strip().lower()

    # Try GSheets
    sheet = connect_to_gsheet()
    if sheet:
        try:
            records = sheet.get_all_values()
            for row in records[1:]:
                if len(row) < 2: continue
                ts_str, row_email = row[0], row[1]
                if row_email.strip().lower() == email_clean:
                    try:
                        ts = datetime.datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                        if ts > cutoff: count += 1
                    except: pass
            return count
        except: pass

    # Fallback CSV
    log_file = os.path.join("logs", "usage_logs.csv")
    if not os.path.isfile(log_file): return 0
    try:
        with open(log_file, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if len(row) < 2: continue
                ts_str, row_email = row[0], row[1]
                if row_email.strip().lower() == email_clean:
                    try:
                        ts = datetime.datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                        if ts > cutoff: count += 1
                    except: pass
    except: pass
    return count

factors = ["Amenities", "Transit", "Schools", "Crime", "Appreciation"]

def update_weights(changed_factor):
    """
    Callback to normalize weights when one slider changes.
    Applies the logic: New Value + Locks + Others = 100.
    """
    # 1. Get the new value of the changed factor
    new_val = st.session_state[f"w_{changed_factor}"]
    
    # 2. Calculate the sum of LOCKED factors (excluding the changed one, even if it was locked, 
    # though UI shouldn't allow changing locked ones)
    locked_factors = [f for f in factors if st.session_state.get(f"lock_{f}", False) and f != changed_factor]
    locked_sum = sum(st.session_state[f"w_{f}"] for f in locked_factors)
    
    # 3. Calculate what is available for the UNLOCKED factors (excluding changed one)
    # Target total is 100
    available_for_others = 100 - new_val - locked_sum
    
    # 4. Identify other UNLOCKED factors
    other_unlocked = [f for f in factors if not st.session_state.get(f"lock_{f}", False) and f != changed_factor]
    
    # 5. Handle Constraints
    if available_for_others < 0:
        # We exceeded 100 using just New Val + Locks. 
        # Cap the New Val to fit.
        new_val = 100 - locked_sum
        st.session_state[f"w_{changed_factor}"] = new_val
        available_for_others = 0
    
    if not other_unlocked:
        # No other unlocked factors to absorb the change.
        # If we stick to strict 100, we might force the changed one to conform?
        # Or if "Strict 100" is the rule, then a single unlocked slider is effectively locked to the remainder.
        # Let's enforce Strict 100.
        remainder = 100 - locked_sum
        st.session_state[f"w_{changed_factor}"] = remainder
        return

    # 6. Distribute available weight proportional to current values of other unlocked factors
    current_sum_others = sum(st.session_state[f"w_{f}"] for f in other_unlocked)
    
    if current_sum_others == 0:
        # If all others were 0, distribute evenly
        share = available_for_others / len(other_unlocked)
        for f in other_unlocked:
            st.session_state[f"w_{f}"] = share
    else:
        # Proportional distribution
        ratio = available_for_others / current_sum_others
        for f in other_unlocked:
            st.session_state[f"w_{f}"] = st.session_state[f"w_{f}"] * ratio

def run_analysis_flow():
    st.session_state.processing = True
    st.session_state.analyzed = False

# --- Main Layout ---
c_left, c_mid, c_right = st.columns([20, 40, 40], gap="medium")

# ==========================================
# LEFT COLUMN: CONTROLS (20%)
# ==========================================
with c_left:
    st.markdown('<div class="panel-container">', unsafe_allow_html=True)
    
    st.markdown('<div class="panel-container">', unsafe_allow_html=True)
    
    # --- Email Input (Required) ---
    st.markdown(
        """
        <div style="border: 2px solid #EA4335; padding: 12px; border-radius: 6px; margin-bottom: 20px; background-color: #FEF7F6;">
            <div style="color: #EA4335; font-size: 12px; font-weight: 600; margin-bottom: 4px;">REQUIRED</div>
        </div>
        """, 
        unsafe_allow_html=True
    )
    # Rendering text input inside the red box via negative margin or just placing it below?
    # Streamlit widgets can't be easily nested in HTML divs. 
    # Workaround: Render the label/box visual, then the input.
    # User asked for "Use Red Box as reminder".
    # Let's try to simulate it or just place it "inside" visually.
    
    # Better approach for Visuals: 
    # Use st.markdown to open the div, but we can't close it after the widget easily in standard Streamlit without hacks.
    # We will use the style provided: "formatted same as address" but with red box.
    # The simplest "Red Box" is just a styled container.
    
    st.markdown('<div style="border: 2px solid #EA4335; border-radius: 6px; padding: 10px; margin-bottom: 16px;">', unsafe_allow_html=True)
    st.text_input("Email (Required)", placeholder="name@example.com", key="email_input", label_visibility="visible")
    st.markdown('</div>', unsafe_allow_html=True)

    # --- Property Details ---
    st.markdown('<div style="font-size: 14px; font-weight: 500; color: #1A73E8; margin-bottom: 12px;">Property Details</div>', unsafe_allow_html=True)
    
    st.caption("Target Address")
    st.text_input("Address", placeholder="Enter address...", key="input_address", label_visibility="collapsed")
    
    st.markdown('<div style="height: 12px;"></div>', unsafe_allow_html=True)
    
    # Bed / Bath / Sqft
    c_b1, c_b2, c_b3 = st.columns(3)
    with c_b1:
        st.caption("Bed")
        st.number_input("Bed", min_value=0, max_value=10, value=2, label_visibility="collapsed", key="input_bedrooms")
    with c_b2:
        st.caption("Bath")
        st.number_input("Bath", min_value=0, max_value=10, value=1, label_visibility="collapsed", key="input_bathrooms")
    with c_b3:
        st.caption("Sqft")
        st.number_input("Sqft", min_value=0, value=1500, step=100, label_visibility="collapsed", key="input_sqft")

    st.markdown('<div style="height: 12px;"></div>', unsafe_allow_html=True)
    st.selectbox("Property Type", ["Apartment", "Single Family", "Condo", "Townhouse"], index=0, key="input_property_type")
    
    st.markdown('<div style="height: 12px;"></div>', unsafe_allow_html=True)
    
    # Address 2 (Collapsible or just standard for now per requirement "Address 2 (Optional)")
    with st.expander("Compare Address (Optional)"):
        st.text_input("Address 2", placeholder="Comparison address...", key="input_address_2")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # --- Factors & Weights ---
    st.markdown('<div class="panel-container">', unsafe_allow_html=True)
    
    # Header
    st.markdown('<div style="font-size: 14px; font-weight: 500; color: #1A73E8; margin-bottom: 12px;">Priorities</div>', unsafe_allow_html=True)

    # Score Method Toggle
    score_method = st.selectbox("Score Method", ["Default", "Normalized & Weighted"], index=0, key="score_method_input")
    use_custom_weights = (score_method == "Normalized & Weighted")
    
    st.markdown('<div style="margin-top: 12px; margin-bottom: 12px; height: 1px; background-color: #E8EEF5;"></div>', unsafe_allow_html=True)
    
    st.markdown('<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">'
                '<div style="font-size: 12px; color: #5F6368;">Factor</div>'
                '<div style="font-size: 12px; color: #5F6368;">Weight / Lock</div>'
                '</div>', unsafe_allow_html=True)
    
    # Initialize weights if not exists (ensure they sum to 100 initially)
    if "init_weights" not in st.session_state:
        st.session_state.init_weights = True
        default_val = 100 / len(factors)
        for f in factors:
            if f"w_{f}" not in st.session_state:
                st.session_state[f"w_{f}"] = default_val
            if f"lock_{f}" not in st.session_state:
                st.session_state[f"lock_{f}"] = False
        
    for f in factors:
        # Layout: Slider (80%) | Lock (20%)
        # Note: Streamlit cols are good for this.
        # We need to construct the key carefully.
        
        c_slide, c_lock = st.columns([85, 15])
        
        with c_slide:
            curr_val = st.session_state.get(f"w_{f}", 20.0)
            
            # Label styling
            label_color = "#202124" if use_custom_weights else "#9AA0A6"
            st.markdown(f'<div style="font-size: 13px; font-weight: 500; margin-bottom: -10px; color: {label_color};">{f} <span style="font-weight:400; color:#9AA0A6;">({int(curr_val)}%)</span></div>', unsafe_allow_html=True)
            
            # Disable slider if locked OR if using Default method
            is_locked = st.session_state.get(f"lock_{f}", False)
            slider_disabled = is_locked or (not use_custom_weights)
            
            st.slider(
            
            st.slider(
                f, 
                min_value=0.0, 
                max_value=100.0, 
                value=float(curr_val),
                step=1.0,
                key=f"w_{f}", 
                label_visibility="collapsed",
                disabled=slider_disabled,
                on_change=update_weights,
                args=(f,)
            )

        with c_lock:
            # Spacer to align with slider
            st.markdown('<div style="height: 18px;"></div>', unsafe_allow_html=True)
            st.checkbox("Lock", key=f"lock_{f}", label_visibility="collapsed")
            # Custom Lock Icon could be done with pure HTML if Checkbox is too ugly, but Checkbox is functional.
            # "🔒" if is_locked else "🔓" - creating a custom button might be better UX but checkbox is robust.

    st.markdown('</div>', unsafe_allow_html=True)
    
    # Analyze Button
    if st.button("Analyze Location", type="primary", use_container_width=True):
         run_analysis_flow()
         
    # Hidden Model Selection for logic but simplified UI
    st.markdown("<!-- Model: gemini-2.5-flash -->", unsafe_allow_html=True)
    # Actually need to set it for logic
    if "input_model" not in st.session_state:
        st.session_state.input_model = "gemini-2.5-flash"
        
    # Configure Key for convenience if not done
    gemini_key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
    if gemini_key:
        llm.configure_genai([gemini_key])

    if st.session_state.email_input:
        usage = get_daily_usage(st.session_state.email_input)
        st.caption(f"Daily Usage: {usage}/3")


# ==========================================
# PROCESSING LOGIC (Uses Middle Column)
# ==========================================
if st.session_state.processing:
    with c_mid:
        loader_placeholder = st.empty()
        components.render_loader(loader_placeholder, 5)

        # Validation
        user_email = st.session_state.email_input
        address = st.session_state.input_address
        if not user_email:
            st.error("Email is required.")
            st.session_state.processing = False
            st.stop()
        if not address:
            st.error("Address is required.")
            st.session_state.processing = False
            st.stop()
            
        usage_count = get_daily_usage(user_email)
        if usage_count >= 3:
            st.error("Daily limit reached.")
            st.session_state.processing = False
            st.stop()
            
        # Logging
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
             # CSV Log
             log_dir = "logs"
             if not os.path.exists(log_dir): os.makedirs(log_dir)
             with open(os.path.join(log_dir, "usage_logs.csv"), 'a', newline='', encoding='utf-8') as f:
                 writer = csv.writer(f)
                 writer.writerow([timestamp, user_email, address])
             # GSheet Log
             sheet = connect_to_gsheet()
             if sheet: sheet.append_row([timestamp, user_email, address])
        except Exception as e:
            print(f"Logging Error: {e}")
        
        components.render_loader(loader_placeholder, 30)
        
        # 1. POI
        geo_key = st.secrets.get("GEOAPIFY_API_KEY")
        pois, lat, lon = data.get_poi(address, api_key=geo_key)
        st.session_state.pois = pois
        st.session_state.lat = lat
        st.session_state.lon = lon
        
        components.render_loader(loader_placeholder, 50)

        # 2. Census (Try Real Data first)
        census = data.get_census_data(address)
        # We DO NOT call estimate_census_data here to save API calls.
        # It will be handled in analyze_location.
        
        components.render_loader(loader_placeholder, 70)
        
        # 3. Rent Analysis
        rent_key = st.secrets.get("RENTCAST_API_KEY")
        if rent_key:
            rent_data = data.get_rentcast_data(
                address, 
                st.session_state.input_bedrooms, 
                st.session_state.input_bathrooms,
                st.session_state.input_sqft,
                "Apartment", 
                rent_key
            )
            st.session_state.rent_data = rent_data
        
        components.render_loader(loader_placeholder, 80)
        
        # 4. LLM Analysis (Integrated Analysis + Estimation)
        model_name = st.session_state.get("input_model", "gemini-2.5-flash")
        
        
        # Collect weights ONLY if "Normalized & Weighted" is selected
        user_weights = None
        if st.session_state.get("score_method_input") == "Normalized & Weighted":
            user_weights = {f: st.session_state.get(f"w_{f}", 50) for f in factors}
        
        analysis = llm.analyze_location(address, pois, census, model_name=model_name, weights=user_weights)
        st.session_state.analysis = analysis
        
        # 5. Backfill Census if missing (using LLM estimate)
        if not census or not census.get('metrics'):
             estimated = analysis.get('estimated_census', {})
             # Ensure structure matches what charts expect
             if 'metrics' not in estimated:
                 # Flattened or wrong structure? Schema should enforce it, but safety first
                 census = {'metrics': estimated, 'source': 'AI (Estimated)'}
             else:
                 census = estimated
                 census['source'] = 'AI (Estimated)'
        
        st.session_state.census = census
        
        components.render_loader(loader_placeholder, 100)
        
        st.session_state.processing = False
        st.session_state.analyzed = True
        st.rerun()

# ==========================================
# RESULTS DISPLAY
# ==========================================
if st.session_state.analyzed:
    census = st.session_state.census
    rent_data = st.session_state.get("rent_data")
    analysis = st.session_state.analysis
    
    # --- MIDDLE COLUMN: ANALYTICS ---
    with c_mid:
        st.markdown('<div class="panel-container">', unsafe_allow_html=True)
        st.subheader("Census & Scores Analysis")
        
        # Cache Indicator
        if analysis.get('_cache_meta'):
            ts = analysis['_cache_meta'].get('timestamp', 'Unknown Date')
            st.caption(f"⚡ Using cached analysis from {ts} (Valid 240hrs)")
        
        # 1. Census Charts (2x2 Placeholder)
        # Using Altair
        metrics = census.get('metrics', {})
        benchmarks = census.get('benchmarks', {})
        
        # Prepare Data for Charts
        def parse_curr(s):
            if isinstance(s, int): return s
            if not s or s == "N/A": return 0
            return int(str(s).replace('$','').replace(',',''))

        local_inc = parse_curr(metrics.get('median_household_income'))
        state_inc = benchmarks.get('state_median_income', 0)
        
        # Chart 1: Income
        df_income = pd.DataFrame([
            {"Region": "State", "Income": state_inc, "Color": "#1A73E8"},
            {"Region": "Local", "Income": local_inc, "Color": "#0F1C2E"}
        ])
        chart_income = alt.Chart(df_income).mark_bar().encode(
             x=alt.X('Region', sort=["State", "Local"]),
             y='Income',
             color=alt.Color('Region', scale=alt.Scale(domain=['State','Local'], range=['#1A73E8', '#0F1C2E'])),
             tooltip=['Region', 'Income']
        ).properties(title="Household Income", height=150)
        
        # Chart 2: Education
        local_bach = metrics.get('education_bachelors_pct', 0)
        if local_bach == "N/A": local_bach = 0
        state_edu = benchmarks.get('state_edu', [0,0,0])
        state_bach = state_edu[1] if state_edu else 0
        
        df_edu = pd.DataFrame([
                {"Region": "State", "Pct": state_bach, "Color": "#1A73E8"},
                {"Region": "Local", "Pct": local_bach, "Color": "#0F1C2E"}
        ])
        chart_edu = alt.Chart(df_edu).mark_bar().encode(
             x=alt.X('Region', sort=["State", "Local"]),
             y=alt.Y('Pct', title='%'),
             color=alt.Color('Region', scale=alt.Scale(domain=['State','Local'], range=['#1A73E8', '#0F1C2E']))
        ).properties(title="Bachelor+ Degree", height=150)
        
        # Render 2x2
        cc1, cc2 = st.columns(2)
        with cc1:
            st.altair_chart(chart_income, use_container_width=True)
        with cc2:
            st.altair_chart(chart_edu, use_container_width=True)
            
        st.markdown("---")
        
        # 2. Composite Score (Horizontal Bar as Radar Proxy)
        st.caption("Factor Composite Score")
        # Use real-time weights for visualization (Logic: Score = Weight * RawScore? 
        # For now, just visualize the Weights themselves as 'Priorities' or mock Scores based on weights)
        # Requirement says "Factor Composite Score". Let's assume we want to show how the factors are weighted or their resulting score.
        # Since we don't have real "Scores" for each factor from the LLM yet (we might), let's show the Weights for now to verify the slider logic visually.
        
        radar_df = pd.DataFrame({
            "Factor": factors,
            "Weight": [st.session_state.get(f"w_{f}", 20) for f in factors]
        })
        
        chart_radar = alt.Chart(radar_df).mark_bar().encode(
            x=alt.X('Weight', scale=alt.Scale(domain=[0, 100]), title="Weight (%)"),
            y=alt.Y('Factor', sort=None),
            color=alt.Color('Weight', legend=None, scale=alt.Scale(scheme='blues')),
            tooltip=['Factor', 'Weight']
        ).properties(height=200, title="Current Factor Weights")
        st.altair_chart(chart_radar, use_container_width=True)

        st.markdown('</div>', unsafe_allow_html=True)
        
        # AI Summary
        st.markdown('<div class="panel-container">', unsafe_allow_html=True)
        st.subheader("🤖 AI Executive Summary")
        if "investment_strategy" in analysis:
            st.info(analysis["investment_strategy"])
        
        ac1, ac2 = st.columns(2)
        with ac1:
            st.markdown("**Pros**")
            if "highlights" in analysis:
                for h in analysis["highlights"][:4]:
                    st.markdown(f"<span style='color:#34A853'>✓</span> {h}", unsafe_allow_html=True)
        with ac2:
            st.markdown("**Risks**")
            if "risks" in analysis:
                for r in analysis["risks"][:4]:
                    st.markdown(f"<span style='color:#FBBC04'>⚠</span> {r}", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- RIGHT COLUMN: MAP ---
    with c_right:
        st.markdown('<div class="panel-container">', unsafe_allow_html=True)
        st.subheader("Interactive Map")
        
        if st.session_state.lat and st.session_state.lon:
            # Re-use map generation
            deck_map, legend_items = map.generate_map(st.session_state.lat, st.session_state.lon, st.session_state.pois)
            st_folium(deck_map, use_container_width=True, height=500)
            
            if legend_items:
                st.caption("Nearby Amenities")
                st.markdown('<div style="display: flex; flex-wrap: wrap; gap: 8px;">', unsafe_allow_html=True)
                for label, (emoji, _) in legend_items.items():
                    st.markdown(f'<div style="background: #F8FAFD; padding: 4px 8px; border-radius: 4px; font-size: 12px; border: 1px solid #E8EEF5;">{emoji} {label}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

else:
    # Empty State
    with c_mid:
        st.markdown("""
        <div style="text-align: center; margin-top: 40px; color: #5F6368;">
            <h3>Welcome to HouSmart</h3>
            <p>Enter an address on the left to begin your location analysis.</p>
        </div>
        """, unsafe_allow_html=True)
