"""Configuration management for MTG Arbitrage."""

import os
from typing import Dict, Any


def load_config() -> Dict[str, Any]:
    """Load configuration from config.env file."""
    config = {}
    config_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.env')
    
    if not os.path.exists(config_file):
        print(f"⚠️  Config file not found: {config_file}")
        return get_default_config()
    
    try:
        with open(config_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Convert to appropriate types
                        if value.lower() in ('true', 'false'):
                            config[key] = value.lower() == 'true'
                        elif '.' in value:
                            try:
                                config[key] = float(value)
                            except ValueError:
                                config[key] = value
                        else:
                            try:
                                config[key] = int(value)
                            except ValueError:
                                config[key] = value
        
        print(f"✅ Loaded configuration from {config_file}")
        return config
    
    except Exception as e:
        print(f"⚠️  Error loading config: {e}")
        return get_default_config()


def get_default_config() -> Dict[str, Any]:
    """Get default configuration values."""
    return {
        'TARGET_NET_MARGIN': 0.12,
        'CARDMARKET_FEE': 0.05,
        'PRICE_MIN': 50.0,
        'PRICE_MAX': 120.0,
        'TREND_DISCOUNT_THRESHOLD': 0.10,
        'RANK_TARGET': 8,
        'UNDERCUT_BUFFER': 0.10,
        'MIN_AVG7': 0.01,
        'USE_GERMAN_SELLERS_ONLY': False
    }


def get_config_value(key: str, default: Any = None) -> Any:
    """Get a single configuration value."""
    config = load_config()
    return config.get(key, default)


# Global config instance
_config = None

def get_config() -> Dict[str, Any]:
    """Get cached configuration."""
    global _config
    if _config is None:
        _config = load_config()
    return _config
