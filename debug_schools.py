
import os
import streamlit as st
from supabase import create_client

def test_supabase():
    # Load secrets
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]

    print(f"Connecting to {url}...")
    supabase = create_client(url, key)

    # 1. Test Select (Count)
    try:
        print("Testing SELECT from Public_School_Location...")
        # Just select 1 row to see if it works
        resp = supabase.table("Public_School_Location").select("*", count="exact").limit(1).execute()
        print(f"Sample Row Keys: {list(resp.data[0].keys())}")
        print(f"Sample Row: {resp.data[0]}")
    except Exception as e:
        print(f"Select FAILED: {e}")

    # 2. Test RPC
    try:
        print("Testing RPC get_nearby_schools...")
        # Use a known location (New York? or defaults)
        params = {"user_lat": 40.7128, "user_lon": -74.0060, "radius_miles": 10.0}
        resp = supabase.rpc("get_nearby_schools", params).execute()
        print(f"RPC Success. Data Rows: {len(resp.data)}")
        if resp.data:
            print(f"RPC Sample: {resp.data[0]}")
    except Exception as e:
        print(f"RPC FAILED: {e}")

if __name__ == "__main__":
    test_supabase()
