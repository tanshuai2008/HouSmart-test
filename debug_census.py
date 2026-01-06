import data
import state_data

def debug_data():
    address = "100 1st Ave, New York, NY 10009"
    print(f"Testing address: {address}")
    
    service = data.CensusDataService()
    
    # 1. Geocode
    print("1. Geocoding...")
    geo_data = service.get_census_geoid(address)
    print(f"Geo Data: {geo_data}")
    
    if not geo_data:
        print("Geocoding failed.")
        return

    # 2. ACS Data
    print("\n2. Fetching ACS Data...")
    acs_data = service.get_acs_data(geo_data)
    print(f"ACS Data: {acs_data}")
    
    # 3. Benchmarks
    print("\n3. Comparing with Benchmarks...")
    final = service.compare_with_benchmarks(acs_data, geo_data)
    print(f"Final Result: {final}")
    
    if final:
        metrics = final.get('metrics', {})
        benchmarks = final.get('benchmarks', {})
        
        print("\n--- Income Check ---")
        print(f"Local: {metrics.get('median_household_income')}")
        print(f"State: {benchmarks.get('state_median_income')}")
        print(f"National: {benchmarks.get('national_median_income')}")
        
    # Check state_data direct access
    print("\n--- Direct State Data Check ---")
    print(f"US Income: {state_data.INCOME_DATA.get('United States')}")
    state_name = "New York"
    print(f"NY Income: {state_data.INCOME_DATA.get(state_name)}")

if __name__ == "__main__":
    debug_data()
