from __future__ import annotations

import os
import threading
import time
import uuid
from typing import List

import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer
from transformers import AutoModelForCausalLM, AutoTokenizer, PreTrainedModel

DEFAULT_EMBEDDING_MODEL = os.getenv(
    "MODEL_GATEWAY_EMBEDDING_MODEL",
    os.getenv("EMBEDDING_MODEL", "text-embedding-embeddinggemma-300m-qat"),
)
DEFAULT_CHAT_MODEL = os.getenv(
    "MODEL_GATEWAY_LLM_MODEL",
    os.getenv("LLM_MODEL", "gemma-3-1b-it-qat"),
)
DEVICE = torch.device(os.getenv("MODEL_GATEWAY_DEVICE", os.getenv("LLM_DEVICE", "cpu")))
DTYPE_NAME = os.getenv("MODEL_GATEWAY_DTYPE", "float32")
MAX_INPUT_TOKENS = int(os.getenv("MODEL_GATEWAY_MAX_INPUT_TOKENS", "4096"))

DTYPE_MAP = {
    "float32": torch.float32,
    "float16": torch.float16,
    "bf16": torch.bfloat16,
    "bfloat16": torch.bfloat16,
}
TORCH_DTYPE = DTYPE_MAP.get(DTYPE_NAME.lower(), torch.float32)

app = FastAPI(title="pmllm-model-gateway", version="0.1.0")

_embedding_model: SentenceTransformer | None = None
_embedding_lock = threading.Lock()
_llm_model: PreTrainedModel | None = None
_tokenizer: AutoTokenizer | None = None
_llm_lock = threading.Lock()


class EmbeddingRequest(BaseModel):
    model: str = Field(default=DEFAULT_EMBEDDING_MODEL)
    input: List[str] | str


class EmbeddingVector(BaseModel):
    embedding: List[float]
    index: int


class EmbeddingResponse(BaseModel):
    model: str
    data: List[EmbeddingVector]


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = Field(default=DEFAULT_CHAT_MODEL)
    messages: List[ChatMessage]
    max_tokens: int = Field(default=512, gt=0, le=2048)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)


class ChatChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str = "stop"


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatChoice]


def _ensure_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        with _embedding_lock:
            if _embedding_model is None:
                _embedding_model = SentenceTransformer(DEFAULT_EMBEDDING_MODEL, device=str(DEVICE))
    return _embedding_model


def _ensure_llm_model() -> tuple[PreTrainedModel, AutoTokenizer]:
    global _llm_model, _tokenizer
    if _llm_model is None or _tokenizer is None:
        with _llm_lock:
            if _llm_model is None or _tokenizer is None:
                _tokenizer = AutoTokenizer.from_pretrained(
                    DEFAULT_CHAT_MODEL,
                    trust_remote_code=True,
                )
                _llm_model = AutoModelForCausalLM.from_pretrained(
                    DEFAULT_CHAT_MODEL,
                    device_map="auto" if str(DEVICE) != "cpu" else None,
                    torch_dtype=TORCH_DTYPE,
                    trust_remote_code=True,
                )
    # Narrow types for static checkers: ensure neither is None before returning
    assert _llm_model is not None and _tokenizer is not None
    return _llm_model, _tokenizer


def _prepare_inputs(payload: EmbeddingRequest) -> List[str]:
    if isinstance(payload.input, str):
        return [payload.input]
    elif isinstance(payload.input, list):
        return payload.input
    else:
        raise HTTPException(status_code=400, detail="Invalid input payload for embeddings")


def _build_prompt(messages: List[ChatMessage]) -> List[dict]:
    if not messages:
        raise HTTPException(status_code=400, detail="messages array cannot be empty")

    # Convert to dict format for tokenizer
    msgs = [{"role": msg.role, "content": msg.content} for msg in messages]
    return msgs


@app.get("/healthz")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/embeddings", response_model=EmbeddingResponse)
async def create_embeddings(payload: EmbeddingRequest) -> EmbeddingResponse:
    texts = _prepare_inputs(payload)
    model = _ensure_embedding_model()
    vectors = model.encode(texts, normalize_embeddings=True)
    data = [EmbeddingVector(embedding=vec.tolist(), index=idx) for idx, vec in enumerate(vectors)]
    return EmbeddingResponse(model=payload.model, data=data)


@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(payload: ChatCompletionRequest) -> ChatCompletionResponse:
    llm, tokenizer = _ensure_llm_model()
    msgs = _build_prompt(payload.messages)
    prompt = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=MAX_INPUT_TOKENS)
    inputs = {k: v.to(DEVICE) for k, v in inputs.items()}

    do_sample = payload.temperature > 0.0
    pad_token_id = tokenizer.eos_token_id
    if pad_token_id is None:
        pad_token_id = tokenizer.pad_token_id
    generated = llm.generate(
        **inputs,
        max_new_tokens=payload.max_tokens,
        temperature=payload.temperature,
        do_sample=do_sample,
        pad_token_id=pad_token_id,
    )
    output_ids = generated[0][inputs["input_ids"].shape[1] :]
    if output_ids.numel() == 0:
        text = ""
    else:
        text = tokenizer.decode(output_ids, skip_special_tokens=True).strip()

    response = ChatCompletionResponse(
        id=str(uuid.uuid4()),
        created=int(time.time()),
        model=payload.model,
        choices=[
            ChatChoice(
                index=0,
                message=ChatMessage(role="assistant", content=text or ""),
            )
        ],
    )
    return response
```}ляд? JSON? need escape? content ok. But there is slicing; ensure no spaces. Some lines >? ok. Need ensure `Sequence` imported from typing but we use `Sequence`. At top we imported from typing `List, Sequence`. But we already used `Sequence`. yes. But also we used Sequence from typing for `payload.input`? we convert. But `Sequence` from typing may treat str as sequence; we handle string earlier. done. Need to import `Sequence`? yes done. But we also used `torch` etc. Should we guard `tokenizer` to CPU? we used `device_map` autop? fine. Should we ensure `inputs` to same device? done `inputs = {k: v.to(llm.device) ... }`. But `llm` object not easily attribute `.device`. For `AutoModelForCausalLM`, there may be `device` property? not standard. Instead we can inspect first parameter: `llm.device` not attribute? For `torch.nn.Module`, there isn't `.device`. Need to determine better approach: we can rely on `next(llm.parameters()).device`. We'll do `model_device = next(llm.parameters()).device`. We'll use there. So adjust code accordingly. Need to modify snippet accordingly. Use doping variable. We'll update file by editing (since we already created file). Instead of editing strongly, easier to re-create file? Could use apply_patch to adjust relevant lines. We'll open snippet for editing? need to read short portion to ensure accuracy. We'll use apply_patch to adjust necessary lines. Specifically in `chat_completions` function, we need to set `model_device = next(llm.parameters()).device`. We'll also adjust `_ensure_llm_model` to set `device_map`? For CPU, `device_map` should not be `None`? we set `None` when CPU? we set `device_map=