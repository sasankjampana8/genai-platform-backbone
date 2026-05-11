import json

from shared.agent_runtime import process_runtime_job
from shared.logger import get_logger

logger = get_logger(__name__)


def lambda_handler(event, context):
    failures = []
    for record in event.get("Records", []):
        try:
            job = json.loads(record.get("body") or "{}")
            logger.info("processing runtime job run_id=%s chat_id=%s", job.get("run_id"), job.get("chat_id"))
            process_runtime_job(job)
        except Exception:
            logger.exception("runtime worker record failed")
            failures.append({"itemIdentifier": record.get("messageId")})
    return {"batchItemFailures": failures}
