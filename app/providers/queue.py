from typing import Any, Protocol

import boto3

from app.core.config import settings


class QueueProvider(Protocol):
    def send(self, queue_url: str, message: dict[str, Any]) -> None: ...


class SqsQueueProvider:
    def __init__(self) -> None:
        self.client = boto3.client("sqs", region_name=settings.aws_region)

    def send(self, queue_url: str, message: dict[str, Any]) -> None:
        import json

        self.client.send_message(QueueUrl=queue_url, MessageBody=json.dumps(message))


class MockQueueProvider:
    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []

    def send(self, queue_url: str, message: dict[str, Any]) -> None:
        self.messages.append({"queue_url": queue_url, "message": message})

