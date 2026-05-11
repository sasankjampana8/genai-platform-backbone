import uuid


def generate_document_id() -> str:
    return f"doc_{uuid.uuid4().hex}"


def generate_process_id() -> str:
    return f"proc_{uuid.uuid4().hex}"


def generate_chunk_id() -> str:
    return f"chunk_{uuid.uuid4().hex}"


def generate_chat_id() -> str:
    return f"chat_{uuid.uuid4().hex}"


def generate_message_id() -> str:
    return f"msg_{uuid.uuid4().hex}"


def generate_run_id() -> str:
    return f"run_{uuid.uuid4().hex}"


def generate_memory_id() -> str:
    return f"mem_{uuid.uuid4().hex}"


def generate_trace_id() -> str:
    return f"trace_{uuid.uuid4().hex}"


def generate_span_id() -> str:
    return f"span_{uuid.uuid4().hex}"


def generate_artifact_id() -> str:
    return f"artifact_{uuid.uuid4().hex}"
