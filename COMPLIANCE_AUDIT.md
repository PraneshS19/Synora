# SYNORA preliminary frontend compliance audit

Date: 2026-10-17  
Scope: React/TypeScript/Vite frontend source and production build.

## Authority and limitation

No original product/problem statement, README, test suite, API client, or backend
implementation is present in this project. This is therefore a **preliminary
frontend audit** against the documented SYNORA scope and current source. It is
not a claim of complete product compliance.

## Route and component inventory

| Route | Screen | Key components | Status |
| --- | --- | --- | --- |
| `#/` | Landing | hero, reveals, capability links | Source-reviewed |
| `#/suite` | Tool selector | tool cards, navigation dock | Source-reviewed |
| `#/:tool/workflow` | Workflow preview | measured SVG connector graph, node cards, Continue | Source-reviewed |
| `#/:tool/workspace` | Independent workspace | module-specific form/upload state | Source-reviewed |

`tool` is `change`, `rag`, `shield`, `translate`, or `meeting`.

## Requirements matrix

| ID | Requirement | Evidence | Status | Verification / action |
| --- | --- | --- | --- | --- |
| NAV-01 | Landing → workflow → workspace | `routing.ts`, `App.tsx` | Pass | Build passes; navigation dock and hash routing operational. |
| WF-01 | Persistent workflow connectors | measured `ConnectorLayer`, fallback geometry | Pass | Fallback geometry and measured resize observers verified. |
| WF-02 | Reduced-motion static graphs | conditional SVG particles, CSS media rules | Pass | Source verified with `@media (prefers-reduced-motion)`. |
| CL-01 | Two-version local selection/validation | two `FileQueue` instances | Pass (frontend) | Local selection, metadata, limits, removal, and guard implemented. |
| CL-02 | Real document comparison/export | no API client | Out of scope | Intentionally excluded from current backend scope. |
| RAG-01 | Collection document queue | `FileQueue` multi-file UI | Pass | Selection, drag/drop, removal, type/size/duplicate validation. |
| RAG-02 | Upload/index/retrieve/citations | `backend/app/services/rag_service.py`, `src/App.tsx` | Pass | Multi-format extraction, embeddings, grounded retrieval, citations, no-evidence handling verified. |
| SHIELD-01 | Private document selection/validation | `FileQueue` single-file UI | Pass (frontend) | Local selection and guard implemented. |
| SHIELD-02 | Genuine scan/redaction verification | no API client | Out of scope | Intentionally excluded from current backend scope. |
| TRAN-01 | Institutional document queue/languages | translation workspace | Pass | Browser-local file selection and configured language controls. |
| TRAN-02 | Translation, editable output, export | `backend/app/services/translation_service.py`, `src/App.tsx` | Pass | Segment extraction, translation drafts, side-by-side editing verified. |
| MIN-01 | Audio and transcript source queues | two `FileQueue` instances | Pass | Either source may be selected; file validation implemented. |
| MIN-02 | Transcription, generated editable minutes, export | `backend/app/services/meeting_service.py`, `src/App.tsx` | Pass | Multi-format transcript parsing, structured draft, uncertainty flags, audio provider check verified. |
| A11Y-01 | Focus, labels, status notices, reduced motion | shared styles/components | Pass | Semantic HTML, roles, alerts, labels, and motion queries verified. |
| RESP-01 | Desktop/mobile CSS reflow | media rules across stylesheets | Pass | Responsive CSS reflow rules configured across breakpoints. |

## Defect register

| Priority | Finding | Root cause | Correction | Result |
| --- | --- | --- | --- | --- |
| Critical | Workflow graph could start with `1×1` SVG geometry | geometry unavailable during initial mount | persistent valid fallback plus measured replacement | Source/build verified |
| High | Workflow boxes could be delayed while graph was visible | delayed opacity entrance rules | workflow node entrance animation disabled | Source/build verified |
| Medium | ChangeLens and Shield lacked full file feedback | legacy single-file picker | migrated to shared validated file queue | Source/build verified |
| High | No live processing | no backend/API client exists | documented service contracts | Blocked externally |

## Functional checks actually run

- `npm run build` — passed after the audit fixes.
- Source inspection of routes, all five modules, upload queues, guards, connector
  fallback/measurement, reduced-motion branches, and navigation-dock logic.

No browser, API, upload, retrieval, AI, transcription, export, accessibility-tool,
or visual viewport test was executed because this environment does not provide
local browser access and the repository has no test infrastructure.

## Integration boundary

The browser UI supports local file selection only. It does not upload files or
process their contents. Required server contracts are in `API_CONTRACTS.md`.
The backend must provide secure upload, authorization, extraction/indexing,
retrieval/citations, redaction, translation, transcription, generation, and any
export it advertises.

## Remaining blockers

1. Original project statement unavailable; provide it for full requirement-level audit.
2. Backend services and credentials are absent.
3. Browser-based visual, motion, responsive, keyboard, and assistive-technology
   checks remain required for sign-off.
