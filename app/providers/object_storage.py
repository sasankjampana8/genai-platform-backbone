from typing import Protocol

import boto3

from app.core.config import settings


class ObjectStorageProvider(Protocol):
    def put_bytes(self, key: str, data: bytes, content_type: str) -> None: ...

    def get_bytes(self, key: str) -> bytes: ...

    def delete_prefix(self, prefix: str) -> None: ...


class S3ObjectStorageProvider:
    def __init__(self) -> None:
        self.client = boto3.client("s3", region_name=settings.aws_region)

    def put_bytes(self, key: str, data: bytes, content_type: str) -> None:
        self.client.put_object(Bucket=settings.s3_bucket, Key=key, Body=data, ContentType=content_type)

    def get_bytes(self, key: str) -> bytes:
        response = self.client.get_object(Bucket=settings.s3_bucket, Key=key)
        return response["Body"].read()

    def delete_prefix(self, prefix: str) -> None:
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=settings.s3_bucket, Prefix=prefix):
            objects = [{"Key": item["Key"]} for item in page.get("Contents", [])]
            if objects:
                self.client.delete_objects(Bucket=settings.s3_bucket, Delete={"Objects": objects})


class MockObjectStorageProvider:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put_bytes(self, key: str, data: bytes, content_type: str) -> None:
        self.objects[key] = data

    def get_bytes(self, key: str) -> bytes:
        return self.objects[key]

    def delete_prefix(self, prefix: str) -> None:
        for key in list(self.objects):
            if key.startswith(prefix):
                del self.objects[key]

