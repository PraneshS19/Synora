# SYNORA integration contracts

The frontend keeps selected files in browser memory only. No upload, extraction,
indexing, translation, transcription, generation, or export occurs without a
server-side implementation of these contracts.

## Shared upload

`POST /api/uploads`

- Request: `multipart/form-data`, with one or more `files` and a `module` value.
- Response: `{ files: [{ id, name, mimeType, size, status }] }`.
- The server must validate file type and size, scan content, enforce access control,
  and return no provider credentials to the browser.

## Institutional RAG

`POST /api/rag/collections`

- Request: `{ name, fileIds }`.
- Response: `{ id, status: "uploading" | "extracting" | "indexing" | "ready" | "failed" }`.

`POST /api/rag/collections/:id/questions`

- Request: `{ question }`.
- Response: `{ answer, citations: [{ fileId, name, page?, section?, excerpt }] }`.
- If retrieval finds insufficient evidence, return an explicit no-evidence status;
  do not generate unsupported answers.

## IndicTranslate

`POST /api/translate/jobs`

- Request: `{ fileIds, sourceLanguage, targetLanguage }`.
- Response: `{ id, status }`.

`GET /api/translate/jobs/:id`

- Response: source segments, translated editable segments, review flags, and any
  extraction limitations. Export endpoints must only advertise formats they create.

## Meeting Minutes

`POST /api/meetings/jobs`

- Request: `{ audioFileIds?, transcriptFileIds? }`.
- Response: `{ id, status }`.

`GET /api/meetings/jobs/:id`

- Response: an editable review draft with only source-supported summary,
  discussions, decisions, action items, timestamps, and uncertainty flags.
