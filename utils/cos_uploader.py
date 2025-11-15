# utils/cos_uploader.py
"""
Tencent Cloud COS (Cloud Object Storage) uploader utility.

This module provides a simple interface for uploading files to Tencent Cloud COS.
"""
import os
import logging
from typing import Optional
from pathlib import Path
from datetime import datetime
from qcloud_cos import CosConfig, CosS3Client

logger = logging.getLogger(__name__)

# ==================== Configuration ====================
COS_CONFIG = {
    "scheme": "https",  # Use HTTPS for secure connections
}


# ==================== COS Client ====================
class COSUploader:
    """Client for uploading files to Tencent Cloud COS"""

    def __init__(
        self,
        secret_id: Optional[str] = None,
        secret_key: Optional[str] = None,
        region: Optional[str] = None,
        bucket: Optional[str] = None,
    ):
        """
        Initialize COS uploader.

        Args:
            secret_id: Tencent Cloud Secret ID (defaults to COS_SECRET_ID env var)
            secret_key: Tencent Cloud Secret Key (defaults to COS_SECRET_KEY env var)
            region: COS region, e.g., 'ap-guangzhou' (defaults to COS_REGION env var)
            bucket: COS bucket name (defaults to COS_BUCKET env var)

        Raises:
            ValueError: If required credentials are not provided
        """
        self.secret_id = secret_id or os.environ.get("COS_SECRET_ID")
        self.secret_key = secret_key or os.environ.get("COS_SECRET_KEY")
        self.region = region or os.environ.get("COS_REGION")
        self.bucket = bucket or os.environ.get("COS_BUCKET")

        if not all([self.secret_id, self.secret_key, self.region, self.bucket]):
            raise ValueError(
                "COS credentials not configured. Required environment variables: "
                "COS_SECRET_ID, COS_SECRET_KEY, COS_REGION, COS_BUCKET"
            )

        # Initialize COS config and client
        self.config = CosConfig(
            Region=self.region,
            SecretId=self.secret_id,
            SecretKey=self.secret_key,
            Scheme=COS_CONFIG["scheme"],
        )
        self.client = CosS3Client(self.config)
        logger.info(
            f"✓ COS uploader initialized - Bucket: {self.bucket}, Region: {self.region}"
        )

    def upload_file(
        self,
        local_file_path: str,
        cos_key: Optional[str] = None,
        prefix: str = "uploads",
    ) -> str:
        """
        Upload a file to COS and return the public URL.

        Args:
            local_file_path: Path to the local file to upload
            cos_key: Optional custom key (path) for the file in COS.
                     If not provided, will generate one based on filename and timestamp.
            prefix: Directory prefix in COS (default: "uploads")

        Returns:
            The public URL of the uploaded file

        Raises:
            FileNotFoundError: If the local file doesn't exist
            Exception: If upload fails
        """
        if not os.path.exists(local_file_path):
            raise FileNotFoundError(f"File not found: {local_file_path}")

        # Generate COS key if not provided
        if cos_key is None:
            filename = Path(local_file_path).name
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            cos_key = f"{prefix}/{timestamp}_{filename}"

        logger.info(f"Uploading file to COS: {local_file_path} -> {cos_key}")

        try:
            # Upload file
            with open(local_file_path, "rb") as fp:
                self.client.put_object(
                    Bucket=self.bucket,
                    Body=fp,
                    Key=cos_key,
                    EnableMD5=False,
                )

            # Generate public URL
            url = f"https://{self.bucket}.cos.{self.region}.myqcloud.com/{cos_key}"
            logger.info(f"✓ File uploaded successfully: {url}")
            return url

        except Exception as e:
            logger.error(f"Failed to upload file to COS: {e}")
            raise

    def upload_bytes(
        self,
        data: bytes,
        filename: str,
        cos_key: Optional[str] = None,
        prefix: str = "uploads",
    ) -> str:
        """
        Upload bytes data to COS and return the public URL.

        Args:
            data: Bytes data to upload
            filename: Filename to use (for generating COS key)
            cos_key: Optional custom key (path) for the file in COS.
                     If not provided, will generate one based on filename and timestamp.
            prefix: Directory prefix in COS (default: "uploads")

        Returns:
            The public URL of the uploaded file

        Raises:
            Exception: If upload fails
        """
        # Generate COS key if not provided
        if cos_key is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            cos_key = f"{prefix}/{timestamp}_{filename}"

        logger.info(f"Uploading bytes data to COS: {cos_key} ({len(data)} bytes)")

        try:
            # Upload data
            self.client.put_object(
                Bucket=self.bucket,
                Body=data,
                Key=cos_key,
                EnableMD5=False,
            )

            # Generate public URL
            url = f"https://{self.bucket}.cos.{self.region}.myqcloud.com/{cos_key}"
            logger.info(f"✓ Data uploaded successfully: {url}")
            return url

        except Exception as e:
            logger.error(f"Failed to upload data to COS: {e}")
            raise

    def delete_file(self, cos_key: str) -> bool:
        """
        Delete a file from COS.

        Args:
            cos_key: The key (path) of the file in COS

        Returns:
            True if deletion was successful, False otherwise
        """
        logger.info(f"Deleting file from COS: {cos_key}")

        try:
            self.client.delete_object(Bucket=self.bucket, Key=cos_key)
            logger.info(f"✓ File deleted successfully: {cos_key}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete file from COS: {e}")
            return False

    def file_exists(self, cos_key: str) -> bool:
        """
        Check if a file exists in COS.

        Args:
            cos_key: The key (path) of the file in COS

        Returns:
            True if the file exists, False otherwise
        """
        try:
            self.client.head_object(Bucket=self.bucket, Key=cos_key)
            return True
        except Exception:
            return False

    def get_file_url(self, cos_key: str) -> str:
        """
        Get the public URL for a file in COS.

        Args:
            cos_key: The key (path) of the file in COS

        Returns:
            The public URL of the file
        """
        return f"https://{self.bucket}.cos.{self.region}.myqcloud.com/{cos_key}"


# Lazy initialization of COS uploader
_cos_uploader = None


def get_cos_uploader() -> COSUploader:
    """Get or create the COS uploader singleton"""
    global _cos_uploader
    if _cos_uploader is None:
        _cos_uploader = COSUploader()
    return _cos_uploader


def is_cos_available() -> bool:
    """
    Check if COS is available (credentials are configured).

    Returns:
        True if COS credentials are available, False otherwise
    """
    required_vars = ["COS_SECRET_ID", "COS_SECRET_KEY", "COS_REGION", "COS_BUCKET"]
    return all(os.environ.get(var) for var in required_vars)

