import json

import boto3
from botocore.exceptions import ClientError

from shared.config import settings
from shared.logger import get_logger

logger = get_logger(__name__)
s3 = boto3.client("s3", region_name=settings.AWS_REGION)


def create_presigned_post(s3_key: str, content_type: str) -> dict:
    logger.info("Creating presigned POST for key=%s", s3_key)
    return s3.generate_presigned_post(
        Bucket=settings.RAW_BUCKET,
        Key=s3_key,
        Fields={"Content-Type": content_type},
        Conditions=[
            {"Content-Type": content_type},
            ["content-length-range", 1, settings.MAX_FILE_SIZE_BYTES],
        ],
        ExpiresIn=settings.UPLOAD_EXPIRY_SECONDS,
    )


def object_exists(bucket: str, key: str) -> bool:
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as exc:
        status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if status == 404:
            return False
        raise


def download_file_bytes(bucket: str, key: str) -> bytes:
    logger.info("Downloading s3://%s/%s", bucket, key)
    return s3.get_object(Bucket=bucket, Key=key)["Body"].read()


def put_json(bucket: str, key: str, data: dict) -> None:
    logger.info("Writing JSON to s3://%s/%s", bucket, key)
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(data, default=str).encode("utf-8"),
        ContentType="application/json",
    )


def put_text(bucket: str, key: str, text: str, content_type: str = "text/plain") -> None:
    logger.info("Writing text to s3://%s/%s content_type=%s", bucket, key, content_type)
    s3.put_object(Bucket=bucket, Key=key, Body=text.encode("utf-8"), ContentType=content_type)


def create_presigned_get(bucket: str, key: str, expires_in: int = 3600) -> str:
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires_in,
    )


def delete_prefix(bucket: str, prefix: str) -> None:
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        objects = [{"Key": item["Key"]} for item in page.get("Contents", [])]
        if objects:
            logger.info("Deleting %s objects from s3://%s/%s", len(objects), bucket, prefix)
            s3.delete_objects(Bucket=bucket, Delete={"Objects": objects})
