# SYNORA API contracts

This document summarizes the FastAPI routes implemented for modules 02, 04, and 05. The source of truth is `backend/app/main.py` and `backend/app/models/schemas.py`; keep this document and the TypeScript API client in `src/api.ts` aligned when contracts change.

Local API base URL: `http://127.0.0.1:8000`. The Vite development server proxies `/api/*` to this address.

## Health

`GET /api/health`

Returns service status, supported backend modules, and configured provider names. This is a liveness/configuration response, not a readiness guarantee that optional models or external services are reachable.

## Upload files

`POST /api/uploads` (`multipart/form-data`)

Fields:

- `files`: one or more selected files.
- `module`: module identifier such as `rag`, `translate`, or `meeting`.

The backend applies module-specific extension, size, and file-content checks. Successful responses contain file metadata and generated internal IDs. Files are stored under `backend/data/` by default and are not served from the frontend. Do not upload sensitive production data to this local prototype.

## Module 02 — Institutional RAG

### Create/index a collection

`POST /api/rag/collections`

```json
{
  "name": "Library Policy",
  "fileIds": ["<uploaded-file-id>"]
}
```

The service extracts passages, builds an index with the configured embedding provider, and returns collection status and embedding metadata.

### Read a collection

`GET /api/rag/collections/{collection_id}`

### Ask a question

`POST /api/rag/collections/{collection_id}/questions`

```json
{ "question": "How many books may a student borrow?" }
```

The response includes `answer`, `citations`, `evidenceFound`, and `providerUsed`. Citations include source file metadata and an excerpt, with page/section information when available. When the collection has insufficient evidence, the expected response has `evidenceFound: false` and an empty citations list. A collection indexed with an incompatible embedding provider/dimension must be re-indexed rather than queried against incompatible vectors.

## Module 04 — IndicTranslate

### Create a translation job

`POST /api/translate/jobs`

```json
{
  "sourceText": "The meeting will begin tomorrow.",
  "sourceLanguage": "English",
  "targetLanguage": "Tamil"
}
```

The request may instead include uploaded `fileIds`. The response contains a job ID, status, source/target language, segments, provider name, limitations, and any error.

- With `TRANSLATION_PROVIDER=local` or `none`, translations are intentionally blank and marked as not machine-translated; users may enter drafts manually.
- With `TRANSLATION_PROVIDER=indictrans2`, local model weights and dependencies must already be installed. The tested checkpoint supports English-to-Indic translation for the seven target languages in the UI. Other source directions are not supported by that tested configuration.
- Generated machine translations require human review; they are not automatically approved.

### Read a job

`GET /api/translate/jobs/{job_id}`

### Save a segment review/edit

`PUT /api/translate/jobs/{job_id}/segments/{segment_id}`

```json
{
  "translated": "<reviewed translation>",
  "reviewFlag": "edited"
}
```

Allowed review states are defined in the schemas and frontend client. The service persists segment changes in the local database.

## Module 05 — Meeting Minutes

### Create a minutes job

`POST /api/meetings/jobs`

```json
{
  "transcriptFileIds": ["<uploaded-transcript-id>"],
  "audioFileIds": [],
  "meetingTitle": "Library Renovation Meeting"
}
```

The response contains job status and, when successful, an editable draft with title, summary, discussion topics, decisions, action items, uncertainties, and human-review limitations. Items should be grounded in transcript content; owner/date information is not invented. Text transcript formats depend on the extractor and upload validation. Audio processing is unavailable unless an audio provider is installed and configured.

### Read a job

- `GET /api/meetings/jobs/{job_id}` — retrieve a specific job and its saved draft.
- `GET /api/meetings/jobs/latest` — retrieve the most recent job for restoring the workspace.

### Save draft edits

`PUT /api/meetings/jobs/{job_id}/draft`

```json
{
  "draft": {
    "title": "Library Renovation Meeting",
    "summary": "<edited summary>",
    "discussions": [],
    "decisions": [],
    "actionItems": [],
    "uncertainties": []
  }
}
```

The service validates and persists the draft in SQLite. Refresh restoration depends on the job ID stored by the frontend and the latest-job endpoint.

## Scope and errors

Modules 01 ChangeLens and 03 IndicShield do not have processing endpoints in this backend. API errors use HTTP status codes and a `detail` or job `error` message; do not expose credentials, raw secrets, or private source text in logs or public error pages.
