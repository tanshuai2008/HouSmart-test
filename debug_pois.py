
import streamlit as st
import data

def test_poi():
    addr = "123 Market St, San Francisco, CA"
    # Ensure key exists
    if "GEOAPIFY_API_KEY" not in st.secrets:
        print("Error: GEOAPIFY_API_KEY not in secrets.")
        return

    key = st.secrets["GEOAPIFY_API_KEY"]
    print(f"Testing POI fetch for {addr} with key {key[:5]}...")
    
    try:
        pois, lat, lon = data.get_poi(addr, api_key=key)
        print(f"Lat: {lat}, Lon: {lon}")
        print(f"POI Count: {len(pois)}")
        if pois:
            print(f"Sample POI: {pois[0]}")
            # Check categories explicitly
            props = pois[0].get('properties', {})
            print(f"Categories: {props.get('categories')}")
            print(f"Category: {props.get('category')}")
    except Exception as e:
        print(f"Error fetching POI: {e}")

if __name__ == "__main__":
    test_poi()
