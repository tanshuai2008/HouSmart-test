import os
import datetime
from supabase import create_client, Client
import streamlit as st

# Helper to get client
def get_supabase_client():
    try:
        # Try loading from Streamlit secrets (Top-level or Nested)
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_KEY")
        
        # Check for [supabase] section in secrets.toml
        if not url and "supabase" in st.secrets:
            url = st.secrets["supabase"].get("URL") or st.secrets["supabase"].get("url")
            key = st.secrets["supabase"].get("KEY") or st.secrets["supabase"].get("key")
            
        # Fallback to Environment variables
        if not url: url = os.environ.get("SUPABASE_URL")
        if not key: key = os.environ.get("SUPABASE_KEY")
        
        if not url or not key:
            # Debugging aid (Safe print)
            print("DEBUG: Supabase Credentials MISSING.")
            if "supabase" in st.secrets:
                print(f"DEBUG: Found [supabase] section. Keys: {list(st.secrets['supabase'].keys())}")
            else:
                print(f"DEBUG: Top-level keys: {list(st.secrets.keys())}")
            return None
            
        return create_client(url, key)
    except Exception as e:
        print(f"Supabase Connection Error: {e}")
        return None

def get_valid_cache(address, hours_valid=240):
    """
    Check if a valid analysis exists for the address within the last 'hours_valid'.
    Returns the analysis_result (dict) if found, else None.
    """
    supabase = get_supabase_client()
    if not supabase:
        return None
        
    try:
        # Calculate the cutoff time (UTC)
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=hours_valid)
        cutoff_str = cutoff.isoformat()
        
        # Query Supabase
        # SELECT * FROM property_logs 
        # WHERE address = address 
        # AND created_at >= cutoff 
        # ORDER BY created_at DESC LIMIT 1
        
        data = supabase.table("property_logs")\
            .select("*")\
            .eq("address", address)\
            .gte("created_at", cutoff_str)\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()
            
        # Check if we got data
        if data.data and len(data.data) > 0:
            return data.data[0].get("analysis_result")
            
        return None
        
    except Exception as e:
        print(f"Supabase Read Error: {e}")
        return None

def save_analysis(user_email, address, result_json):
    """
    Save a new analysis to Supabase.
    """
    supabase = get_supabase_client()
    if not supabase:
        return False
        
    try:
        # Prepare record
        record = {
            "user_email": user_email,
            "address": address,
            "analysis_result": result_json,
            # created_at is automatic, but can be passed if needed
        }
        
        supabase.table("property_logs").insert(record).execute()
        return True
    except Exception as e:
        print(f"Supabase Write Error: {e}")
        return False

def get_user_preferences(user_email):
    """
    Retrieve specific refined preferences for a user.
    """
    supabase = get_supabase_client()
    if not supabase or not user_email: 
        return None
        
    try:
        data = supabase.table("user_preferences")\
            .select("preference_summary")\
            .eq("user_email", user_email)\
            .execute()
            
        if data.data and len(data.data) > 0:
            return data.data[0].get("preference_summary")
        return None
    except Exception as e:
        print(f"Supabase Prefs Read Error: {e}")
        return None

def save_user_preferences(user_email, summary):
    """
    Upsert user preferences. Returns (success, error_msg).
    """
    supabase = get_supabase_client()
    if not supabase:
        return False, "Supabase Client failed to initialize (Missing Key/URL)."
    if not user_email:
        return False, "User Email is missing."
        
    try:
        record = {
            "user_email": user_email,
            "preference_summary": summary,
            "last_updated": datetime.datetime.utcnow().isoformat()
        }
        
        # Upsert
        supabase.table("user_preferences").upsert(record).execute()
        return True, None
    except Exception as e:
        print(f"Supabase Prefs Write Error: {e}")
        return False, str(e)

def save_user_rating(user_email, rating, context=None):
    """
    Saves a user's star rating to the `user_ratings` table.
    """
    supabase = get_supabase_client()
    if not supabase:
        return False
    
    try:
        data = {
            "user_email": user_email,
            "rating": rating,
            "context": context
        }
        supabase.table("user_ratings").insert(data).execute()
        return True
    except Exception as e:
        print(f"Error saving rating: {e}")
        return False
