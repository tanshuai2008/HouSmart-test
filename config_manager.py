import json
import os
import time
from typing import Dict, Any

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "model_name": "gemini-2.5-flash",
    "temperature": 0.7,
    "customized_scoring_method": False,
    "cache_ttl_hours": 240,
    "enable_daily_limit": True,
    "whitelist_emails": [],
    "enable_geoapify": True,
    "enable_rentcast": True,
    "enable_census": True,
    "enable_llm": True
}

class ConfigManager:
    _instance = None
    _config_cache: Dict[str, Any] = {}
    _last_load_time = 0
    _last_mtime = 0

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._ensure_config_exists()
        return cls._instance

    def _ensure_config_exists(self):
        if not os.path.exists(CONFIG_FILE):
            self.save_config(DEFAULT_CONFIG)

    def get_config(self) -> Dict[str, Any]:
        """
        Get configuration, reloading from disk if file has changed.
        Checks file modification time.
        """
        try:
            if not os.path.exists(CONFIG_FILE):
                return DEFAULT_CONFIG.copy()

            mtime = os.path.getmtime(CONFIG_FILE)
            
            # Reload if file changed or cache is empty
            if mtime > self._last_mtime or not self._config_cache:
                with open(CONFIG_FILE, 'r') as f:
                    self._config_cache = json.load(f)
                self._last_mtime = mtime
                self._last_load_time = time.time()
                
            # Merge with defaults to ensure all keys exist
            config = DEFAULT_CONFIG.copy()
            config.update(self._config_cache)
            return config
            
        except Exception as e:
            print(f"Error reading config: {e}")
            return DEFAULT_CONFIG.copy()

    def save_config(self, new_config: Dict[str, Any]):
        """
        Save configuration to disk.
        """
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(new_config, f, indent=4)
            
            # Update cache immediately
            self._config_cache = new_config
            self._last_mtime = os.path.getmtime(CONFIG_FILE)
            self._last_load_time = time.time()
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

# Global instance
config_manager = ConfigManager()
