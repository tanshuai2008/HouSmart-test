import requests
import urllib.parse
import random
import state_data

# Map state FIPS to state names for benchmark lookup if needed
# (Or we can reverse look up from state_data if we had FIPS mapping, 
# but for now let's hope we rely on the address or simple mapping if needed)
# Actually, the Census Geocoder returns State Name usually.


def get_coordinates(address, api_key):
    """
    Get coordinates for an address using Geoapify Geocoding API.
    """
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

def get_poi(address, api_key=None):
    """
    Fetch POIs around the address using Geoapify Places API.
    """
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
        # Since currently it's 2026, we use 2024 ACS 5-Year Data
        self.acs_base_url = "https://api.census.gov/data/2024/acs/acs5"
        self.variables = {
            "B19013_001E": "Median Household Income",
            "B25077_001E": "Median Home Value",
            "B25064_001E": "Median Gross Rent"
        }

    def get_census_geoid(self, address):
        """
        Step 1: Convert address to Block Group GEOID.
        """
        params = {
            "address": address,
            "benchmark": "Public_AR_Current",
            "vintage": "Current_Current",
            "layers": "10", # Block Groups
            "format": "json"
        }
        
        try:
            resp = requests.get(self.geocoder_url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                matches = data.get('result', {}).get('addressMatches', [])
                if matches:
                    geo = matches[0]['geographies']['Census Block Groups'][0]
                    
                    # Padding FIPS codes (zfill)
                    state = geo['STATE'].zfill(2)
                    county = geo['COUNTY'].zfill(3)
                    tract = geo['TRACT'].zfill(6)
                    block_group = geo['BLKGRP']
                    
                    full_geoid = f"{state}{county}{tract}{block_group}"
                    
                    return {
                        "full_geoid": full_geoid,
                        "state": state,
                        "county": county,
                        "tract": tract,
                        "block_group": block_group,
                        "state_name_ref": geo.get("BASENAME", "") # Usually need state name for lookup
                    }
        except Exception as e:
            print(f"Geocoder Error: {e}")
            
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
                            if val and int(val) > 0:
                                result[code] = int(val)
                            else:
                                result[code] = None
                    return result
        except Exception as e:
            print(f"ACS API Error: {e}")
            
        return None

    def compare_with_benchmarks(self, local_data, geoid_data):
        """
        Step 3: Compare local results with State Benchmarks.
        """
        if not local_data:
            return None

        # Try to find State Name from FIPS or pass it in. 
        # Geocoder "state_name_ref" might be Block Group name, not State name.
        # Simple FIPS lookup for state data might be needed if we want to be robust. 
        # For now, let's look up by FIPS provided in `state_data` if available, or just ignore exact state match if we don't have mapping code.
        # Actually, `state_data` keys are Names.
        # We need a FIPS -> Name mapper.
        
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
            "benchmarks": {
                "state_median_income": benchmarks['state_income'],
                "national_median_income": benchmarks['us_income']
            }
        }
        
        # Populate Metrics
        # Household Income
        med_income = local_data.get("B19013_001E")
        output["metrics"]["median_household_income"] = f"${med_income:,}" if med_income else "N/A"
        
        # Home Value
        med_value = local_data.get("B25077_001E")
        output["metrics"]["median_home_value"] = f"${med_value:,}" if med_value else "N/A"
        
        # Rent
        med_rent = local_data.get("B25064_001E")
        output["metrics"]["median_gross_rent"] = f"${med_rent:,}" if med_rent else "N/A"
        
        return output

def get_census_data(address):
    """
    Main entry point for App to get Census Data.
    """
    service = CensusDataService()
    
    # 1. Geocode
    geo_data = service.get_census_geoid(address)
    if not geo_data:
        return None
        
    # 2. Get Data
    acs_data = service.get_acs_data(geo_data)
    
    # 3. Compare & Compile
    final_result = service.compare_with_benchmarks(acs_data, geo_data)
    
    if final_result:
        final_result['source'] = "US Census Bureau (2024 ACS 5-year)"
        
    return final_result

def get_rentcast_data(address, bedrooms, bathrooms, sqft, property_type, api_key):
    """
    Fetch Rent Estimates and Comparables from RentCast API.
    """
    if not api_key:
        return None

    # RentCast endpoint
    url = "https://api.rentcast.io/v1/avm/rent/long-term"
    
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
            
            # Extract basic estimate
            estimate = data.get("rent", 0)
            rent_range = [data.get("rentRangeLow", 0), data.get("rentRangeHigh", 0)]
            
            # Extract Comps
            comps = data.get("comparables", [])
            
            # Sort by similarity score (descending) if available.
            comps.sort(key=lambda x: x.get("similarityScore", 0), reverse=True)
            
            top_3 = []
            for c in comps[:3]:
                top_3.append({
                    "address": c.get("formattedAddress"),
                    "price": c.get("price"),
                    "similarity": c.get("similarityScore")
                })
                
            return {
                "estimated_rent": estimate,
                "rent_range": rent_range,  # [Low, High]
                "currency": data.get("currency", "USD"),
                "comparables": top_3
            }
            
        else:
            print(f"RentCast API Error: {resp.status_code} - {resp.text}")
            
    except Exception as e:
        print(f"RentCast Execution Error: {e}")
        
    return None
