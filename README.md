# SYNORA

SYNORA is a React and TypeScript frontend prototype for five institutional document workflows: document comparison, knowledge retrieval, sensitive-information review, translation, and meeting minutes. The interface is designed to keep each tool independent and make review part of the workflow.

## Requirements

- Node.js and npm
- A modern browser

## Setup

Clone the repository and install the locked dependencies:

```bash
git clone https://github.com/<your-github-username>/Synora.git
cd Synora
npm ci
```

Start the development server:

```bash
npm run dev
```

Open the local URL printed by Vite in your terminal. To verify a production build and serve it locally:

```bash
npm run build
npm run preview
```

## Use

1. From the landing page, choose **Explore the suite** or open one of the five capabilities.
2. Review the illustrative workflow, then continue to that tool's workspace.
3. Select supported source files where the workspace provides a file queue. Files are selected in the browser; you can remove them before leaving the page.
4. Use the available fields and controls to prepare the task. Navigation controls let you return to the suite or landing page.

The five tools are:

- **ChangeLens** compares two document versions.
- **Institutional RAG** presents a document-grounded question and answer workflow.
- **IndicShield** presents a sensitive-information review workflow.
- **IndicTranslate** presents a reviewable translation workflow.
- **Meeting Minutes** presents a recording or transcript to minutes workflow.

## Processing and privacy boundary

This repository contains the frontend only. File selection is local to the browser session: the current app does not upload, parse, compare, index, translate, transcribe, redact, generate, or export document contents. Actions that require processing explain that a server-side provider must be configured. The workflow diagrams are illustrative and are not evidence that a task has been processed.

Before connecting a backend, review [API_CONTRACTS.md](API_CONTRACTS.md) for the expected service boundaries and [COMPLIANCE_AUDIT.md](COMPLIANCE_AUDIT.md) for known implementation limits and verification gaps. Do not treat this prototype as a production document-processing or security service.

## Project commands

| Command | Purpose |
| --- | --- |
| `npm run dev` | Start the Vite development server. |
| `npm run build` | Type-check and create the production build in `dist/`. |
| `npm run preview` | Serve the production build locally. |

## Project structure

- `src/App.tsx` — page, workflow, file-selection, and workspace UI.
- `src/modules.ts` — module names, descriptions, and workflow content.
- `src/routing.ts` — hash-based navigation.
- `src/*.css` — application styling.
- `API_CONTRACTS.md` — proposed frontend/backend integration contracts.
- `COMPLIANCE_AUDIT.md` — preliminary frontend audit and open blockers.

## Development notes

Dependencies are pinned in `package-lock.json`; use `npm ci` for a reproducible install. There is currently no automated test script in `package.json`. A successful production build checks TypeScript compilation and Vite bundling, but does not verify backend behavior, accessibility, or browser rendering across devices.