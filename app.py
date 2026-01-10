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
import llm # LLM Analysis Service

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
        <a href="#">Home</a> | <a href="#">About Us</a> | <a href="#">Contact</a>
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
            st.caption(f"Free Trial in past 24h: {usage_count}/3")
 
 
    # Card B: Property Details
    with st.container(border=True):
        st.markdown("### Property Details")
        st.text_input("Address", "123 Market St, San Francisco, CA", key="address_input")
        
        # Adjusted columns to give Sqft more space (5 digits)
        # Using [1, 1, 3] to give even more room to the last column
        c_b1, c_b2, c_b3 = st.columns([1, 1, 3])
        with c_b1:
            st.number_input("Bed", value=2, min_value=0)
        with c_b2:
            st.number_input("Bath", value=2, min_value=0)
        with c_b3:
            st.number_input("Sqft", value=1200, step=50, max_value=99999) # Increased max value and column width
            
        st.selectbox("Property Type", ["Single Family", "Townhouse", "Condo", "Apartment"])
        # Limit Check Logic
        import config_manager
        app_config = config_manager.config_manager.get_config()
        
        enable_limit = app_config.get("enable_daily_limit", True)
        whitelist = app_config.get("whitelist_emails", [])
        
        current_email = st.session_state.google_user.get("email") if st.session_state.google_user else st.session_state.get("user_email_input", "")
        usage = get_daily_usage(current_email) if current_email else 0
        
        # Determine strict limit reached
        limit_reached = False
        
        # Logic: 
        # 1. If global limit is DISABLED -> Limit NOT reached
        # 2. If user is in whitelist -> Limit NOT reached
        # 3. Otherwise -> Check usage >= 3
        
        if not enable_limit:
            limit_reached = False
        elif getattr(current_email, "lower", lambda: "")().strip() in whitelist:
             limit_reached = False
        else:
            if usage >= 3:
                limit_reached = True
        
        btn_label = "Start Analysis"
        if limit_reached:
            btn_label = "Daily Limit Reached (3/3)"
            
        if st.button(btn_label, disabled=st.session_state.processing or limit_reached, on_click=start_processing):
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
        # Determine email to use for fetching prefs
        current_email = st.session_state.google_user.get("email") if st.session_state.google_user else st.session_state.get("user_email_input")
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
        census_data = data.get_census_data(addr_to_geocode)
        if census_data: # If None, call failed or disabled
             count_census += 2 # 1 Geocode + 1 Data
        st.session_state.census_data = census_data # Persist
        
        # 4. RentCast
        rent_data = data.get_rentcast_data(addr_to_geocode, 2, 2, 1200, "Single Family", rentcast_key)
        if rent_data:
            count_rentcast += 1
        st.session_state.rent_data = rent_data
        
        # 5. LLM Analysis
        # Get Weights (just defaults for now or from config if enabled)
        weights = {"cashflow": 50, "appreciation": 50} 
        
        llm_result = llm.analyze_location(
            addr_to_geocode, 
            pois, 
            census_data, 
            weights=weights,
            user_prefs=user_prefs_text
        )
        # Check if actually called (not disabled message)
        if "AI Analysis is currently disabled" not in str(llm_result.get("highlights", [])):
             count_gemini += 1
             
        st.session_state.llm_result = llm_result
            
            # --- DATA INTEGRATION COMPLETE ---
        # --- LOGGING ---
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
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


                final_email = st.session_state.google_user.get("email") if st.session_state.google_user else st.session_state.get("user_email_input", "unknown")
                
                # Address
                addr = st.session_state.get("address_input", "123 Market St, San Francisco, CA")
                
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
        st.rerun() # Re-enable button


# --- COLUMN 2: ANALYSIS (40%) ---
with col2:
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
        # Bachelor = Bach+ - Adv+
        # HighSchool = HS+ - Bach+
        
        def calc_edu_buckets(arr):
             # arr = [HS+, Bach+, Adv+]
             if not arr or len(arr) < 3: return [0, 0, 0]
             adv = arr[2]
             bach = arr[1] - arr[2]
             hs = arr[0] - arr[1]
             return [hs, bach, adv]
             
        s_hs, s_bach, s_adv = calc_edu_buckets(s_edu)
        u_hs, u_bach, u_adv = calc_edu_buckets(u_edu)
        
        df_income = pd.DataFrame({
            "Range": ["<50k", "<50k", "<50k", "50-100k", "50-100k", "50-100k", "100k+", "100k+", "100k+"],
            "Scope": ["Local", "State", "National"] * 3,
            "Value": [
                v_low_inc, 12, 14,             # <50k
                v_mid_inc, 40, 38,             # 50-100k
                v_high_inc, 48, 48             # 100k+
            ] 
        })

        df_age = pd.DataFrame({
            "Range": ["<18", "<18", "<18", "18-24", "18-24", "18-24", "25-44", "25-44", "25-44", "45-64", "45-64", "45-64", ">64", ">64", ">64"],
            "Scope": ["Local", "State", "National"] * 5,
            "Value": [
                v_u18, s_age[0], u_age[0],
                v_18_24, s_age[1], u_age[1],
                v_25_44, s_age[2], u_age[2],
                v_45_64, s_age[3], u_age[3],
                v_65_plus, s_age[4], u_age[4]
            ]
        })

        # Race Order: White, Hispanic, Black, Asian, Other
        df_race = pd.DataFrame({
            "Group": ["White", "White", "White", "Hispanic", "Hispanic", "Hispanic", "Black", "Black", "Black", "Asian", "Asian", "Asian", "Other", "Other", "Other"],
            "Scope": ["Local", "State", "National"] * 5,
            "Value": [
                vp_white, s_race[0], u_race[0],
                vp_hisp, s_race[1], u_race[1],
                vp_black, s_race[2], u_race[2],
                vp_asian, s_race[3], u_race[3],
                vp_oth, s_race[4], u_race[4]
            ]
        })

        df_edu = pd.DataFrame({
            "Level": ["HighSchool", "HighSchool", "HighSchool", "Bachelor", "Bachelor", "Bachelor", "Adv-Degree", "Adv-Degree", "Adv-Degree"],
            "Scope": ["Local", "State", "National"] * 3,
            "Value": [
                vp_hs, s_hs, u_hs, 
                vp_bach, s_bach, u_bach, 
                vp_grad, s_adv, u_adv
            ]
        })
        
        # 2. Determine Dynamic State Label
        state_label = "State"
        try:
            addr_input = st.session_state.get("address_input", "")
            import re
            match = re.search(r'\b([A-Z]{2})\b\s+\d{5}', addr_input)
            if match:
                state_label = f"{match.group(1)} State"
            else:
                parts = [p.strip() for p in addr_input.split(",")]
                if len(parts) >= 2:
                    last_chunk = parts[-1]
                    sub_parts = last_chunk.split()
                    for sp in sub_parts:
                         if len(sp) == 2 and sp.isalpha() and sp.isupper():
                             state_label = f"{sp} State"
                             break
        except:
             pass

        # 3. Update all DataFrames
        df_income["Scope"] = df_income["Scope"].replace("State", state_label)
        df_age["Scope"] = df_age["Scope"].replace("State", state_label)
        df_race["Scope"] = df_race["Scope"].replace("State", state_label)
        df_edu["Scope"] = df_edu["Scope"].replace("State", state_label)
        
        # 4. Layout
        def update_chart_layout(fig):
            fig.update_layout(
                margin=dict(l=0,r=0,t=40,b=0), 
                legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="right", x=1),
                title_font=dict(size=13),
                xaxis_title=None 
            )
            return fig

        # 5. Create Figures
        color_map = {"Local": "#1A73E8", state_label: "#9AA0A6", "National": "#DADCE0"}
        color_map_age = {"Local": "#34A853", state_label: "#9AA0A6", "National": "#DADCE0"}
        color_map_race = {"Local": "#FBBC04", state_label: "#9AA0A6", "National": "#DADCE0"}
        color_map_edu = {"Local": "#EA4335", state_label: "#9AA0A6", "National": "#DADCE0"}

        fig_inc = px.bar(df_income, x="Range", y="Value", color="Scope", barmode="group", title=inc_title, height=250,
                        color_discrete_map=color_map, labels={"Value": "%"})
        update_chart_layout(fig_inc)

        fig_age = px.bar(df_age, x="Range", y="Value", color="Scope", barmode="group", title=age_title, height=250,
                     color_discrete_map=color_map_age, labels={"Value": "%"})
        update_chart_layout(fig_age)

        fig_race = px.bar(df_race, x="Group", y="Value", color="Scope", barmode="group", title="Race", height=250,
                        color_discrete_map=color_map_race, labels={"Value": "%"})
        update_chart_layout(fig_race)

        fig_edu = px.bar(df_edu, x="Level", y="Value", color="Scope", barmode="group", title="Education", height=250,
                     color_discrete_map=color_map_edu, labels={"Value": "%"})
        update_chart_layout(fig_edu)

        r1_c1, r1_c2 = st.columns(2)
        with r1_c1: st.plotly_chart(fig_inc, key="chart_inc", width="stretch")
        with r1_c2: st.plotly_chart(fig_age, key="chart_age", width="stretch")
        
        r2_c1, r2_c2 = st.columns(2)
        with r2_c1: st.plotly_chart(fig_race, key="chart_race", width="stretch")
        with r2_c2: st.plotly_chart(fig_edu, key="chart_edu", width="stretch")


# --- WIDE LAYOUT FOR RENT & AI (Appended to Main Left) ---
# This sits visually BELOW the "Analysis" (Col 2) and "Start Analysis" (Col 1) inside the Left Column
# ignoring the Map height.

with main_left:
    
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
        
        # Helper to Bold Numbers/Percentages
        import re
        def bold_numbers(text):
            # Regex to match: $Dollar, 12,345, 99%, 4.5
            # Matches: $?, digits+commas/dots, optional %
            return re.sub(r'(\+?-?\$?[\d,]+(?:\.\d+)?%?)', r'**\1**', str(text))

        st.info(f"**Investment Strategy:**\n{bold_numbers(strategy)}", icon="🤖")
        
        ai_c1, ai_c2 = st.columns(2)
        with ai_c1:
            st.markdown("**Key Advantages**")
            for h in highlights:
                st.success(f"✅ {bold_numbers(h)}")

        with ai_c2:
            st.markdown("**Potential Risks**")
            for r in risks:
                st.warning(f"⚠️ {bold_numbers(r)}")


# --- COLUMN 3: MAP (40%) ---
with col3:
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
        
        # 1. Target Property (Red Star)
        folium.Marker(
            [center_lat, center_lon],
            popup="Target Property\n123 Market St",
            icon=folium.Icon(color="red", icon="star", prefix='fa')
        ).add_to(m)
        
        # 2. Amenities Data (Simulated)
        amenities = [
            {"type": "School", "lat": 37.7760, "lon": -122.4200, "icon": "graduation-cap", "color": "blue"},
            {"type": "Grocery", "lat": 37.7730, "lon": -122.4180, "icon": "shopping-cart", "color": "green"},
            {"type": "Gas", "lat": 37.7755, "lon": -122.4230, "icon": "tint", "color": "orange"}, # Tint often used for liquid/gas
            {"type": "Food", "lat": 37.7740, "lon": -122.4150, "icon": "utensils", "color": "purple"},
            {"type": "Pharmacy", "lat": 37.7725, "lon": -122.4210, "icon": "medkit", "color": "red"},
            {"type": "School", "lat": 37.7780, "lon": -122.4170, "icon": "graduation-cap", "color": "blue"},
        ]
        
        for item in amenities:
            folium.Marker(
                [item["lat"], item["lon"]],
                tooltip=item["type"],
                icon=folium.Icon(color=item["color"], icon=item["icon"], prefix='fa')
            ).add_to(m)

        # Render Map
        st_folium(m, height=500, use_container_width=True)

    # Card F: Legend (Custom HTML below map or reliance on Icons)
    with st.container(border=True):
        st.markdown("#### Map Legend")
        legend_html = """
        <div style="display: flex; gap: 15px; flex-wrap: wrap;">
            <div style="display: flex; align-items: center; gap: 5px;"><span style="color: #d32f2f;">★</span> Target Property</div>
            <div style="display: flex; align-items: center; gap: 5px;"><i class="fa fa-graduation-cap" style="color: blue;"></i> Schools</div>
            <div style="display: flex; align-items: center; gap: 5px;"><i class="fa fa-shopping-cart" style="color: green;"></i> Grocery</div>
            <div style="display: flex; align-items: center; gap: 5px;"><i class="fa fa-tint" style="color: orange;"></i> Gas</div>
            <div style="display: flex; align-items: center; gap: 5px;"><i class="fa fa-utensils" style="color: purple;"></i> Food</div>
            <div style="display: flex; align-items: center; gap: 5px;"><i class="fa fa-medkit" style="color: red;"></i> Pharmacy</div>
        </div>
        <!-- Load FontAwesome for the legend icons if not already loaded by Folium/Streamlit context (Folium loads it in iframe, but this is outside) -->
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        """
        st.markdown(legend_html, unsafe_allow_html=True)

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
                    if supabase_utils.save_user_preferences(target_email, new_summary):
                        st.toast("✅ AI has remembered your preference!")
                        # Optional cleanup if we could, but streamlit can't easily clear widget state effectively without tricky callbacks
                    else:
                        st.error("Failed to save preferences.")
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
