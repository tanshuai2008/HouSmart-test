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
            --primary-color: #1A73E8;
            --secondary-bg: #0F1C2E;
            --light-border: #E8EEF5;
            --text-color: #333333;
            --shadow-light: 0px 2px 6px rgba(0,0,0,0.08);
            --glass-bg: rgba(255, 255, 255, 0.85);
        }

        html, body, [class*="css"] {
            font-family: 'Inter', 'Roboto', sans-serif;
            color: var(--text-color);
        }
        
        /* Fixed Header */
        .fixed-header {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 60px;
            background: var(--glass-bg);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            z-index: 9999;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 40px;
            box-shadow: 0 1px 0 rgba(0,0,0,0.05);
            border-bottom: 1px solid var(--light-border);
        }
        
        .header-logo {
            font-size: 20px;
            font-weight: 600;
            color: var(--secondary-bg);
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .header-nav {
            display: flex;
            gap: 24px;
        }
        
        .nav-item {
            text-decoration: none;
            color: #555;
            font-weight: 500;
            font-size: 14px;
            padding-bottom: 4px;
            transition: all 0.2s ease;
            cursor: pointer;
        }
        
        .nav-item:hover {
            color: var(--primary-color);
            border-bottom: 2px solid var(--primary-color);
        }

        /* Container Styles for Columns */
        .panel-container {
            border: 1px solid var(--light-border);
            border-radius: 6px;
            padding: 20px;
            background: #FFFFFF;
            box-shadow: var(--shadow-light);
            margin-bottom: 16px;
        }
        
        .stButton > button {
            width: 100%;
            border-radius: 6px;
            background-color: var(--primary-color);
            color: white;
            border: none;
            height: 48px;
            font-weight: 500;
        }
        
        .stButton > button:hover {
            background-color: #1557B0;
            color: white;
        }
        
        /* Input Fields */
        .stTextInput > div > div > input {
            border-radius: 4px;
            border: 1px solid #E0E0E0;
        }
        
        .stTextInput > div > div > input:focus {
            border-color: var(--primary-color);
            box-shadow: 0 0 0 1px var(--primary-color);
        }
    </style>
    """

def render_header():
    """
    Renders the fixed top navigation bar.
    """
    header_html = """
    <div class="fixed-header">
        <div class="header-logo">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M3 9L12 2L21 9V20C21 20.5304 20.7893 21.0391 20.4142 21.4142C20.0391 21.7893 19.5304 22 19 22H5C4.46957 22 3.96086 21.7893 3.58579 21.4142C3.21071 21.0391 3 20.5304 3 20V9Z" stroke="#1A73E8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M9 22V12H15V22" stroke="#1A73E8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            HouSmart
        </div>
        <div class="header-nav">
            <a class="nav-item" href="#">Home</a>
            <a class="nav-item" href="#">About Us</a>
            <a class="nav-item" href="mailto:tanshuai2008@gmail.com">Contact</a>
        </div>
    </div>
    <div style="height: 60px; margin-bottom: 20px;"></div> <!-- Spacer -->
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
    <div style="text-align: center; font-family: 'Inter', sans-serif; color: #555; margin-top: 10px; font-weight: 500;">
        Analyzing... {progress}%
    </div>
    """
    return html_code

def render_loader(placeholder, progress):
    """
    Renders the loader in the given Streamlit placeholder.
    """
    placeholder.markdown(get_house_loader_html(progress), unsafe_allow_html=True)
