from typing import Literal
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.cache import answer_cache
from app.config import get_settings
from app.orchestrator import answer_query
from prompts.compose import list_prompt_templates


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1)
    model_choice: Literal["Auto", "Llama", "Gemini"] = "Llama"
    temperature: float = Field(default=0.2, ge=0.0, le=1.0)
    include_trace: bool = False
    user_id: str = "api_user"
    user_email: str | None = None
    user_roles: list[str] = Field(default_factory=list)
    user_groups: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    answer: str
    model_choice: str
    used_context_count: int = 0
    trace: dict[str, Any] | None = None


app = FastAPI(title="SNTI AI Assistant API", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/config")
def config():
    return get_settings().public_dict()


@app.get("/prompts")
def prompts():
    return {"templates": list_prompt_templates()}


@app.get("/cache/top")
def top_cached_queries(limit: int = 10):
    return {"queries": answer_cache.top_queries(limit)}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    result = answer_query(
        request.query,
        request.model_choice,
        include_trace=request.include_trace,
        temperature=request.temperature,
        user_id=request.user_id,
        user_context={
            "user_id": request.user_id,
            "email": request.user_email or "",
            "roles": request.user_roles,
            "groups": request.user_groups,
        },
    )

    if isinstance(result, dict):
        return ChatResponse(
            answer=result["answer"],
            model_choice=request.model_choice,
            used_context_count=result["used_context_count"],
            trace=result["trace"],
        )

    return ChatResponse(answer=result, model_choice=request.model_choice)
