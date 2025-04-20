import json
import os
from typing import Any, Dict, List

CONFIG_FILE = "config.json"
DEFAULT_SETTINGS = {
    "kobold_port": 5001,
    "max_length": 250,
    "temperature": 0.15,
    "min_p": 0.1,
    "top_p": 0.95,
    "rep_pen": 1.0,
    "stop_sequences": ["[INST]", "[/INST]"] # Default stop sequences
}

def get_config_path() -> str:
    """Gets the absolute path to the config file."""
    # Assuming config.json is in the project root (where main.py is)
    # Adjust if settings.py is moved or config location changes
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(project_root, CONFIG_FILE)

def load_settings() -> Dict[str, Any]:
    """Loads settings from the config file or returns defaults."""
    config_path = get_config_path()
    settings = DEFAULT_SETTINGS.copy() # Start with defaults
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                loaded_settings = json.load(f)
                # Update defaults with loaded values, ensuring keys exist
                for key in DEFAULT_SETTINGS:
                    if key in loaded_settings:
                        # Basic type validation (can be expanded)
                        if isinstance(loaded_settings[key], type(DEFAULT_SETTINGS[key])):
                            settings[key] = loaded_settings[key]
                        else:
                            print(f"Warning: Type mismatch for setting '{key}' in {CONFIG_FILE}. Using default.")
                    else:
                         print(f"Warning: Setting '{key}' not found in {CONFIG_FILE}. Using default.")

    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading {CONFIG_FILE}: {e}. Using default settings.")
        return DEFAULT_SETTINGS.copy() # Return fresh defaults on error
    return settings

def save_settings(settings: Dict[str, Any]):
    """Saves the provided settings dictionary to the config file."""
    config_path = get_config_path()
    try:
        # Ensure all default keys are present before saving
        settings_to_save = DEFAULT_SETTINGS.copy()
        settings_to_save.update(settings)

        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(settings_to_save, f, indent=4, ensure_ascii=False)
    except IOError as e:
        print(f"Error saving settings to {config_path}: {e}")

# Example usage (optional, for testing)
if __name__ == "__main__":
    # Test loading
    current_settings = load_settings()
    print("Loaded settings:", current_settings)

    # Modify a setting (example)
    current_settings["temperature"] = 0.7
    current_settings["stop_sequences"].append("# End")

    # Test saving
    save_settings(current_settings)
    print(f"Settings saved to {get_config_path()}")

    # Verify by loading again
    reloaded_settings = load_settings()
    print("Reloaded settings:", reloaded_settings)
