import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import time

# Page Configuration
st.set_page_config(layout="wide", page_title="HouSmart Dashboard", page_icon="🏠")

# Session State for Button Management
if "processing" not in st.session_state:
    st.session_state.processing = False

def start_processing():
    st.session_state.processing = True

def finish_processing():
    st.session_state.processing = False

# CSS Injection
st.markdown("""
<style>
    /* Global Background */
    .stApp {
        background-color: #f4f6f9;
        font-family: 'Inter', sans-serif;
    }
    
    /* Card Styling for Vertical Blocks */
    div[data-testid="stVerticalBlock"] > div {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 20px;
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
    .stButton>button {
        width: 100%;
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
    st.markdown("### User Info")
    # To mimic red border specific card, we can't easily style just THIS block parent div via pure CSS selectors in Streamlit 
    # without `st.container` and experimental key or just treating the input as the card.
    
    # We will use valid Streamlit way: A container styled via CSS specific class if possible, 
    # but Streamlit CSS injection is global.
    # Workaround: Put content inside a markdown div with styling? 
    # No, inputs can't go inside markdown.
    # We will just place the input. The global "Card Styling" applied to `stVerticalBlock > div` 
    # might wrap EACH widget or groups? 
    # Actually `stVerticalBlock > div` targets the direct children of the vertical layout. 
    # If we put elements in a container, the container is the div.
    
    with st.container():
        # Red Box Container
        st.markdown('<div class="email-card" style="padding: 10px; border-radius: 5px;">', unsafe_allow_html=True)
        st.text_input("User Email", placeholder="email@example.com", label_visibility="visible")
        st.markdown('</div>', unsafe_allow_html=True)


    # Card B: Property Details
    st.markdown("### Property Details")
    with st.container():
        st.text_input("Address", "123 Market St, San Francisco, CA")
        
        c_b1, c_b2, c_b3 = st.columns(3)
        with c_b1:
            st.number_input("Bed", value=2, min_value=0)
        with c_b2:
            st.number_input("Bath", value=2, min_value=0)
        with c_b3:
            st.number_input("Sqft", value=1200, step=50)
            
        st.selectbox("Property Type", ["Single Family", "Townhouse", "Condo", "Apartment"])
        if st.button("Update Analysis", disabled=st.session_state.processing, on_click=start_processing):
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
    st.subheader("Census & Demographics")
    with st.container():
        # Dummy Data Generation
        categories = ['Income', 'Age', 'Race', 'Education']
        
        # 1. Income Distribution
        df_income = pd.DataFrame({
            "Range": ["<50k", "50-100k", "100-150k", ">150k"],
            "Value": [15, 30, 35, 20]
        })
        fig_inc = px.bar(df_income, x="Range", y="Value", title="Income", height=200)
        fig_inc.update_layout(margin=dict(l=0,r=0,t=30,b=0), coloraxis_showscale=False)
        fig_inc.update_traces(marker_color='#1A73E8')

        # 2. Age Distribution
        df_age = pd.DataFrame({
            "Range": ["0-18", "19-35", "36-50", "50+"],
            "Value": [20, 40, 25, 15]
        })
        fig_age = px.bar(df_age, x="Range", y="Value", title="Age", height=200)
        fig_age.update_layout(margin=dict(l=0,r=0,t=30,b=0))
        fig_age.update_traces(marker_color='#34A853')

        # 3. Race Distribution
        df_race = pd.DataFrame({
            "Group": ["Asian", "White", "Hispanic", "Other"],
            "Value": [35, 30, 20, 15]
        })
        fig_race = px.bar(df_race, x="Group", y="Value", title="Race", height=200)
        fig_race.update_layout(margin=dict(l=0,r=0,t=30,b=0))
        fig_race.update_traces(marker_color='#FBBC04')

        # 4. Education
        df_edu = pd.DataFrame({
            "Level": ["HighSch", "Bach", "Master", "PhD"],
            "Value": [10, 50, 30, 10]
        })
        fig_edu = px.bar(df_edu, x="Level", y="Value", title="Education", height=200)
        fig_edu.update_layout(margin=dict(l=0,r=0,t=30,b=0))
        fig_edu.update_traces(marker_color='#EA4335')

        # 2x2 Grid
        r1_c1, r1_c2 = st.columns(2)
        with r1_c1: st.plotly_chart(fig_inc, use_container_width=True)
        with r1_c2: st.plotly_chart(fig_age, use_container_width=True)
        
        r2_c1, r2_c2 = st.columns(2)
        with r2_c1: st.plotly_chart(fig_race, use_container_width=True)
        with r2_c2: st.plotly_chart(fig_edu, use_container_width=True)

    # Card D: AI Insight Summary
    st.subheader("AI Insight Summary")
    with st.container():
        st.info("Based on the data, this property represents a **High Opportunity** investment due to rising local income levels and strong transit connectivity.", icon="🤖")
        
        ai_c1, ai_c2 = st.columns(2)
        with ai_c1:
            st.markdown("**Key Advantages**")
            st.markdown("- ✅ High Walk Score (92)")
            st.markdown("- ✅ Strong Appreciation (+5% YoY)")
            st.markdown("- ✅ Low Crime Rate")
        with ai_c2:
            st.markdown("**Potential Risks**")
            st.markdown("- ⚠️ High HOA Fees")
            st.markdown("- ⚠️ Noise Levels (Moderate)")

# --- COLUMN 3: MAP (40%) ---
with col3:
    # Card E: Interactive Map
    st.subheader("Location Intelligence")
    with st.container():
        # Dummy Map Data: San Francisco
        map_data = pd.DataFrame({
            'lat': np.random.normal(37.7749, 0.01, 100),
            'lon': np.random.normal(-122.4194, 0.01, 100),
            'type': np.random.choice(['A', 'B', 'C'], 100)
        })
        
        st.map(map_data, zoom=12, use_container_width=True, height=500)

    # Card F: Legend
    st.markdown("#### Amenities Legend")
    with st.container():
        st.caption("Nearby Services")
        
        # Flexbox helper for legend items
        legend_html = """
        <div style="display: flex; gap: 15px; flex-wrap: wrap;">
            <div style="display: flex; align-items: center; gap: 5px;">🍔 <span style="font-size: 14px;">Food</span></div>
            <div style="display: flex; align-items: center; gap: 5px;">🛒 <span style="font-size: 14px;">Grocery</span></div>
            <div style="display: flex; align-items: center; gap: 5px;">⛽ <span style="font-size: 14px;">Gas</span></div>
            <div style="display: flex; align-items: center; gap: 5px;">💊 <span style="font-size: 14px;">Pharmacy</span></div>
        </div>
        """
        st.markdown(legend_html, unsafe_allow_html=True)
