import requests
import urllib.parse
import random
import datetime
import state_data
import state_data
from config_manager import config_manager
from supabase import create_client, Client # Ensure supabase is in requirements
import os

def log_debug(msg):

# Map state FIPS to state names for benchmark lookup if needed
# (Or we can reverse look up from state_data if we had FIPS mapping, 
# but for now let's hope we rely on the address or simple mapping if needed)
# Actually, the Census Geocoder returns State Name usually.


    with open("debug_log.txt", "a") as f:
        f.write(f"{str(msg)}\n")

def get_coordinates(address, api_key):
    """
    Get coordinates for an address using Geoapify Geocoding API.
    """
    if not config_manager.get_config().get("enable_geoapify", True):
        # Return default if disabled
        return 40.785091, -73.968285

    if not api_key:
        return 40.785091, -73.968285

    encoded_address = urllib.parse.quote(address)
    url = f"https://api.geoapify.com/v1/geocode/search?text={encoded_address}&apiKey={api_key}"
    
    try:
        resp = requests.get(url)
        if resp.status_code == 200:
            data = resp.json()
            if data['features']:
                coords = data['features'][0]['geometry']['coordinates']
                return coords[1], coords[0] # Lat, Lon
    except Exception as e:
        print(f"Error fetching coordinates: {e}")
        
    return 40.785091, -73.968285

def get_poi(address, api_key=None, lat=None, lon=None):
    """
    Fetch POIs around the address using Geoapify Places API.
    """
    if not config_manager.get_config().get("enable_geoapify", True):
        # Return only coords (default) and empty POIs
        if lat is None or lon is None:
            lat, lon = get_coordinates(address, api_key)
        return [], lat, lon

    if lat is None or lon is None:
        lat, lon = get_coordinates(address, api_key)

    pois = []

    if api_key:
        categories = "commercial,education,leisure,catering,healthcare"
        radius = 1000
        limit = 30
        
        url = f"https://api.geoapify.com/v2/places?categories={categories}&filter=circle:{lon},{lat},{radius}&limit={limit}&apiKey={api_key}"
        
        try:
            resp = requests.get(url)
            if resp.status_code == 200:
                pois = resp.json()['features']
                return pois, lat, lon
        except Exception as e:
            print(f"Error fetching POIs: {e}")

    if not api_key:
        mock_cats = ['cafe', 'school', 'park', 'gym', 'supermarket']
        for _ in range(10):
            cat = random.choice(mock_cats)
            pois.append({
                "properties": {
                    "name": f"Mock {cat.title()}",
                    "category": cat,
                    "distance": random.randint(100, 2000),
                    "lat": lat + random.uniform(-0.01, 0.01),
                    "lon": lon + random.uniform(-0.01, 0.01)
                }
            })
            
    return pois, lat, lon

class CensusDataService:
    def __init__(self):
        self.geocoder_url = "https://geocoding.geo.census.gov/geocoder/geographies/onelineaddress"
        # Use 2022 ACS 5-Year Data (Stable)
        self.acs_base_url = "https://api.census.gov/data/2022/acs/acs5"
        self.variables = {
            # Income & Value
            "B19013_001E": "Median Household Income",
            "B25077_001E": "Median Home Value",
            "B25064_001E": "Median Gross Rent",
            # Education (Simplified - using key points)
            "B15003_001E": "Edu_Total_25_Plus",
            "B15003_017E": "Edu_HS_Diploma", # Regular HS
            "B15003_022E": "Edu_Bachelor", 
            "B15003_023E": "Edu_Master",
            "B15003_024E": "Edu_Prof",
            "B15003_025E": "Edu_Doctorate",
            "B15003_025E": "Edu_Doctorate",
            # Age
            "B01002_001E": "Median Age",
            "B01001_001E": "Total Population",
            # Race (Simplified)
            "B02001_002E": "Race_White",
            "B02001_003E": "Race_Black",
            "B02001_005E": "Race_Asian",
            "B03003_003E": "Origin_Hispanic"
        }

    def get_census_geoid(self, address):
        """
        Step 1: Convert address to Block Group GEOID.
        Attempts Census Geocoder first, then falls back to Coordinate->FCC API.
        """
        # A. Try Census Geocoder (Good for standard addresses)
        params = {
            "address": address,
            "benchmark": "Public_AR_Current",
            "vintage": "Current_Current",
            "layers": "10", # Block Groups
            "format": "json"
        }
        
        try:
            resp = requests.get(self.geocoder_url, params=params, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                matches = data.get('result', {}).get('addressMatches', [])
                if matches:
                    geo = matches[0]['geographies']['Census Block Groups'][0]
                    return {
                        "full_geoid": f"{geo['STATE'].zfill(2)}{geo['COUNTY'].zfill(3)}{geo['TRACT'].zfill(6)}{geo['BLKGRP']}",
                        "state": geo['STATE'].zfill(2),
                        "county": geo['COUNTY'].zfill(3),
                        "tract": geo['TRACT'].zfill(6),
                        "block_group": geo['BLKGRP']
                    }
        except Exception as e:
            log_debug(f"Census Geocoder Error: {e}")

        # B. Fallback: Geoapify -> FCC Block API (Good for landmarks/pois)
        log_debug("Fallback: Using Geoapify + FCC API")
        lat, lon = get_coordinates(address, None) # Uses default if no key, but assume key is likely present or defaulting to NY
        
        # If get_coordinates returns default coordinates because of missing key, this might not be accurate for arbitrary input,
        # but better than failing.
        
        fcc_url = "https://geo.fcc.gov/api/census/block/find"
        params = {
            "latitude": lat,
            "longitude": lon,
            "showall": "false",
            "format": "json"
        }
        
        try:
            r = requests.get(fcc_url, params=params, timeout=5)
            if r.status_code == 200:
                data = r.json()
                # FCC returns Block FIPS (15 digits). Block Group is first 12 digits.
                # State (2) + County (3) + Tract (6) + Block (4)
                fips = data['Block']['FIPS']
                state = fips[:2]
                county = fips[2:5]
                tract = fips[5:11]
                block_group = fips[11] # 1st digit of block
                
                return {
                    "full_geoid": fips[:12],
                    "state": state,
                    "county": county,
                    "tract": tract,
                    "block_group": block_group
                }
        except Exception:
            pass
            
        return None

    def get_acs_data(self, geoid_data):
        """
        Step 2: Query ACS Data for the Block Group.
        """
        if not geoid_data:
            return None
            
        state = geoid_data['state']
        county = geoid_data['county']
        tract = geoid_data['tract']
        bg = geoid_data['block_group']
        
        # Construct variable list
        vars_str = ",".join(self.variables.keys())
        
        # https://api.census.gov/data/2024/acs/acs5?get=NAME,B19013_001E...&for=block group:X&in=state:xx county:xxx tract:xxxxxx
        params = {
            "get": f"NAME,{vars_str}",
            "for": f"block group:{bg}",
            "in": f"state:{state} county:{county} tract:{tract}"
        }
        
        try:
            r = requests.get(self.acs_base_url, params=params)
            if r.status_code == 200:
                # Response is list of lists. Row 0 = Headers, Row 1 = Data
                rows = r.json()
                if len(rows) > 1:
                    headers = rows[0]
                    data_row = rows[1]
                    
                    result = {}
                    # Map back to readable keys
                    for code, label in self.variables.items():
                        if code in headers:
                            idx = headers.index(code)
                            val = data_row[idx]
                            # Clean up values (negative numbers often mean missing data in Census)
                            if val:
                                try:
                                    num_val = float(val)
                                    if num_val > 0:
                                        # Store as int if integer, else float
                                        if num_val.is_integer():
                                            result[code] = int(num_val)
                                        else:
                                            result[code] = num_val
                                except ValueError:
                                    pass
                    return result
        except Exception as e:
            print(f"ACS API Error: {e}")
            
        return None

    def compare_with_benchmarks(self, local_data, geoid_data):
        """
        Step 3: Compare local results with State Benchmarks.
        Returns standardized structure: { key: { 'local': val, 'state': val, 'national': val } }
        """
        if not local_data:
            return None

        # FIPS to Name Mapping
        FIPS_TO_NAME = {
            "01": "Alabama", "02": "Alaska", "04": "Arizona", "05": "Arkansas", "06": "California",
            "08": "Colorado", "09": "Connecticut", "10": "Delaware", "11": "District of Columbia",
            "12": "Florida", "13": "Georgia", "15": "Hawaii", "16": "Idaho", "17": "Illinois",
            "18": "Indiana", "19": "Iowa", "20": "Kansas", "21": "Kentucky", "22": "Louisiana",
            "23": "Maine", "24": "Maryland", "25": "Massachusetts", "26": "Michigan", "27": "Minnesota",
            "28": "Mississippi", "29": "Missouri", "30": "Montana", "31": "Nebraska", "32": "Nevada",
            "33": "New Hampshire", "34": "New Jersey", "35": "New Mexico", "36": "New York",
            "37": "North Carolina", "38": "North Dakota", "39": "Ohio", "40": "Oklahoma", "41": "Oregon",
            "42": "Pennsylvania", "44": "Rhode Island", "45": "South Carolina", "46": "South Dakota",
            "47": "Tennessee", "48": "Texas", "49": "Utah", "50": "Vermont", "51": "Virginia",
            "53": "Washington", "54": "West Virginia", "55": "Wisconsin", "56": "Wyoming", "72": "Puerto Rico"
        }
        
        state_fips = geoid_data['state']
        state_name = FIPS_TO_NAME.get(state_fips, "United States")
        
        benchmarks = state_data.get_state_benchmarks(state_name)
        
        # Build final object
        output = {
            "location_identifiers": geoid_data,
            "metrics": {},
            "benchmarks": benchmarks
        }
        
        # Helper to structure metric
        def make_metric(local_val, key_bench=None):
            return {
                "local": local_val,
                "state": benchmarks.get(key_bench, {} if key_bench else 0), # Simplified
                "national": 0 # Placeholder
            }
        
        # 1. Household Income
        med_income = local_data.get("B19013_001E")
        output["metrics"]["median_income"] = {"local": med_income if med_income else 0}
        
        # 2. Home Value
        med_value = local_data.get("B25077_001E")
        output["metrics"]["median_home_value"] = {"local": med_value if med_value else 0}
        
        # 3. Rent
        med_rent = local_data.get("B25064_001E")
        output["metrics"]["median_gross_rent"] = {"local": med_rent if med_rent else 0}
        
        # 4. Education (Bachelors+)
        total_25_plus = local_data.get("B15003_001E", 0) or 0
        
        e_hs = 0
        e_bach = 0
        e_mast = 0
        e_prof = 0
        e_doc = 0
        
        if total_25_plus > 0:
            e_hs = local_data.get("B15003_017E", 0) or 0
            e_bach = local_data.get("B15003_022E", 0) or 0
            e_mast = local_data.get("B15003_023E", 0) or 0
            e_prof = local_data.get("B15003_024E", 0) or 0
            e_doc = local_data.get("B15003_025E", 0) or 0

        # Pass raw counts so app.py can calculate percentages correctly
        output["metrics"]["Edu_Total_25_Plus"] = {"local": total_25_plus}
        output["metrics"]["Edu_HS_Diploma"] = {"local": e_hs}
        output["metrics"]["Edu_Bachelor"] = {"local": e_bach}
        output["metrics"]["Edu_Master"] = {"local": e_mast}
        output["metrics"]["Edu_Prof"] = {"local": e_prof}
        output["metrics"]["Edu_Doctorate"] = {"local": e_doc}

        # 5. Race
        r_tot = local_data.get("B01001_001E", 0) or 0
        r_white = local_data.get("B02001_002E", 0) or 0
        r_black = local_data.get("B02001_003E", 0) or 0
        r_asian = local_data.get("B02001_005E", 0) or 0
        r_hisp = local_data.get("B03003_003E", 0) or 0
        
        # Pass raw counts
        output["metrics"]["Race_White"] = {"local": r_white}
        output["metrics"]["Race_Black"] = {"local": r_black}
        output["metrics"]["Race_Asian"] = {"local": r_asian}
        output["metrics"]["Origin_Hispanic"] = {"local": r_hisp}
        output["metrics"]["Race_Total"] = {"local": r_tot}
    
        # 6. Age
        med_age = local_data.get("B01002_001E")
        output["metrics"]["median_age"] = {"local": med_age if med_age else 0}
    
        return output

def get_census_data(address):
    """
    Main entry point for App to get Census Data.
    """
    log_debug(f"Starting Census Fetch for: {address}")
    try:
        if not config_manager.get_config().get("enable_census", True):
            log_debug("Census API Disabled in Config")
            return None

        service = CensusDataService()
        
        # 1. Geocode
        geo_data = service.get_census_geoid(address)
        log_debug(f"Geode Result: {geo_data}")
        
        if not geo_data:
            return None
            
        # 2. Get Data
        acs_data = service.get_acs_data(geo_data)
        log_debug(f"ACS Result Count: {len(acs_data) if acs_data else 0}")
        
        # 3. Compare & Compile
        final_result = service.compare_with_benchmarks(acs_data, geo_data)
        log_debug(f"Final Result Keys: {final_result.keys() if final_result else 'None'}")
        
        if final_result:
            final_result['source'] = "US Census Bureau (2022 ACS 5-year)"
            
        return final_result
    except Exception as e:
        log_debug(f"CRITICAL ERROR in get_census_data: {e}")
        return None

def get_rentcast_data(address, bedrooms, bathrooms, sqft, property_type, api_key):
    """
    Fetch Rent Estimates and Comparables from RentCast API.
    """
    if not config_manager.get_config().get("enable_rentcast", True):
        return None

    if not api_key:
        return None

    # RentCast endpoint
    url = "https://api.rentcast.io/v1/avm/rent/long-term"
    
    params = {
        "address": address,
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "squareFootage": sqft,
        "propertyType": property_type,
        "radius": 3.0, # Expanded to 3 miles
        "limit": 10   # Fetch more candidates to sort
    }
    
    headers = {
        "accept": "application/json",
        "X-Api-Key": api_key
    }
    
    try:
        resp = requests.get(url, params=params, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            
            # Extract basic estimate
            estimate = data.get("rent", 0)
            rent_range = [data.get("rentRangeLow", 0), data.get("rentRangeHigh", 0)]
            
            # Extract Comps
            comps = data.get("comparables", [])
            
            # Sort by similarity score (descending) if available.
            comps.sort(key=lambda x: x.get("similarityScore", 0), reverse=True)
            
            top_3 = []
            top_3 = []
            for c in comps[:3]:
                # Safe conversions
                price = c.get("price") or 0
                sqft = c.get("squareFootage") or 0
                
                # Calc Price per Sqft
                ppsf = 0
                if sqft > 0 and price > 0:
                    ppsf = round(price / sqft, 2)
                    
                # Last Seen (Days Ago)
                # Input format usually: "2023-10-27T..." or similar. 
                # Be robust.
                last_seen_date = c.get("lastSeen", "")
                days_old = "N/A"
                if last_seen_date:
                    try:
                        # Simple parse if ISO-ish
                        # RentCast often returns 'YYYY-MM-DD...'
                        dt = datetime.datetime.fromisoformat(last_seen_date.replace("Z", "+00:00"))
                        # Just use naive comparison roughly
                        diff = datetime.datetime.now(dt.tzinfo) - dt
                        days_old = diff.days
                    except:
                        pass
                
                # Address parts
                addr_full = c.get("formattedAddress", "Unknown")
                # Try to split for display (Street \n City, Zip)
                addr_line1 = c.get("addressLine1", addr_full.split(",")[0])
                addr_line2 = c.get("addressLine2", "")
                if not addr_line2 and "," in addr_full:
                    # simplistic fallback
                    parts = addr_full.split(",")
                    if len(parts) > 1:
                        addr_line2 = ",".join(parts[1:]).strip()

                top_3.append({
                    "address_line1": addr_line1,
                    "address_line2": addr_line2,
                    "price": price,
                    "ppsf": ppsf,
                    "similarity": c.get("similarityScore", 0) or 0, # Could be None
                    "bedrooms": c.get("bedrooms"),
                    "bathrooms": c.get("bathrooms"),
                    "squareFootage": sqft,
                    "distance": c.get("distance", 0), # Miles
                    "lastSeenDate": last_seen_date[:10] if last_seen_date else "N/A",
                    "daysOld": days_old,
                    "propertyType": c.get("propertyType", "Unknown"),
                    "yearBuilt": c.get("yearBuilt", "")
                })
            
            # Sort by similarity (high to low)
            # Handle None/0 safely by using .get('similarity', 0)
            comps_sorted = sorted(top_3, key=lambda x: x.get("similarity", 0), reverse=True)
            
            # Take Top 5
            comps_final = comps_sorted[:5]
                
            return {
                "estimated_rent": estimate,
                "rent_range": rent_range,  # [Low, High]
                "currency": data.get("currency", "USD"),
                "comparables": comps_final
            }
            
        else:
            print(f"RentCast API Error: {resp.status_code} - {resp.text}")
            
    except Exception as e:
        print(f"RentCast Execution Error: {e}")
        
    return None

def get_nearby_schools_data(lat, lon, supabase_url, supabase_key, miles=3.0):
    """
    Fetch nearby schools using Supabase RPC.
    """
    if not supabase_url or not supabase_key:
        return []
        
    try:
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Call RPC 'get_nearby_schools'
        # user_lat, user_lon, radius_miles
        params = {
            "user_lat": float(lat), 
            "user_lon": float(lon), 
            "radius_miles": float(miles)
        }
        
        response = supabase.rpc("get_nearby_schools", params).execute()
        return response.data # specific to supabase-py v2+
        
    except Exception as e:
        print(f"Supabase School Fetch Error: {e}")
        return []
