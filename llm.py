import google.generativeai as genai
import os
import json
import time
import random
import hashlib
import pickle
import datetime

import google.api_core.exceptions

import state_data
from config_manager import config_manager

# Module-level variable to store keys
_GEMINI_KEYS = []
CACHE_DIR = "analysis_cache"
_LAST_CALL_TM = 0.0
_REQUEST_HISTORY = []

# Ensure cache directory exists
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

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

def get_cached_analysis(address, weights=None):
    """
    Retrieve cached analysis if valid (exists and < 240 hours old).
    Key is based on hash(address + weights).
    """
    try:
        # Create a unique key based on address and weights
        # Sort weights to ensure consistent hashing key for dicts
        weight_str = json.dumps(weights, sort_keys=True) if weights else "None"
        key_str = f"{address}_{weight_str}".encode('utf-8')
        file_hash = hashlib.md5(key_str).hexdigest()
        filename = os.path.join(CACHE_DIR, f"{file_hash}.pkl")
        
        if os.path.exists(filename):
            # Check modification time
            mtime = os.path.getmtime(filename)
            file_time = datetime.datetime.fromtimestamp(mtime)
            age = datetime.datetime.now() - file_time
            
            # Get Cache TTL from config
            config = config_manager.get_config()
            ttl_hours = config.get("cache_ttl_hours", 240)
            
            if age.total_seconds() < ttl_hours * 3600:
                with open(filename, 'rb') as f:
                    data = pickle.load(f)
                
                # Inject cache metadata if not present
                if '_cache_meta' not in data:
                    data['_cache_meta'] = {'timestamp': file_time.strftime("%Y-%m-%d %H:%M:%S")}
                return data
    except Exception as e:
        print(f"Cache usage error: {e}")
        return None
    return None

def save_to_cache(address, data, weights=None):
    """
    Save analysis result to cache.
    """
    try:
        weight_str = json.dumps(weights, sort_keys=True) if weights else "None"
        key_str = f"{address}_{weight_str}".encode('utf-8')
        file_hash = hashlib.md5(key_str).hexdigest()
        filename = os.path.join(CACHE_DIR, f"{file_hash}.pkl")
        
        # Add metadata before saving
        data['_cache_meta'] = {'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        
        with open(filename, 'wb') as f:
            pickle.dump(data, f)
    except Exception as e:
        print(f"Cache save error: {e}")

def call_with_retry(func, max_retries=5):
    """
    Execute a function with exponential backoff for 429/ResourceExhausted errors.
    Waits (2^i + jitter) seconds between retries.
    """
    for i in range(max_retries):
        try:
            return func()
        except Exception as e:
            # Check for Quota/429 errors
            is_quota_error = False
            if isinstance(e, google.api_core.exceptions.ResourceExhausted):
                is_quota_error = True
            elif "quota" in str(e).lower() or "429" in str(e).lower():
                is_quota_error = True
            
            # If it's not a quota error, or if it's the last retry, re-raise
            if not is_quota_error or i == max_retries - 1:
                raise e
            
            # Exponential Backoff with higher base for strict limits
            # 5s + 2^i + jitter (e.g., 6s, 8s, 10s...)
            wait_time = 5.0 + (2 ** i) + random.uniform(0, 1)
            print(f"Quota hit. Retrying in {wait_time:.2f}s... (Attempt {i+1}/{max_retries})")
            time.sleep(wait_time)
    return None

def call_with_rotation(func_to_call, *args, **kwargs):
    """
    Helper to call a GenAI function with key rotation on quota error.
    Includes internal retry logic per key.
    Implements Global Rate Limiting & Throttling.
    """
    global _GEMINI_KEYS, _LAST_CALL_TM, _REQUEST_HISTORY
    
    # --- Rate Limiting Logic ---
    now = time.time()
    
    # 1. Minute Throttling (Sliding Window)
    # Remove timestamps older than 60 seconds
    _REQUEST_HISTORY = [t for t in _REQUEST_HISTORY if now - t < 60]
    
    if len(_REQUEST_HISTORY) > 15: # Max 15 requests per minute
        print("Rate Limit: Throttling (Max 15 req/min). Waiting 5s...")
        time.sleep(5) 
        # Re-check or just proceed slowly? 
        # A simple sleep allows basic recovery without complex queuing
        
    _REQUEST_HISTORY.append(now)
    
    # 2. Global Request Spacing (2-3s)
    elapsed = now - _LAST_CALL_TM
    if elapsed < 2.5:
        # If we called it too recently, forced wait
        delay = 2.5 - elapsed + random.uniform(0, 0.5)
        print(f"Rate Limit: Spacing delay {delay:.2f}s")
        time.sleep(delay)
        
    _LAST_CALL_TM = time.time()
    
    # --- End Rate Limiting ---
    
    # Try each key
    for i, key in enumerate(_GEMINI_KEYS):
        try:
            # Re-configure with current key
            genai.configure(api_key=key)
            
            # Use retry logic for THIS key
            # We wrap the call in a lambda so call_with_retry can execute it
            return call_with_retry(lambda: func_to_call(*args, **kwargs))
            
        except Exception as e:
            # Check if we should rotate
            is_quota_error = False
            if isinstance(e, google.api_core.exceptions.ResourceExhausted):
                is_quota_error = True
            elif "quota" in str(e).lower() or "429" in str(e).lower():
                is_quota_error = True

            if is_quota_error:
                print(f"Key {i} exhausted after retries. Rotating...")
                if i == len(_GEMINI_KEYS) - 1:
                    print("All keys exhausted.")
                    raise e
            else:
                # Other error (e.g. 400, 500), re-raise immediately
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

def analyze_location(address, poi_data, census_data, model_name=None, weights=None, user_prefs=None):
    """
    Analyze the location using Gemini.
    Merged functionality: Estimates Census data if missing, and provides Investment Analysis.
    Now includes Result Caching (240 Hours).
    """
    # 1. Check Cache (Include user_prefs in cache key if significant, but for simplicity, we might just re-run or rely on weights)
    # Actually, if preferences change, we SHOULD re-run analysis. 
    # Let's include user_prefs in the cache key/hash logic implicitly or explicitly?
    # For now, let's strictly pass "user_prefs" into the prompt.
    # To avoid stale cache invalidation issues, we should ideally include it in the hash, 
    # but the cache function signature needs update.
    # Alternative: Disable cache if user_prefs are provided? Or just risk it?
    # Let's bypass cache if user_prefs is present to ensure fresh "Warning" generation.
    if not user_prefs:
        cached_result = get_cached_analysis(address, weights=weights)
        if cached_result:
            print("Using cached analysis.")
            return cached_result

    # 1.5 Get Config
    config = config_manager.get_config()
    
    # CHECK ENABLE FLAG
    if not config.get("enable_llm", True):
        return {
            "highlights": ["AI Analysis is currently disabled by Admin."],
            "risks": [],
            "score": 0,
            "investment_strategy": "Feature disabled.",
            "estimated_census": {"metrics": {}}
        }

    # Priority: Function Arg > Config > Default
    # But for "Dynamic Config" requirement, if user didn't explicitly pass a model (passed default), we should prefer config.
    # The default arg is 'models/gemini-1.5-flash'. If caller passed anything else, respect it.
    # However, app.py passes model_name from st.session_state. We should update app.py to get it from config.
    # Here we just ensure we have a fallback or override if needed.
    # Actually, let's just use the config for temperature effectively.
    
    if not model_name:
        model_name = config.get("model_name", "models/gemini-2.5-flash")
    
    current_model_name = model_name
    temperature = config.get("temperature", 0.7)

    # Handle short names vs full names
    if not model_name.startswith('models/'):
        pass 
        
    try:
        # Define Schema for Structured Output
        # We want a robust JSON output
        analysis_schema = {
            "type": "OBJECT",
            "properties": {
                "highlights": {
                    "type": "ARRAY", 
                    "items": {"type": "STRING"}
                },
                "risks": {
                    "type": "ARRAY", 
                    "items": {"type": "STRING"}
                },
                "score": {"type": "INTEGER"},
                "investment_strategy": {"type": "STRING"},
                "estimated_census": {
                    "type": "OBJECT",
                    "properties": {
                        "metrics": {
                            "type": "OBJECT",
                            "properties": {
                                "median_household_income": {"type": "STRING", "description": "e.g. $75,000"},
                                "education_bachelors_pct": {"type": "INTEGER", "description": "Percentage 0-100"},
                                "population_density": {"type": "STRING", "description": "High/Medium/Low"}
                            }
                        }
                    }
                }
            },
            "required": ["highlights", "risks", "score", "investment_strategy"]
        }
        
        # Configure model with valid generation config
        generation_config = {
            "response_mime_type": "application/json",
            "response_schema": analysis_schema
        }
        
        model = genai.GenerativeModel(
            model_name=current_model_name,
            generation_config=generation_config
        )
        # Set temperature via generation_config if supported in this SDK version, 
        # or we might need to update generation_config dict.
        generation_config["temperature"] = temperature
        
        # Look up state benchmarks
        detected_state = "United States" 
        for s_name in state_data.INCOME_DATA.keys():
            if s_name in address:
                detected_state = s_name
                break
        benchmarks = state_data.get_state_benchmarks(detected_state)
        
        # Construct prompt
        if weights:
            weight_str = json.dumps(weights, indent=2)

        prefs_section = ""
        if user_prefs:
            prefs_section = f"""
        [IMPORTANT: USER PREFERENCE ANALYSIS]
        The user has specific preferences (see below). When analyzing, do NOT simply say "Recommended" or "Not Recommended" based on these.
        Instead, follow this "Objective Evidence" protocol:
        
        1. DETECT CONFLICT: Check if the property data conflicts with USER PREFERENCES.
        2. EXTRACT EVIDENCE: Search for QUANTITATIVE data (e.g., "0.5 miles from highway", "2 mins to train") or specific QUALITATIVE descriptions.
        3. NEUTRAL ALERT: If a potential conflict is found, you MUST add a warning in the 'risks' array using this EXACT format:
           "⚠️ Preference Alert: You previously mentioned dislike for [Preference Item]. This property [Specific Evidence]. Please determine if this is acceptable."
           
        Example: "⚠️ Preference Alert: You dislike highway noise. This property is located 0.5 miles from I-95. Please determine if this is acceptable."

        USER PREFERENCES CONTEXT:
        {user_prefs}
        """

        prompt = f"""
        You are a real estate investment expert. Analyze the following location data for "{address}".
        
        USER PRIORITIES (Weights 0-100):
        {weight_str}
        {prefs_section}
        Adjust your 'score', 'highlights', and 'risks' based on these priorities.
        
        INPUT DATA:
        - POI Data (Sample): {str(poi_data)[:1500]}...
        - Census Data (Provided): {census_data}
        
        INSTRUCTIONS:
        1. If 'Census Data' is missing, empty, or invalid, you MUST ESTIMATE the 'estimated_census' fields (Income, Education, Density) based on the address location.
        2. If 'Census Data' is provided, you can just mirror it in 'estimated_census' or refine it.
        3. Provide 'highlights' (Max 4), 'risks' (Max 3), 'score' (0-100), and 'investment_strategy' (Max 50 words).
        
        CONTEXTUAL BENCHMARKS:
        State ({benchmarks['state_name']}) Income: ${benchmarks['state_income']:,}
        National Income: ${benchmarks['us_income']:,}
        """
        
        def _generate():
            response = model.generate_content(prompt)
            # With structured output, response.text should be valid JSON
            return json.loads(response.text)

        data = call_with_rotation(_generate)
        
        # 2. Save to Cache
        if data and "error" not in data:
            save_to_cache(address, data, weights=weights)
            
        return data

    except Exception as e:
        print(f"Analysis Error: {e}")
        return {
            "highlights": ["Error generating analysis"],
            "risks": [str(e)],
            "score": 0,
            "investment_strategy": "System Error.",
            "estimated_census": {"metrics": {}}
        }

def refine_preferences(current_summary, new_feedback, model_name='models/gemini-1.5-flash'):
    """
    Refine the user's preference summary based on new feedback.
    """
    try:
        model = genai.GenerativeModel(model_name)
        
        prompt = f"""
        You are a Personal Real Estate Preference Assistant.
        
        CURRENT PREFERENCE SUMMARY:
        "{current_summary or 'No prior preferences.'}"
        
        NEW USER FEEDBACK:
        "{new_feedback}"
        
        TASK:
        Update and refine the "Current Preference Summary" to incorporate the "New User Feedback".
        - Convert specific feedback into general rules (e.g., "Too noisy here" -> "Avoid areas with high noise levels").
        - Keep it concise (bullet points or a short paragraph).
        - If the new feedback contradicts old preferences, update to reflect the LATEST feedback.
        
        OUTPUT (The new summary ONLY):
        """
        
        response = call_with_rotation(lambda: model.generate_content(prompt))
        if response and response.text:
            return response.text.strip()
        return current_summary
        
    except Exception as e:
        print(f"Preference Refinement Error: {e}")
        # Fallback: Just append
        return f"{current_summary}\n- {new_feedback}" if current_summary else new_feedback
