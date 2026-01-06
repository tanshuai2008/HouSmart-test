import time
import os
import json
from config_manager import config_manager, CONFIG_FILE

def test_config_reload():
    print("Testing Config Manager Reload...")
    
    # Ensure starting state
    start_config = config_manager.get_config()
    print(f"Initial Config Model: {start_config.get('model_name')}")
    
    # Modify config file directly
    new_config = start_config.copy()
    new_config['model_name'] = "test-model-reload"
    
    # Wait a bit to ensure mtime changes
    time.sleep(1.1) 
    
    with open(CONFIG_FILE, 'w') as f:
        json.dump(new_config, f)
    
    # Check if ConfigManager picks it up
    updated_config = config_manager.get_config()
    print(f"Updated Config Model: {updated_config.get('model_name')}")
    
    if updated_config.get('model_name') == "test-model-reload":
        print("SUCCESS: Config reload detected.")
    else:
        print("FAILURE: Config reload NOT detected.")

    # Clean up (restore default/original)
    original_config = start_config
    if original_config.get('model_name') == "test-model-reload":
        original_config['model_name'] = "gemini-2.5-flash"
        
    time.sleep(1.1)
    config_manager.save_config(original_config)
    print("Test Complete.")

if __name__ == "__main__":
    test_config_reload()
