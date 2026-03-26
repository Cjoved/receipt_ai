from __future__ import annotations

from typing import BinaryIO

from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError

from .client import create_s3_client
from .config import WasabiConfig
from .errors import WasabiStorageError
from .paths import folder_key, full_key


class WasabiStorage:
    """S3-compatible adapter for folder/file operations in Wasabi."""

    # Create and keep one boto3 client for all storage calls.
    def __init__(self, config: WasabiConfig) -> None:
        self._config = config
        self._client: BaseClient = create_s3_client(config)

    # Create a virtual folder by uploading an empty object with trailing slash.
    def create_folder(self, folder_path: str) -> None:
        key = folder_key(self._config, folder_path)
        try:
            self._client.put_object(Bucket=self._config.bucket, Key=key, Body=b"")
        except (ClientError, BotoCoreError) as exc:
            raise WasabiStorageError(f"Failed to create folder '{folder_path}': {exc}") from exc

    # Upload binary stream to a folder and return the saved object key.
    def upload_fileobj(self, folder_path: str, filename: str, file_obj: BinaryIO) -> str:
        object_key = full_key(self._config, f"{folder_path.strip('/')}/{filename}")
        try:
            self._client.upload_fileobj(file_obj, self._config.bucket, object_key)
            return object_key
        except (ClientError, BotoCoreError) as exc:
            raise WasabiStorageError(f"Failed to upload '{filename}': {exc}") from exc

    # List direct files inside one folder (non-recursive).
    def list_folder_files(self, folder_path: str) -> list[str]:
        prefix = folder_key(self._config, folder_path)
        try:
            response = self._client.list_objects_v2(
                Bucket=self._config.bucket,
                Prefix=prefix,
                Delimiter="/",
            )
        except (ClientError, BotoCoreError) as exc:
            raise WasabiStorageError(f"Failed to list folder '{folder_path}': {exc}") from exc

        names: list[str] = []
        for item in response.get("Contents", []):
            key = item.get("Key", "")
            if key and not key.endswith("/"):
                names.append(key.split("/")[-1])
        return names

    # Delete one object key from the bucket.
    def delete_object(self, object_key: str) -> None:
        key = full_key(self._config, object_key)
        try:
            self._client.delete_object(Bucket=self._config.bucket, Key=key)
        except (ClientError, BotoCoreError) as exc:
            raise WasabiStorageError(f"Failed to delete '{object_key}': {exc}") from exc

    # Rename object via copy + delete, the standard S3-compatible pattern.
    def rename_object(self, old_key: str, new_key: str) -> None:
        old_full = full_key(self._config, old_key)
        new_full = full_key(self._config, new_key)

        try:
            self._client.copy_object(
                Bucket=self._config.bucket,
                CopySource={"Bucket": self._config.bucket, "Key": old_full},
                Key=new_full,
            )
            self._client.delete_object(Bucket=self._config.bucket, Key=old_full)
        except (ClientError, BotoCoreError) as exc:
            raise WasabiStorageError(
                f"Failed to rename '{old_key}' -> '{new_key}': {exc}"
            ) from exc

    # List all object keys under a folder prefix (recursive).
    def list_keys_under_prefix(self, prefix: str) -> list[str]:
        target_prefix = folder_key(self._config, prefix).rstrip("/") + "/"
        keys: list[str] = []
        token: str | None = None

        try:
            while True:
                kwargs: dict[str, str] = {
                    "Bucket": self._config.bucket,
                    "Prefix": target_prefix,
                }
                if token:
                    kwargs["ContinuationToken"] = token

                response = self._client.list_objects_v2(**kwargs)
                for item in response.get("Contents", []):
                    key = item.get("Key")
                    if key:
                        keys.append(key)

                if not response.get("IsTruncated"):
                    break
                token = response.get("NextContinuationToken")
        except (ClientError, BotoCoreError) as exc:
            raise WasabiStorageError(
                f"Failed to list keys under prefix '{prefix}': {exc}"
            ) from exc

        return keys

    # Delete all keys inside a folder prefix (recursive delete).
    def delete_prefix(self, prefix: str) -> int:
        keys = self.list_keys_under_prefix(prefix)
        if not keys:
            return 0

        deleted = 0
        try:
            # S3 DeleteObjects supports up to 1000 keys per request.
            for i in range(0, len(keys), 1000):
                chunk = keys[i : i + 1000]
                self._client.delete_objects(
                    Bucket=self._config.bucket,
                    Delete={"Objects": [{"Key": key} for key in chunk]},
                )
                deleted += len(chunk)
        except (ClientError, BotoCoreError) as exc:
            raise WasabiStorageError(f"Failed to delete prefix '{prefix}': {exc}") from exc

        return deleted

    # Rename a whole folder prefix by copy-all then delete source keys.
    def rename_prefix(self, old_prefix: str, new_prefix: str) -> int:
        old_folder = folder_key(self._config, old_prefix).rstrip("/") + "/"
        new_folder = folder_key(self._config, new_prefix).rstrip("/") + "/"
        keys = self.list_keys_under_prefix(old_prefix)

        if not keys:
            # Preserve destination folder marker even when source is empty.
            self.create_folder(new_prefix)
            return 0

        copied = 0
        try:
            for old_key in keys:
                suffix = old_key[len(old_folder):] if old_key.startswith(old_folder) else ""
                new_key = f"{new_folder}{suffix}" if suffix else new_folder

                self._client.copy_object(
                    Bucket=self._config.bucket,
                    CopySource={"Bucket": self._config.bucket, "Key": old_key},
                    Key=new_key,
                )
                copied += 1

            self.delete_prefix(old_prefix)
        except (ClientError, BotoCoreError) as exc:
            raise WasabiStorageError(
                f"Failed to rename prefix '{old_prefix}' -> '{new_prefix}': {exc}"
            ) from exc

        return copied

    # List all folders in the bucket.
    def list_folders(self) -> list[str]:
        try:
            response = self._client.list_objects_v2(
                Bucket=self._config.bucket,
                Prefix="",
                Delimiter="/",
            )
        except (ClientError, BotoCoreError) as exc:
            raise WasabiStorageError(f"Failed to list folders: {exc}") from exc

        folders: list[str] = []
        for item in response.get("CommonPrefixes", []):
            prefix = item.get("Prefix", "")
            if prefix.endswith("/"):
                prefix = prefix[:-1]
            if prefix:
                # Keep only last segment in case a global prefix is used.
                folders.append(prefix.split("/")[-1])
        return folders
