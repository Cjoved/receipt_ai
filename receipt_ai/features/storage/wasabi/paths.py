from .config import WasabiConfig


def full_key(config: WasabiConfig, key: str) -> str:
    """Normalize object key and apply optional global prefix."""
    key = key.lstrip("/")
    prefix = config.default_prefix.strip("/")
    return f"{prefix}/{key}" if prefix else key


def folder_key(config: WasabiConfig, folder_path: str) -> str:
    """Normalize folder paths to trailing slash keys."""
    folder = full_key(config, folder_path.strip("/"))
    return f"{folder}/"
