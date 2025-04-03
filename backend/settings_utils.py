# backend/settings_utils.py
import json
from pathlib import Path
from pydantic import BaseModel

# --- Configuration --- #
SETTINGS_FILE = Path(__file__).parent / "settings.json" # Path to settings file relative to this file

# --- Pydantic Model --- #
class UserSettings(BaseModel):
    urgent_context: str = ""
    delegate_context: str = ""
    loop_context: str = ""

# --- Utility Functions --- #
def load_settings() -> UserSettings:
    """Loads settings from the JSON file."""
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, 'r') as f:
                data = json.load(f)
                # Validate data against Pydantic model
                return UserSettings(**data) 
        except (json.JSONDecodeError, TypeError, Exception) as e:
            print(f"[WARN] Error loading settings file ({SETTINGS_FILE}): {e}. Returning defaults.")
            return UserSettings() 
    else:
        print(f"Settings file not found ({SETTINGS_FILE}). Returning defaults.")
        return UserSettings()

def save_settings(settings: UserSettings):
    """Saves settings to the JSON file."""
    try:
        with open(SETTINGS_FILE, 'w') as f:
            # Use model_dump (v2) or dict() (v1)
            json.dump(settings.model_dump() if hasattr(settings, 'model_dump') else settings.dict(), f, indent=4)
        print(f"Settings saved successfully to {SETTINGS_FILE}")
    except Exception as e:
        print(f"[ERROR] Failed to save settings to {SETTINGS_FILE}: {e}") 