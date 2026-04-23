from __future__ import annotations

import mimetypes
from datetime import UTC, datetime
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
        guessed_type, _ = mimetypes.guess_type(filename)
        extra_args: dict[str, str] = {}
        if guessed_type:
            # Store content type so browsers can render file inline when possible.
            extra_args["ContentType"] = guessed_type
        extra_args["Metadata"] = {
            "uploaded_at": datetime.now(UTC).isoformat(),
        }
        try:
            if extra_args:
                self._client.upload_fileobj(
                    file_obj,
                    self._config.bucket,
                    object_key,
                    ExtraArgs=extra_args,
                )
            else:
                self._client.upload_fileobj(file_obj, self._config.bucket, object_key)
            return object_key
        except (ClientError, BotoCoreError) as exc:
            raise WasabiStorageError(f"Failed to upload '{filename}': {exc}") from exc

    # List direct files inside one folder (non-recursive).
    def list_folder_file_objects(self, folder_path: str) -> list[dict[str, object]]:
        """List direct files with metadata (name, size_bytes, last_modified, uploaded_at)."""
        prefix = folder_key(self._config, folder_path)
        try:
            response = self._client.list_objects_v2(
                Bucket=self._config.bucket,
                Prefix=prefix,
                Delimiter="/",
            )
        except (ClientError, BotoCoreError) as exc:
            raise WasabiStorageError(f"Failed to list folder '{folder_path}': {exc}") from exc

        objects: list[dict[str, object]] = []
        for item in response.get("Contents", []):
            key = item.get("Key", "")
            if key and not key.endswith("/"):
                objects.append(
                    {
                        "name": key.split("/")[-1],
                        "size_bytes": int(item.get("Size", 0)),
                        "last_modified": item.get("LastModified"),
                        "uploaded_at": item.get("LastModified"),
                    }
                )
        # Hydrate upload timestamp from object metadata (best effort).
        for obj in objects:
            try:
                full_path = f"{folder_path.strip('/')}/{str(obj.get('name', '')).strip('/')}"
                key = full_key(self._config, full_path)
                head = self._client.head_object(Bucket=self._config.bucket, Key=key)
                meta = head.get("Metadata", {}) or {}
                uploaded_raw = str(meta.get("uploaded_at", "")).strip()
                if uploaded_raw:
                    uploaded_at = datetime.fromisoformat(uploaded_raw.replace("Z", "+00:00"))
                    obj["uploaded_at"] = uploaded_at
            except Exception:
                # Fallback to last_modified when metadata is missing/unparseable.
                obj["uploaded_at"] = obj.get("last_modified")
        return objects

    # List direct files inside one folder (non-recursive).
    def list_folder_files(self, folder_path: str) -> list[str]:
        return [obj["name"] for obj in self.list_folder_file_objects(folder_path) if isinstance(obj.get("name"), str)]

    # Short-lived HTTPS URL for viewing or downloading an object in the browser.
    def presigned_get_url(
        self,
        object_relative: str,
        expires_in: int = 3600,
        *,
        inline: bool = True,
    ) -> str:
        """Return a time-limited GET URL for the given key (folder/file path)."""
        key = full_key(self._config, object_relative)
        params: dict[str, str] = {"Bucket": self._config.bucket, "Key": key}
        guessed_type, _ = mimetypes.guess_type(object_relative)
        if guessed_type:
            params["ResponseContentType"] = guessed_type
        if inline:
            # Hint browser to open file in viewer instead of forcing attachment download.
            params["ResponseContentDisposition"] = "inline"
        else:
            # Force browser download behavior for explicit download action.
            params["ResponseContentDisposition"] = "attachment"
        try:
            return self._client.generate_presigned_url(
                "get_object",
                Params=params,
                ExpiresIn=expires_in,
            )
        except (ClientError, BotoCoreError) as exc:
            raise WasabiStorageError(
                f"Failed to presign URL for '{object_relative}': {exc}"
            ) from exc

    # Read object content as UTF-8 text (used for txt/csv/md inline previews).
    def read_text(self, object_relative: str, max_bytes: int = 200_000) -> str:
        """Return decoded text content for a key, capped to avoid huge previews."""
        key = full_key(self._config, object_relative)
        try:
            response = self._client.get_object(Bucket=self._config.bucket, Key=key)
            body = response["Body"].read(max_bytes)
            # Replace unknown chars so preview won't crash on mixed encodings.
            return body.decode("utf-8", errors="replace")
        except (ClientError, BotoCoreError, UnicodeDecodeError) as exc:
            raise WasabiStorageError(
                f"Failed to read text preview for '{object_relative}': {exc}"
            ) from exc

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
        base_prefix = self._config.default_prefix.strip("/")
        request_prefix = f"{base_prefix}/" if base_prefix else ""
        folder_names: set[str] = set()
        token: str | None = None

        try:
            while True:
                kwargs: dict[str, str] = {
                    "Bucket": self._config.bucket,
                    "Prefix": request_prefix,
                    "Delimiter": "/",
                }
                if token:
                    kwargs["ContinuationToken"] = token

                response = self._client.list_objects_v2(**kwargs)

                for item in response.get("CommonPrefixes", []):
                    prefix = item.get("Prefix", "")
                    if not prefix:
                        continue
                    # Remove configured base prefix from returned absolute prefix.
                    if request_prefix and prefix.startswith(request_prefix):
                        prefix = prefix[len(request_prefix):]
                    prefix = prefix.strip("/")
                    if prefix:
                        folder_names.add(prefix.split("/")[0])

                if not response.get("IsTruncated"):
                    break
                token = response.get("NextContinuationToken")
        except (ClientError, BotoCoreError) as exc:
            raise WasabiStorageError(f"Failed to list folders: {exc}") from exc

        # Fallback: derive folders from object keys if no explicit folder markers are present.
        if not folder_names:
            for key in self.list_keys_under_prefix(""):
                normalized = key
                if request_prefix and normalized.startswith(request_prefix):
                    normalized = normalized[len(request_prefix):]
                normalized = normalized.lstrip("/")
                if "/" in normalized:
                    folder_names.add(normalized.split("/", 1)[0])

        return sorted(folder_names, key=str.lower)
