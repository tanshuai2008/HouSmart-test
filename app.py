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

def run_analysis_flow():
    st.session_state.processing = True
    st.session_state.analyzed = False

# --- Main Layout ---
col1, col2, col3 = st.columns([20, 40, 40])

# ==========================================
# COLUMN 1: CONTROLS (20%)
# ==========================================
with col1:
    with st.container():
        st.markdown('<div class="panel-container">', unsafe_allow_html=True)
        
        st.markdown("### Location Analysis")
        
        email = st.text_input("Email Address", placeholder="Required", key="email_input")
        
        # Model Selection
        gemini_keys = []
        main_key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
        if main_key: gemini_keys.append(main_key)
        for i in range(2, 11):
            val = st.secrets.get(f"GEMINI_API_KEY_{i}") or os.getenv(f"GEMINI_API_KEY_{i}")
            if val: gemini_keys.append(val)
        
        available_models = ["models/gemini-1.5-flash"]
        if gemini_keys:
            llm.configure_genai(gemini_keys)
            try:
                models = llm.get_available_models()
                if models and not str(models[0]).startswith("Error"):
                    available_models = models
            except: pass
            
        st.selectbox("Model Selection", available_models, index=0, key="input_model")
        
        st.selectbox("Scoring Method", ["Default", "Normalized & Weighted"], disabled=True, key="scoring_method")
        
        st.markdown("---")
        
        st.text_input("Address 1", placeholder="Enter address...", key="input_address")
        
        # Detailed Property Inputs
        st.markdown("**Property Details**")
        st.caption("Bedroom / Bathroom / Size (sqft)")
        
        c_bed, c_bath, c_sqft = st.columns(3)
        with c_bed:
            st.number_input("Bed", min_value=0, max_value=10, value=2, label_visibility="collapsed", key="input_bedrooms")
        with c_bath:
            st.number_input("Bath", min_value=0, max_value=10, value=1, label_visibility="collapsed", key="input_bathrooms")
        with c_sqft:
            st.number_input("Sqft", min_value=0, max_value=10000, value=1000, step=50, label_visibility="collapsed", key="input_sqft")
            
        st.selectbox("Property Type", ["Apartment", "Single Family", "Condo", "Townhouse"], index=0, key="input_property_type")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("Analyze", type="primary", use_container_width=True):
             run_analysis_flow()

        if st.session_state.email_input:
            usage = get_daily_usage(st.session_state.email_input)
            st.caption(f"Daily Trials: {usage}/3")
            
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# PROCESSING LOGIC
# ==========================================
if st.session_state.processing:
    # Use a placeholder in Col 2 for the loader
    with col2:
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

        components.render_loader(loader_placeholder, 20)
        
        # Logging
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_dir = "logs"
        if not os.path.exists(log_dir): os.makedirs(log_dir)
        try:
             # CSV Log
             with open(os.path.join(log_dir, "usage_logs.csv"), 'a', newline='', encoding='utf-8') as f:
                 writer = csv.writer(f)
                 writer.writerow([timestamp, user_email, address])
             # GSheet Log
             sheet = connect_to_gsheet()
             if sheet: sheet.append_row([timestamp, user_email, address])
        except: pass
        
        components.render_loader(loader_placeholder, 40)
        
        # 1. POI
        geo_key = st.secrets.get("GEOAPIFY_API_KEY")
        pois, lat, lon = data.get_poi(address, api_key=geo_key)
        st.session_state.pois = pois
        st.session_state.lat = lat
        st.session_state.lon = lon
        
        components.render_loader(loader_placeholder, 50)

        # 2. Census
        census = data.get_census_data(address)
        if not census:
            census = llm.estimate_census_data(address, model_name=st.session_state.input_model)
            census['source'] = "AI Estimation"
        st.session_state.census = census
        
        components.render_loader(loader_placeholder, 70)
        
        # 3. Rent Analysis
        rent_key = st.secrets.get("RENTCAST_API_KEY") or os.getenv("RENTCAST_API_KEY")
        if rent_key:
            rent_data = data.get_rentcast_data(
                address, 
                st.session_state.input_bedrooms, 
                st.session_state.input_bathrooms,
                st.session_state.input_sqft,
                st.session_state.input_property_type, 
                rent_key
            )
            st.session_state.rent_data = rent_data
        else:
            st.session_state.rent_data = None
        
        components.render_loader(loader_placeholder, 80)
        
        # 4. LLM Analysis
        model_name = st.session_state.input_model
        analysis = llm.analyze_location(address, pois, census, model_name=model_name)
        st.session_state.analysis = analysis
        
        components.render_loader(loader_placeholder, 100)
        
        st.session_state.processing = False
        st.session_state.analyzed = True
        st.rerun()

# ==========================================
# RENDER ANALYTICS & MAP (Columns 2 & 3)
# ==========================================
if st.session_state.analyzed:
    census = st.session_state.census
    rent_data = st.session_state.get("rent_data")

    # COLUMN 2: ANALYTICS (40%)
    with col2:
        # --- RENT ANALYSIS MODULE ---
        if rent_data:
            st.markdown('<div class="panel-container">', unsafe_allow_html=True)
            st.subheader("Rent Analysis")
            
            # Rent Metrics
            est_rent = rent_data.get('estimated_rent', 0)
            low, high = rent_data.get('rent_range', [0, 0])
            
            # Census Benchmark
            census_median_rent = 0
            metrics = census.get('metrics', {})
            if metrics:
                s_rent = metrics.get('median_gross_rent', "N/A")
                if s_rent != "N/A":
                    census_median_rent = int(str(s_rent).replace('$','').replace(',',''))
            
            # Displays
            rc1, rc2 = st.columns(2)
            with rc1:
                st.metric("Estimated Rent", f"${est_rent:,}", f"${low:,} - ${high:,}")
            with rc2:
                if census_median_rent > 0:
                     delta = est_rent - census_median_rent
                     st.metric("Census Median Rent", f"${census_median_rent:,}", f"{delta:+,} vs Avg")
                else:
                    st.metric("Census Median Rent", "N/A", "No Local Data")

            # Comparables Chart & List
            comps = rent_data.get('comparables', [])
            if comps:
                st.markdown("**Comparable Rents**")
                
                # Bar Chart for Comps
                df_comps = pd.DataFrame(comps)
                # Shorten address for chart label
                df_comps['Label'] = df_comps['address'].apply(lambda x: x.split(',')[0] if x else "N/A")
                
                chart_comps = alt.Chart(df_comps).mark_bar().encode(
                    x=alt.X('Label', sort='-y', title=None),
                    y=alt.Y('price', title='Rent ($)'),
                    color=alt.Color('Label', legend=None),
                    tooltip=['address', 'price', 'similarity']
                ).properties(height=150)
                
                st.altair_chart(chart_comps, use_container_width=True)

                st.markdown("**Comp Details**")
                for comp in comps:
                    st.markdown(f"""
                    <div style="background: #F8FAFC; padding: 8px; border-radius: 4px; margin-bottom: 8px; border: 1px solid #E2E8F0;">
                        <div style="font-weight: 500; font-size: 13px;">{comp.get('address')}</div>
                        <div style="display: flex; justify-content: space-between; font-size: 12px; color: #64748B;">
                           <span>${comp.get('price', 0):,} / mo</span>
                           <span>Similarity: {comp.get('similarity', 0)}%</span> 
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.caption("No comparable properties found.")
                
            st.markdown('</div>', unsafe_allow_html=True)


        st.markdown('<div class="panel-container">', unsafe_allow_html=True)
        st.subheader("Demographics Analysis")
        
        # Prepare Data for Charts
        # 1. Income
        metrics = census.get('metrics', {})
        benchmarks = census.get('benchmarks', {})
        
        def parse_curr(s):
            if isinstance(s, int): return s
            if not s or s == "N/A": return 0
            return int(str(s).replace('$','').replace(',',''))

        local_inc = parse_curr(metrics.get('median_household_income'))
        state_inc = benchmarks.get('state_median_income', 0)
        us_inc = benchmarks.get('national_median_income', 0)
        
        df_income = pd.DataFrame([
            {"Region": "National", "Income": us_inc, "Color": "#E8EEF5"},
            {"Region": "State", "Income": state_inc, "Color": "#1A73E8"},
            {"Region": "Local", "Income": local_inc, "Color": "#0F1C2E"}
        ])
        
        chart_income = alt.Chart(df_income).mark_bar().encode(
            x=alt.X('Region', sort=["National", "State", "Local"]),
            y='Income',
            color=alt.Color('Region', scale=alt.Scale(domain=['National','State','Local'], range=['#9CA3AF', '#1A73E8', '#0F1C2E'])),
            tooltip=['Region', 'Income']
        ).properties(title="Median Household Income", height=180)

        # Draw 2x2 Grid
        c_1, c_2 = st.columns(2)
        with c_1:
            st.altair_chart(chart_income, use_container_width=True)
            
            # Education Chart
            # Local: Bachelor+ Pct vs State Bachelor+ (roughly)
            local_bach = metrics.get('education_bachelors_pct', 0)
            if local_bach == "N/A": local_bach = 0
            
            state_edu = benchmarks.get('state_edu', [0,0,0])
            state_bach = state_edu[1] if state_edu else 0 # Benchmark is [HS+, Bach+, Adv+]
            
            df_edu = pd.DataFrame([
                {"Region": "State", "Pct": state_bach, "Color": "#1A73E8"},
                {"Region": "Local", "Pct": local_bach, "Color": "#0F1C2E"}
            ])
            
            chart_edu = alt.Chart(df_edu).mark_bar().encode(
                x=alt.X('Region', sort=["State", "Local"]),
                y=alt.Y('Pct', title='Bachelor+ (%)'),
                color=alt.Color('Region', scale=alt.Scale(domain=['State','Local'], range=['#1A73E8', '#0F1C2E'])),
                tooltip=['Region', 'Pct']
            ).properties(title="Education (Bachelor+)", height=180)
            
            st.altair_chart(chart_edu, use_container_width=True)
            
        with c_2:
            # Race Chart (Pie or Bar) - Let's do Bar for simplicity and comparison if State data available
            # We have local race dict: {White, Black, Asian...}
            # We have state race list: [White, Hisp, Black, Asian, Other] -> Be careful with order
            local_race = metrics.get('race', {})
            state_race = benchmarks.get('state_race', [])
            
            # Helper to align keys
            # State order: White(0), Hispanic(1), Black(2), Asian(3), Other(4)
            data_race = []
            keys = ["White", "Hispanic", "Black", "Asian", "Other"]
            
            if local_race:
                for k in keys:
                    data_race.append({"Demographic": k, "Source": "Local", "Pct": local_race.get(k, 0), "Color": "#0F1C2E"})
                    
            if state_race and len(state_race) == 5:
                # Add State benchmarks
                data_race.append({"Demographic": "White", "Source": "State", "Pct": state_race[0], "Color": "#1A73E8"})
                data_race.append({"Demographic": "Hispanic", "Source": "State", "Pct": state_race[1], "Color": "#1A73E8"})
                data_race.append({"Demographic": "Black", "Source": "State", "Pct": state_race[2], "Color": "#1A73E8"})
                data_race.append({"Demographic": "Asian", "Source": "State", "Pct": state_race[3], "Color": "#1A73E8"})
                data_race.append({"Demographic": "Other", "Source": "State", "Pct": state_race[4], "Color": "#1A73E8"})

            if data_race:
                df_race = pd.DataFrame(data_race)
                chart_race = alt.Chart(df_race).mark_bar().encode(
                    x=alt.X('Demographic', sort=keys),
                    y=alt.Y('Pct', title='Percentage'),
                    xOffset='Source', # Grouped bar
                    color=alt.Color('Source', scale=alt.Scale(domain=['State','Local'], range=['#1A73E8', '#0F1C2E'])),
                    tooltip=['Demographic', 'Source', 'Pct']
                ).properties(title="Race Demographics", height=180)
                st.altair_chart(chart_race, use_container_width=True)
            else:
                st.info("Race: Data Unavailable")

            # Age (Median) Display
            st.markdown("##### Median Age")
            local_age = metrics.get('median_age', "N/A")
            if local_age != "N/A":
                st.metric("Local Median Age", local_age)
            else:
                 st.info("Age Data Unavailable")
            st.caption("Detailed Age buckets not loaded for preview.")
            
        st.markdown('</div>', unsafe_allow_html=True)
        
        # AI Summary
        st.markdown('<div class="panel-container">', unsafe_allow_html=True)
        st.subheader("🤖 AI Executive Summary")
        
        analysis = st.session_state.analysis
        if "investment_strategy" in analysis:
            st.markdown(f"**Strategy:** {analysis['investment_strategy']}")
            
        if "highlights" in analysis:
            st.markdown("##### ✅ Pros")
            for h in analysis["highlights"]:
                st.markdown(f"<span style='color:green'>✓</span> {h}", unsafe_allow_html=True)
                
        if "risks" in analysis:
            st.markdown("##### ⚠️ Cons")
            for r in analysis["risks"]:
                st.markdown(f"<span style='color:orange'>⚠</span> {r}", unsafe_allow_html=True)
        
        st.caption("AI generated content may vary.")
        st.markdown('</div>', unsafe_allow_html=True)


    # COLUMN 3: MAP (40%)
    with col3:
        st.markdown('<div class="panel-container">', unsafe_allow_html=True)
        st.subheader("Interactive Map")
        
        if st.session_state.lat and st.session_state.lon:
            deck_map, legend_items = map.generate_map(st.session_state.lat, st.session_state.lon, st.session_state.pois)
            st_folium(deck_map, use_container_width=True, height=500)
            
            if legend_items:
                st.caption("Map Legend")
                legend_html = " &nbsp; | &nbsp; ".join([f"{emoji} {label}" for label, (emoji, _) in legend_items.items()])
                st.markdown(legend_html)
                
            st.success(f"Score: {analysis.get('score', 'N/A')}/100")
        else:
            st.warning("Map requires analysis data.")
            
        st.markdown('</div>', unsafe_allow_html=True)

else:
    # Empty State (Welcome) - Displayed in Col 2 and 3 usually, or just a big hero in Col 2
    with col2:
        st.info("👈 Enter an address in the sidebar and click 'Analyze' to start.")
        st.markdown("""
        ### Features
        - **POI Analysis**: Analyzes nearby points of interest.
        - **Demographics**: Evaluates census data suitability.
        - **Rent Analysis**: Estimates long-term rent and comparables.
        - **Investment Scoring**: AI-generated scoring.
        """)
