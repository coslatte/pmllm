from __future__ import annotations

import logging
import os
import time
import uuid
from threading import Lock
from typing import List, Sequence

import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator
from sentence_transformers import SentenceTransformer
from transformers import AutoModelForCausalLM, AutoTokenizer

logging.basicConfig(level=os.getenv("MODEL_GATEWAY_LOG_LEVEL", "INFO"))
LOGGER = logging.getLogger("pmllm.model_gateway")

EMBEDDING_MODEL_NAME = os.getenv(
    "MODEL_GATEWAY_EMBEDDING_MODEL", "text-embedding-embeddinggemma-300m-qat"
)
LLM_MODEL_NAME = os.getenv("MODEL_GATEWAY_LLM_MODEL", "gemma-3-1b-it-qat")
REQUEST_DEVICE = os.getenv("MODEL_GATEWAY_DEVICE", "cpu")
DTYPE_NAME = os.getenv("MODEL_GATEWAY_DTYPE", "float32").lower()
DEFAULT_MAX_NEW_TOKENS = int(
    os.getenv("MODEL_GATEWAY_MAX_NEW_TOKENS", os.getenv("LLM_MAX_NEW_TOKENS", "512"))
)

ALLOWED_DTYPES = {
    "float32": torch.float32,
    "float16": torch.float16,
    "bfloat16": torch.bfloat16,
}
TORCH_DTYPE = ALLOWED_DTYPES.get(DTYPE_NAME, torch.float32)

if REQUEST_DEVICE.startswith("cuda") and not torch.cuda.is_available():
    LOGGER.warning(
        "CUDA requested for MODEL_GATEWAY_DEVICE but no GPU detected; falling back to CPU"
    )
    DEVICE = "cpu"
else:
    DEVICE = REQUEST_DEVICE

_embedding_model: SentenceTransformer | None = None
_llm_model: AutoModelForCausalLM | None = None
_llm_tokenizer: AutoTokenizer | None = None

_embedding_lock = Lock()
_llm_lock = Lock()


def _get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    with _embedding_lock:
        if _embedding_model is None:
            LOGGER.info("Loading embedding model %s", EMBEDDING_MODEL_NAME)
            _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME, device=DEVICE)
            _embedding_model.eval()
        return _embedding_model


def _get_llm_components() -> tuple[AutoTokenizer, AutoModelForCausalLM]:
    global _llm_model, _llm_tokenizer
    with _llm_lock:
        if _llm_model is None or _llm_tokenizer is None:
            LOGGER.info("Loading LLM %s", LLM_MODEL_NAME)
            tokenizer = AutoTokenizer.from_pretrained(
                LLM_MODEL_NAME, trust_remote_code=True
            )
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
                tokenizer.pad_token_id = tokenizer.eos_token_id
            model = AutoModelForCausalLM.from_pretrained(
                LLM_MODEL_NAME,
                torch_dtype=TORCH_DTYPE,
                device_map="auto" if DEVICE != "cpu" else None,
                trust_remote_code=True,
            )
            if DEVICE == "cpu":
                model.to(DEVICE)
            model.eval()
            _llm_model = model
            _llm_tokenizer = tokenizer
        return _llm_tokenizer, _llm_model


class EmbeddingRequest(BaseModel):
    model: str | None = None
    input: List[str] | str

    @field_validator("input")
    @classmethod
    def validate_input(cls, value: List[str] | str) -> List[str] | str:
        if isinstance(value, str):
            if not value.strip():
                raise ValueError("Input text cannot be blank")
            return value
        if not value:
            raise ValueError("Input list cannot be empty")
        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise ValueError("Every input item must be a non-empty string")
        return value


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(system|user|assistant)$")
    content: str

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Message content cannot be blank")
        return value


class ChatRequest(BaseModel):
    model: str | None = None
    messages: List[ChatMessage]
    max_tokens: int | None = None
    temperature: float | None = None
    stream: bool | None = False

    @field_validator("messages")
    @classmethod
    def validate_messages(cls, value: Sequence[ChatMessage]) -> Sequence[ChatMessage]:
        if not value:
            raise ValueError("At least one message is required")
        return value


app = FastAPI(
    title="PMLLM Model Gateway",
    description=(
        "Serves embeddings and chat completions for the Music RAG system using Gemma-based models."
    ),
)


@app.on_event("startup")
async def preload_models() -> None:
    """Warm up models so first request is responsive."""
    _get_embedding_model()
    _get_llm_components()


@app.get("/healthz")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/embeddings")
async def create_embeddings(request: EmbeddingRequest) -> dict:
    texts = request.input if isinstance(request.input, list) else [request.input]
    model = _get_embedding_model()
    with torch.inference_mode():
        vectors = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    data = [
        {
            "object": "embedding",
            "index": idx,
            "embedding": vector.tolist(),
        }
        for idx, vector in enumerate(vectors)
    ]
    return {
        "object": "list",
        "model": request.model or EMBEDDING_MODEL_NAME,
        "data": data,
        "usage": {
            "prompt_tokens": len(texts),
            "total_tokens": len(texts),
        },
    }


def _build_prompt(messages: Sequence[ChatMessage], tokenizer: AutoTokenizer) -> str:
    payload = [
        {"role": message.role, "content": message.content}
        for message in messages
    ]
    if hasattr(tokenizer, "apply_chat_template"):
        try:
            return tokenizer.apply_chat_template(
                payload,
                tokenize=False,
                add_generation_prompt=True,
            )
        except Exception as exc:  # pragma: no cover - best effort
            LOGGER.warning("Fell back to manual prompt building: %s", exc)

    parts: List[str] = []
    for message in messages:
        prefix = message.role.capitalize()
        parts.append(f"{prefix}: {message.content.strip()}")
    parts.append("Assistant:")
    return "\n".join(parts)


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest) -> dict:
    if request.stream:
        raise HTTPException(status_code=400, detail="Streaming responses are not supported")

    tokenizer, model = _get_llm_components()
    prompt = _build_prompt(request.messages, tokenizer)

    max_tokens = request.max_tokens or DEFAULT_MAX_NEW_TOKENS
    max_tokens = max(1, min(max_tokens, DEFAULT_MAX_NEW_TOKENS))
    temperature = request.temperature or 0.7
    temperature = max(0.0, min(temperature, 2.0))

    with torch.inference_mode():
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        output = model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=temperature,
            do_sample=temperature > 0,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )
    generated = output[0, inputs["input_ids"].shape[-1] :]
    completion = tokenizer.decode(generated, skip_special_tokens=True).strip()

    created = int(time.time())
    identifier = f"chatcmpl-{uuid.uuid4()}"
    return {
        "id": identifier,
        "object": "chat.completion",
        "created": created,
        "model": request.model or LLM_MODEL_NAME,
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": completion},
            }
        ],
        "usage": {
            "prompt_tokens": int(inputs["input_ids"].shape[-1]),
            "completion_tokens": int(generated.shape[-1]),
            "total_tokens": int(inputs["input_ids"].shape[-1] + generated.shape[-1]),
        },
    }