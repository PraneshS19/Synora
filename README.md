# SYNORA

SYNORA is a React/TypeScript frontend and FastAPI backend prototype for institutional document workflows. This repository connects three modules to local backend services:

| Module | Capability | Current local behavior |
| --- | --- | --- |
| 01 ChangeLens | Compare document versions | Frontend prototype; backend processing is not implemented. |
| 02 Institutional RAG | Ask questions about a private document collection | Local text extraction, retrieval, grounded answers, citations, and an insufficient-evidence guard. |
| 03 IndicShield | Review sensitive information | Frontend prototype; backend processing is not implemented. |
| 04 IndicTranslate | Translate and review text | Optional local IndicTrans2 provider for **English → supported Indic languages**; without a model, drafts are blank and manually editable. |
| 05 Meeting Minutes | Draft minutes from transcripts | Local transcript extraction and evidence-based draft; edits persist. Audio transcription is not configured by default. |

This is a development/demo project, not a production document-processing or security service. See [COMPLIANCE_AUDIT.md](COMPLIANCE_AUDIT.md) for boundaries and remaining work.

## Requirements

- Windows 10/11, macOS, or Linux
- Node.js and npm
- Python 3.11 or later
- A modern browser

The optional local translation model requires additional Python packages and model weights. No paid API, billing account, or API key is needed for the default local RAG and transcript workflows.

## Quick start — Windows PowerShell

Run the backend and frontend in **two separate PowerShell windows**. Commands below assume you are in the repository root.

### 1. Get the project and install frontend packages

If you are cloning the handoff branch before it is merged:

```powershell
git clone --branch synora-backend-handoff https://github.com/PraneshS19/Synora.git
cd Synora
```

For the default branch after the handoff is merged, use `git clone https://github.com/PraneshS19/Synora.git` instead.

In the repository root, install the locked frontend dependencies:

```powershell
npm ci
```

### 2. Set up and start the backend

In **PowerShell window 1**, from the repository root:

```powershell
cd backend
python -m venv .venv
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

Keep this window open. Wait for Uvicorn to report that it is running at `http://127.0.0.1:8000` and that application startup is complete. You can check the health endpoint at [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health) or interactive API documentation at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

The default `.env.example` selects local RAG, manual translation mode, and no audio provider. Keep `.env` private; it is excluded from Git.

### 3. Start the frontend

In **PowerShell window 2**, return to the repository root if needed, then run:

```powershell
npm run dev
```

Open the local URL Vite prints, normally [http://localhost:5173](http://localhost:5173). The Vite development server forwards `/api` requests to the backend at `127.0.0.1:8000`.

If the app reports **Bad Gateway**, check that the backend window is still running. In a new PowerShell window, return to the repository root, run `cd backend`, then start it with `.\.venv\Scripts\python.exe run.py`.

## Local workflows

### Institutional RAG

- Accepts supported document files through the upload workflow; files are stored in the backend's local data directory, not served from the frontend.
- The default local embedding and extractive answer providers require no API key.
- Answers include inspectable evidence when retrieved passages support them. If the collection lacks evidence, the system should decline to answer and return no citations.
- Collections are isolated by collection ID and record their embedding configuration. Changing embedding provider/dimensions may require re-indexing.

### IndicTranslate

- Without a configured translation model, SYNORA deliberately returns blank translation drafts marked as unconfigured; the user may enter and save a translation manually.
- The optional IndicTrans2 English-to-Indic distilled checkpoint has been exercised locally with English source text and seven targets: Tamil, Hindi, Telugu, Kannada, Malayalam, Bengali, and Marathi. Machine output remains unreviewed until a human edits or approves it.
- The tested local model weights are **not included** in this repository. They occupy about 1.1 GB in the reported local cache. Installing PyTorch for GPU may add several GB of downloads. Exact package and disk requirements depend on the platform and PyTorch build.
- The tested machine used a Hugging Face mirror cache. Before redistribution or institutional use, verify the model files against AI4Bharat's official checkpoint and license. The upstream IndicTrans2 checkpoint is listed as MIT-licensed by AI4Bharat. Model quality still requires review by a fluent human.
- This integrated checkpoint is for English → Indic; other source-language directions are not supported by the tested configuration.

Optional setup outline (requires internet to install packages and fetch weights; inference is local afterward):

1. Install a PyTorch build appropriate for your Python version and CPU/GPU from the [official PyTorch installation selector](https://pytorch.org/get-started/locally/).
2. In the backend virtual environment, install the translation dependencies required by the provider, including `transformers`, `sentencepiece`, `huggingface-hub`, and `IndicTransToolkit`.
3. Obtain any required Hugging Face access for the official model, then download `ai4bharat/indictrans2-en-indic-dist-200M`. Keep any Hugging Face token out of source files, `.env`, screenshots, and chat messages.
4. Set `TRANSLATION_PROVIDER=indictrans2` and `INDICTRANS2_EN_INDIC_MODEL=ai4bharat/indictrans2-en-indic-dist-200M` in `backend/.env`, then restart the backend.
5. Run the live provider test and verify output in the UI before relying on it.

Do not install model weights automatically as part of the base setup. Review current upstream instructions before installing optional packages; Windows/Python support can change.

### Meeting Minutes

- Text transcripts (`.txt`, `.docx`, `.pdf`, `.vtt`, and `.srt`, subject to the upload validation) can be processed locally.
- The deterministic draft includes a summary, grouped discussions, decisions, action items, and uncertainties only when supported by transcript evidence. Owners and deadlines are not invented.
- Draft fields can be edited and saved to the local SQLite database; the latest job can be restored after a page reload.
- Audio transcription is **not enabled by default**. It requires a local speech-to-text provider such as Whisper and FFmpeg. Without those configured, audio should report that transcription is unavailable; no audio model is bundled.

## Storage and privacy

The backend stores uploads and SQLite data under `backend/data/` by default. This is local development storage, not encrypted multi-user storage. There is no authentication, authorization, institutional SSO, tenant boundary, automatic retention policy, or production-grade deletion mechanism. Do not use sensitive real institutional documents or expose the development servers to a public network.

Local mode avoids sending document contents to a cloud model. If someone configures an external provider, review that provider's data handling, terms, cost, and configuration before sending any content.

## Verification commands

From the repository root:

```powershell
npm run build
```

From the `backend` directory:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_api.py -v
.\.venv\Scripts\python.exe -m pytest tests\test_live_providers.py -v
```

The local API suite is designed to run without cloud keys. Live provider tests may skip when optional providers are not configured. The reported Windows verification was: frontend build passed; backend API suite **20 passed**; IndicTrans2 GPU smoke test passed; Gemini and Whisper checks skipped (Gemini access not configured; FFmpeg/audio provider unavailable). These are local demo checks, not production certification.

## Project map

- `src/` — React application and styles.
- `backend/app/main.py` — FastAPI routes.
- `backend/app/services/` — storage, extraction, RAG, translation job, and minutes logic.
- `backend/app/providers/` — local and optional model provider adapters.
- `backend/tests/` — backend API and optional live-provider tests.
- `backend/.env.example` — safe configuration template; copy to `.env` for local settings.
- `API_CONTRACTS.md` — implemented API endpoints and payload shapes.
- `COMPLIANCE_AUDIT.md` — scope, reported checks, and remaining production gaps.

## License and model notices

The repository's source license and the model checkpoints/dependencies have separate license terms. Check each upstream license before redistribution or commercial/institutional deployment. Human review is required for machine translation and generated meeting minutes.
