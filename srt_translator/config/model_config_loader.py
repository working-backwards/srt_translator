import json
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "model_config.json"

with open(CONFIG_FILE) as f:
    MODEL_CONFIG = json.load(f)

def get_model_config(model_name: str):
    return MODEL_CONFIG.get(model_name, {})
