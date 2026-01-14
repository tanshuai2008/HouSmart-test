import requests
import urllib.parse
import random
import datetime
import state_data
import state_data
from config_manager import config_manager
from supabase import create_client, Client # Ensure supabase is in requirements
import os
import hashlib
import pickle
import json

CACHE_DIR = "analysis_cache"

def log_debug(msg):
    try:
        with open("debug_log.txt", "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now()}: {str(msg)}\n")
    except Exception:
        pass

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
    def __init__(self, geo_key=None):
        self.geo_key = geo_key
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
            "B03003_003E": "Origin_Hispanic",
            # Income Buckets (B19001)
            "B19001_002E": "Inc_2", "B19001_003E": "Inc_3", "B19001_004E": "Inc_4",
            "B19001_005E": "Inc_5", "B19001_006E": "Inc_6", "B19001_007E": "Inc_7",
            "B19001_008E": "Inc_8", "B19001_009E": "Inc_9", "B19001_010E": "Inc_10", # <50k end
            "B19001_011E": "Inc_11", "B19001_012E": "Inc_12", "B19001_013E": "Inc_13",
            "B19001_014E": "Inc_14", "B19001_015E": "Inc_15", # <125k
            "B19001_016E": "Inc_16", "B19001_017E": "Inc_17", # 125-150, 150-200, 200+ is 018? Assume 17 is max here or add 18
            "B19001_018E": "Inc_17plus", # Just in case
            # Age Buckets (B01001) - Simplified to key ranges if possible, else fetch many
            # Fetching Male (003-025) and Female (027-049) is too many.
            # Use total population to approximate? No. 
            # We need standard query. Just add the critical ones.
            # <18: Male 003(5),004(5-9),005(10-14),006(15-17). Female 027-030.
            "B01001_003E":"Age_M_U5", "B01001_004E":"Age_M_5_9", "B01001_005E":"Age_M_10_14", "B01001_006E":"Age_M_15_17",
            "B01001_027E":"Age_F_U5", "B01001_028E":"Age_F_5_9", "B01001_029E":"Age_F_10_14", "B01001_030E":"Age_F_15_17",
            # 18-24: M 007-010, F 031-034
            "B01001_007E":"Age_M_18_19", "B01001_008E":"Age_M_20", "B01001_009E":"Age_M_21", "B01001_010E":"Age_M_22_24",
            "B01001_031E":"Age_F_18_19", "B01001_032E":"Age_F_20", "B01001_033E":"Age_F_21", "B01001_034E":"Age_F_22_24",
            # 25-44: M 011-014, F 035-038
            "B01001_011E":"Age_M_25_29", "B01001_012E":"Age_M_30_34", "B01001_013E":"Age_M_35_39", "B01001_014E":"Age_M_40_44",
            "B01001_035E":"Age_F_25_29", "B01001_036E":"Age_F_30_34", "B01001_037E":"Age_F_35_39", "B01001_038E":"Age_F_40_44",
            # 45-64: M 015-019, F 039-043
            "B01001_015E":"Age_M_45_49", "B01001_016E":"Age_M_50_54", "B01001_017E":"Age_M_55_59", "B01001_018E":"Age_M_60_61", "B01001_019E":"Age_M_62_64",
            "B01001_039E":"Age_F_45_49", "B01001_040E":"Age_F_50_54", "B01001_041E":"Age_F_55_59", "B01001_042E":"Age_F_60_61", "B01001_043E":"Age_F_62_64",
            # 65+: M 020-025, F 044-049
            "B01001_020E":"Age_M_65_66", "B01001_021E":"Age_M_67_69", "B01001_022E":"Age_M_70_74", "B01001_023E":"Age_M_75_79", "B01001_024E":"Age_M_80_84", "B01001_025E":"Age_M_85",
            "B01001_044E":"Age_F_65_66", "B01001_045E":"Age_F_67_69", "B01001_046E":"Age_F_70_74", "B01001_047E":"Age_F_75_79", "B01001_048E":"Age_F_80_84", "B01001_049E":"Age_F_85"
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
        lat, lon = get_coordinates(address, self.geo_key) # Uses default if no key, but assume key is likely present or defaulting to NY
        
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
            print(f"DEBUG: Calling FCC API with lat={lat}, lon={lon}")
            r = requests.get(fcc_url, params=params, timeout=5)
            if r.status_code == 200:
                data = r.json()
                print(f"DEBUG: FCC Response: {data}")
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
            else:
                print(f"DEBUG: FCC API Status {r.status_code}: {r.text}")
        except Exception as e:
            print(f"DEBUG: FCC API Exception: {e}")
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
            print(f"DEBUG: Fetching ACS Data for State:{state} County:{county} Tract:{tract} BG:{bg}")
            r = requests.get(self.acs_base_url, params=params)
            print(f"DEBUG: ACS Response Code: {r.status_code}")
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
        if local_data is None:
            local_data = {}

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
        
        # 7. Aggregates for Buckets (Viz Utils Support)
        # Income <50k (B19001_002E .. 010E)
        inc_low = sum(local_data.get(f"B19001_{i:03d}E", 0) or 0 for i in range(2, 11))
        # Income 50-150k (011E .. 016E? 016 is 125-150. 017 is 150-200. So 11-16 is <150k)
        inc_mid = sum(local_data.get(f"B19001_{i:03d}E", 0) or 0 for i in range(11, 17))
        # Income >150k (017E .. ?)
        inc_high = (local_data.get("B19001_017E", 0) or 0) + (local_data.get("B19001_018E", 0) or 0) # Adjust if 18 doesn't exist
        
        # Normalize to Percentages? Viz utils expects raw or pct?
        # Viz utils seems to render as is. If passing counts, the bars will be huge counts.
        # But Benchmarks are percentages (e.g. 20.5).
        # So we MUST calculate percentages here.
        total_hh = local_data.get("B19001_001E", 0) or 1
        if total_hh > 0:
            output["metrics"]["income_below_50k"] = {"local": round(inc_low / total_hh * 100, 1)}
            output["metrics"]["income_50k_150k"] = {"local": round(inc_mid / total_hh * 100, 1)}
            output["metrics"]["income_above_150k"] = {"local": round(inc_high / total_hh * 100, 1)}
        
        # Age Aggregates
        # <18: M(3-6) + F(27-30)
        age_u18 = sum(local_data.get(f"B01001_{i:03d}E", 0) or 0 for i in range(3, 7)) + \
                  sum(local_data.get(f"B01001_{i:03d}E", 0) or 0 for i in range(27, 31))
        # 18-24: M(7-10) + F(31-34)
        age_18_24 = sum(local_data.get(f"B01001_{i:03d}E", 0) or 0 for i in range(7, 11)) + \
                    sum(local_data.get(f"B01001_{i:03d}E", 0) or 0 for i in range(31, 35))
        # 25-44: M(11-14) + F(35-38)
        age_25_44 = sum(local_data.get(f"B01001_{i:03d}E", 0) or 0 for i in range(11, 15)) + \
                    sum(local_data.get(f"B01001_{i:03d}E", 0) or 0 for i in range(35, 39))
        # 45-64: M(15-19) + F(39-43)
        age_45_64 = sum(local_data.get(f"B01001_{i:03d}E", 0) or 0 for i in range(15, 20)) + \
                    sum(local_data.get(f"B01001_{i:03d}E", 0) or 0 for i in range(39, 44))
        # 65+: M(20-25) + F(44-49)
        age_65_plus = sum(local_data.get(f"B01001_{i:03d}E", 0) or 0 for i in range(20, 26)) + \
                      sum(local_data.get(f"B01001_{i:03d}E", 0) or 0 for i in range(44, 50))
                      
        total_pop = local_data.get("B01001_001E", 0) or 1
        if total_pop > 0:
            output["metrics"]["age_under_18"] = {"local": round(age_u18 / total_pop * 100, 1)}
            output["metrics"]["age_18_24"] = {"local": round(age_18_24 / total_pop * 100, 1)}
            output["metrics"]["age_25_44"] = {"local": round(age_25_44 / total_pop * 100, 1)}
            output["metrics"]["age_45_64"] = {"local": round(age_45_64 / total_pop * 100, 1)}
            output["metrics"]["age_65_plus"] = {"local": round(age_65_plus / total_pop * 100, 1)}

        # Education Percentages (Viz Utils expects these keys directly? No, it uses edu_high_school etc)
        # viz_utils keys: edu_high_school, edu_bachelor, edu_graduate
        # We store raw counts above: Edu_HS_Diploma, Edu_Bachelor, etc.
        # But viz_utils expects keys "edu_high_school" etc. AND they should be percents to match benchmarks.
        if total_25_plus > 0:
             # HS = HS Diploma + GED? (Usually 017E is Regular HS, 018E is GED)
             # B15003_017E is Regular HS. B15003_018E is GED.
             # We only fetched 017E in vars. Let's assume simplified.
             # Actually we Should create the specific keys expected by viz_utils
             output["metrics"]["edu_high_school"] = {"local": round(e_hs / total_25_plus * 100, 1)}
             output["metrics"]["edu_bachelor"] = {"local": round(e_bach / total_25_plus * 100, 1)}
             output["metrics"]["edu_graduate"] = {"local": round((e_mast + e_prof + e_doc) / total_25_plus * 100, 1)}

        # Race Percentages
        # viz_utils keys: race_white, race_black, race_asian, race_hispanic, race_other
        if r_tot > 0:
             output["metrics"]["race_white"] = {"local": round(r_white / r_tot * 100, 1)}
             output["metrics"]["race_black"] = {"local": round(r_black / r_tot * 100, 1)}
             output["metrics"]["race_asian"] = {"local": round(r_asian / r_tot * 100, 1)}
             output["metrics"]["race_hispanic"] = {"local": round(r_hisp / r_tot * 100, 1)}
             r_other = r_tot - (r_white + r_black + r_asian + r_hisp)
             output["metrics"]["race_other"] = {"local": round(max(0, r_other) / r_tot * 100, 1)}

        return output

def get_census_data(address, geo_key=None):
    """
    Main entry point for App to get Census Data.
    """
    log_debug(f"Starting Census Fetch for: {address}")
    try:
        if not config_manager.get_config().get("enable_census", True):
            log_debug("Census API Disabled in Config")
            print("DEBUG: Census API Disabled in Config")
            return None

        service = CensusDataService(geo_key=geo_key)
        
        # 1. Geocode
        print(f"DEBUG: Geocoding {address}...")
        geo_data = service.get_census_geoid(address)
        log_debug(f"Geode Result: {geo_data}")
        print(f"DEBUG: Geocode Result: {geo_data}")
        
        if not geo_data:
            print("DEBUG: Geocoding Failed. No data returned.")
            return None
            
        # 2. Get Data
        acs_data = service.get_acs_data(geo_data)
        if acs_data is None:
             print("DEBUG: ACS Data is None. Proceeding with Benchmarks only.")
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


def get_cached_rentcast(key_data):
    """
    Retrieve cached RentCast data.
    """
    try:
        if not os.path.exists(CACHE_DIR):
            return None
            
        # Create hash key
        key_str = json.dumps(key_data, sort_keys=True).encode('utf-8')
        file_hash = hashlib.md5(key_str).hexdigest()
        filename = os.path.join(CACHE_DIR, f"rent_{file_hash}.pkl")
        
        if os.path.exists(filename):
            # Check modification time (TTL: 240 hours / 10 days)
            mtime = os.path.getmtime(filename)
            file_time = datetime.datetime.fromtimestamp(mtime)
            age = datetime.datetime.now() - file_time
            
            if age.total_seconds() < 240 * 3600:
                with open(filename, 'rb') as f:
                    return pickle.load(f)
    except Exception as e:
        print(f"RentCast Cache Read Error: {e}")
    return None

def save_rentcast_cache(key_data, data):
    """
    Save RentCast data to cache.
    """
    try:
        if not os.path.exists(CACHE_DIR):
            os.makedirs(CACHE_DIR)
            
        key_str = json.dumps(key_data, sort_keys=True).encode('utf-8')
        file_hash = hashlib.md5(key_str).hexdigest()
        filename = os.path.join(CACHE_DIR, f"rent_{file_hash}.pkl")
        
        with open(filename, 'wb') as f:
            pickle.dump(data, f)
    except Exception as e:
        print(f"RentCast Cache Save Error: {e}")

def get_rentcast_data(address, bedrooms, bathrooms, sqft, property_type, api_key):
    """
    Fetch Rent Estimates and Comparables from RentCast API.
    Checks Cache First.
    """
    if not config_manager.get_config().get("enable_rentcast", True):
        return None

    # Check Cache
    cache_key = {
        "address": address,
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "sqft": sqft,
        "propertyType": property_type
    }
    
    cached = get_cached_rentcast(cache_key)
    if cached:
        print("Using Cached RentCast Data")
        return cached

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
    
    print(f"DEBUG: RentCast Params: {params}")
    
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
                
            result = {
                "estimated_rent": estimate,
                "rent_range": rent_range,  # [Low, High]
                "currency": data.get("currency", "USD"),
                "comparables": comps_final
            }
            
            # Save to Cache
            save_rentcast_cache(cache_key, result)
            
            return result
            
        else:
            print(f"RentCast API Error: {resp.status_code} - {resp.text}")
            
    except Exception as e:
        print(f"RentCast Execution Error: {e}")
        
    return None

def get_rentcast_value(address, bedrooms, bathrooms, sqft, property_type, api_key):
    """
    Fetch Property Value Estimate (AVM) from RentCast API.
    Checks Cache First.
    """
    if not config_manager.get_config().get("enable_rentcast", True):
        return None

    # Check Cache
    cache_key = {
        "type": "value_avm", # Distinguish from rent
        "address": address,
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "sqft": sqft,
        "propertyType": property_type
    }
    
    cached = get_cached_rentcast(cache_key)
    if cached:
        print("Using Cached RentCast Value")
        return cached

    if not api_key:
        return None

    url = "https://api.rentcast.io/v1/avm/value"
    
    params = {
        "address": address,
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "squareFootage": sqft,
        "propertyType": property_type
    }
    
    headers = {
        "accept": "application/json",
        "X-Api-Key": api_key
    }
    
    try:
        resp = requests.get(url, params=params, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            
            result = {
                "estimated_value": data.get("price", 0),
                "value_range": [data.get("priceRangeLow", 0), data.get("priceRangeHigh", 0)],
                "currency": data.get("currency", "USD")
            }
            
            # Save to Cache
            save_rentcast_cache(cache_key, result)
            
            return result
            
        else:
            print(f"RentCast Value API Error: {resp.status_code} - {resp.text}")
            
    except Exception as e:
        print(f"RentCast Value Execution Error: {e}")
        
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
