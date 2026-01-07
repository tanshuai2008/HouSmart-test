import streamlit as st
import os
import google_auth_oauthlib.flow
from googleapiclient.discovery import build

# Constants
SCOPES = [
    "https://www.googleapis.com/auth/userinfo.email", 
    "openid"
]

def get_flow():
    """
    Creates the OAuth flow using client config from secrets.
    """
    # Load client config from secrets
    if "GOOGLE_OAUTH" not in st.secrets:
        st.error("Missing [GOOGLE_OAUTH] configuration in secrets.toml")
        return None
        
    client_config = {
        "web": {
            "client_id": st.secrets["GOOGLE_OAUTH"]["client_id"],
            "client_secret": st.secrets["GOOGLE_OAUTH"]["client_secret"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [st.secrets["GOOGLE_OAUTH"]["redirect_uri"]] 
        }
    }
    
    flow = google_auth_oauthlib.flow.Flow.from_client_config(
        client_config=client_config,
        scopes=SCOPES,
        redirect_uri=st.secrets["GOOGLE_OAUTH"]["redirect_uri"]
    )
    return flow

def login_button():
    """
    Renders a 'Sign in with Google' button (as a link).
    """
    flow = get_flow()
    if not flow:
        return
        
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    
    # Styled Button Link
    st.markdown(f'''
    <a href="{authorization_url}" target="_self">
        <button style="
            background-color: white; 
            color: #3c4043; 
            border: 1px solid #dadce0; 
            border-radius: 4px; 
            padding: 8px 16px; 
            font-family: 'Google Sans',Roboto,Arial,sans-serif; 
            font-size: 14px; 
            font-weight: 500; 
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 10px;
        ">
            <img src="https://upload.wikimedia.org/wikipedia/commons/5/53/Google_%22G%22_Logo.svg" width="18" height="18">
            Sign in with Google
        </button>
    </a>
    ''', unsafe_allow_html=True)

def handle_callback():
    """
    Checks for 'code' in query params, exchanges for token, and returns user info.
    """
    # Check for authorization code
    if "code" not in st.query_params:
        return None
        
    code = st.query_params["code"]
    
    try:
        flow = get_flow()
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Get User Info
        service = build("oauth2", "v2", credentials=credentials)
        user_info = service.userinfo().get().execute()
        
        # Clear Query Params to prevent re-execution
        st.query_params.clear()
        
        return user_info
        
    except Exception as e:
        st.error(f"Login Failed: {e}")
        return None
