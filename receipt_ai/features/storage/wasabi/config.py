from __future__ import annotations

from dataclasses import dataclass
import os

from dotenv import load_dotenv

from .errors import WasabiStorageError


@dataclass(frozen=True)
class WasabiConfig:
    """All configuration values needed by the Wasabi client."""

    access_key: str
    secret_key: str
    bucket: str
    region: str
    endpoint: str
    default_prefix: str = ""

    # Read connection settings from .env and validate required fields.
    @classmethod
    def from_env(cls) -> "WasabiConfig":
        load_dotenv()

        access_key = os.getenv("WASABI_ACCESS_KEY", "").strip()
        secret_key = os.getenv("WASABI_SECRET_KEY", "").strip()
        bucket = os.getenv("WASABI_BUCKET", "").strip()
        region = os.getenv("WASABI_REGION", "").strip()
        endpoint = os.getenv("WASABI_ENDPOINT", "").strip()
        default_prefix = os.getenv("WASABI_PREFIX", "").strip()

        required = {
            "WASABI_ACCESS_KEY": access_key,
            "WASABI_SECRET_KEY": secret_key,
            "WASABI_BUCKET": bucket,
            "WASABI_REGION": region,
            "WASABI_ENDPOINT": endpoint,
        }
        missing = [key for key, value in required.items() if not value]
        if missing:
            raise WasabiStorageError(f"Missing required env vars: {', '.join(missing)}")

        return cls(
            access_key=access_key,
            secret_key=secret_key,
            bucket=bucket,
            region=region,
            endpoint=endpoint,
            default_prefix=default_prefix,
        )
