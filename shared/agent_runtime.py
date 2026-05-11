from shared.chart_tool import create_chart_artifact
from shared.config import settings
from shared.model_gateway import generate_answer
from shared.observability import end_span, record_error, save_trace_to_s3, start_span, start_trace, summarize_trace
from shared.orchestrator import plan_runtime
from shared.prompt_builder import build_system_prompt
from shared.rag_engine import retrieve_context
from shared.repositories import chat_repository, memory_repository, run_repository
from shared.repositories.base import now_iso
from shared.web_tool import build_web_context, search_web


def _message_prompt(memory: dict, rag: dict, web: dict, query: str) -> list[dict]:
    memory_summary = memory.get("memory_summary") or ""
    recent_messages = memory.get("recent_messages") or []
    history = "\n".join(f"{item.get('role', '').lower()}: {item.get('content', '')}" for item in recent_messages[-10:])
    context_parts = []
    if memory_summary:
        context_parts.append(f"Conversation memory:\n{memory_summary}")
    if history:
        context_parts.append(f"Recent messages:\n{history}")
    if rag.get("context"):
        context_parts.append(f"Retrieved document context:\n{rag['context']}")
    if web.get("context"):
        context_parts.append(f"Web/API tool context:\n{web['context']}")
    user_prompt = (
        "\n\n".join(context_parts)
        + f"\n\nUser question:\n{query}\n\nAnswer clearly. Use document citations like [1] when document context is used."
    )
    return [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user", "content": user_prompt},
    ]


def _load_memory(chat_id: str, user_id: str, use_memory: bool) -> dict:
    if not use_memory:
        return {"memory_summary": "", "recent_messages": []}
    chat = chat_repository.get_chat_for_user(chat_id, user_id) or {}
    messages = memory_repository.list_recent_messages(chat_id, limit=10)
    return {
        "memory_summary": chat.get("memory_summary") or "",
        "recent_messages": [
            {"role": item.get("role", "USER"), "content": item.get("content", "")}
            for item in messages
            if item.get("user_id") == user_id
        ],
    }


def process_runtime_job(job: dict) -> dict:
    user_id = job["user_id"]
    chat_id = job["chat_id"]
    message_id = job["message_id"]
    run_id = job["run_id"]
    query = job["input"]
    document_ids = job.get("document_ids") or []
    runtime_options = job.get("runtime_options") or {}
    trace = start_trace(run_id, user_id, chat_id, message_id)

    try:
        run_repository.update_run(run_id, status="RUNNING")
        chat_repository.update_message_status(chat_id, message_id, "RUNNING")

        route_span = start_span(trace, "orchestrator_route")
        plan = plan_runtime(
            {
                "user_id": user_id,
                "chat_id": chat_id,
                "message_id": message_id,
                "run_id": run_id,
                "query": query,
                "document_ids": document_ids,
                "runtime_options": runtime_options,
            }
        )
        end_span(trace, route_span, attributes={"route": plan.get("route")})

        memory_span = start_span(trace, "memory_load")
        memory = _load_memory(chat_id, user_id, bool(runtime_options.get("use_memory", True)))
        end_span(trace, memory_span, attributes={"recent_messages": len(memory.get("recent_messages", []))})

        rag = {"chunks": [], "citations": [], "context": "", "strategy": None}
        if plan.get("needs_rag"):
            rag_span = start_span(trace, "rag_retrieval", {"strategy": "rerank_parent_context"})
            rag = retrieve_context(
                user_id=user_id,
                query=query,
                document_ids=document_ids,
                top_k=int(runtime_options.get("top_k") or settings.DEFAULT_TOP_K),
                similarity_threshold=runtime_options.get("similarity_threshold"),
                metadata_filters=runtime_options.get("metadata_filters"),
            )
            trace["retrieved_chunks"] = rag["chunks"]
            end_span(trace, rag_span, attributes={"retrieved_chunks": len(rag["chunks"])})

        web = {"result": None, "context": ""}
        if plan.get("needs_web"):
            web_span = start_span(trace, "tool_web_search")
            web_result = search_web(query)
            web = {"result": web_result, "context": build_web_context(web_result)}
            trace["tool_calls"].append(web_result)
            end_span(trace, web_span, attributes={"result_count": len(web_result.get("results", []))})

        llm_span = start_span(trace, "openai_chat")
        model_result = generate_answer(_message_prompt(memory, rag, web, query), model=runtime_options.get("llm_model"))
        answer = model_result["content"]
        end_span(
            trace,
            llm_span,
            attributes={
                "model": model_result["model"],
                "input_tokens": model_result["input_tokens"],
                "output_tokens": model_result["output_tokens"],
            },
        )

        artifacts = []
        if plan.get("needs_chart"):
            chart_span = start_span(trace, "tool_chart")
            artifact = create_chart_artifact(
                user_id,
                run_id,
                {
                    "title": "CloudRAG Chart",
                    "data": [{"label": "Retrieved chunks", "value": len(rag.get("chunks", [])) or 1}],
                },
            )
            artifacts.append(artifact)
            trace["artifacts"].append(artifact)
            end_span(trace, chart_span, attributes={"artifact_id": artifact["artifact_id"]})

        assistant_message = {
            "chat_id": chat_id,
            "message_id": f"{message_id}_assistant",
            "user_id": user_id,
            "role": "ASSISTANT",
            "content": answer,
            "status": "COMPLETED",
            "run_id": run_id,
            "citations": rag["citations"],
            "artifacts": artifacts,
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        chat_repository.put_message(assistant_message)
        chat_repository.update_message_status(chat_id, message_id, "COMPLETED")
        chat_repository.update_chat_after_message(chat_id, answer)

        trace["status"] = "COMPLETED"
        trace["final_answer_preview"] = answer[:500]
        trace_s3_key = save_trace_to_s3(trace, user_id, run_id)
        trace_summary = summarize_trace(trace)
        run_repository.update_run(
            run_id,
            status="COMPLETED",
            route=plan.get("route"),
            answer_preview=answer[:500],
            latency_ms=trace_summary["latency_ms"],
            input_tokens=model_result["input_tokens"],
            output_tokens=model_result["output_tokens"],
            estimated_cost=model_result["estimated_cost"],
            trace_id=trace["trace_id"],
            trace_s3_key=trace_s3_key,
        )
        return {"status": "COMPLETED", "answer": answer, "citations": rag["citations"], "artifacts": artifacts}
    except Exception as exc:
        record_error(trace, None, exc)
        trace["status"] = "FAILED"
        trace_s3_key = save_trace_to_s3(trace, user_id, run_id)
        chat_repository.update_message_status(chat_id, message_id, "FAILED", error_message=str(exc))
        run_repository.update_run(run_id, status="FAILED", error_message=str(exc), trace_s3_key=trace_s3_key)
        raise
