# Prompts Guide

This project keeps prompt logic in code:

- Chat RAG prompt: `receipt_ai/features/chat/rag_service.py`
- Kimi image extraction prompt: `receipt_ai/features/extraction/adapters/image_kimi_extractor.py`

## Chat Prompt (LangChain template)

`rag_service.py` uses:

- `_RAG_SYSTEM` for behavior rules
- `_RAG_PROMPT = ChatPromptTemplate.from_messages(...)` for structured prompt assembly

Current flow:

1. Retrieve context chunks.
2. Format prompt with `{context}` and `{question}`.
3. Convert LangChain messages into OpenAI-compatible messages.
4. Send to Kimi chat completion.

## Extraction Prompt (Kimi Vision)

`image_kimi_extractor.py` sets strict instruction:

- Extract from receipt images only.
- Return `NOT_RECEIPT` when image is not a receipt.

Validation is applied after model output:

- Empty output => fail
- `NOT_RECEIPT` => fail
- Fails receipt signal checks => fail (when enabled)

## Best Practice

- Keep prompts versioned by updating this file when prompt text changes.
- Keep prompt intent and constraints short and explicit.
