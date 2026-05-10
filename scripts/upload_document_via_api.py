import argparse
import mimetypes
import sys
from pathlib import Path

import requests


CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def detect_content_type(path: Path) -> str:
    if path.suffix.lower() in CONTENT_TYPES:
        return CONTENT_TYPES[path.suffix.lower()]
    guessed, _ = mimetypes.guess_type(path.name)
    if guessed:
        return guessed
    raise ValueError("Only .pdf and .docx are supported by the MVP upload API")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate presigned POST data and upload one local document to S3.")
    parser.add_argument("--api-base-url", required=True, help="Example: https://abc.execute-api.ap-south-1.amazonaws.com/dev")
    parser.add_argument("--user-id", default="user_123")
    parser.add_argument("--file-path", required=True)
    args = parser.parse_args()

    api_base_url = args.api_base_url.rstrip("/")
    path = Path(args.file_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(path)

    content_type = detect_content_type(path)
    payload = {
        "user_id": args.user_id,
        "files": [
            {
                "file_name": path.name,
                "content_type": content_type,
                "file_size_bytes": path.stat().st_size,
            }
        ],
    }

    upload_url_response = requests.post(
        f"{api_base_url}/documents/upload-url",
        json=payload,
        timeout=30,
    )
    upload_url_response.raise_for_status()
    document = upload_url_response.json()["documents"][0]
    upload = document["upload"]

    with path.open("rb") as file_obj:
        s3_response = requests.post(
            upload["url"],
            data=upload["fields"],
            files={"file": (path.name, file_obj, content_type)},
            timeout=120,
        )
    s3_response.raise_for_status()

    status_response = requests.get(
        f"{api_base_url}/documents/{document['document_id']}",
        timeout=30,
    )

    print("Upload complete")
    print(f"document_id: {document['document_id']}")
    print(f"file_name: {path.name}")
    print(f"s3_bucket: {document['s3_bucket']}")
    print(f"s3_key: {document['s3_key']}")
    print(f"s3_status_code: {s3_response.status_code}")
    print(f"document_status: {status_response.text}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Upload failed: {exc}", file=sys.stderr)
        raise
