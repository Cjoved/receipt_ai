import boto3
from botocore.client import BaseClient

from .config import WasabiConfig


def create_s3_client(config: WasabiConfig) -> BaseClient:
    """Create a boto3 S3 client for Wasabi endpoint."""
    return boto3.client(
        "s3",
        endpoint_url=config.endpoint,
        aws_access_key_id=config.access_key,
        aws_secret_access_key=config.secret_key,
        region_name=config.region,
    )
