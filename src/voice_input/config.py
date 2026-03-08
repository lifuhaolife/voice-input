"""Configuration management module."""

import os
from pathlib import Path
from typing import Any

import yaml


class Config:
    """Configuration manager for voice input."""

    DEFAULT_CONFIG = {
        "backend": "whisper",
        "hotkey": {
            "trigger": "ctrl+alt+v",
            "mode": "hold",
        },
        "recording": {
            "sample_rate": 16000,
            "channels": 1,
            "max_duration": 60,
        },
        "whisper": {
            "model": "small",
            "language": "zh",
            "device": "auto",
        },
        "baidu": {
            "app_id": "",
            "api_key": "",
            "secret_key": "",
        },
        "xunfei": {
            "app_id": "",
            "api_key": "",
            "api_secret": "",
        },
        "tencent": {
            "secret_id": "",
            "secret_key": "",
        },
        "notification": {
            "enabled": True,
            "show_status": True,
            "show_result": True,
        },
        "input": {
            "method": "type",
            "type_delay": 0.01,
        },
    }

    def __init__(self, config_path: Path | None = None):
        """Initialize configuration.

        Args:
            config_path: Path to config file. If None, uses default locations.
        """
        self._config: dict[str, Any] = {}
        self._config_path = config_path or self._find_config_path()
        self._load_config()

    def _find_config_path(self) -> Path:
        """Find configuration file in standard locations."""
        # Priority: XDG config home > project dir > home
        locations = [
            Path(os.environ.get("XDG_CONFIG_HOME", "~/.config")).expanduser()
            / "voice-input" / "config.yaml",
            Path.home() / ".voice-input" / "config.yaml",
            Path(__file__).parent.parent.parent / "config.yaml",
        ]

        for loc in locations:
            if loc.exists():
                return loc

        # Return default location for creating new config
        return locations[0]

    def _load_config(self) -> None:
        """Load configuration from file."""
        # Start with defaults
        self._config = self.DEFAULT_CONFIG.copy()

        # Deep merge with file config
        if self._config_path.exists():
            with open(self._config_path, "r", encoding="utf-8") as f:
                file_config = yaml.safe_load(f) or {}
                self._deep_merge(self._config, file_config)

    def _deep_merge(self, base: dict, override: dict) -> None:
        """Deep merge override dict into base dict."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-separated key.

        Args:
            key: Dot-separated key path (e.g., "whisper.model")
            default: Default value if key not found

        Returns:
            Configuration value or default.
        """
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def __getitem__(self, key: str) -> Any:
        """Get configuration value."""
        return self._config[key]

    @property
    def backend(self) -> str:
        """Current speech recognition backend."""
        return self._config["backend"]

    @property
    def hotkey(self) -> dict:
        """Hotkey configuration."""
        return self._config["hotkey"]

    @property
    def recording(self) -> dict:
        """Recording configuration."""
        return self._config["recording"]

    @property
    def whisper(self) -> dict:
        """Whisper configuration."""
        return self._config["whisper"]

    @property
    def notification(self) -> dict:
        """Notification configuration."""
        return self._config["notification"]

    @property
    def input_config(self) -> dict:
        """Input configuration."""
        return self._config["input"]

    def save(self) -> None:
        """Save current configuration to file."""
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._config_path, "w", encoding="utf-8") as f:
            yaml.dump(self._config, f, default_flow_style=False, allow_unicode=True)


# Global config instance
_config: Config | None = None


def get_config(config_path: Path | None = None) -> Config:
    """Get global configuration instance."""
    global _config
    if _config is None:
        _config = Config(config_path)
    return _config