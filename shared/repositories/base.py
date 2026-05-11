from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import boto3

from shared.config import settings

dynamodb = boto3.resource("dynamodb", region_name=settings.AWS_REGION)


def table(name: str):
    return dynamodb.Table(name)


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def clean_for_dynamodb(value: Any):
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {k: clean_for_dynamodb(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clean_for_dynamodb(v) for v in value]
    return value


def int_value(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    return int(value)
