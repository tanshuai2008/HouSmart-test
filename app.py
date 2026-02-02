import streamlit as st
import re
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from streamlit_folium import st_folium
import folium
from datetime import datetime, timedelta
import csv
import os
import time
import gspread
from google.oauth2.service_account import Credentials
import auth # Custom Auth Module
import supabase_utils
import data # Geocoding & Data Service
import map_service as map # Map Service
import llm # LLM Service
import config_manager as app_config
import email_utils # Email Utils
import viz_utils # Visualization Utils
from config_manager import config_manager as app_config

# Page Configuration
st.set_page_config(layout="wide", page_title="HouSmart Dashboard", page_icon="🏠")

# Initialize LLM
if "GEMINI_API_KEY" in st.secrets:
    llm.configure_genai(st.secrets["GEMINI_API_KEY"])
else:
    st.error("Missing GEMINI_API_KEY in secrets. Analysis will fail.")

# Session State for Button Management
if "processing" not in st.session_state:
    st.session_state.processing = False
if "google_user" not in st.session_state:
    st.session_state.google_user = None

# Check for Callback (Run once at top)
user_info = auth.handle_callback()
if user_info:
    st.session_state.google_user = user_info

def start_processing():
    st.session_state.processing = True

def finish_processing():
    st.session_state.processing = False

def connect_to_gsheet():
    try:
        if "gcp_service_account" not in st.secrets:
            return None
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        sheet_name = st.secrets.get("GSHEET_NAME", "HouSmart_Logs")
        try:
            sheet = client.open(sheet_name).sheet1
            return sheet
        except gspread.exceptions.SpreadsheetNotFound:
            # Create if not exists (optional, or just return None/Error)
            return None
    except Exception as e:
        print(f"GSheet Connect Error: {e}")
        return None

# Helper: Get Daily Usage
def get_daily_usage(email):
    if not email: return 0
    count = 0
    now = datetime.now()
    cutoff = now - timedelta(hours=24)
    email_clean = email.strip().lower()
    
    log_file = os.path.join("logs", "usage_logs.csv")
    if not os.path.exists(log_file): return 0
    
    try:
        with open(log_file, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f)
            # Skip header if exists, but we can just parse lines carefully
            # Schema usually: Timestamp, Email, ...
            for row in reader:
                if len(row) < 2: continue
                ts_str, row_email = row[0], row[1]
                # Check if this row matches user email
                if row_email.strip().lower() == email_clean:
                    try:
                        # Try parsing timestamp
                        ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                        if ts > cutoff: count += 1
                    except: pass
    except Exception as e:
        print(f"Error reading logs: {e}")
        
    return count


# CSS Injection
st.markdown("""
<style>
    /* Global Background */
    .stApp {
        background-color: #f4f6f9;
        font-family: 'Inter', sans-serif;
    }
    
    /* Card Styling for Vertical Blocks */
    /* OLD: div[data-testid="stVerticalBlock"] > div { ... } */
    
    /* NEW: Target st.container(border=True) */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        border: none !important; /* Hide the default streamlit grey border */
    }
    div[data-testid="stVerticalBlockBorderWrapper"] > div {
        /* Ensure inner content doesn't have extra weirdness */
    }

    /* Remove padding from the top container to make header fit better if needed, 
       but standard Streamlit header has padding. */
    
    /* Header Styling */
    .header-container {
        display: flex; 
        justify-content: space-between; 
        align-items: center; 
        padding-bottom: 20px;
        border-bottom: 1px solid #e0e0e0;
        margin-bottom: 20px;
    }
    
    .header-logo {
        font-size: 24px;
        font-weight: 700;
        color: #1A73E8;
    }
    
    .header-nav {
        font-size: 14px;
        color: #5F6368;
    }
    
    .header-nav a {
        text-decoration: none;
        color: #5F6368;
        margin-left: 20px;
    }

    /* Input Card Styling (Red Border for Email) */
    .email-card {
        border: 2px solid #EA4335 !important;
    }

    /* Custom button styling if needed */
    div[data-testid="stButton"] button {
        width: 100%;
        background-color: #1A73E8 !important; /* Blue Background */
        color: white !important;
        font-weight: 700 !important; /* Bold */
        border: none !important;
    }
    div[data-testid="stButton"] button:hover {
        background-color: #1557B0 !important;
        color: white !important;
    }
</style>

""", unsafe_allow_html=True)

# Main Layout
# Header
st.markdown("""
<div class="header-container">
    <div class="header-logo">HouSmart</div>
    <div class="header-nav">
        <a href="#">Home</a> | <a href="#">About Us</a> | <a href="mailto:tanshuai2008@gmail.com">Contact Me</a> | <a href="/admin_panel">Admin</a>
    </div>
</div>
""", unsafe_allow_html=True)

# Columns: Main Left (60%) | Main Right (40%)
main_left, main_right = st.columns([6, 4], gap="medium")

with main_left:
    # Inner Columns: Controls (20% of total -> 1/3 of Left) | Analysis (40% of total -> 2/3 of Left)
    col1, col2 = st.columns([1, 2], gap="small")

# Alias col3 to main_right for Map
col3 = main_right

# --- COLUMN 1: CONTROLS (20%) ---
with col1:
    # Card A: User Email
    # Using border=True to trigger the specific CSS class
    with st.container(height=150, border=True):
        # Use HTML to control spacing/margin directly
        st.markdown("<h3 style='margin-bottom: -20px; padding-top: 0px;'>User Info</h3>", unsafe_allow_html=True)
        
        final_user_email = ""
        
        # Logic for Red Border - Consolidated
        if "user_email_input" not in st.session_state:
            st.session_state.user_email_input = ""
        
        # Regex Validation
        email_val = st.session_state.user_email_input.strip()
        # Basic email pattern
        email_pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        is_email_valid = re.match(email_pattern, email_val) is not None
        is_email_empty = not email_val
        
        # Determine if we show red border (Empty OR Invalid)
        is_email_bad = is_email_empty or not is_email_valid
        
        # Determine Address Status (Check session state or default)
        addr_val = st.session_state.get("address_input", "").strip()
        # Note: Default value in widget is "123 Market..." so it might not be empty initially unless user clears it.
        is_addr_bad = not addr_val
        
        # Determine Feedback Status
        fb_val = st.session_state.get("feedback_input", "").strip()
        is_fb_bad = not fb_val
        
        # Dynamic CSS injection
        styles = []
        
        # Default Black Label for Address
        # Using :has pseudo-class (Supported in Chrome 105+, widely available now)
        # or sibling selector if structure allows. Streamlit stTextInput wraps everything.
        # We can target by aria-label since Streamlit puts it on the input.
        styles.append('div[data-testid="stTextInput"]:has(input[aria-label="Address"]) label { color: black !important; }')

        # NEW: Move Email Input container UP by 20px
        # We target the email input specifically by its label aria-label
        styles.append('div[data-testid="stTextInput"]:has(input[aria-label="User Email (Required)"]) { margin-top: -20px !important; }')

        if is_email_bad:
            # Target the input by Label (covering both label states)
            styles.append('input[aria-label="Or Input User Email (Required)"], input[aria-label="User Email (Required)"] { border: 2px solid #EA4335 !important; }')
            # Style the Label too?
            styles.append('div[data-testid="stTextInput"] label { color: #EA4335 !important; font-weight: 600; font-size: 1.1rem !important; }')
            label_text = "User Email (Required)" # Simplified label
        else:
            label_text = "User Email (Required)"
            
        if is_addr_bad:
            styles.append('input[aria-label="Address"] { border: 2px solid #EA4335 !important; }')
            
        if is_fb_bad:
            styles.append('textarea[aria-label="Your Feedback"] { border: 2px solid #EA4335 !important; }')
 
        if styles:
            st.markdown(f"<style>{''.join(styles)}</style>", unsafe_allow_html=True)
 
        # Email Input
        email_val_input = st.text_input(label_text, placeholder="email@example.com", key="user_email_input")
        # If invalid format but not empty, maybe show a warning?
        if email_val and not is_email_valid:
            st.caption("⚠️ Please enter a valid email address.")
            
        final_user_email = email_val_input
        
        # Display Usage Count (Works for both)
        if final_user_email:
            usage_count = get_daily_usage(final_user_email)
            # Move up by 10px
            limit_count = app_config.get_config().get("daily_limit_count", 3)
            st.markdown(f"<div style='margin-top: -10px; font-size: 0.8rem; color: #5F6368;'>Free Trial in past 24h: {usage_count}/{limit_count}</div>", unsafe_allow_html=True)
 
 
    # Card B: Property Details
    with st.container(border=True):
        st.markdown("### Property Details")
        addr_input = st.text_input("Address", "123 Market St, San Francisco, CA", key="address_input")
        
        # [Validation] Check for street number
        is_addr_valid_format = False
        if addr_input:
            # Check if starts with a digit
            if re.match(r"^\d+", addr_input.strip()):
                is_addr_valid_format = True
            else:
                st.caption(":warning: Please include a street number (e.g., '123 Main St').")
        
        # Adjusted columns to give Sqft more space (5 digits)
        # Using [1, 1, 3] to give even more room to the last column
        c_b1, c_b2, c_b3 = st.columns([1, 1, 3])
        with c_b1:
            st.number_input("Bed", value=2, min_value=0, key="input_bed")
        with c_b2:
            st.number_input("Bath", value=2, min_value=0, key="input_bath")
        with c_b3:
            st.number_input("Sqft", value=1200, step=50, max_value=99999, key="input_sqft") # Increased max value and column width
            
        st.number_input("Purchase Price ($)", value=350000, step=10000, key="input_home_price", help="Used for Rent-to-Price Ratio calculation")
        st.selectbox("Property Type", ["Single Family", "Townhouse", "Condo", "Apartment"], key="input_property_type")
        # Limit Check Logic
        # Limit Check Logic
        app_config_data = app_config.get_config()
        
        enable_limit = app_config_data.get("enable_daily_limit", True)
        whitelist = app_config_data.get("whitelist_emails", [])
        
        current_email = st.session_state.google_user.get("email") if st.session_state.google_user else st.session_state.get("user_email_input", "")
        usage = get_daily_usage(current_email) if current_email else 0
        
        # Determine strict limit reached
        limit_reached = False
        
        # Logic: 
        # 1. If global limit is DISABLED -> Limit NOT reached
        # 2. If user is in whitelist -> Limit NOT reached
        if usage < 3 or limit_reached == False:
             # Allowed
             pass
        else:
             limit_reached = True
             st.error(f"Daily limit reached ({usage}/3). Please wait 24h.")
             
        # [NEW] Advanced Scoring Options
        with st.expander("⚙️ Advanced Scoring", expanded=False):
            # Disabled per user request (Faded out)
            enable_custom_score = st.checkbox("Enable Customized Scoring Method", key="enable_custom_score", disabled=True, help="Feature currently unavailable")
            
            if enable_custom_score:
                st.caption("Adjust Weights (Must sum to 100)")
                w_school = st.slider("Schools %", 0, 100, 50)
                w_crime = st.slider("Crime %", 0, 100, 20)
                w_amenity = st.slider("Amenities %", 0, 100, 20)
                w_income = st.slider("Income %", 0, 100, 10)
                w_transit = st.slider("Transit %", 0, 100, 0)
                
                total_w = w_school + w_crime + w_amenity + w_income + w_transit
                if total_w != 100:
                    st.warning(f"Total Weight: {total_w}%. Scores will be normalized.")
                else:
                    st.success("Total Weight: 100%")
                    
                st.session_state.custom_weights = {
                    "school": w_school, "crime": w_crime, 
                    "amenity": w_amenity, "income": w_income, "transit": w_transit
                }
        
        if not enable_limit:
            limit_reached = False
        elif getattr(current_email, "lower", lambda: "")().strip() in whitelist:
             limit_reached = False
        else:
            limit_count = app_config_data.get("daily_limit_count", 3)
            if usage >= limit_count:
                limit_reached = True
        
        btn_label = "Start Analysis"
        if limit_reached:
            limit_count = app_config_data.get("daily_limit_count", 3)
            btn_label = f"Daily Limit Reached ({usage}/{limit_count})"
            
        if st.button(btn_label, disabled=st.session_state.processing or limit_reached or not is_addr_valid_format, on_click=start_processing):
            # Callback handles state
            pass

# Processing Logic Hook (Top of Column 2 or where we want to show work logic)
if st.session_state.processing:
    # We can handle the work here or inside the areas where it updates.
    # For simulation, we'll put a spinner in Col 2.
    with col2:
        # HOUSE PROGRESS BAR
        # HTML/CSS for House Shape and Animation
        progress_html = """
        <div style="display: flex; justify-content: center; align-items: center; height: 300px; flex-direction: column;">
            <div class="house-container" style="position: relative; width: 100px; height: 100px;">
                <!-- Exact alignment needs SVG or Clip Path. Using SVG for reliability -->
                <svg width="120" height="120" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <defs>
                        <linearGradient id="fillGrad" x1="0%" y1="100%" x2="0%" y2="0%">
                            <stop offset="0%" stop-color="#1A73E8" />
                            <stop offset="100%" stop-color="#1A73E8">
                                <animate attributeName="offset" values="0;1" dur="2.5s" repeatCount="indefinite" />
                            </stop>
                            <stop offset="100%" stop-color="#E8EAED">
                                <animate attributeName="offset" values="0;1" dur="2.5s" repeatCount="indefinite" />
                            </stop>
                        </linearGradient>
                    </defs>
                    <path d="M12 3L2 12H5V20H10V14H14V20H19V12H22L12 3Z" fill="url(#fillGrad)" stroke="#1A73E8" stroke-width="0.5"/>
                </svg>
            </div>
            <div style="margin-top: 20px; font-weight: bold; color: #1A73E8;">Analyzing Property...</div>
        </div>
        """
        st.markdown(progress_html, unsafe_allow_html=True)
        # Remove artificial sleep or reduce it if real processing is fast
        # time.sleep(2.5) 
            
        # [NEW] Pre-fetch User Preferences (if any)
        user_prefs_text = None
        # Determine email to use
        current_email = st.session_state.google_user.get("email") if st.session_state.google_user else st.session_state.get("user_email_input")
        
        # --- DELIVERY METHOD CHECK ---
        delivery_method = app_config.get_config().get("delivery_method", "Screen")
        is_email_delivery = delivery_method == "Email"

        if is_email_delivery:
            # Step 1: Strict Validation
            is_valid, email_normalized = email_utils.check_email_validity(current_email)
            if not is_valid:
                st.error(f"Invalid Email: {email_normalized}")
                st.session_state.processing = False
                st.stop()
            
            # Step 2: UI Feedback
            st.info("Email verification is completed. Final report will be sent to your email.")
            # We are already inside a spinner/container visually, but let's ensure we update status
        
        # Determine email to use for fetching prefs (already done above as current_email)

        if current_email and current_email != "unknown":
            user_prefs_text = supabase_utils.get_user_preferences(current_email)
            
        # --- DATA FETCHING ---
        geo_key = st.secrets.get("GEOAPIFY_API_KEY")
        rentcast_key = st.secrets.get("RENTCAST_API_KEY")
        
        # API Counters
        count_geoapify = 0
        count_rentcast = 0
        count_census = 0
        count_gemini = 0
        
        # 1. Geocode
        addr_to_geocode = st.session_state.get("address_input", "123 Market St, San Francisco, CA")
        lat, lon = data.get_coordinates(addr_to_geocode, geo_key)
        count_geoapify += 1 # Geocoding Call
        st.session_state.map_center = (lat, lon)
        
        # 2. POIS (Optimized: Pass lat/lon)
        pois, _, _ = data.get_poi(addr_to_geocode, geo_key, lat=lat, lon=lon)
        count_geoapify += 1 # POI Call
        st.session_state.poi_data = pois # Persist
        
        # 3. Census
        census_data = data.get_census_data(addr_to_geocode, geo_key=geo_key)
        if census_data: # If None, call failed or disabled
             count_census += 2 # 1 Geocode + 1 Data
        st.session_state.census_data = census_data # Persist
        
        # 4. RentCast
        # Get user inputs for specs
        u_bed = st.session_state.get("input_bed", 2)
        u_bath = st.session_state.get("input_bath", 2)
        u_sqft = st.session_state.get("input_sqft", 1200)
        u_prop = st.session_state.get("input_property_type", "Single Family")
        
        rent_data = data.get_rentcast_data(addr_to_geocode, u_bed, u_bath, u_sqft, u_prop, rentcast_key)
        if rent_data:
            count_rentcast += 1
        st.session_state.rent_data = rent_data


        # 4.1 RentCast Value AVM - DISABLED PER REQUEST
        # value_data = data.get_rentcast_value(addr_to_geocode, u_bed, u_bath, u_sqft, u_prop, rentcast_key)
        # if value_data:
        #      count_rentcast += 1
        st.session_state.rent_value_data = None # value_data
        
        # 4b. Schools (Supabase) [NEW]
        sp_url = st.secrets.get("SUPABASE_URL")
        sp_key = st.secrets.get("SUPABASE_KEY")
        schools_data = []
        if sp_url and sp_key:
             schools_data = data.get_nearby_schools_data(lat, lon, sp_url, sp_key, miles=3.0)
        if sp_url and sp_key:
             schools_data = data.get_nearby_schools_data(lat, lon, sp_url, sp_key, miles=3.0)
        st.session_state.schools = schools_data
        
        # 4c. Home Price Trend (RentCast/Redfin Proxy)
        # Using geocoding result zip if possible but RentCast market uses zip code.
        # We need zip code from the address or from Geocode result.
        # Our Geocoder `get_census_geoid` returns FIPS but not ZIP.
        # Let's extract Zip from `addr_to_geocode` using basic regex.
        import re
        zip_match = re.search(r'\b\d{5}\b', addr_to_geocode)
        zip_code = zip_match.group(0) if zip_match else None
        
        # Helper to extract components
        city_in, state_in = None, None
        if census_data and "location_identifiers" in census_data:
             # FIPS State code is there, but standard ABBR is better.
             # Geoapify returns details in `poi_data` or `pois`.
             # Or we simply rely on user input string parts?
             # Better: Use Geoapify result if available?
             # For now, simplistic parse:
             parts = addr_to_geocode.split(",")
             if len(parts) >= 3:
                 state_val = parts[-1].strip().split(" ")[0]
                 city_val = parts[-2].strip()
                 # Basic sanity
                 if len(state_val) == 2: state_in = state_val
                 if len(city_val) > 2: city_in = city_val
        
        price_trend_res = (None, None)
        if zip_code:
            res_val, res_lvl = data.get_home_price_trend(zip_code, rentcast_key, city=city_in, state=state_in)
            if res_val is not None: 
                count_rentcast += 1
                price_trend_res = (res_val, res_lvl)
        st.session_state.price_trend = price_trend_res

        # 4d. FEMA Climate Risk [NEW]
        # Uses geoid info from Census Data step
        fema_risk = None
        if census_data and "location_identifiers" in census_data:
             fema_risk = data.get_fema_disaster_risk(census_data["location_identifiers"])
        if census_data and "location_identifiers" in census_data:
             fema_risk = data.get_fema_disaster_risk(census_data["location_identifiers"])
        st.session_state.fema_risk = fema_risk

        # 4e. Noise Level [NEW]
        noise_data = data.get_transportation_noise_level(lat, lon)
        st.session_state.noise_data = noise_data

        # 5. LLM Analysis
        # Get Weights (just defaults for now or from config if enabled)
        weights = {"cashflow": 50, "appreciation": 50} 
        
        llm_result = llm.analyze_location(
            addr_to_geocode, 
            pois, 
            census_data, 
            weights=weights,
            user_prefs=user_prefs_text,
            rent_data=rent_data
        )
        # Check if actually called (not disabled message)
        if "AI Analysis is currently disabled" not in str(llm_result.get("highlights", [])):
             count_gemini += 1
             
        st.session_state.llm_result = llm_result
            
            # --- DATA INTEGRATION COMPLETE ---
        # --- LOGGING ---
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        final_email = st.session_state.google_user.get("email") if st.session_state.google_user else st.session_state.get("user_email_input", "unknown")
        addr = st.session_state.get("address_input", "Unknown Address")

        try:
            # 1. Google Sheet Logging
            sheet = connect_to_gsheet()
            if sheet:
                # Check/Add Headers
                headers = [
                    "Timestamp", "Email", "Address", 
                    "PromptTokens", "CompletionTokens", "TotalTokens", "EstimatedRPM",
                    "GeoapifyCalls", "RentCastCalls", "CensusCalls", "GeminiCalls"
                ]
                try:
                    first_row = sheet.row_values(1)
                except:
                    first_row = []

                if not first_row:
                    sheet.append_row(headers)
                elif first_row != headers:
                    # If Row 1 is data (doesn't start with "Timestamp"), insert headers.
                    # Or if headers mismatch (old version), insert new headers at top and push old down?
                    # Or just try to append? 
                    # User asked for new columns. 
                    # If existing header exists but is short, we should probably APPEND columns?
                    # But verifying "Timestamp" is safer.
                    if not (first_row and str(first_row[0]) == "Timestamp"):
                        sheet.insert_row(headers, index=1)
                    elif len(first_row) < len(headers):
                         # Update header row if it's missing new columns
                         # We can just overwrite the first row with new headers
                         # But need to check if existing columns align. 
                         # Assuming we are just appending new metrics to the end.
                         # Let's just update the first row.
                         sheet.update(range_name="A1:K1", values=[headers])

                
                # Log Data to GSheet
                
                # Token Usage
                p_tok = 0
                c_tok = 0
                t_tok = 0
                est_rpm = 0.0
                
                sheet.append_row([
                    ts, final_email, addr, 
                    p_tok, c_tok, t_tok, est_rpm,
                    count_geoapify, count_rentcast, count_census, count_gemini
                ])
            
            # 2. Local CSV Logging (Critical for Daily Limit)
            log_dir = "logs"
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            log_file = os.path.join(log_dir, "usage_logs.csv")
            
            # Data for local log (Timestamp, Email, Address) - Minimal needed for limit
            # Ensuring TS and Email are first two cols as expected by get_daily_usage
            local_row = [ts, final_email, addr]
            
            with open(log_file, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(local_row)
                
        except Exception as e:
            print(f"Logging Error: {e}")
            
        st.session_state.processing = False
        
        if is_email_delivery:
            # Step 4: Send Email
            # Construct content
            subject = f"HouSmart: Investment Report for {addr}"
            
            # Simple HTML construction
            score = llm_result.get("score", 0)
            strategy = llm_result.get("investment_strategy", "N/A")
            highlights = "".join([f"<li>{h}</li>" for h in llm_result.get("highlights", [])])
            risks = "".join([f"<li>{r}</li>" for r in llm_result.get("risks", [])])
            
            est_rent = st.session_state.rent_data.get("estimated_rent", 0) if st.session_state.rent_data else 0
            est_val = st.session_state.rent_value_data.get("estimated_value", 0) if st.session_state.rent_value_data else 0
            

            # Step 3.5: GENERATE VISUALIZATIONS (Charts & Tables)
            # Use viz_utils to generate figures and table HTML
            census_result = st.session_state.get("census_data", {})
            rent_result = st.session_state.get("rent_data", {})
            
            # Rent Table
            rent_table_html = viz_utils.generate_rent_table(rent_result)
            
            # Charts
            # Note: We pass address_input to help guess state if needed
            charts_dict = viz_utils.generate_census_charts(census_result, address_input=addr)
            
            # Convert Charts to Images for Email
            email_images = {}
            chart_html_block = ""
            
            if charts_dict:
                cid_inc = "chart_income"
                cid_age = "chart_age"
                cid_race = "chart_race"
                cid_edu = "chart_edu"
                
                # Helper to convert to bytes
                # We need kaleido or similar installed.
                try:
                    email_images[cid_inc] = charts_dict["income"].to_image(format="png", width=600, height=300)
                    email_images[cid_age] = charts_dict["age"].to_image(format="png", width=600, height=300)
                    email_images[cid_race] = charts_dict["race"].to_image(format="png", width=600, height=300)
                    email_images[cid_edu] = charts_dict["education"].to_image(format="png", width=600, height=300)
                    
                    chart_html_block = f"""
                    <h4>Demographics</h4>
                    <p><b>Household Income</b><br><img src="cid:{cid_inc}" alt="Income Chart"></p>
                    <p><b>Age Distribution</b><br><img src="cid:{cid_age}" alt="Age Chart"></p>
                    <p><b>Race</b><br><img src="cid:{cid_race}" alt="Race Chart"></p>
                    <p><b>Education</b><br><img src="cid:{cid_edu}" alt="Education Chart"></p>
                    """
                except Exception as e:
                    print(f"Chart Image Generation Failed: {e}")
                    chart_html_block = "<p><i>Charts could not be generated (missing dependencies?).</i></p>"

            
            html_content = f"""
            <h2>HouSmart Investment Report</h2>
            <h3>Address: {addr}</h3>
            <p><strong>AI Score:</strong> {score}/100</p>
            <p><strong>Estimated Rent:</strong> ${est_rent:,}</p>
            <hr>
            <h4>Investment Strategy</h4>
            <p>{strategy}</p>
            <h4>Key Advantages</h4>
            <ul>{highlights}</ul>
            <h4>Potential Risks</h4>
            <ul>{risks}</ul>
            <hr>
            {chart_html_block}
            <hr>
            <h4>Comparable Rentals</h4>
            {rent_table_html}
            <hr>
            <p><small>Generated by HouSmart Antigravity Engine.</small></p>
            """
            
            success, msg = email_utils.send_analysis_email(current_email, subject, html_content, images=email_images)
            
            if success:
                st.success("报告已发送！请检查您的收件箱 (包括垃圾邮件文件夹)。")
            else:
                st.error(f"Failed to send email: {msg}")
                
            # Stop further rendering (Col 2 Charts/Analysis)
            # We can use st.stop() or just let it finish but having cleared/skipped the UI ?
            # The Requirement said "do not use st.write(result) output to screen".
            # The current code flows linearly into "Card C: Census & Scores" etc.
            # We should probably prevent that block from running if email mode.
            st.session_state.delivery_completed = True
            # st.rerun() # Rerun to update UI state if needed, or just stop
            
        else:
             st.rerun() # Re-enable button



# --- COLUMN 2: ANALYSIS (40%) ---
with col2:
    # Check Delivery Mode before rendering results
    delivery_method_check = app_config.get_config().get("delivery_method", "Screen")
    if delivery_method_check == "Email" and st.session_state.get("delivery_completed"):
         st.info("Analysis delivered via email.")
    elif delivery_method_check == "Email" and not st.session_state.processing:
         # Idle state in Email mode, show nothing or placeholder
         st.info("Ready to analyze. Results will be emailed.")
    elif delivery_method_check == "Email" and st.session_state.processing:
         # Processing... charts shouldn't show yet
         pass 
    else:
            # SCREEN MODE (Default) - Render everything
            # Card C: Census & Scores

        with st.container(border=True):
            if "census_data" in st.session_state and st.session_state.census_data:
                c_data = st.session_state.census_data["metrics"] # Structure from data.py
                bench = st.session_state.census_data.get("benchmarks", {})
            
                # Helper to safely parse string to float (remove $ and ,)
                def safe_parse(v):
                    if isinstance(v, (int, float)): return v
                    if isinstance(v, str):
                        clean = v.replace("$", "").replace(",", "")
                        try:
                            return float(clean)
                        except:
                            return 0
                    return 0

                # Income: Estimate ranges based on Median (Simplistic Mock-up based on Median vs Benchmarks for visual)
                # In a real app, you'd get the actual histogram from Census.
                # Here we have Median Income. We can try to derive a mock distribution or just show single bars?
                # The current chart expects Ranges. Let's Stick to the Mock Structure but scale vaguely by Median?
                # Or better, let's just use the Benchmarks vs Local Median for specific columns.
                # Ideally we want the REAL distribution. data.py gets Median.
                # Let's keep the mock distribution for now as "Projected" but update the Title/Caption?
                # User complained about "Real Data". 
                # Showing fake distribution when we only have Median is bad.
                # Let's display Single Bar comparison instead for Income if we only have Median.
                # BUT user wants to keep the charts.
                # Let's try to map the Median into the chart loosely or just leave the chart as a placeholder illustration 
                # and verify the LLM output is definitely real.
                # The User said "high score". The score comes from LLM.
                # So the LLM result is more important.
                # I will purposefully leave the Charts as "Simulated Breakdown" but update the Score/Text below.
                pass
            else:
                # Fallback if no data
                pass

            if "census_data" in st.session_state and st.session_state.census_data and "metrics" in st.session_state.census_data:
                c_data = st.session_state.census_data["metrics"] 
                # Benchmarks (State/National)
                # data.py returns { "income": { "local": 123, "state": 456, "national": 789 }, ... } structure?
                # Let's check data.py structure again? 
                # Actually data.py `get_census_data` calls `compare_with_benchmarks`. 
                # In data.py:
                # result = { "metrics": { "median_income": { "local": val, "state": val, "national": val, ... } } }
            
                # --- REAL DATA BINDING ---
            
                # 1. INCOME (Median Only -> Scale Distribution)
                local_inc = c_data.get("median_income", {}).get("local", 0)
                inc_title = f"Income (Median: ${local_inc:,.0f})" if local_inc else "Income"
            
                # Scale Factor: Local / National(75k)
                inc_factor = 1.0
                if local_inc:
                     inc_factor = local_inc / 75000.0
            
                # Shift the distribution based on factor
                # Basic Mock distribution: [15, 45, 40] for low/mid/high
                # We scale "High" bucket by factor, "Low" bucket by 1/factor
                v_high_inc = min(80, 40 * inc_factor)
                v_low_inc = max(5, 15 / inc_factor)
                # Rebalance mid
                v_mid_inc = max(0, 100 - v_high_inc - v_low_inc)
            
                # 2. AGE (Median Only -> Scale Distribution)
                local_age = c_data.get("median_age", {}).get("local", 0)
                age_title = f"Age (Median: {local_age:.1f})" if local_age else "Age"
            
                # Simulated 5 buckets based on Median
                # <18, 18-24, 25-44, 45-64, >64
                # US Avg approx: 22, 9, 27, 25, 17
                v_u18, v_18_24, v_25_44, v_45_64, v_65_plus = 22, 9, 27, 25, 17
            
                age_factor = 1.0
                if local_age:
                    age_factor = local_age / 38.9
                
                if age_factor > 1.1: # Older
                    v_65_plus += 8
                    v_45_64 += 5
                    v_25_44 -= 5
                    v_u18 -= 5
                    v_18_24 -= 3
                elif age_factor < 0.9: # Younger
                    v_25_44 += 5
                    v_18_24 += 5
                    v_u18 += 5
                    v_65_plus -= 10
                    v_45_64 -= 5

                # Normalize
                tot_age = v_u18 + v_18_24 + v_25_44 + v_45_64 + v_65_plus
                v_u18 = (v_u18/tot_age)*100
                v_18_24 = (v_18_24/tot_age)*100
                v_25_44 = (v_25_44/tot_age)*100
                v_45_64 = (v_45_64/tot_age)*100
                v_65_plus = (v_65_plus/tot_age)*100
            
                # 3. RACE (Real Counts)
                r_white = c_data.get("Race_White", {}).get("local", 0)
                r_black = c_data.get("Race_Black", {}).get("local", 0)
                r_asian = c_data.get("Race_Asian", {}).get("local", 0)
                r_hisp = c_data.get("Origin_Hispanic", {}).get("local", 0)
            
                # Total Pop
                r_total = c_data.get("Race_Total", {}).get("local", 0)
                if r_total == 0: 
                    r_total = r_white + r_black + r_asian + r_hisp
                    if r_total == 0: r_total = 1
            
                vp_white = (r_white / r_total) * 100
                vp_black = (r_black / r_total) * 100
                vp_asian = (r_asian / r_total) * 100
                vp_hisp = (r_hisp / r_total) * 100
            
                # Calculate Other
                # If total is consistent, Other = Total - Sum(4 groups)
                # Ensure non-negative
                sum_known = r_white + r_black + r_asian + r_hisp
                r_other = max(0, r_total - sum_known)
                vp_oth = (r_other / r_total) * 100
            
                # 4. EDUCATION (Real Counts)
                e_tot = c_data.get("Edu_Total_25_Plus", {}).get("local", 1)
                e_hs = c_data.get("Edu_HS_Diploma", {}).get("local", 0)
                e_bach = c_data.get("Edu_Bachelor", {}).get("local", 0)
                e_mast = c_data.get("Edu_Master", {}).get("local", 0)
                e_prof = c_data.get("Edu_Prof", {}).get("local", 0)
                e_doc = c_data.get("Edu_Doctorate", {}).get("local", 0)
            
                if e_tot == 0: e_tot = 1
            
                # Local is discrete
                vp_hs = (e_hs / e_tot) * 100
                vp_bach = (e_bach / e_tot) * 100
                vp_grad = ((e_mast + e_prof + e_doc) / e_tot) * 100
            
            else:
                # Fallback Defaults
                inc_title = "Income"
                v_low_inc, v_mid_inc, v_high_inc = 15, 45, 40
                age_title = "Age"
                v_u18, v_18_24, v_25_44, v_45_64, v_65_plus = 22, 9, 27, 25, 17
                vp_white, vp_hisp, vp_black, vp_asian, vp_oth = 40, 20, 15, 10, 15
                vp_hs, vp_bach, vp_grad = 20, 40, 40

            # 1. Define DataFrames (Use session_state if available, else Mock)
        
            # Determine State Benchmarks
            # data.py returns `benchmarks` dict inside census_data
            # state_data.get_state_benchmarks returns: state_edu (List), state_age (List), state_race (List)
            bench_data = st.session_state.census_data.get("benchmarks", {}) if "census_data" in st.session_state and st.session_state.census_data else {}
        
            # State Data
            s_edu = bench_data.get("state_edu", [90, 35, 13]) # HS+, Bach+, Adv+
            s_age = bench_data.get("state_age", [22, 9, 27, 25, 17]) # <18, 18-24, 25-44, 45-64, >64
            s_race = bench_data.get("state_race", [57, 20, 14, 7, 2]) # White, Hispanic, Black, Asian, Other
        
            # National Data
            u_edu = bench_data.get("us_edu", [90.6, 35.4, 13.2])
            u_age = bench_data.get("us_age", [21.5, 9.2, 26.5, 24.8, 18.0])
            u_race = bench_data.get("us_race", [57.5, 20.0, 13.7, 6.7, 2.1])
        
            # Logic for Education Bars (Subtraction for Benchmarks)
            # Adv-Degree = Adv+
    with st.container(border=True):
        if "census_data" in st.session_state and st.session_state.census_data:
            # Use shared visualization logic
            # Pass user input address for state detection fallback
            addr_in = st.session_state.get("address_input", "")
            charts = viz_utils.generate_census_charts(st.session_state.census_data, address_input=addr_in)
            
            if charts:
                 r1_c1, r1_c2 = st.columns(2)
                 with r1_c1: st.plotly_chart(charts["income"], key="chart_inc", use_container_width=True)
                 with r1_c2: st.plotly_chart(charts["age"], key="chart_age", use_container_width=True)
                
                 r2_c1, r2_c2 = st.columns(2)
                 with r2_c1: st.plotly_chart(charts["race"], key="chart_race", use_container_width=True)
                 with r2_c2: st.plotly_chart(charts["education"], key="chart_edu", use_container_width=True)
                 
                 # Extra Metrics Grid (4 Rows x 2 Columns)
                 st.markdown("---")
                 c_met = st.session_state.census_data.get("metrics", {})
                 
                 # Helpers
                 def get_val(k): return c_met.get(k, {}).get("local", 0)
                 
                 # Values
                 val_home = get_val("median_home_value_raw")
                 if not val_home: val_home = get_val("median_home_value") # fallback
                 
                 val_tax = get_val("median_re_taxes")
                 val_rent_ratio = get_val("renter_ratio")
                 val_unemp = get_val("unemployment_rate")
                 val_pop_growth = get_val("population_growth") 
                 
                 # Formatters
                 def fmt_dlr_full(v): 
                     return f"${v:,.0f}" if v and v > 0 else "N/A"
                 def fmt_pct(v): 
                     return f"{v}%" if v is not None else "N/A"
                 def fmt_trend(v):
                     if v is None: return "N/A"
                     sym = "+" if v > 0 else ""
                     return f"{sym}{v}%"

                 # CSS for Grid Spacing & Value Size
                 st.markdown("""
                 <style>
                 div[data-testid="metric-container"] {
                    background-color: #F8F9FA;
                    padding: 10px;
                    border-radius: 8px;
                    margin-bottom: 10px;
                 }
                 div[data-testid="metric-container"] > label {
                    font-size: 0.85rem !important;
                    color: #555 !important;
                 }
                 div[data-testid="metric-container"] > div[data-testid="stMetricValue"] {
                    font-size: 1.5rem !important;
                 }
                 </style>
                 """, unsafe_allow_html=True)

                 # Row 1: Median Home Value | Renter Ratio
                 g1_c1, g1_c2 = st.columns(2)
                 with g1_c1:
                     st.metric("Median Home Value", fmt_dlr_full(val_home), help="Median value of owner-occupied units")
                 with g1_c2:
                     st.metric("Renter Ratio", fmt_pct(val_rent_ratio))
                     
                 # Row 2: Median Taxes | Home Price YoY
                 g2_c1, g2_c2 = st.columns(2)
                 with g2_c1:
                     st.metric("Median RE Taxes", fmt_dlr_full(val_tax))
                 with g2_c2:
                     pt_val, pt_lvl = st.session_state.get("price_trend", (None, None))
                     st.metric("Home Price (YoY)", fmt_trend(pt_val), help=f"Median Sale Price Trend. Data Level: {pt_lvl or 'Zip'}")

                 # Row 3: Pop Growth | Unemployment Rate
                 g3_c1, g3_c2 = st.columns(2)
                 with g3_c1:
                     st.metric("Population Growth", fmt_trend(val_pop_growth), help="Population Growth (Census)")
                 with g3_c2:
                     st.metric("Unemployment Rate", fmt_pct(val_unemp))

                 # Row 4: Noise Level | Climate Risk
                 g4_c1, g4_c2 = st.columns(2)
                 with g4_c1:
                     # Noise
                     val_noise = st.session_state.get("noise_data")
                     if val_noise:
                         db = val_noise.get("max_db", 0)
                         if db > 0:
                             severity = "High" if db >= 70 else "Medium" if db >= 55 else "Low"
                             color_icon = "🔴" if db >= 70 else "🟠" if db >= 55 else "🟢"
                             srcs = ", ".join(val_noise.get("sources", []))
                             st.metric("Noise Level", f"{db} dB", delta=f"{color_icon} {severity}", delta_color="off", help=f"Sources: {srcs}")
                         else:
                             st.metric("Noise Level", "<45 dB", delta="🟢 Low Risk", delta_color="off")
                     else:
                         st.metric("Noise Level", "N/A")
                         
                 with g4_c2:
                     # Climate
                     val_fema = st.session_state.get("fema_risk")
                     if val_fema:
                         count = val_fema.get('count', 0)
                         top = val_fema.get('top_hazard', 'None')
                         st.metric("Climate Risk", f"{count} Events", delta=f"Top: {top}", delta_color="off", help="FEMA Declarations since 2000")
                     else:
                         st.metric("Climate Risk", "N/A")
                 
                 # Data Source / Citations
                 citations = st.session_state.census_data.get("metrics", st.session_state.census_data.get("citations", {})) # Guard against structure variation
                 # Actually 'citations' is separate key in data.py
                 citations = st.session_state.census_data.get("citations", {})
                 
                 # Census Level
                 c_level = st.session_state.census_data.get("data_level", "Block Group")
                 trend_data = st.session_state.get("price_trend", (None, None))
                 trend_lvl = trend_data[1] if trend_data else None

                 if citations or trend_lvl:
                      with st.expander("ℹ️ Data Sources & Verification"):
                          st.markdown(f"**Census Data Level:** {c_level} (Used for Taxes/Values)")
                          if trend_lvl:
                              st.markdown(f"**Home Price Trend Source:** RentCast ({trend_lvl} Level Data)")
                          
                          st.markdown(f"**Source:** {citations.get('source', 'US Census Bureau')}")
                          urls = citations.get("urls", {})
                          st.markdown(f"""
                          - **Employment Data (B23025):** [Verify Definition]({urls.get('Employment','#')})
                          - **Real Estate Taxes (B25103):** [Verify Definition]({urls.get('Taxes','#')})
                          - **Tenure/Renters (B25003):** [Verify Definition]({urls.get('Tenure','#')})
                          - **General Search:** [data.census.gov]({urls.get('General','#')})
                          """)
                          st.caption("Note: 'Median RE Taxes' of $0 or 'N/A' often indicates insufficient data for the specific block group or no owner-occupied units with mortgages recorded.")
            else:
                 st.info("No census charts available.")

        else:
             st.info("Census data not available.")



    # --- WIDE LAYOUT FOR RENT & AI (Appended to Main Left) ---
    # This sits visually BELOW the "Analysis" (Col 2) and "Start Analysis" (Col 1) inside the Left Column
    # ignoring the Map height.

    with main_left:
    
        # VISIBILITY CHECK FOR DELIVERY
        delivery_method_check = app_config.get_config().get("delivery_method", "Screen")
        if delivery_method_check == "Email" and (not st.session_state.processing or st.session_state.get("delivery_completed")):
            # If not processing (idle or done), hide result cards
            pass
        else:
            # SCREEN MODE or PROCESSING (In processing, we might want to hide result cards until done? 
            # Actually in standard mode we update session state. If "Email", we want to hide THESE specific result cards entirely.)
        
            # 1. RENTCAST INTEGRATION (Moved per user request)
            with st.container(border=True):
        
                # Debug Check
                if not st.secrets.get("RENTCAST_API_KEY"):
                     st.error("⚠️ Configuration Error: 'RENTCAST_API_KEY' is missing.")
        
                rent_d = st.session_state.get("rent_data", {})
                if rent_d and "comparables" in rent_d:
                    comps = rent_d["comparables"]
                    est_rent = rent_d.get("estimated_rent", 0)
            
                    # Formatting "Estimated Monthly Rent" with Bolds? User said "AI summary... numbers bold".
                    # Assume Rent Metrics standard.
            
                    st.metric("Estimated Monthly Rent", f"${est_rent:,}")
                
                    if comps:
                        st.markdown("#### 🏘️ Comparable Listings")
                        st.caption(f"Based on recent rentals within a 1.5 mile radius.")
                
                        # CSS Style Block
                        style_block = "<style>.comp-table{width:100%;border-collapse:collapse;font-family:'Inter',sans-serif;font-size:0.9rem;color:#202124;}.comp-table th{text-align:left;text-transform:uppercase;font-size:0.75rem;color:#5F6368;border-bottom:1px solid #E0E0E0;padding:10px 5px;font-weight:600;}.comp-table td{padding:12px 5px;border-bottom:1px solid #F1F3F4;vertical-align:top;}.comp-num{display:inline-block;width:24px;height:24px;background-color:#5F6368;color:white;border-radius:50%;text-align:center;line-height:24px;font-size:0.8rem;font-weight:bold;}.addr-main{font-weight:600;font-size:0.95rem;}.addr-sub{color:#5F6368;font-size:0.85rem;}.price-main{font-weight:700;color:#333;}.price-sub{color:#5F6368;font-size:0.85rem;}.sim-badge{background-color:#E6F4EA;color:#137333;padding:3px 8px;border-radius:12px;font-weight:600;display:inline-block;font-size:0.85rem;}.type-main{color:#3C4043;}.type-sub{color:#5F6368;font-size:0.8rem;}</style>"
                
                        rows_html = ""
                        # LIMIT TO TOP 5
                        for i, c in enumerate(comps[:5]):
                            price_fmt = f"${c.get('price', 0):,}"
                            ppsf_fmt = f"${c.get('ppsf', 0):.2f} /ft²" if c.get('ppsf') else "-"
                            dist_fmt = f"{c.get('distance', 0):.2f} mi"
                            beds = c.get('bedrooms', '-')
                            baths = c.get('bathrooms', '-')
                            sqft = f"{c.get('squareFootage', 0):,}"
                            p_type = c.get('propertyType', 'Single Family')
                            y_built = f"Built {c.get('yearBuilt')}" if c.get('yearBuilt') else ""
                    
                            addr1 = c.get('address_line1', 'Unknown')
                            addr2 = c.get('address_line2', '')
                    
                            rows_html += f"""<tr><td><span class="comp-num">{i+1}</span></td><td><div class="addr-main">{addr1}</div><div class="addr-sub">{addr2}</div></td><td><div class="price-main">{price_fmt}</div><div class="price-sub">{ppsf_fmt}</div></td><td style="color:#5F6368;">{dist_fmt}</td><td style="color:#3C4043;">{beds}</td><td style="color:#3C4043;">{baths}</td><td style="color:#3C4043;">{sqft}</td><td><div class="type-main">{p_type}</div><div class="type-sub">{y_built}</div></td></tr>"""

                        full_table = f"""{style_block}<table class="comp-table"><thead><tr><th style="width:5%;"></th><th style="width:30%;">ADDRESS</th><th style="width:20%;">LISTED RENT</th><th style="width:10%;">DISTANCE</th><th style="width:5%;">BEDS</th><th style="width:5%;">BATHS</th><th style="width:10%;">SQ.FT.</th><th style="width:15%;">TYPE</th></tr></thead><tbody>{rows_html}</tbody></table>"""
                
                        st.markdown(full_table, unsafe_allow_html=True)

                    else:
                         st.info("Rental Analysis: No comparable data returned by RentCast.")
                else:
                     st.info("Rental Analysis: No data available.")

            # 2. AI INSIGHT SUMMARY (Moved per user request)
            with st.container(border=True):
                # Header with Score
                c_head, c_score = st.columns([3, 1])
                with c_head:
                    st.subheader("AI Insight Summary")
        
                llm_res = st.session_state.get("llm_result") or {}
                score = llm_res.get("score", 0)
                highlights = llm_res.get("highlights", [])
                risks = llm_res.get("risks", [])
                strategy = llm_res.get("investment_strategy", "No analysis available.")
        
                with c_score:
                    # 75-100: Green "High Opportunity", 60-74 Orng "Good Opportunity", <60 Red "Caution!"
                    delta_color = "normal"
                    if score >= 75:
                        delta_label = "High Opportunity"
                        delta_color = "normal" # We really want Green. delta="text" usually colors green for positive
                        score_icon = "🟢"
                    elif score >= 60:
                        delta_label = "Good Opportunity"
                        score_icon = "🟠"
                        delta_color = "off" # Greyish? Streamlit metrics limited. We can use st.markdown instead.
                    else:
                        delta_label = "Caution!"
                        delta_color = "inverse"
                        score_icon = "🔴"
            
                    # Using custom HTML/Markdown for better color control
                    color_hex = "#137333" if score >= 75 else ("#E37400" if score >= 60 else "#D93025")
                    st.markdown(f"""
                    <div style="text-align: right;">
                        <div style="font-size: 1rem; color: #5f6368;">AI Location Score</div>
                        <div style="font-size: 2rem; font-weight: bold; color: {color_hex};">
                            {score}/100
                        </div>
                        <div style="font-size: 0.9rem; color: {color_hex}; font-weight: 600;">
                            {score_icon} {delta_label}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        
                # [NEW] Display Tier and Tenant Profile
                tier = llm_res.get("location_tier")
                tenant = llm_res.get("tenant_profile")
        
                if tier or tenant:
                     st.markdown("---") # Divider
                     t_c1, t_c2 = st.columns(2)
                     if tier: 
                         t_c1.markdown(f"🏷️ **Location Tier:** {tier}")
                     if tenant:
                         t_c2.markdown(f"👥 **Tenant Profile:** {tenant}")
                     st.markdown("---")

                # Helper to Bold Numbers/Percentages
                import re
                def bold_numbers(text):
                    if not text: return ""
                    # Regex to match: $Dollar, 12,345, 99%, 4.5
                    # Must contain at least one digit to avoid matching punctuation like "," or "."
                    return re.sub(r'(\+?-?\$?\d+(?:,\d+)*(?:\.\d+)?%?)', r'**\1**', str(text))

                st.info(f"**Investment Strategy:**\n{bold_numbers(strategy)}", icon="🤖")
        
                ai_c1, ai_c2 = st.columns(2)
                with ai_c1:
                    st.markdown("**Key Advantages**")
                    # Filter empty strings and strip accidental quotes
                    valid_highlights = [h.strip().strip('"').strip("'") for h in highlights if h and str(h).strip()]
                    for h in valid_highlights:
                        # Remove bold_numbers to prevent formatting issues
                        st.success(f"✅ {h}")

                with ai_c2:
                    st.markdown("**Potential Risks**")
                    valid_risks = [r.strip().strip('"').strip("'") for r in risks if r and str(r).strip()]
                    for r in valid_risks:
                        st.warning(f"⚠️ {r}")


    # --- COLUMN 3: MAP (40%) ---
with col3:
    # VISIBILITY CHECK FOR MAP
    delivery_method_check = app_config.get_config().get("delivery_method", "Screen")
    
    # If Email Mode + Completed -> Maybe show map? Or Hide? 
    # Requirement: "Result via Email Only". Assuming map is also "Result".
    # But User Feedback might be useful.
    # Let's hide Map Result if Email Mode.
    
    if delivery_method_check == "Email" and st.session_state.get("delivery_completed"):
        st.info("Map data sent via email.")
    elif delivery_method_check == "Email":
         # Show placeholder or map for input location?
         # "Interactive Map" is often useful for selecting location. 
         # Let's KEEP the map for Input/Geocoding context, but maybe not the Analysis overlays?
         # Actually, the map code below relies on "poi_data" in session state.
         # If Email mode runs, we DO fetch POI data. 
         # So we can show the map. BUT "Result via Email Only" implies we shouldn't show "Intelligence".
         # Let's compromise: Show Map but maybe clearer title.
         pass
         
    # Card E: Interactive Map
    with st.container(border=True):
        st.subheader("Location Intelligence")
        
        # Center Map on Dummy Location (SF)
        # Check if we have dynamic coordinates
        if "map_center" in st.session_state:
            center_lat, center_lon = st.session_state.map_center
        else:
            center_lat, center_lon = 37.7749, -122.4194
            
        m = folium.Map(location=[center_lat, center_lon], zoom_start=14, prefer_canvas=True)
        
        # DEBUG: Show POI Data
        with st.expander("Debug Map Data"):
            try:
                st.write("--- Debug Start ---")
                
                # Check Config
                cfg_enable = app_config.get_config().get("enable_geoapify", True)
                st.write(f"Geoapify Config Enabled: {cfg_enable}")
                
                # Check Session State
                val = st.session_state.get("poi_data")
                st.write(f"Type of pois: {type(val)}")
                
                if val is None:
                    st.info("ℹ️ No POI data found. Please click 'Start Analysis' to fetch data.")
                elif isinstance(val, list):
                    st.markdown(f"**Count:** {len(val)}")
                    if len(val) > 0:
                        st.json(val[0])
                    else:
                        st.warning("List is empty.")
                else:
                    st.error(f"Unexpected type: {val}")
            except Exception as e:
                st.error(f"Debug Error: {e}") 
        
        # 1. Target Property (Red Star)

        # 1. Target Property (Red Star)
        folium.Marker(
            [center_lat, center_lon],
            popup="Target Property\n123 Market St",
            icon=folium.Icon(color="red", icon="star", prefix='fa')
        ).add_to(m)
        
        # Use map module to generate map with real POIs
        pois_to_map = st.session_state.get("poi_data", [])
        # Overwrite m with the robust map from map.py
        m, legend_items = map.generate_map(center_lat, center_lon, pois_to_map)

        # Render Map
        st_folium(m, height=500, use_container_width=True)

# Card F: Legend (Dynamic based on Map)
    with st.container(border=True):
        st.markdown("#### Map Legend")
        
        # Build dynamic HTML from legend_items
        legend_html = '<div style="display: flex; gap: 10px; flex-wrap: wrap; align-items: center;">'
        
        # 1. Target Property (Always add if not present, though map.py might not return it in items)
        # map.py uses specific styles. We recreate the "Target Pin" style in CSS, but here we just need a visual representation.
        # Target Pin CSS in map.py: blue bg, white border, pulse. 
        # For legend, we can just use a static blue circle with white border.
        
        target_icon_html = """
        <div style="display: flex; align-items: center; gap: 6px; margin-right: 10px;">
            <div style="width: 20px; height: 20px; background-color: #1A73E8; border: 2px solid white; border-radius: 50%; box-shadow: 0 1px 3px rgba(0,0,0,0.3);"></div>
            <span style="font-size: 0.9rem; color: #333; font-weight: 500;">Target Property</span>
        </div>
        """
        legend_html += target_icon_html.replace('\n', ' ')

        # 2. POI Items from map.generate_map
        if legend_items:
            for label, (emoji, color) in legend_items.items():
                if label == "Target Property": continue # Already handled
                
                # Match .amenity-pin style from map.py
                pin_style = f"width: 24px; height: 24px; background-color: white; border-radius: 50%; border: 2px solid {color}; display: flex; alignItems: center; justify-content: center; font-size: 14px; box-shadow: 0 1px 2px rgba(0,0,0,0.15);"
                
                item_html = f"""
                <div style="display: flex; align-items: center; gap: 6px; margin-right: 8px;">
                    <div style="{pin_style}">{emoji}</div> 
                    <span style="font-size: 0.85rem; color: #444;">{label}</span>
                </div>
                """
                legend_html += item_html.replace('\n', ' ')
             
        legend_html += '</div>'
        st.markdown(legend_html, unsafe_allow_html=True)

    # Card E (New Placement): Investment Type & AI Insight Summary
    # If Custom Scoring is Enabled, we might want to prioritize that display or show BOTH?
    # User said: "Stability Score should have a mark to let user know that there is some missing data."
    
    use_custom = st.session_state.get("enable_custom_score", False)
    
    if use_custom:
        with st.container(border=True):
            st.markdown("### 🏆 AI Location Score (Stability)")
            
            # Retrieve Weights
            weights = st.session_state.get("custom_weights", {"school": 50, "crime": 20, "amenity": 20, "income": 10, "transit": 0})
            
            # --- CALCULATE FACTORS ---
            
            # 1. School Quality (Percentile based on Rating)
            # Fetch Schools
            schools_list = st.session_state.get("schools", [])
            # Find closest/best school? Usually assigned school. We use max rating found for now.
            max_rating = 0
            # If we don't have ratings in DB, this stays 0.
            # Assuming 'schools' list might have 'rating' key if we updated data.py?
            # Check data.py logic? We didn't change data.py to fetch ratings from GreatSchools API, only Supabase.
            # Supabase might not have ratings. Assuming 0 (Missing) if not found.
            # For demonstration, if we had ratings:
            for s in schools_list:
                r = s.get("rating", 0) # Assumes 'rating' key exists
                if r > max_rating: max_rating = r
            
            score_school = 0
            if max_rating >= 10: score_school = 100
            elif max_rating >= 9: score_school = 95
            elif max_rating >= 8: score_school = 90
            elif max_rating >= 7: score_school = 80
            elif max_rating >= 6: score_school = 70
            elif max_rating >= 5: score_school = 60
            elif max_rating >= 4: score_school = 50
            elif max_rating >= 3: score_school = 40
            elif max_rating >= 2: score_school = 30
            elif max_rating >= 1: score_school = 20
            else: score_school = 0 # Missing
            
            # 2. Crime (Min-Max)
            # Data Missing -> 0
            score_crime = 0
            
            # 3. Amenities (Rubric)
            pois_list = st.session_state.get("poi_data", [])
            poi_count = len(pois_list) if isinstance(pois_list, list) else 0
            
            score_amenity = 0
            # New Rubric:
            # > 50 -> 100
            # 40-49 -> 85
            # 30-39 -> 70
            # 20-29 -> 50
            # 10-19 -> 30
            # < 10 -> 10
            if poi_count > 50: score_amenity = 100
            elif poi_count >= 40: score_amenity = 85
            elif poi_count >= 30: score_amenity = 70
            elif poi_count >= 20: score_amenity = 50
            elif poi_count >= 10: score_amenity = 30
            else: score_amenity = 10
            
            # 4. Income (Ratio Table)
            # National Median 2022 (approx) = 75149
            nat_inc = 75149
            loc_inc = st.session_state.census_data.get("metrics", {}).get("median_income", {}).get("local", 0)
            
            score_income = 0
            if loc_inc > 0:
                ratio = loc_inc / nat_inc
                if ratio > 1.5: score_income = 100
                elif ratio >= 1.3: score_income = 90
                elif ratio >= 1.1: score_income = 80
                elif ratio >= 0.9: score_income = 70
                elif ratio >= 0.7: score_income = 50
                elif ratio >= 0.5: score_income = 30
                else: score_income = 10
            
            # 5. Transit (Missing)
            score_transit = 0
            
            # --- STABILITY SCORE ---
            # Wi * Xi
            # Normalize weights if sum != 100
            tot_w = sum(weights.values())
            stability_score = 0
            if tot_w > 0:
                weighted_sum = (score_school * weights["school"]) + \
                               (score_crime * weights["crime"]) + \
                               (score_amenity * weights["amenity"]) + \
                               (score_income * weights["income"]) + \
                               (score_transit * weights["transit"])
                stability_score = weighted_sum / tot_w
                
            # Formatting
            st.metric("Stability Score", f"{stability_score:.1f}/100")
            
            # Breakdown Table
            st.markdown("#### Factor Breakdown")
            
            factors = [
                {"Factor": "School Quality", "Weight": f"{weights['school']}%", "Score": score_school},
                {"Factor": "Crime Rate", "Weight": f"{weights['crime']}%", "Score": 0, "Note": "Data Unavailable"},
                {"Factor": "Amenities", "Weight": f"{weights['amenity']}%", "Score": score_amenity, "Note": f"{poi_count} POIs"},
                {"Factor": "Income Level", "Weight": f"{weights['income']}%", "Score": score_income},
                {"Factor": "Transit", "Weight": f"{weights['transit']}%", "Score": 0, "Note": "Data Unavailable"},
            ]
            
            # Simple HTML Table
            rows = ""
            for f in factors:
                n = f.get("Note", "")
                rows += f"<tr><td>{f['Factor']}</td><td>{f['Weight']}</td><td>{f['Score']}</td><td style='font-size:0.8em; color:#666;'>{n}</td></tr>"
                
            st.markdown(f"""
            <table style="width:100%; border-collapse: collapse;">
                <tr style="border-bottom:1px solid #ddd; text-align:left;"><th>Factor</th><th>Weight</th><th>Score</th><th>Notes</th></tr>
                {rows}
            </table>
            """, unsafe_allow_html=True)
            
            if score_crime == 0 or score_transit == 0:
                st.caption("⚠️ Some factors (Crime, Transit) assume score 0 due to missing data.")

    # Card: Investment Analysis (Standard) - Always Show or Custom Only?
    # User said "Add AI Location Score... ENABLED ONLY WHEN...". 
    # Implies Standard Logic runs by default. 
    # If Custom is ON, do we hide Standard?
    # User didn't say to hide standard. Let's keep Standard as "Investment Analysis" and Custom as "Location Score".
    
    with st.container(border=True):
        st.markdown("### Investment Analysis")
        
        # --- MARKET SCORE / INVESTMENT TYPE LOGIC ---
        # 1. Gather Data
        
        # A. Rent-to-Price Ratio (30%)
        # Needs Rent (RentCast estimated_rent) and Price (User Input)
        score_rtp = 0
        w_rtp = 30
        
        # Guard against None
        rent_d = st.session_state.get("rent_data") or {}
        # Fetch estimated rent or fall back to 'rent'
        rent_val= rent_d.get("estimated_rent", 0) 
        if not rent_val: rent_val = rent_d.get("rent", 0)
        
        price_val = st.session_state.get("input_home_price", 0)
        
        val_rtp_ratio = 0
        if rent_val > 0 and price_val > 0:
            val_rtp_ratio = (rent_val / price_val) * 100
            # Thresholds:
            # >= 0.8% -> Cash Flow (Score 0 based on mapping logic? user said: "≥ 0.8% → Cash Flow")
            # Wait, Scoring Logic:
            # User: "Market Score < 40 → Cash Flow", "Market Score ≥ 65 → Appreciation"
            # Component Thresholds:
            # RTP >= 0.8% -> Cash Flow. 
            # If Cash Flow is "Low Score" (0), then >= 0.8% should give 0?
            # User: "For any reason, that any aspect is N/A... set weight 0".
            # Let's align "Appreciation" = 100, "Cash Flow" = 0.
            # RTP: >= 0.8% (Cash Flow) -> 0. < 0.5% (Appreciation) -> 100.
            if val_rtp_ratio < 0.5: score_rtp = 100
            elif val_rtp_ratio < 0.8: score_rtp = 50
            else: score_rtp = 0
        else:
            w_rtp = 0 # N/A

        # B. Home Price Trend (25%)
        score_trend = 0
        w_trend = 25
        
        pt_val, _ = st.session_state.get("price_trend", (None, None))
        if pt_val is not None:
            # +5% -> Appr (100)
            # -2 to 5 -> Neutral (50)
            # < -2 -> Cash Flow (0)
            if pt_val >= 5: score_trend = 100
            elif pt_val >= -2: score_trend = 50
            else: score_trend = 0
        else:
            w_trend = 0

        # C. Pop Growth (15%) - Prefer 5-Year
        score_pop = 0
        w_pop = 15
        
        # Check metrics
        census_d = st.session_state.get("census_data") or {}
        metrics = census_d.get("metrics", {})
        pg_5y = metrics.get("pop_growth_5y", {}).get("local")
        
        if pg_5y is not None:
            # +3% -> Appr (100)
            # -2 to 3 -> Neutral (50)
            # < -2 -> Cash Flow (0)
            if pg_5y >= 3: score_pop = 100
            elif pg_5y >= -2: score_pop = 50
            else: score_pop = 0
        else:
            w_pop = 0

        # D. Income Growth (10%)
        score_inc = 0
        w_inc = 10
        
        ig_5y = metrics.get("income_growth_5y", {}).get("local")
        if ig_5y is not None:
            # +5% -> Appr (100)
            # 0-5 -> Neutral (50)
            # < 0 -> Cash Flow (0)
            if ig_5y >= 5: score_inc = 100
            elif ig_5y >= 0: score_inc = 50
            else: score_inc = 0
        else:
            w_inc = 0

        # E. Effective Tax Rate (10%)
        score_tax = 0
        w_tax = 10
        
        m_tax = metrics.get("median_re_taxes", {}).get("local", 0)
        m_val = metrics.get("median_home_value_raw", {}).get("local", 0)
        
        if m_val > 0:
            eff_tax = (m_tax / m_val) * 100
            # > 2% -> Appr (100) (User rule: Appreciation (cash flow suppressed)) -> Wait. 
            # User said: "2% → Appreciation (cash flow suppressed)". 
            # Usually high tax -> bad for cash flow -> good for appreciation? 
            # If logic is Appr=100, then Tax>2% = 100.
            # < 1% -> Cash Flow -> 0.
            if eff_tax > 2: score_tax = 100
            elif eff_tax >= 1: score_tax = 50
            else: score_tax = 0
        else:
            w_tax = 0

        # F. Renter Ratio (10%)
        score_rent = 0
        w_rent = 10
        
        rr_val = metrics.get("renter_ratio", {}).get("local")
        if rr_val is not None:
            # < 30 -> Appr (100)
            # 30-45 -> Mixed (50)
            # > 45 -> Cash Flow (0)
            if rr_val < 30: score_rent = 100
            elif rr_val <= 45: score_rent = 50
            else: score_rent = 0
        else:
            w_rent = 0
            
        # CALCULATION
        total_weight = w_rtp + w_trend + w_pop + w_inc + w_tax + w_rent
        final_market_score = 0
        inv_type = "N/A"
        
        if total_weight > 0:
            weighted_sum = (score_rtp * w_rtp) + (score_trend * w_trend) + \
                           (score_pop * w_pop) + (score_inc * w_inc) + \
                           (score_tax * w_tax) + (score_rent * w_rent)
                           
            # Normalize to 100 scale?
            # If total_weight < 100, we need to scale up?
            # User: "re-normalize other factors".
            # Formula: weighted_sum / total_weight.
            # Example: Only Rent-to-Price (30) avail. Score 100.
            # Weighted Sum = 3000. Total Weight = 30. Result = 100. Correct.
            
            final_market_score = weighted_sum / total_weight
            final_market_score = int(round(final_market_score))
            
            # Determine Type
            if final_market_score >= 65: inv_type = "Appreciation"
            elif final_market_score >= 40: inv_type = "Mixed"
            else: inv_type = "Cash Flow"
        
        # DISPLAY
        # Color coding
        c_color = "green" if inv_type == "Appreciation" else "orange" if inv_type == "Mixed" else "blue"
        
        st.markdown(f"""
        <div style="background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin-bottom: 20px;">
            <h4 style="margin:0; color:#333;">Investment Type: <span style="color:{c_color}">{inv_type}</span></h4>
        </div>
        """, unsafe_allow_html=True)
        
        # LLM Result Display
        llm_res_text = ""
        res_obj = st.session_state.get("llm_result", {})
        if res_obj:
             llm_res_text = res_obj.get("analysis", "")
             
        if llm_res_text:
            st.write(llm_res_text)
        elif st.session_state.get("processing", False):
            st.spinner("Generating AI Analysis...")
        else:
             if st.session_state.get("census_data"):
                 st.info("Analysis Ready. See metrics above.")
             else:
                 st.info("Click 'Analyze' to generate AI insights.")

    # Card G: Nearby Schools [NEW]
    with st.container(border=True):
        st.subheader("Nearby Schools (3 Mile Radius)")
        schools = st.session_state.get("schools", [])
        if schools:
            for s in schools[:5]: # Show top 5
                # Assuming s has keys: name, address, dist_miles, nces_id, city, state, zip
                dist = s.get('dist_miles', 0)
                name = s.get('name', 'Unknown School')
                addr = s.get('address', '')
                city = s.get('city', '')
                state_code = s.get('state', '')
                
                with st.expander(f"🎓 {name} ({dist:.2f} mi)"):
                    st.write(f"Address: {addr}, {city}, {state_code} {s.get('zip','')}")
                    
                    # Fix: Use Google Search for "GreatSchools rating" as it's more robust
                    # GreatSchools internal search is sensitive to City names (e.g. Allston vs Boston)
                    import urllib.parse
                    query = f"GreatSchools rating {name} {city} {state_code}"
                    q_enc = urllib.parse.quote(query)
                    
                    # Google Search Link
                    gs_url = f"https://www.google.com/search?q={q_enc}"
                    st.markdown(f"[View GreatSchools Rating (Google) ↗]({gs_url})")
        else:
             st.info("No schools found within 3 miles (or DB connection skipped).")


    # --- USER FEEDBACK LOOP ---
    # --- USER FEEDBACK LOOP ---
    with st.expander("🎯 Fine-tune AI Preferences", expanded=True):
        st.caption("Tell AI your preferences (e.g., 'I dislike noise', 'I need a park nearby').")
        
        # Custom Header for Feedback
        st.markdown("### Your Feedback")
        
        # Feedback Input (No Form)
        # Using label="Your Feedback" but hidden visibility to ensure aria-label exists for CSS
        user_input = st.text_area("Your Feedback", height=100, 
                                 placeholder="For example: I do not want to be close to the highway...",
                                 key="feedback_input",
                                 label_visibility="collapsed")
                                 
        if st.button("Submit Feedback"):
            target_email = st.session_state.google_user.get("email") if st.session_state.get("google_user") else st.session_state.get("user_email_input")
            
            if not target_email or target_email == "unknown":
                st.error("Please sign in to save preferences.")
            elif not user_input:
                st.warning("Please enter some feedback.")
            else:
                try:
                    current_prefs = supabase_utils.get_user_preferences(target_email)
                    new_summary = llm.refine_preferences(current_prefs, user_input)
                    success, err_msg = supabase_utils.save_user_preferences(target_email, new_summary)
                    if success:
                        st.toast("✅ AI has remembered your preference!")
                        # Optional cleanup if we could, but streamlit can't easily clear widget state effectively without tricky callbacks
                    else:
                        st.error(f"Failed to save preferences. Details: {err_msg}")
                except Exception as e:
                    st.error(f"Error: {e}")

    # --- STAR RATING COMPONENT ---
    # --- CSS FOR LARGER STARS ---
    st.markdown("""
    <style>
    div[data-testid="stFeedback"] > ul > li > span {
        font-size: 2.5rem !important;
    }
    div[data-testid="stFeedback"] {
        margin-bottom: -15px; 
    }
    </style>
    """, unsafe_allow_html=True)

    # --- STAR RATING COMPONENT ---
    with st.container(border=True):
        st.markdown("### Rate this Analysis")
        
        # Session state for rating
        if "rating_submitted" not in st.session_state:
            st.session_state.rating_submitted = False
            
        rate_col1, rate_col2 = st.columns([2, 1])
        
        with rate_col1:
            # Use st.feedback if available
            rating_val = 0
            # Disable if submitted
            disabled = st.session_state.rating_submitted
            
            if hasattr(st, "feedback"):
                # Using key='user_rating_widget' 
                st.feedback("stars", key="user_rating_widget", disabled=disabled)
            else:
                st.slider("Rating", 0.0, 5.0, 0.0, 0.5, key="user_rating_widget", disabled=disabled)
        
        with rate_col2:
            st.write("") # Spacer
            st.write("")
            
            if st.session_state.rating_submitted:
                 st.info("User already submitted.")
            else:
                if st.button("Submit Rating", type="primary", use_container_width=True):
                     # Retrieve value from widget state
                     raw_val = st.session_state.get("user_rating_widget")
                     
                     # Adjust for 0-index if using feedback
                     final_rating = 0
                     if raw_val is not None:
                         if hasattr(st, "feedback") and isinstance(raw_val, int):
                             final_rating = raw_val + 1
                         else:
                             final_rating = raw_val
                     
                     if final_rating > 0:
                        target_email = st.session_state.google_user.get("email") if st.session_state.get("google_user") else st.session_state.get("user_email_input")
                        ctx = f"Address: {st.session_state.get('address_input', 'Unknown')}"
                        
                        st.session_state.rating_submitted = True # Lock it
                        
                        if target_email:
                            # We can try/except here just in case
                            try:
                                supabase_utils.save_user_rating(target_email, final_rating, context=ctx)
                                st.toast(f"✅ Submitted {final_rating} Stars!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error saving rating: {e}")
                                st.session_state.rating_submitted = False # Unlock if failed
                        else:
                            st.toast(f"✅ Thanks for rating!")
                            st.rerun()
                     else:
                        st.warning("Please select stars first.")
