import requests

base_url = "https://api.census.gov/data/2022/acs/acs5"
# Empire State Building Block Group
state = "36"
county = "061"
tract = "007600"
bg = "1"

variables = {
    "B19013_001E": "Median Household Income",
    "B25077_001E": "Median Home Value",
    "B25064_001E": "Median Gross Rent",
    "B15003_001E": "Edu_Total_25_Plus",
    "B15003_017E": "Edu_HS_Diploma",
    "B15003_022E": "Edu_Bachelor", 
    "B15003_023E": "Edu_Master",
    "B15003_024E": "Edu_Prof",
    "B15003_025E": "Edu_Doctorate",
    "B01002_001E": "Median Age",
    "B01001_001E": "Total Population",
    "B02001_002E": "Race_White",
    "B02001_003E": "Race_Black",
    "B02001_005E": "Race_Asian",
    "B03003_003E": "Origin_Hispanic"
}

print(f"Testing {len(variables)} variables against {base_url}...")

# Test 1: All at once (Baseline)
vars_str = ",".join(variables.keys())
params = {
    "get": f"NAME,{vars_str}",
    "for": f"block group:{bg}",
    "in": f"state:{state} county:{county} tract:{tract}"
}
print("\n--- Test 1: All Variables ---")
r = requests.get(base_url, params=params)
print(f"Status: {r.status_code}")
if r.status_code != 200:
    print(f"Error: {r.text}")

# Test 2: Individual
print("\n--- Test 2: Individual Variables ---")
for code, name in variables.items():
    params = {
        "get": f"NAME,{code}",
        "for": f"block group:{bg}",
        "in": f"state:{state} county:{county} tract:{tract}"
    }
    r = requests.get(base_url, params=params)
    if r.status_code != 200:
        print(f"[FAIL] {code} ({name}): {r.status_code} - {r.text}")
    else:
        print(f"[PASS] {code} ({name})")
