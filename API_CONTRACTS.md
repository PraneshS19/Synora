# SYNORA integration contracts

This document details the implemented REST integration contracts connecting the SYNORA frontend with the FastAPI backend services for **Institutional RAG (02)**, **IndicTranslate (04)**, and **ForumNotes (05)**.

Selected files remain in the browser until the user triggers a task. Modules 01 (ChangeLens) and 03 (IndicShield) remain in prototype mode with clear notices that server providers are required.

---

## Health Check

`GET /api/health`

- **Purpose**: Verify backend service liveness, module readiness, and active provider configuration.
- **Response**:
  ```json
  {
    "status": "ok",
    "version": "1.0.0",
    "modules": ["rag", "translate", "meeting"],
    "providers": {
      "embeddings": "local",
      "llm": "local",
      "translation": "local",
      "audio": "none"
    }
  }
  ```

---

## Shared Upload

`POST /api/uploads`

- **Content-Type**: `multipart/form-data`
- **Request Fields**:
  - `files`: One or more files.
  - `module`: Target module string (`"rag"`, `"translate"`, `"meeting"`, `"change"`, `"shield"`).
- **Validation**:
  - Validates extension, file size (up to 20MB for documents, up to 200MB for audio), MIME type, and magic bytes (PDF header `%PDF-`, DOCX ZIP header `PK\x03\x04`, WAV/MP3/M4A audio headers, text encoding).
  - Generates secure internal UUIDs and stores files in a private directory outside web roots.
- **Response**:
  ```json
  {
    "files": [
      {
        "id": "7dfb642a-9cb8-4e89-8b06-03f16952d73f",
        "name": "Academic_Calendar_2026.pdf",
        "mimeType": "application/pdf",
        "size": 142080,
        "status": "ready",
        "module": "rag"
      }
    ]
  }
  ```

---

## Institutional RAG (Module 02)

### Create Collection
`POST /api/rag/collections`

- **Request**:
  ```json
  {
    "name": "Admissions Regulations",
    "fileIds": ["7dfb642a-9cb8-4e89-8b06-03f16952d73f"]
  }
  ```
- **Processing**: Extracts document passages, preserves page and section numbers, generates vector embeddings via configured `EmbeddingProvider`, and indexes passages in SQLite/vector store.
- **Response**:
  ```json
  {
    "id": "col-uuid",
    "name": "Admissions Regulations",
    "status": "ready",
    "fileCount": 1,
    "chunkCount": 14,
    "embeddingProvider": "local",
    "embeddingDim": 256
  }
  ```

### Get Collection
`GET /api/rag/collections/:id`

- **Response**: Current collection status, embedding metadata, and chunk metrics.

### Query Collection
`POST /api/rag/collections/:id/questions`

- **Request**:
  ```json
  {
    "question": "When does the admissions portal close?"
  }
  ```
- **Dimension Compatibility Guard**: Returns `409 Conflict` if the stored collection's vector dimension differs from the currently configured `EMBEDDING_PROVIDER`.
- **Response (Evidence Found)**:
  ```json
  {
    "answer": "The annual student admissions portal opens on July 15 and closes on August 30.",
    "citations": [
      {
        "fileId": "7dfb642a-9cb8-4e89-8b06-03f16952d73f",
        "name": "Academic_Calendar_2026.pdf",
        "page": 4,
        "section": "Page 4",
        "excerpt": "Section 4: The annual student admissions portal opens on July 15 and closes on August 30."
      }
    ],
    "evidenceFound": true,
    "providerUsed": "LocalExtractiveLLMProvider"
  }
  ```
- **Response (No Evidence Found)**:
  ```json
  {
    "answer": "No sufficient evidence was found in the private collection to answer this question.",
    "citations": [],
    "evidenceFound": false,
    "providerUsed": "LocalEmbeddingProvider"
  }
  ```

---

## IndicTranslate (Module 04)

### Create Translation Job
`POST /api/translate/jobs`

- **Request**:
  ```json
  {
    "fileIds": ["file-uuid"],
    "sourceText": "Optional direct passage if no file uploaded",
    "sourceLanguage": "English",
    "targetLanguage": "Tamil"
  }
  ```
- **Response**:
  ```json
  {
    "id": "job-uuid",
    "status": "completed",
    "sourceLanguage": "English",
    "targetLanguage": "Tamil",
    "segments": [
      {
        "id": "seg-1",
        "source": "The academic council approved the new admissions policy for the institution.",
        "translated": "கல்விசார் மன்றம் நிறுவனம் மாணவர் சேர்க்கை கொள்கை ஒப்புதல் அளித்தது.",
        "reviewFlag": "unreviewed",
        "confidence": 0.92
      }
    ],
    "limitations": [
      "Machine translation draft. Human review required before institutional publication."
    ]
  }
  ```

### Get Translation Job
`GET /api/translate/jobs/:id`

- Returns job status, segment pairs, and limitations.

### Update Translation Segment (Human Review)
`PUT /api/translate/jobs/:id/segments/:segment_id`

- **Request**:
  ```json
  {
    "translated": "கல்விசார் மன்றம் புதிய சேர்க்கைக் கொள்கைக்கு ஒப்புதல் அளித்தது.",
    "reviewFlag": "edited"
  }
  ```
- **Response**: Updated `TranslationJobResponse`.

---

## ForumNotes (Module 05)

### Transcribe Audio Recording
`POST /api/meetings/transcribe`

- **Request**:
  ```json
  {
    "audioFileId": "audio-file-uuid"
  }
  ```
- **Processing**:
  - Transcribes audio locally using OpenAI Whisper (`WHISPER_DEVICE=auto|cuda|cpu`).
  - Preserves segment timestamps `[MM:SS - MM:SS]`.
  - Rejects empty recordings or unsupported audio with clear error messages.
  - Never invents fictional speaker names (no unverified diarization).
- **Response**:
  ```json
  {
    "transcript": "[00:00 - 00:20]: Good morning everyone. We are starting the review.\n[00:20 - 00:50]: We agreed to organize the technical workshop on 14 November 2026.",
    "audioFileName": "workshop_recording.mp3",
    "providerUsed": "whisper"
  }
  ```

### Create Meeting Job
`POST /api/meetings/jobs`

- **Request**:
  ```json
  {
    "transcriptFileIds": ["transcript-file-uuid"],
    "audioFileIds": ["audio-file-uuid"],
    "rawTranscriptText": "[00:00 - 00:20]: Dr. Raman: Good morning everyone...",
    "meetingTitle": "Academic Council Review"
  }
  ```
- **Processing**:
  - If `rawTranscriptText` is supplied, generates draft minutes directly from user-reviewed/edited transcript.
  - If transcript file uploaded: extracts timestamps, dialogue, and sections.
  - If audio uploaded: transcribes audio locally with Whisper and preserves segment timestamps.
  - Generates structured draft containing only source-supported content.
- **Response (Completed)**:
  ```json
  {
    "id": "meeting-job-uuid",
    "status": "completed",
    "source": "audio",
    "transcript": "[00:00 - 00:20]: Good morning everyone...",
    "audioFileName": "workshop_recording.mp3",
    "draft": {
      "title": "Academic Council Review",
      "summary": "Meeting proceedings recorded from transcript.",
      "discussions": [
        {
          "topic": "Admissions Calendar Review",
          "points": ["Reviewed proposed timeline for 2026."],
          "timestamp": "00:01:20"
        }
      ],
      "decisions": [
        {
          "decision": "Academic council approved the revised timeline.",
          "status": "agreed",
          "evidence": "Identified in transcript"
        }
      ],
      "actionItems": [
        {
          "task": "Dr. Sharma will prepare the portal guidelines by next week.",
          "owner": "Dr. Sharma",
          "dueDate": "next week",
          "uncertain": false
        },
        {
          "task": "Someone should check the server bandwidth.",
          "owner": null,
          "dueDate": null,
          "uncertain": true
        }
      ],
      "uncertainties": [
        "Uncertain owner/deadline for action: 'Someone should check the server bandwidth…'"
      ]
    },
    "limitations": [
      "Generated draft requires human review. Action owners and deadlines are included only when explicitly stated in source."
    ]
  }
  ```

### List Saved ForumNotes Drafts
`GET /api/meetings/jobs`

- **Purpose**: Retrieve a list of all saved ForumNotes drafts, ordered by last updated date descending.
- **Response**: Array of `MeetingJobResponse` objects with `createdAt`, `updatedAt`, `draft`, `transcript`, and `source`.

### Get Meeting Job
`GET /api/meetings/jobs/:id`

- Returns meeting job status, timestamps, and current draft.

### Download ForumNotes DOCX
`GET /api/meetings/jobs/:id/download`

- **Purpose**: Export the draft as a formatted institutional `.docx` document containing the latest saved edits (Title, Summary, Discussion Topics, Formal Decisions Table, Action Items Table with Owners & Deadlines, and Uncertainties).
- **Response**: Binary `.docx` stream with `Content-Disposition: attachment; filename="<title>.docx"`.

### Update Meeting Draft
`PUT /api/meetings/jobs/:id/draft`

- **Request**:
  ```json
  {
    "draft": { "...": "updated draft object" }
  }
  ```
- **Response**: Updated `MeetingJobResponse`.
