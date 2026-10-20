# SYNORA local demo — scope and compliance notes

**Status date:** 2026-10-20
**Scope:** frontend and local FastAPI workflows for Institutional RAG (02), IndicTranslate (04), and Meeting Minutes (05).

This is a prototype audit, not legal advice, a security certification, or approval for production processing of institutional data.

## Functional scope

| Module | Current implementation | Important boundary |
| --- | --- | --- |
| 01 ChangeLens | Frontend workflow/prototype | No document comparison backend. |
| 02 Institutional RAG | Local upload, extraction, collection indexing, retrieval, answer, evidence citations, and insufficient-evidence response | Local vectorizer/extractive answering are not equivalent to a validated institutional search system. External providers are optional and require separate configuration. |
| 03 IndicShield | Frontend workflow/prototype | No sensitive-information scanning or redaction backend. Do not rely on it to detect or remove personal data. |
| 04 IndicTranslate | Editable review workflow; optional IndicTrans2 provider | Tested configuration supports English source to the seven UI target languages. Other source directions are not verified/supported. Human review is required. Local manual mode does not automatically translate. |
| 05 Meeting Minutes | Local text-transcript extraction, structured editable draft, action/decision/uncertainty handling, and SQLite persistence | Audio transcription is disabled unless an audio provider and FFmpeg are configured. Drafts can contain extraction mistakes and require human review. |

## Local processing and data handling

- Default RAG and transcript workflows run locally. The optional IndicTrans2 weights are downloaded separately and are not in Git.
- The backend stores uploaded files and job/collection data in `backend/data/` by default. Treat this as ordinary local development storage; no encryption-at-rest or managed retention schedule is provided.
- No authentication, authorization, SSO, role-based access control, or multi-tenant user isolation is implemented. Random IDs are not an authorization boundary.
- The development server and Vite proxy are intended for localhost only. Do not expose them to the public internet.
- No data deletion/retention UI or secure erasure guarantees are implemented.
- External providers, if enabled, may receive document text. Review provider terms, privacy, cost, region, and applicable institutional approvals before use.
- API keys, Hugging Face tokens, `.env`, virtual environments, model caches, uploaded documents, and SQLite databases must not be committed.

## Model and output safeguards

- RAG answers should be supported by citations to retrieved source passages. When evidence is insufficient, the expected response is a refusal with no citations rather than a fabricated answer.
- IndicTrans2 output is machine-generated, remains unreviewed by default, and is not an authoritative translation. The local checkpoint used in the reported demo was cached from a Hugging Face mirror; verify the artifact against the official AI4Bharat checkpoint before distributing weights or using it institutionally.
- Meeting minutes are an extractive/deterministic draft. Verify names, dates, decisions, action assignments, and summary against the original transcript.
- Audio transcription is not available in the default configuration. The application must not imply that an audio file was transcribed when no audio provider is active.
- ChangeLens and IndicShield are prototypes and must not be represented as operational backend services.

## Verification reported for the local Windows demo

The following results were provided from the developer's local machine on 2026-10-20; they are not continuous integration results and have not been independently reproduced on every platform:

| Check | Reported result | Notes |
| --- | --- | --- |
| `npm run build` | Passed | TypeScript and Vite production build. |
| `python -m pytest tests/test_api.py -v` | 20 passed | Local API tests include RAG evidence/insufficient evidence, translation configuration paths, transcript drafting, and draft persistence. |
| IndicTrans2 live smoke test | Passed | GPU inference produced Tamil, Hindi, and Telugu output; the developer also manually verified all seven UI target languages. |
| Gemini live test | Skipped/unavailable | The Google project required billing; the project is being kept in no-paid-API mode. |
| Whisper live test | Skipped | FFmpeg/audio model setup is absent; audio transcription is not verified. |

Run the checks on the current checkout before relying on future changes. A successful test suite does not establish translation quality, accessibility conformance, security, or production readiness.

## Production blockers

Before processing real or sensitive institutional documents, the project needs, at minimum:

1. Authentication and authorization, with tenant-scoped access checks for every file, collection, and job.
2. A documented retention policy, deletion workflow, backups, and protected storage.
3. Security review of file parsing, model loading, dependency provenance, and upload limits; isolate parsers and model inference in appropriately constrained workers.
4. Operational controls such as TLS, secrets management, rate limits, monitoring, audit logs, and deployment-specific CORS configuration.
5. Quality evaluation with representative documents, fluent human reviewers for translation, and checks for fabricated or omitted content in minutes and RAG answers.
6. A production database and migration/backup plan if concurrent multi-user operation is required.

Until these controls are designed, tested, and approved, treat SYNORA as a local demo only.
