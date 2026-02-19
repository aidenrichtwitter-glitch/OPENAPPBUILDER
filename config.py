import json
import os
import sys
import platform

LLM_MODEL = "qwen2.5:32b-instruct-q5_K_M"
EXPAND_MODEL = "qwen2.5:32b-instruct-q5_K_M"
FIX_MODEL = "qwen2.5:32b-instruct-q5_K_M"
VISION_MODEL = "llava"
GROK_MODEL = "grok-4"

LLM_PROVIDERS = {
    "ollama": {
        "name": "Ollama",
        "local": True,
        "model": LLM_MODEL,
        "color": "#22d3ee",
    },
    "xai": {
        "name": "Grok",
        "base_url": "https://api.x.ai/v1",
        "model": "grok-4",
        "color": "#a855f7",
    },
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o",
        "color": "#4ade80",
    },
    "anthropic": {
        "name": "Claude",
        "base_url": "https://api.anthropic.com/v1/messages",
        "model": "claude-sonnet-4-20250514",
        "color": "#f97316",
    },
    "google": {
        "name": "Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "model": "gemini-2.5-flash",
        "color": "#3b82f6",
    },
}

BROWSER_CMD_TEMPLATE = 'start chrome --user-data-dir="{profile_path}" https://grok.com/'
WINDSCRIBE_DOWNLOAD_URL = "https://assets.windscribe.com/desktop/windows/latest/Windscribe.exe"
WINDSCRIBE_INSTALLER = "Windscribe.exe"
WINDSCRIBE_CLI = "windscribe"

def get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

APP_DIR = get_app_dir()

CONFIG_FILE = os.path.join(APP_DIR, "grok_automation_config.json")
ROTATION_FILE = os.path.join(APP_DIR, "grok_profile_rotation.json")

gemini_folder = os.path.join(APP_DIR, "projects")
os.makedirs(gemini_folder, exist_ok=True)

DEFAULT_XAI_API_KEY = "xai-"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)
    print(f"Config saved to {CONFIG_FILE}")

def validate_config(config, exit_on_fail=True):
    required_keys = ['vpn_cmd', 'browser_cmd_template', 'profile_paths', 'input_field', 'down_button', 'copy_button', 'click_offset_radius']
    missing = [key for key in required_keys if key not in config]
    if missing:
        print(f"Config incomplete (missing: {', '.join(missing)}).")
        if exit_on_fail:
            sys.exit(1)
        return False
    return True

def get_xai_api_key():
    env_key = os.environ.get("XAI_API_KEY")
    if env_key:
        return env_key
    cfg = load_config()
    if cfg.get("xai_api_key"):
        return cfg["xai_api_key"]
    llm_keys = cfg.get("llm_keys", {})
    if llm_keys.get("xai"):
        return llm_keys["xai"]
    return DEFAULT_XAI_API_KEY

XAI_API_KEY = get_xai_api_key()

def get_available_providers(config):
    available = ["ollama"]
    llm_keys = config.get("llm_keys", {})
    if llm_keys.get("xai") or config.get("xai_api_key") or os.environ.get("XAI_API_KEY"):
        available.append("xai")
    elif DEFAULT_XAI_API_KEY:
        available.append("xai")
    for provider_id in ["openai", "anthropic", "google"]:
        if llm_keys.get(provider_id):
            available.append(provider_id)
    return available

def get_provider_key(config, provider_id):
    llm_keys = config.get("llm_keys", {})
    if provider_id == "xai":
        return llm_keys.get("xai") or config.get("xai_api_key") or os.environ.get("XAI_API_KEY") or DEFAULT_XAI_API_KEY
    return llm_keys.get(provider_id, "")
