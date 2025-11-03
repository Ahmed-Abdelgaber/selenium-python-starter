from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from .config import Config
from .logger import get_logger


LOGGER = get_logger("core.storage")


@dataclass(frozen=True)
class UploadedObject:
    bucket: str
    key: str
    s3_uri: str
    url: Optional[str]
    local_path: str


class S3Uploader:
    def __init__(
        self,
        *,
        bucket: str,
        region: str | None,
        base_prefix: str | None,
        site_prefixes: Dict[str, str | None],
        url_expiration: int | None,
        delete_after_upload: bool = False,
    ) -> None:
        self.bucket = bucket
        self.region = region
        self.base_prefix = base_prefix
        self.site_prefixes = site_prefixes
        self.url_expiration = url_expiration
        self.delete_after_upload = delete_after_upload
        self.client = boto3.client("s3", region_name=region)

    @classmethod
    def from_config(cls, cfg: Config) -> "S3Uploader" | None:
        if not cfg.download_s3_bucket:
            return None

        site_prefixes = {
            "zio": cfg.download_s3_prefix_zio or "zio",
            "xr": cfg.download_s3_prefix_xr or "xr",
            "quest": cfg.download_s3_prefix_quest or "quest",
            "tricore": cfg.download_s3_prefix_tricore or "tricore",
        }

        return cls(
            bucket=cfg.download_s3_bucket,
            region=cfg.download_s3_region,
            base_prefix=cfg.download_s3_prefix,
            site_prefixes=site_prefixes,
            url_expiration=cfg.download_s3_url_expiration,
            delete_after_upload=cfg.download_s3_direct,
        )

    def upload_files(self, site: str, file_paths: Iterable[str]) -> List[UploadedObject]:
        uploaded: List[UploadedObject] = []
        run_segment = datetime.utcnow().strftime("%Y%m%dT%H%M%S")

        site_prefix = self.site_prefixes.get(site, site)
        prefix_parts = [self.base_prefix, site_prefix, run_segment]
        base_key_prefix = self._join_parts(prefix_parts)

        for raw_path in file_paths:
            path = Path(raw_path)
            if not path.exists():
                LOGGER.warning("Skipping missing file '%s' for S3 upload", raw_path)
                continue

            key = self._join_parts([base_key_prefix, path.name])
            try:
                LOGGER.info("Uploading '%s' to s3://%s/%s", path, self.bucket, key)
                self.client.upload_file(str(path), self.bucket, key)
            except (BotoCoreError, ClientError) as exc:
                LOGGER.error("Failed to upload '%s' to S3: %s", path, exc)
                continue

            presigned_url = None
            expires_in = self.url_expiration if self.url_expiration is not None else 604800
            try:
                presigned_url = self.client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self.bucket, "Key": key},
                    ExpiresIn=expires_in,
                )
            except (BotoCoreError, ClientError) as exc:
                LOGGER.warning(
                    "Unable to generate presigned URL for s3://%s/%s: %s",
                    self.bucket,
                    key,
                    exc,
                )

            s3_uri = f"s3://{self.bucket}/{key}"
            uploaded.append(
                UploadedObject(
                    bucket=self.bucket,
                    key=key,
                    s3_uri=s3_uri,
                    url=presigned_url,
                    local_path=str(path),
                )
            )

            if self.delete_after_upload:
                try:
                    path.unlink()
                except Exception as exc:
                    LOGGER.warning("Unable to remove local file '%s' after S3 upload: %s", path, exc)

        return uploaded

    @staticmethod
    def _join_parts(parts: Iterable[str | None]) -> str:
        cleaned = [segment.strip("/") for segment in parts if segment]
        return "/".join(cleaned)
