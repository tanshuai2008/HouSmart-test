import google.generativeai as genai
import os
import json

import google.api_core.exceptions

import state_data

# Module-level variable to store keys
_GEMINI_KEYS = []

def configure_genai(api_keys):
    """
    Configure the Gemini API with the provided key(s).
    Accepts a single string or a list of strings.
    """
    global _GEMINI_KEYS
    if not api_keys:
        return False
        
    if isinstance(api_keys, str):
        _GEMINI_KEYS = [api_keys]
    elif isinstance(api_keys, list):
        _GEMINI_KEYS = api_keys
    else:
        return False
    
    # Configure with the first key initially
    if _GEMINI_KEYS:
        genai.configure(api_key=_GEMINI_KEYS[0])
        return True
    return False

def call_with_rotation(func_to_call, *args, **kwargs):
    """
    Helper to call a GenAI function with key rotation on quota error.
    """
    global _GEMINI_KEYS
    
    # Try each key
    for i, key in enumerate(_GEMINI_KEYS):
        try:
            # Re-configure with current key
            genai.configure(api_key=key)
            return func_to_call(*args, **kwargs)
        except google.api_core.exceptions.ResourceExhausted as e:
            print(f"Key {i} exhausted. Rotating...")
            if i == len(_GEMINI_KEYS) - 1:
                # Last key failed
                print("All keys exhausted.")
                raise e # Re-raise if no more keys
        except Exception as e:
            # If it's not a quota error, verify if text indicates quota
            # Sometimes specific quota errors are just generic 429s wrapped differently
            lower_err = str(e).lower()
            if "quota" in lower_err or "429" in lower_err:
                 print(f"Key {i} quota/429 error. Rotating...")
                 if i == len(_GEMINI_KEYS) - 1:
                    print("All keys exhausted.")
                    raise e
            else:
                # Other error, re-raise immediately
                raise e
    return None

def get_available_models():
    """
    List available models that support generation.
    """
    try:
        models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                models.append(m.name)
        return models
    except Exception as e:
        return [f"Error listing models: {str(e)}"]

def estimate_census_data(address, model_name='models/gemini-1.5-flash'):
    """
    Estimate census data for a location using LLM knowledge.
    """
    try:
        model = genai.GenerativeModel(model_name)
        prompt = f"""
        Provide a realistic ESTIMATE of demographic/census data for the location: "{address}".
        
        Return pure JSON with these exact keys:
        - "population_density": (string, e.g. "High", "Low")
        - "median_household_income": (string with currency)
        - "median_age": (integer)
        - "education_level": (string)
        - "unemployment_rate": (string percentage)
        - "housing_vacancy_rate": (string percentage)
        - "top_industries": (list of strings)
        
        Based on general knowledge of the area.
        """

        def _generate():
            response = model.generate_content(prompt)
            data = json.loads(response.text.replace('```json', '').replace('```', '').strip())
            return data

        data = call_with_rotation(_generate)
        return data
    except Exception:
        return {
            "error": "Could not estimate census data."
        }


def analyze_location(address, poi_data, census_data, model_name='models/gemini-1.5-flash'):
    """
    Analyze the location using Gemini.
    """
    # Handle short names vs full names
    if not model_name.startswith('models/'):
        # If user selected a short name or we defaulted, try to align
        pass 
        
    try:
        model = genai.GenerativeModel(model_name)
        
        # Look up state benchmarks
        # Try to extract state from address string (naive approach: look for state names)
        # We can iterate through the keys in state_data.INCOME_DATA
        detected_state = "United States" # Fallback
        
        # Simple lookup
        for s_name in state_data.INCOME_DATA.keys():
            if s_name in address:
                detected_state = s_name
                break
        
        # Get benchmarks
        benchmarks = state_data.get_state_benchmarks(detected_state)
        
        # Construct prompt
        prompt = f"""
        You are a real estate investment expert. Analyze the following location data for "{address}".
        
        POI Data (Sample): {str(poi_data)[:2000]}... # Truncate if too long
        Census Data (Target Location): {census_data}
        
        CONTEXTUAL BENCHMARKS (Use these for comparison):
        State ({benchmarks['state_name']}) Median Income: ${benchmarks['state_income']:,}
        State ({benchmarks['state_name']}) Education (HS+|Bach+|Grad+): {benchmarks['state_edu']}
        State ({benchmarks['state_name']}) Age (Under18|18-24|25-44|45-64|65+): {benchmarks['state_age']}
        State ({benchmarks['state_name']}) Race (White|Hisp|Black|Asian|Other): {benchmarks['state_race']}
        
        National Median Income: ${benchmarks['us_income']:,}
        National Education (HS+|Bach+|Grad+): {benchmarks['us_edu']}
        National Age (Under18|18-24|25-44|45-64|65+): {benchmarks['us_age']}
        National Race (White|Hisp|Black|Asian|Other): {benchmarks['us_race']}
        
        Please provide an analysis in pure JSON format with the following keys:
        - "highlights": [list of strings describing pros]. Max 4 points. Total word count for this list must be under 80 words.
        - "risks": [list of strings describing cons]. Max 3 points. Total word count for this list must be under 60 words.
        - "score": (integer 0-100). Use the Benchmarks to help determine if this is a high-income/educated area relative to the state/nation.
        - "investment_strategy": (string describing brief strategy). Max 50 words.
        
        Do not use Markdown code blocks. Just valid JSON.
        If there are any numbers or values, always make them **Bold**.
        """
        

        
        def _generate():
            response = model.generate_content(prompt)
            # Attempt to clean code blocks if present
            text_content = response.text.replace('```json', '').replace('```', '').strip()
            data = json.loads(text_content)
            return data

        data = call_with_rotation(_generate)
        return data
    except Exception as e:
        return {
            "highlights": ["Error generating analysis"],
            "risks": [f"Model: {model_name}", str(e)],
            "score": 0,
            "investment_strategy": "Please check API Key or Model selection."
        }
