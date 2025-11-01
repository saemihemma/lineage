"""Internationalization module"""
from pathlib import Path
import json
from typing import Dict, Optional

_LANG = "en"
_TRANSLATIONS: Optional[Dict[str, str]] = None
_TRANSLATIONS_DIR = Path(__file__).parent


def load_translations(lang: str = "en") -> Dict[str, str]:
    """Load translations from JSON file"""
    global _TRANSLATIONS, _LANG
    _LANG = lang
    
    json_path = _TRANSLATIONS_DIR / f"{lang}.json"
    if json_path.exists():
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                _TRANSLATIONS = json.load(f)
        except Exception as e:
            print(f"Error loading translations: {e}")
            _TRANSLATIONS = {}
    else:
        _TRANSLATIONS = {}
    
    return _TRANSLATIONS


def get(key: str, default: Optional[str] = None, **kwargs) -> str:
    """
    Get a translated string by key, with optional formatting.
    
    Args:
        key: Translation key (supports dot notation like "ui.buttons.build_womb")
        default: Default value if key not found
        **kwargs: Format arguments for string formatting
    
    Returns:
        Translated string or default (formatted if kwargs provided)
    """
    global _TRANSLATIONS
    
    if _TRANSLATIONS is None:
        load_translations()
    
    # Handle dot notation (e.g., "ui.buttons.build_womb")
    if "." in key:
        parts = key.split(".")
        value = _TRANSLATIONS
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                result = default or key
                return result.format(**kwargs) if kwargs else result
        result = value if isinstance(value, str) else (default or key)
        return result.format(**kwargs) if kwargs else result
    
    # Simple key lookup
    result = _TRANSLATIONS.get(key, default or key)
    return result.format(**kwargs) if kwargs else result


def set_language(lang: str):
    """Set the current language and reload translations"""
    load_translations(lang)


# Load translations on import
load_translations()

