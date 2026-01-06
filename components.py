import streamlit as st

def get_base_css():
    """
    Returns the CSS string for the application's theme.
    """
    return """
    <style>
        /* Import Google Fonts: Inter and Roboto */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Roboto:wght@300;400;500;700&display=swap');

        :root {
            /* Color Palette */
            --primary-color: #1A73E8;
            --dark-tech-bg: #0F1C2E;
            --light-border: #E8EEF5;
            --text-primary: #202124;
            --text-secondary: #5F6368;
            --success-green: #34A853;
            --warning-orange: #FBBC04;
            --danger-red: #EA4335;
            
            /* Styles */
            --surface-color: #FFFFFF;
            --app-bg-color: #F8FAFD;
            --tech-shadow: 0px 2px 6px rgba(26, 115, 232, 0.08);
            --header-h: 64px;
        }

        html, body, [class*="css"] {
            font-family: 'Inter', 'Roboto', sans-serif;
            color: var(--text-primary);
            background-color: var(--app-bg-color);
        }
        
        /* Main Streamlit Background Fix */
        .stApp {
            background-color: var(--app-bg-color);
        }
        
        /* Fixed Header */
        .fixed-header {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: var(--header-h);
            background: rgba(255, 255, 255, 0.85);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            z-index: 1000;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 40px;
            border-bottom: 1px solid var(--light-border);
        }
        
        .header-logo {
            font-size: 20px;
            font-weight: 600;
            color: var(--primary-color);
            display: flex;
            align-items: center;
            gap: 10px;
            letter-spacing: -0.5px;
        }
        
        .header-nav {
            display: flex;
            gap: 32px;
        }
        
        .nav-item {
            position: relative;
            text-decoration: none;
            color: var(--text-secondary);
            font-weight: 500;
            font-size: 14px;
            padding: 8px 0;
            transition: color 0.2s ease;
            cursor: pointer;
        }
        
        /* Blue underline animation */
        .nav-item::after {
            content: '';
            position: absolute;
            width: 0;
            height: 2px;
            bottom: 0px;
            left: 50%;
            background-color: var(--primary-color);
            transition: all 0.3s ease;
            transform: translateX(-50%);
        }
        
        .nav-item:hover {
            color: var(--primary-color);
        }

        .nav-item:hover::after {
            width: 100%;
        }

        /* Container Styles for Columns */
        .panel-container {
            border: 1px solid var(--light-border);
            border-radius: 6px;
            padding: 24px;
            background: var(--surface-color);
            box-shadow: var(--tech-shadow);
            margin-bottom: 20px;
        }
        
        /* Headers */
        h1, h2 {
            font-weight: 500;
            letter-spacing: -0.5px;
        }
        h3 {
            font-size: 18px !important;
            font-weight: 500 !important;
            color: var(--text-primary);
        }
        
        /* Buttons */
        .stButton > button {
            width: 100%;
            border-radius: 6px;
            background-color: var(--primary-color);
            color: white;
            border: none;
            height: 44px;
            font-weight: 500;
            font-size: 14px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
            transition: all 0.2s;
        }
        
        .stButton > button:hover {
            background-color: #1557B0; /* Slightly darker blue */
            box-shadow: 0 2px 4px rgba(0,0,0,0.15);
            transform: translateY(-1px);
        }
        
        /* Inputs */
        .stTextInput > div > div > input,
        .stNumberInput > div > div > input,
        .stSelectbox > div > div > div {
            border-radius: 6px !important;
            border: 1px solid var(--light-border) !important;
            background-color: #FFFFFF !important;
            color: var(--text-primary) !important;
            box-shadow: none !important;
        }
        
        /* Input Focus */
        .stTextInput > div > div > input:focus,
        .stNumberInput > div > div > input:focus,
        .stSelectbox > div > div > div:focus-within {
        /* Slider Customization */
        .stSlider > div > div > div[role="slider"] {
            background-color: #FFFFFF !important;
            border: 2px solid var(--primary-color) !important;
            box-shadow: 0 1px 3px rgba(0,0,0,0.2) !important;
            height: 16px !important;
            width: 16px !important;
        }
        
        .stSlider > div > div > div > div {
            background-color: var(--primary-color) !important;
            height: 4px !important;
        }
        
        .stSlider > div > div > div {
            height: 4px !important;
            background-color: var(--light-border) !important; /* Inactive track */
            border-radius: 4px;
        }
        
        /* Metric Styling */
        div[data-testid="stMetricValue"] {
            font-size: 24px;
            font-weight: 600;
            color: var(--text-primary);
        }
        div[data-testid="stMetricLabel"] {
            font-size: 13px;
            color: var(--text-secondary);
        }
    </style>
    """

def card_container(item):
    """
    Wraps the content in a standardized card container.
    Usage:
        with components.card_container():
            st.write("Inside card")
    But since we can't easily yield from a function in a `with` block without contextlib,
    we can just use st.container() but we need to inject the HTML wrapper.
    Easier usage:
        st.markdown('<div class="panel-container">', unsafe_allow_html=True)
        # content
        st.markdown('</div>', unsafe_allow_html=True)
    """
    pass # Placeholder, we use raw HTML strings in app.py for flexibility

def render_header():
    """
    Renders the fixed top navigation bar.
    """
    header_html = """
    <div class="fixed-header">
        <div class="header-logo">
            <!-- Simple geometric logo or icon -->
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect x="2" y="9" width="20" height="13" rx="2" stroke="#1A73E8" stroke-width="2"/>
                <path d="M12 2L2 9H22L12 2Z" fill="#1A73E8"/>
            </svg>
            <span style="font-weight: 600; font-size: 18px; color: #1A73E8; margin-left: 8px;">HouSmart</span>
        </div>
        <div class="header-nav">
            <a class="nav-item" href="#">Home</a>
            <a class="nav-item" href="#">About Us</a>
            <a class="nav-item" href="mailto:tanshuai2008@gmail.com">Contact</a>
        </div>
    </div>
    <div style="height: 80px;"></div> <!-- Spacer for fixed header -->
    """
    st.markdown(header_html, unsafe_allow_html=True)

def get_house_loader_html(progress=0):
    """
    Returns HTML for a house-shaped loader with the given progress percentage (0-100).
    Color updated to Tech Blue.
    """
    # Ensure progress is clamped between 0 and 100
    progress = max(0, min(100, progress))
    
    html_code = f"""
    <div style="display: flex; justify-content: center; align-items: center; margin: 20px 0;">
        <div style="
            position: relative;
            width: 100px;
            height: 100px;
            background-color: #E8EEF5;
            clip-path: polygon(50% 0%, 100% 40%, 80% 40%, 80% 100%, 20% 100%, 20% 40%, 0% 40%);
            -webkit-clip-path: polygon(50% 0%, 100% 40%, 80% 40%, 80% 100%, 20% 100%, 20% 40%, 0% 40%);
        ">
            <div style="
                position: absolute;
                bottom: 0;
                left: 0;
                height: 100%;
                width: {progress}%;
                background-color: #1A73E8;
                transition: width 0.5s ease;
            "></div>
        </div>
    </div>
    <div style="text-align: center; font-family: 'Inter', sans-serif; color: #5F6368; margin-top: 10px; font-weight: 500; font-size: 14px;">
        Analyzing... {progress}%
    </div>
    """
    return html_code

def render_loader(placeholder, progress):
    """
    Renders the loader in the given Streamlit placeholder.
    """
    placeholder.markdown(get_house_loader_html(progress), unsafe_allow_html=True)
