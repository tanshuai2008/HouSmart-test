import streamlit as st
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

# Page Configuration
st.set_page_config(layout="wide", page_title="HouSmart Dashboard", page_icon="🏠")

# Session State for Button Management
if "processing" not in st.session_state:
    st.session_state.processing = False

def start_processing():
    st.session_state.processing = True

def finish_processing():
def finish_processing():
    st.session_state.processing = False

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

# Columns: 20% - 40% - 40%
col1, col2, col3 = st.columns([2, 4, 4], gap="medium")

# --- COLUMN 1: CONTROLS (20%) ---
with col1:
    # Card A: User Email
    # Using border=True to trigger the specific CSS class
    with st.container(border=True):
        st.markdown("### User Info")
    
        # Logic for Red Border
        if "user_email_input" not in st.session_state:
            st.session_state.user_email_input = ""
            
        is_email_empty = not st.session_state.user_email_input.strip()
        
        # Dynamic CSS for Red Border on the specific input
        if is_email_empty:
            st.markdown("""
            <style>
            /* Target the specific input widget if possible, or all text inputs in this container */
            /* Since we have other inputs, we need to be careful. 
               But this input is the first one in col1. */
            div[data-testid="stTextInput"] input {
                border: 2px solid #EA4335 !important;
            }
            div[data-testid="stTextInput"] label {
                color: #EA4335 !important;
                font-weight: 600;
            }
            </style>
            """, unsafe_allow_html=True)
            label_text = "User Email (Required)"
        else:
            label_text = "User Email"

        # Just the input, no extra wrapper that looks like a card inside a card
        email_val = st.text_input(label_text, placeholder="email@example.com", key="user_email_input")
        
        # Display Usage Count
        if email_val:
            usage_count = get_daily_usage(email_val)
            st.caption(f"Free Trial in past 24h: {usage_count}/3")


    # Card B: Property Details
    with st.container(border=True):
        st.markdown("### Property Details")
        st.text_input("Address", "123 Market St, San Francisco, CA")
        
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
        if st.button("Start Analysis", disabled=st.session_state.processing, on_click=start_processing):
            # This block runs after the callback. 
            # However, since we want to show processing state and then finish, we do it here.
            # But with on_click, the rerun happens first with disabled=True? No.
            # Standard pattern: click -> callback (sets processing=True) -> rerun -> script runs top-down -> button is disabled -> we check if processing -> do work -> set processing=False -> rerun.
            pass

# Processing Logic Hook (Top of Column 2 or where we want to show work logic)
if st.session_state.processing:
    # We can handle the work here or inside the areas where it updates.
    # For simulation, we'll put a spinner in Col 2.
    with col2:
        with st.spinner("Analyzing property... (Simulated)"):
            time.sleep(2.5) # Simulate Loading
        st.session_state.processing = False
        st.rerun() # Re-enable button


# --- COLUMN 2: ANALYSIS (40%) ---
with col2:
    # Card C: Census & Scores
    with st.container(border=True):
        st.subheader("Census & Demographics")
        # Dummy Data Generation
        categories = ['Income', 'Age', 'Race', 'Education']
        
        # 1. Income Distribution
        # Using Grouped Bar Chart for Comparison
        df_income = pd.DataFrame({
            "Range": ["<50k", "<50k", "<50k", "50-100k", "50-100k", "50-100k", "100k+", "100k+", "100k+"],
            "Scope": ["Local", "State", "National"] * 3,
            "Value": [15, 12, 14, 45, 40, 38, 40, 48, 48]
        })
        fig_inc = px.bar(df_income, x="Range", y="Value", color="Scope", barmode="group", title="Income", height=250,
                        color_discrete_map={"Local": "#1A73E8", "State": "#9AA0A6", "National": "#DADCE0"})
        fig_inc.update_layout(margin=dict(l=0,r=0,t=30,b=0), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))

        # 2. Age Distribution
        df_age = pd.DataFrame({
            "Range": ["0-18", "0-18", "0-18", "19-35", "19-35", "19-35", "36-50", "36-50", "36-50", "50+", "50+", "50+"],
            "Scope": ["Local", "State", "National"] * 4,
            "Value": [20, 22, 21, 40, 35, 30, 25, 28, 29, 15, 15, 20]
        })
        fig_age = px.bar(df_age, x="Range", y="Value", color="Scope", barmode="group", title="Age", height=250,
                        color_discrete_map={"Local": "#34A853", "State": "#9AA0A6", "National": "#DADCE0"})
        fig_age.update_layout(margin=dict(l=0,r=0,t=30,b=0), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))

        # 3. Race Distribution
        df_race = pd.DataFrame({
            "Group": ["Asian", "Asian", "Asian", "White", "White", "White", "Hisp", "Hisp", "Hisp", "Oth", "Oth", "Oth"],
            "Scope": ["Local", "State", "National"] * 4,
            "Value": [35, 15, 6, 30, 40, 60, 20, 30, 18, 15, 15, 16]
        })
        fig_race = px.bar(df_race, x="Group", y="Value", color="Scope", barmode="group", title="Race", height=250,
                        color_discrete_map={"Local": "#FBBC04", "State": "#9AA0A6", "National": "#DADCE0"})
        fig_race.update_layout(margin=dict(l=0,r=0,t=30,b=0), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))

        # 4. Education
        df_edu = pd.DataFrame({
            "Level": ["HighSch", "HighSch", "HighSch", "Bach", "Bach", "Bach", "Grad", "Grad", "Grad"],
            "Scope": ["Local", "State", "National"] * 3,
            "Value": [10, 20, 25, 50, 45, 40, 40, 35, 35]
        })
        fig_edu = px.bar(df_edu, x="Level", y="Value", color="Scope", barmode="group", title="Education", height=250,
                        color_discrete_map={"Local": "#EA4335", "State": "#9AA0A6", "National": "#DADCE0"})
        fig_edu.update_layout(margin=dict(l=0,r=0,t=30,b=0), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))

        # 2x2 Grid
        r1_c1, r1_c2 = st.columns(2)
        with r1_c1: st.plotly_chart(fig_inc, use_container_width=True)
        with r1_c2: st.plotly_chart(fig_age, use_container_width=True)
        
        r2_c1, r2_c2 = st.columns(2)
        with r2_c1: st.plotly_chart(fig_race, use_container_width=True)
        with r2_c2: st.plotly_chart(fig_edu, use_container_width=True)

    # Card D: AI Insight Summary
    with st.container(border=True):
        # Header with Score
        c_head, c_score = st.columns([3, 1])
        with c_head:
            st.subheader("AI Insight Summary")
        with c_score:
            st.metric("AI Score", "85/100", delta="High Opportunity")

        st.info("Based on a comprehensive analysis of the local demographic trends, economic indicators, and amenity access, this property represents a **High Opportunity** investment. The area is witnessing a significant influx of young professionals (ages 19-35), driving demand for modern housing. Income levels are robust, with over 60% of households earning above $100k, surpassing both state and national averages. While HOA fees are higher than the market median, the strong appreciation potential (+5% YoY) and excellent walkability make this a prime location for long-term growth.", icon="🤖")
        
        ai_c1, ai_c2 = st.columns(2)
        with ai_c1:
            st.markdown("**Key Advantages**")
            st.success("✅ **High Walk Score (92)**\nLocated within a 'Walker's Paradise', daily errands do not require a car, significantly boosting tenant appeal and property value.")
            st.success("✅ **Strong Appreciation (+5% YoY)**\nThe neighborhood has consistently outperformed the broader market, driven by limited inventory and high demand from tech workers.")
            st.success("✅ **Low Crime Rate**\nSafety statistics indicate this area is in the top 10% safest neighborhoods in the city, lowering insurance costs and tenant turnover.")
            st.success("✅ **Top Rated Schools**\nZoned for 9/10 rated elementary and high schools, making it highly desirable for families looking to settle long-term.")

        with ai_c2:
            st.markdown("**Potential Risks**")
            st.warning("⚠️ **High HOA Fees**\nMonthly association dues are 20% above the city median, which may impact net cash flow if rent prices stagnate.")
            st.warning("⚠️ **Noise Levels (Moderate)**\nProximity to main transit corridors results in elevated ambient noise during rush hours, potentially affecting street-facing units.")
            st.warning("⚠️ **Market Saturation**\nA high number of new condo developments in the pipeline (500+ units) could temporarily soften rental yields in the next 12-18 months.")

# --- COLUMN 3: MAP (40%) ---
with col3:
    # Card E: Interactive Map
    with st.container(border=True):
    # Card E: Interactive Map
    with st.container(border=True):
        st.subheader("Location Intelligence")
        
        # Center Map on Dummy Location (SF)
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
