"""Storage: S3 upload/delete via boto3."""

from app.core.config import get_settings


def get_s3_client():
    import boto3
    s = get_settings()
    if not s.storage_bucket or not s.storage_access_key_id:
        return None, None
    client = boto3.client(
        "s3",
        region_name=s.storage_region,
        aws_access_key_id=s.storage_access_key_id,
        aws_secret_access_key=s.storage_secret_access_key,
    )
    return client, s.storage_bucket


def upload_file(key: str, body: bytes, content_type: str | None = None) -> str | None:
    """Upload bytes to S3. Returns key on success, None if S3 not configured."""
    client, bucket = get_s3_client()
    if not client or not bucket:
        return None
    extra = {}
    if content_type:
        extra["ContentType"] = content_type
    client.put_object(Bucket=bucket, Key=key, Body=body, **extra)
    return key


def delete_file(key: str) -> bool:
    """Delete object from S3. Returns True if deleted or S3 not configured."""
    client, bucket = get_s3_client()
    if not client or not bucket:
        return True
    client.delete_object(Bucket=bucket, Key=key)
    return True


def get_presigned_url(key: str, expires_in: int = 3600) -> str | None:
    """Generate presigned GET URL for download."""
    client, bucket = get_s3_client()
    if not client or not bucket:
        return None
    return client.generate_presigned_url(
        "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=expires_in
    )
